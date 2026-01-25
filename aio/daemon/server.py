"""AIO Daemon server orchestration.

Main entry point for the daemon that coordinates services, cache, and transports.
"""

import asyncio
import logging
import signal
from pathlib import Path
from typing import Any

from aio.daemon.cache import VaultCache
from aio.daemon.handlers import HandlerContext, dispatch_request
from aio.daemon.protocol import JsonRpcRequest, JsonRpcResponse
from aio.daemon.transports.http import HttpTransport
from aio.daemon.transports.unix_socket import UnixSocketTransport
from aio.services.context_pack import ContextPackService
from aio.services.dashboard import DashboardService
from aio.services.file import FileService
from aio.services.person import PersonService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService

logger = logging.getLogger(__name__)


class AioDaemon:
    """AIO daemon server.

    Coordinates services, cache, and transport layers to provide
    a unified interface for all AIO clients.
    """

    # Default paths and ports
    DEFAULT_SOCKET_PATH = Path.home() / ".aio" / "daemon.sock"
    DEFAULT_HTTP_HOST = "127.0.0.1"
    DEFAULT_HTTP_PORT = 7432

    def __init__(
        self,
        vault_path: Path | None = None,
        socket_path: Path | None = None,
        http_host: str | None = None,
        http_port: int | None = None,
        enable_http: bool = True,
        enable_socket: bool = True,
    ) -> None:
        """Initialize the daemon.

        Args:
            vault_path: Path to the Obsidian vault. If None, discovers automatically.
            socket_path: Path for Unix socket. If None, uses default.
            http_host: Host for HTTP server. If None, uses default.
            http_port: Port for HTTP server. If None, uses default.
            enable_http: Whether to start HTTP transport.
            enable_socket: Whether to start Unix socket transport.
        """
        self._vault_path = vault_path
        self._socket_path = socket_path or self.DEFAULT_SOCKET_PATH
        self._http_host = http_host or self.DEFAULT_HTTP_HOST
        self._http_port = http_port or self.DEFAULT_HTTP_PORT
        self._enable_http = enable_http
        self._enable_socket = enable_socket

        # Services (initialized on start)
        self._vault_service: VaultService | None = None
        self._task_service: TaskService | None = None
        self._project_service: ProjectService | None = None
        self._person_service: PersonService | None = None
        self._dashboard_service: DashboardService | None = None
        self._context_pack_service: ContextPackService | None = None
        self._file_service: FileService | None = None

        # Cache and transports
        self._cache: VaultCache | None = None
        self._socket_transport: UnixSocketTransport | None = None
        self._http_transport: HttpTransport | None = None

        # Handler context
        self._context: HandlerContext | None = None

        # State
        self._running = False
        self._shutdown_event: asyncio.Event | None = None

    @property
    def is_running(self) -> bool:
        """Check if the daemon is running."""
        return self._running

    @property
    def vault_path(self) -> Path | None:
        """Get the vault path."""
        return self._vault_service.vault_path if self._vault_service else None

    async def start(self) -> None:
        """Start the daemon.

        Initializes services, populates cache, and starts transports.
        """
        if self._running:
            logger.warning("Daemon is already running")
            return

        logger.info("Starting AIO daemon...")

        # Initialize services
        self._init_services()

        # Initialize and populate cache
        self._init_cache()
        logger.info("Populating cache...")
        await self._cache.refresh()  # type: ignore[union-attr]

        # Start file watcher
        self._cache.start()  # type: ignore[union-attr]

        # Create handler context
        self._context = HandlerContext(
            vault_service=self._vault_service,  # type: ignore[arg-type]
            task_service=self._task_service,  # type: ignore[arg-type]
            project_service=self._project_service,  # type: ignore[arg-type]
            person_service=self._person_service,  # type: ignore[arg-type]
            dashboard_service=self._dashboard_service,  # type: ignore[arg-type]
            context_pack_service=self._context_pack_service,  # type: ignore[arg-type]
            file_service=self._file_service,  # type: ignore[arg-type]
            cache=self._cache,  # type: ignore[arg-type]
        )

        # Start transports
        if self._enable_socket:
            await self._start_socket_transport()

        if self._enable_http:
            await self._start_http_transport()

        self._running = True
        self._shutdown_event = asyncio.Event()

        logger.info("AIO daemon started successfully")
        logger.info("  Vault: %s", self._vault_service.vault_path)  # type: ignore[union-attr]
        logger.info("  Cache: %d tasks loaded", self._cache.task_count)  # type: ignore[union-attr]
        if self._enable_socket:
            logger.info("  Unix socket: %s", self._socket_path)
        if self._enable_http:
            logger.info("  HTTP API: http://%s:%d", self._http_host, self._http_port)

    async def stop(self) -> None:
        """Stop the daemon.

        Stops transports, file watcher, and cleans up resources.
        """
        if not self._running:
            return

        logger.info("Stopping AIO daemon...")

        # Stop transports
        if self._socket_transport:
            await self._socket_transport.stop()
            self._socket_transport = None

        if self._http_transport:
            await self._http_transport.stop()
            self._http_transport = None

        # Stop file watcher
        if self._cache:
            self._cache.stop()

        # Signal shutdown
        if self._shutdown_event:
            self._shutdown_event.set()

        self._running = False
        logger.info("AIO daemon stopped")

    async def run_forever(self) -> None:
        """Run the daemon until interrupted.

        Blocks until shutdown is requested via signal or stop().
        """
        await self.start()

        if self._shutdown_event:
            await self._shutdown_event.wait()

    def health_check(self) -> dict[str, Any]:
        """Get health status of the daemon.

        Returns:
            Dictionary with health information.
        """
        status: dict[str, Any] = {
            "status": "healthy" if self._running else "stopped",
            "vault": str(self._vault_service.vault_path) if self._vault_service else None,
        }

        if self._cache:
            status["cache"] = self._cache.get_stats()

        if self._socket_transport:
            status["socket"] = {
                "path": str(self._socket_path),
                "running": self._socket_transport.is_running,
            }

        if self._http_transport:
            status["http"] = {
                "url": self._http_transport.url,
                "running": self._http_transport.is_running,
            }

        return status

    def _init_services(self) -> None:
        """Initialize service layer."""
        # Create vault service
        self._vault_service = VaultService(self._vault_path)

        # Verify vault is accessible and initialized
        self._vault_service.ensure_initialized()

        # Create dependent services
        self._task_service = TaskService(self._vault_service)
        self._project_service = ProjectService(self._vault_service)
        self._person_service = PersonService(self._vault_service)
        self._dashboard_service = DashboardService(
            self._vault_service, self._task_service
        )
        self._context_pack_service = ContextPackService(self._vault_service)
        self._file_service = FileService(self._vault_service)

    def _init_cache(self) -> None:
        """Initialize the vault cache."""
        if self._vault_service is None or self._task_service is None:
            raise RuntimeError("Services must be initialized before cache")

        self._cache = VaultCache(self._vault_service, self._task_service)

    async def _start_socket_transport(self) -> None:
        """Start the Unix socket transport."""
        self._socket_transport = UnixSocketTransport(
            self._socket_path,
            self._handle_request,
        )
        await self._socket_transport.start()

    async def _start_http_transport(self) -> None:
        """Start the HTTP transport."""
        self._http_transport = HttpTransport(
            self._http_host,
            self._http_port,
            self._handle_request,
            self.health_check,
        )
        await self._http_transport.start()

    async def _handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Handle a JSON-RPC request.

        Args:
            request: The incoming request.

        Returns:
            JSON-RPC response.
        """
        if self._context is None:
            return JsonRpcResponse.error_response(
                -32603,
                "Daemon not initialized",
                request_id=request.id,
            )

        return await dispatch_request(
            self._context,
            request.method,
            request.params,
            request.id,
        )


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for the daemon."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Entry point for aio-daemon command."""
    import argparse

    # Set process title for Activity Monitor (optional)
    try:
        import setproctitle
        setproctitle.setproctitle("AIorganization daemon")
    except ImportError:
        pass  # Not critical - just makes it easier to find in Activity Monitor

    parser = argparse.ArgumentParser(description="AIO Daemon Server")
    parser.add_argument(
        "--vault", "-v",
        type=Path,
        help="Path to Obsidian vault (default: auto-discover)",
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=AioDaemon.DEFAULT_SOCKET_PATH,
        help=f"Unix socket path (default: {AioDaemon.DEFAULT_SOCKET_PATH})",
    )
    parser.add_argument(
        "--host",
        default=AioDaemon.DEFAULT_HTTP_HOST,
        help=f"HTTP host (default: {AioDaemon.DEFAULT_HTTP_HOST})",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=AioDaemon.DEFAULT_HTTP_PORT,
        help=f"HTTP port (default: {AioDaemon.DEFAULT_HTTP_PORT})",
    )
    parser.add_argument(
        "--no-http",
        action="store_true",
        help="Disable HTTP transport",
    )
    parser.add_argument(
        "--no-socket",
        action="store_true",
        help="Disable Unix socket transport",
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)

    # Create daemon
    daemon = AioDaemon(
        vault_path=args.vault,
        socket_path=args.socket,
        http_host=args.host,
        http_port=args.port,
        enable_http=not args.no_http,
        enable_socket=not args.no_socket,
    )

    # Set up signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_shutdown(signum: int) -> None:
        """Handle shutdown signal."""
        logger.info("Received signal %s, shutting down...", signal.Signals(signum).name)
        loop.create_task(daemon.stop())

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, sig)

    try:
        loop.run_until_complete(daemon.run_forever())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(daemon.stop())
        loop.close()


if __name__ == "__main__":
    main()
