"""Unix socket transport for the AIO daemon.

Uses length-prefixed JSON-RPC messages over a Unix domain socket.
Protocol: 4-byte big-endian length prefix followed by JSON payload.
"""

import asyncio
import contextlib
import json
import logging
import struct
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from aio.daemon.protocol import ErrorCode, JsonRpcRequest, JsonRpcResponse

logger = logging.getLogger(__name__)

# Message format: 4-byte big-endian length prefix + JSON payload
LENGTH_PREFIX_FORMAT = ">I"
LENGTH_PREFIX_SIZE = 4
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB max message size


class UnixSocketTransport:
    """Unix socket transport using length-prefixed JSON-RPC.

    The protocol uses a simple framing mechanism:
    - 4 bytes: message length (big-endian unsigned int)
    - N bytes: JSON-RPC message

    This allows for reliable message boundaries without delimiter parsing.
    """

    def __init__(
        self,
        socket_path: Path,
        handler: Callable[[JsonRpcRequest], Awaitable[JsonRpcResponse]],
    ) -> None:
        """Initialize the Unix socket transport.

        Args:
            socket_path: Path to the Unix domain socket.
            handler: Async function to handle incoming requests.
        """
        self._socket_path = socket_path
        self._handler = handler
        self._server: asyncio.Server | None = None
        self._clients: set[asyncio.Task[None]] = set()

    @property
    def socket_path(self) -> Path:
        """Get the socket path."""
        return self._socket_path

    @property
    def is_running(self) -> bool:
        """Check if the transport is running."""
        return self._server is not None and self._server.is_serving()

    async def start(self) -> None:
        """Start the Unix socket server.

        Creates the socket file and begins accepting connections.
        Sets socket permissions to owner-only (0o600) for security.
        """
        # Ensure parent directory exists
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing socket file if present
        if self._socket_path.exists():
            self._socket_path.unlink()

        # Create and start the server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self._socket_path),
        )

        # Set socket permissions to owner-only
        self._socket_path.chmod(0o600)

        logger.info("Unix socket listening at %s", self._socket_path)

    async def stop(self) -> None:
        """Stop the Unix socket server.

        Closes all client connections and removes the socket file.
        """
        if self._server is None:
            return

        # Stop accepting new connections
        self._server.close()
        await self._server.wait_closed()
        self._server = None

        # Cancel all client tasks
        for task in self._clients:
            task.cancel()

        # Wait for client tasks to complete
        if self._clients:
            await asyncio.gather(*self._clients, return_exceptions=True)
        self._clients.clear()

        # Remove socket file
        if self._socket_path.exists():
            self._socket_path.unlink()

        logger.info("Unix socket server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection.

        Args:
            reader: Stream reader for receiving data.
            writer: Stream writer for sending data.
        """
        peer = writer.get_extra_info("peername") or "unknown"
        logger.debug("Client connected: %s", peer)

        # Track this client task
        task = asyncio.current_task()
        if task:
            self._clients.add(task)

        try:
            while True:
                # Read message
                request_data = await self._read_message(reader)
                if request_data is None:
                    break  # Connection closed

                # Process request
                response = await self._process_request(request_data)

                # Send response
                await self._write_message(writer, response)

        except asyncio.CancelledError:
            logger.debug("Client connection cancelled: %s", peer)
        except Exception as e:
            logger.error("Error handling client %s: %s", peer, e)
        finally:
            # Clean up
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

            if task:
                self._clients.discard(task)
            logger.debug("Client disconnected: %s", peer)

    async def _read_message(self, reader: asyncio.StreamReader) -> bytes | None:
        """Read a length-prefixed message from the stream.

        Args:
            reader: Stream reader to read from.

        Returns:
            Message bytes, or None if connection closed.

        Raises:
            ValueError: If message is too large.
        """
        # Read length prefix
        length_data = await reader.read(LENGTH_PREFIX_SIZE)
        if len(length_data) < LENGTH_PREFIX_SIZE:
            return None  # Connection closed

        (message_length,) = struct.unpack(LENGTH_PREFIX_FORMAT, length_data)

        # Validate message size
        if message_length > MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {message_length} bytes")

        # Read message body
        message_data = await reader.read(message_length)
        if len(message_data) < message_length:
            return None  # Connection closed mid-message

        return message_data

    async def _write_message(self, writer: asyncio.StreamWriter, data: dict[str, Any]) -> None:
        """Write a length-prefixed JSON message to the stream.

        Args:
            writer: Stream writer to write to.
            data: Data to serialize and send.
        """
        # Serialize to JSON
        json_data = json.dumps(data).encode("utf-8")

        # Write length prefix and message
        length_prefix = struct.pack(LENGTH_PREFIX_FORMAT, len(json_data))
        writer.write(length_prefix + json_data)
        await writer.drain()

    async def _process_request(self, data: bytes) -> dict[str, Any]:
        """Process a request and return a response.

        Args:
            data: Raw request bytes.

        Returns:
            Response dictionary.
        """
        request_id: int | str | None = None

        try:
            # Parse JSON
            try:
                request_dict = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                return JsonRpcResponse.error_response(
                    ErrorCode.PARSE_ERROR,
                    f"Invalid JSON: {e}",
                ).to_dict()

            # Parse request
            try:
                request = JsonRpcRequest.from_dict(request_dict)
                request_id = request.id
            except ValueError as e:
                return JsonRpcResponse.error_response(
                    ErrorCode.INVALID_REQUEST,
                    str(e),
                    request_id=request_dict.get("id"),
                ).to_dict()

            # Handle request
            response = await self._handler(request)
            return response.to_dict()

        except Exception as e:
            logger.exception("Error processing request")
            return JsonRpcResponse.error_response(
                ErrorCode.INTERNAL_ERROR,
                str(e),
                request_id=request_id,
            ).to_dict()
