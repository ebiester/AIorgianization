"""Daemon management commands for aio CLI."""

import contextlib
import json
import os
import signal
import socket
import struct
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


def error(msg: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {msg}")


def warning(msg: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {msg}")


def info(msg: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{msg}[/dim]")


def success(msg: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {msg}")

# Default paths
DEFAULT_SOCKET_PATH = Path.home() / ".aio" / "daemon.sock"
DEFAULT_PID_FILE = Path.home() / ".aio" / "daemon.pid"
DEFAULT_LOG_FILE = Path.home() / ".aio" / "daemon.log"


def _get_pid() -> int | None:
    """Get the daemon PID if running.

    Returns:
        PID if daemon is running, None otherwise.
    """
    if not DEFAULT_PID_FILE.exists():
        return None

    try:
        pid = int(DEFAULT_PID_FILE.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        # PID file is stale, clean it up
        DEFAULT_PID_FILE.unlink(missing_ok=True)
        return None


def _is_socket_alive() -> bool:
    """Check if the daemon socket is responding.

    Returns:
        True if socket is responding.
    """
    if not DEFAULT_SOCKET_PATH.exists():
        return False

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(str(DEFAULT_SOCKET_PATH))

        # Send a health check request
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "list_tasks",
            "params": {"status": "inbox"},
        }).encode("utf-8")

        # Length-prefixed message
        sock.sendall(struct.pack(">I", len(request)) + request)

        # Read response length
        length_data = sock.recv(4)
        if len(length_data) < 4:
            return False

        length = struct.unpack(">I", length_data)[0]
        response_data = sock.recv(length)

        sock.close()
        return len(response_data) > 0

    except (OSError, TimeoutError):
        return False


def _wait_for_daemon(timeout: float = 5.0) -> bool:
    """Wait for daemon to start responding.

    Args:
        timeout: Maximum time to wait in seconds.

    Returns:
        True if daemon started, False if timeout.
    """
    import time

    start = time.time()
    while time.time() - start < timeout:
        if _is_socket_alive():
            return True
        time.sleep(0.1)
    return False


def _wait_for_shutdown(pid: int, timeout: float = 5.0) -> bool:
    """Wait for daemon to shut down.

    Args:
        pid: Process ID to wait for.
        timeout: Maximum time to wait in seconds.

    Returns:
        True if daemon shut down, False if timeout.
    """
    import time

    start = time.time()
    while time.time() - start < timeout:
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except OSError:
            return True
    return False


@click.group()
def daemon() -> None:
    """Manage the AIO daemon."""
    pass


@daemon.command()
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (don't daemonize)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--port", "-p", type=int, default=7432, help="HTTP port (default: 7432)")
@click.pass_context
def start(ctx: click.Context, foreground: bool, verbose: bool, port: int) -> None:
    """Start the AIO daemon."""
    # Check if already running
    pid = _get_pid()
    if pid:
        if _is_socket_alive():
            warning(f"Daemon is already running (PID {pid})")
            return
        else:
            info("Found stale PID file, cleaning up...")
            DEFAULT_PID_FILE.unlink(missing_ok=True)

    # Get vault path from context or discover
    vault_path = ctx.obj.get("vault_path") if ctx.obj else None

    # Ensure .aio directory exists
    DEFAULT_SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)

    if foreground:
        # Run in foreground - exec the daemon process
        args = [sys.executable, "-m", "aio.daemon.server"]
        if vault_path:
            args.extend(["--vault", str(vault_path)])
        args.extend(["--port", str(port)])
        if verbose:
            args.append("--verbose")

        info("Starting daemon in foreground...")
        try:
            os.execv(sys.executable, args)
        except OSError as e:
            error(f"Failed to start daemon: {e}")
            raise SystemExit(1) from e
    else:
        # Daemonize - run in background
        args = [sys.executable, "-m", "aio.daemon.server"]
        if vault_path:
            args.extend(["--vault", str(vault_path)])
        args.extend(["--port", str(port)])
        if verbose:
            args.append("--verbose")

        # Open log file for daemon output
        DEFAULT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(DEFAULT_LOG_FILE, "a")  # noqa: SIM115

        info("Starting daemon in background...")
        try:
            proc = subprocess.Popen(
                args,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Write PID file
            DEFAULT_PID_FILE.write_text(str(proc.pid))

            # Wait for daemon to be ready
            if _wait_for_daemon():
                success(f"Daemon started (PID {proc.pid})")
                info(f"  Socket: {DEFAULT_SOCKET_PATH}")
                info(f"  HTTP: http://127.0.0.1:{port}")
                info(f"  Logs: {DEFAULT_LOG_FILE}")
            else:
                warning("Daemon process started but not responding yet")
                info(f"Check logs: {DEFAULT_LOG_FILE}")

        except OSError as e:
            error(f"Failed to start daemon: {e}")
            raise SystemExit(1) from e


@daemon.command()
@click.option("--force", "-f", is_flag=True, help="Force kill if graceful shutdown fails")
def stop(force: bool) -> None:
    """Stop the AIO daemon."""
    pid = _get_pid()

    if not pid:
        if DEFAULT_SOCKET_PATH.exists():
            info("Cleaning up stale socket file...")
            DEFAULT_SOCKET_PATH.unlink()
        warning("Daemon is not running")
        return

    info(f"Stopping daemon (PID {pid})...")

    # Try graceful shutdown first
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        error(f"Failed to send SIGTERM: {e}")
        DEFAULT_PID_FILE.unlink(missing_ok=True)
        raise SystemExit(1) from e

    # Wait for graceful shutdown
    if _wait_for_shutdown(pid):
        success("Daemon stopped")
        DEFAULT_PID_FILE.unlink(missing_ok=True)
        DEFAULT_SOCKET_PATH.unlink(missing_ok=True)
        return

    if force:
        warning("Graceful shutdown failed, forcing...")
        try:
            os.kill(pid, signal.SIGKILL)
            _wait_for_shutdown(pid, timeout=2.0)
            success("Daemon killed")
        except OSError as e:
            error(f"Failed to kill daemon: {e}")
    else:
        error("Graceful shutdown timed out. Use --force to kill.")
        raise SystemExit(1)

    DEFAULT_PID_FILE.unlink(missing_ok=True)
    DEFAULT_SOCKET_PATH.unlink(missing_ok=True)


@daemon.command()
def status() -> None:
    """Check daemon status."""
    pid = _get_pid()

    if not pid:
        info("Daemon is not running")
        return

    socket_alive = _is_socket_alive()

    if socket_alive:
        success(f"Daemon is running (PID {pid})")
        info(f"  Socket: {DEFAULT_SOCKET_PATH}")
        info("  HTTP: http://127.0.0.1:7432")

        # Try to get more info from the daemon
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(str(DEFAULT_SOCKET_PATH))

            # Send a list_tasks request to check cache state
            request = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "list_tasks",
                "params": {},
            }).encode("utf-8")

            sock.sendall(struct.pack(">I", len(request)) + request)

            length_data = sock.recv(4)
            length = struct.unpack(">I", length_data)[0]
            response_data = sock.recv(length)
            response = json.loads(response_data.decode("utf-8"))

            if "result" in response and "count" in response["result"]:
                info(f"  Tasks cached: {response['result']['count']}")

            sock.close()
        except (OSError, json.JSONDecodeError):
            pass
    else:
        warning(f"Daemon process running (PID {pid}) but not responding")
        info("The daemon may still be starting up, or may have crashed.")
        info(f"Check logs: {DEFAULT_LOG_FILE}")


@daemon.command()
@click.pass_context
def restart(ctx: click.Context) -> None:
    """Restart the AIO daemon."""
    # Stop if running
    pid = _get_pid()
    if pid:
        ctx.invoke(stop)

    # Start
    ctx.invoke(start)


@daemon.command()
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(lines: int, follow: bool) -> None:
    """View daemon logs."""
    if not DEFAULT_LOG_FILE.exists():
        warning("No log file found")
        info(f"Expected location: {DEFAULT_LOG_FILE}")
        return

    if follow:
        # Use tail -f
        with contextlib.suppress(KeyboardInterrupt):
            subprocess.run(["tail", "-f", str(DEFAULT_LOG_FILE)], check=True)
    else:
        # Show last N lines
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), str(DEFAULT_LOG_FILE)],
                capture_output=True,
                text=True,
                check=True,
            )
            click.echo(result.stdout)
        except subprocess.CalledProcessError as e:
            error(f"Failed to read logs: {e}")


@daemon.command()
@click.pass_context
def install(ctx: click.Context) -> None:
    """Install daemon as a system service.

    On macOS: Uses launchd (auto-starts on login)
    On Linux: Uses systemd user service (auto-starts on login)
    """
    try:
        from aio.daemon.service import get_service_manager

        manager = get_service_manager()
    except NotImplementedError as e:
        error(str(e))
        raise SystemExit(1) from e

    if manager.is_installed():
        warning("Service is already installed")
        return

    vault_path = ctx.obj.get("vault_path") if ctx.obj else None

    info("Installing AIO daemon service...")
    if manager.install(vault_path):
        success("Service installed successfully")
        info("The daemon will start automatically on login.")
        info("To start it now, run: aio daemon start")
    else:
        error("Failed to install service")
        raise SystemExit(1)


@daemon.command()
def uninstall() -> None:
    """Uninstall daemon system service."""
    try:
        from aio.daemon.service import get_service_manager

        manager = get_service_manager()
    except NotImplementedError as e:
        error(str(e))
        raise SystemExit(1) from e

    if not manager.is_installed():
        warning("Service is not installed")
        return

    info("Uninstalling AIO daemon service...")
    if manager.uninstall():
        success("Service uninstalled successfully")
    else:
        error("Failed to uninstall service")
        raise SystemExit(1)
