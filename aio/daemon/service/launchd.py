"""macOS launchd service manager for the AIO daemon."""

import plistlib
import subprocess
import sys
from pathlib import Path

from aio.daemon.service.base import ServiceManager

# Service identifier
SERVICE_LABEL = "com.aio.daemon"

# Paths
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{SERVICE_LABEL}.plist"
LOG_DIR = Path.home() / ".aio"


class LaunchdServiceManager(ServiceManager):
    """macOS launchd service manager."""

    def install(self, vault_path: Path | None = None) -> bool:
        """Install the daemon as a launchd service.

        Args:
            vault_path: Optional vault path to use.

        Returns:
            True if installation succeeded.
        """
        # Ensure directories exist
        LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Find the aio-daemon executable
        python_path = sys.executable

        # Build arguments
        program_args = [python_path, "-m", "aio.daemon.server"]
        if vault_path:
            program_args.extend(["--vault", str(vault_path)])

        # Create plist content
        plist: dict[str, object] = {
            "Label": SERVICE_LABEL,
            "ProgramArguments": program_args,
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(LOG_DIR / "daemon.log"),
            "StandardErrorPath": str(LOG_DIR / "daemon.log"),
            "WorkingDirectory": str(Path.home()),
            "EnvironmentVariables": {
                "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
            },
        }

        # Write plist file
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist, f)

        # Load the service
        result = subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )

        return result.returncode == 0

    def uninstall(self) -> bool:
        """Uninstall the daemon service.

        Returns:
            True if uninstallation succeeded.
        """
        if not PLIST_PATH.exists():
            return True

        # Unload the service first
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )

        # Remove plist file
        PLIST_PATH.unlink(missing_ok=True)
        return True

    def is_installed(self) -> bool:
        """Check if the service is installed.

        Returns:
            True if the service is installed.
        """
        return PLIST_PATH.exists()

    def start(self) -> bool:
        """Start the service.

        Returns:
            True if start succeeded.
        """
        if not self.is_installed():
            return False

        result = subprocess.run(
            ["launchctl", "start", SERVICE_LABEL],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def stop(self) -> bool:
        """Stop the service.

        Returns:
            True if stop succeeded.
        """
        if not self.is_installed():
            return False

        result = subprocess.run(
            ["launchctl", "stop", SERVICE_LABEL],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def restart(self) -> bool:
        """Restart the service.

        Returns:
            True if restart succeeded.
        """
        self.stop()
        return self.start()
