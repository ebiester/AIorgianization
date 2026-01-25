"""Daemon client for CLI communication.

This module provides a thin client that communicates with the AIO daemon
over a Unix socket using JSON-RPC 2.0 protocol.
"""

import json
import socket
import struct
from pathlib import Path
from typing import Any, cast


class DaemonError(Exception):
    """Error communicating with the daemon."""

    def __init__(self, message: str, code: int | None = None) -> None:
        """Initialize the error.

        Args:
            message: Error message.
            code: Optional error code from daemon.
        """
        super().__init__(message)
        self.code = code


class DaemonUnavailableError(DaemonError):
    """Daemon is not running or unreachable."""

    pass


class DaemonClient:
    """Client for communicating with the AIO daemon.

    Uses length-prefixed JSON-RPC over Unix socket for fast IPC.
    Protocol: 4-byte big-endian length prefix + JSON payload.

    Example:
        client = DaemonClient()
        if client.is_running():
            result = client.call("list_tasks", {"status": "inbox"})
            print(result["tasks"])
    """

    # Wire format: 4-byte big-endian unsigned int length prefix
    LENGTH_PREFIX_FORMAT = ">I"
    LENGTH_PREFIX_SIZE = 4
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, socket_path: Path | None = None) -> None:
        """Initialize the daemon client.

        Args:
            socket_path: Path to the daemon socket. Defaults to ~/.aio/daemon.sock.
        """
        if socket_path is None:
            socket_path = Path.home() / ".aio" / "daemon.sock"
        self._socket_path = socket_path
        self._request_id = 0

    @property
    def socket_path(self) -> Path:
        """Get the socket path."""
        return self._socket_path

    def is_running(self) -> bool:
        """Check if the daemon is running and reachable.

        Attempts a quick health check by connecting to the socket.

        Returns:
            True if daemon is reachable, False otherwise.
        """
        if not self._socket_path.exists():
            return False

        try:
            # Quick connection test
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # 500ms timeout for health check
            sock.connect(str(self._socket_path))
            sock.close()
            return True
        except OSError:
            return False

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 5.0,
    ) -> Any:
        """Call a method on the daemon.

        Args:
            method: The JSON-RPC method name.
            params: Optional parameters for the method.
            timeout: Socket timeout in seconds.

        Returns:
            The result from the daemon.

        Raises:
            DaemonUnavailableError: If daemon is not running.
            DaemonError: If daemon returns an error.
        """
        if not self._socket_path.exists():
            raise DaemonUnavailableError("Daemon socket not found")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        try:
            # Connect to daemon
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect(str(self._socket_path))

            try:
                # Send request
                self._send_message(sock, request)

                # Receive response
                response = self._receive_message(sock)
            finally:
                sock.close()

        except FileNotFoundError as e:
            raise DaemonUnavailableError("Daemon socket not found") from e
        except ConnectionRefusedError as e:
            raise DaemonUnavailableError("Daemon refused connection") from e
        except TimeoutError as e:
            raise DaemonError("Daemon request timed out") from e
        except OSError as e:
            raise DaemonUnavailableError(f"Failed to connect to daemon: {e}") from e

        # Check for JSON-RPC error
        if "error" in response:
            error = response["error"]
            raise DaemonError(
                error.get("message", "Unknown error"),
                code=error.get("code"),
            )

        return response.get("result")

    def _send_message(self, sock: socket.socket, data: dict[str, Any]) -> None:
        """Send a length-prefixed JSON message.

        Args:
            sock: Connected socket.
            data: Data to serialize and send.
        """
        json_bytes = json.dumps(data).encode("utf-8")
        length_prefix = struct.pack(self.LENGTH_PREFIX_FORMAT, len(json_bytes))
        sock.sendall(length_prefix + json_bytes)

    def _receive_message(self, sock: socket.socket) -> dict[str, Any]:
        """Receive a length-prefixed JSON message.

        Args:
            sock: Connected socket.

        Returns:
            Parsed JSON response.

        Raises:
            DaemonError: If message is malformed or too large.
        """
        # Read length prefix
        length_data = self._recv_exact(sock, self.LENGTH_PREFIX_SIZE)
        (message_length,) = struct.unpack(self.LENGTH_PREFIX_FORMAT, length_data)

        # Validate size
        if message_length > self.MAX_MESSAGE_SIZE:
            raise DaemonError(f"Response too large: {message_length} bytes")

        # Read message body
        message_data = self._recv_exact(sock, message_length)

        # Parse JSON
        try:
            return cast(dict[str, Any], json.loads(message_data.decode("utf-8")))
        except json.JSONDecodeError as e:
            raise DaemonError(f"Invalid JSON response: {e}") from e

    def _recv_exact(self, sock: socket.socket, size: int) -> bytes:
        """Receive exactly the specified number of bytes.

        Args:
            sock: Connected socket.
            size: Number of bytes to receive.

        Returns:
            Received bytes.

        Raises:
            DaemonError: If connection closed before receiving all bytes.
        """
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise DaemonError("Connection closed unexpectedly")
            data += chunk
        return data

    # Convenience methods for common operations

    def list_tasks(
        self,
        status: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status (inbox, next, waiting, etc.).
            project: Filter by project name.

        Returns:
            Dict with 'tasks' list and 'count'.
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if project:
            params["project"] = project
        return cast(dict[str, Any], self.call("list_tasks", params))

    def get_task(self, query: str) -> dict[str, Any]:
        """Get a task by ID or query.

        Args:
            query: Task ID or title substring.

        Returns:
            Dict with 'task'.
        """
        return cast(dict[str, Any], self.call("get_task", {"query": query}))

    def add_task(
        self,
        title: str,
        due: str | None = None,
        project: str | None = None,
        status: str | None = None,
        assign: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task.

        Args:
            title: Task title.
            due: Optional due date (natural language).
            project: Optional project name or link.
            status: Optional initial status.
            assign: Optional person to assign/delegate to.

        Returns:
            Dict with 'task'.
        """
        params: dict[str, Any] = {"title": title}
        if due:
            params["due"] = due
        if project:
            params["project"] = project
        if status:
            params["status"] = status
        if assign:
            params["assign"] = assign
        return cast(dict[str, Any], self.call("add_task", params))

    def complete_task(self, query: str) -> dict[str, Any]:
        """Mark a task as complete.

        Args:
            query: Task ID or title substring.

        Returns:
            Dict with 'task'.
        """
        return cast(dict[str, Any], self.call("complete_task", {"query": query}))

    def start_task(self, query: str) -> dict[str, Any]:
        """Move a task to Next status.

        Args:
            query: Task ID or title substring.

        Returns:
            Dict with 'task'.
        """
        return cast(dict[str, Any], self.call("start_task", {"query": query}))

    def defer_task(self, query: str) -> dict[str, Any]:
        """Move a task to Someday status.

        Args:
            query: Task ID or title substring.

        Returns:
            Dict with 'task'.
        """
        return cast(dict[str, Any], self.call("defer_task", {"query": query}))

    def delegate_task(self, query: str, person: str) -> dict[str, Any]:
        """Delegate a task to a person.

        Args:
            query: Task ID or title substring.
            person: Person name or ID.

        Returns:
            Dict with 'task' and 'delegated_to'.
        """
        return cast(dict[str, Any], self.call("delegate_task", {"query": query, "person": person}))

    def get_dashboard(self, date: str | None = None) -> dict[str, Any]:
        """Get the daily dashboard.

        Args:
            date: Optional date (YYYY-MM-DD format).

        Returns:
            Dict with 'content' and 'date'.
        """
        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        return cast(dict[str, Any], self.call("get_dashboard", params))

    def list_projects(self, status: str | None = None) -> dict[str, Any]:
        """List projects.

        Args:
            status: Optional status filter.

        Returns:
            Dict with 'projects' and 'count'.
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        return cast(dict[str, Any], self.call("list_projects", params))

    def list_people(self) -> dict[str, Any]:
        """List people.

        Returns:
            Dict with 'people' and 'count'.
        """
        return cast(dict[str, Any], self.call("list_people", {}))
