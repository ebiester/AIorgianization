"""Linux systemd service manager for the AIO daemon."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from aio.daemon.service.base import ServiceManager

# Service name
SERVICE_NAME = "aio-daemon"

# Paths
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_PATH = SYSTEMD_USER_DIR / f"{SERVICE_NAME}.service"
LOG_DIR = Path.home() / ".aio"


class SystemdServiceManager(ServiceManager):
    """Linux systemd service manager."""

    def install(self, vault_path: Path | None = None) -> bool:
        """Install the daemon as a systemd user service.

        Args:
            vault_path: Optional vault path to use.

        Returns:
            True if installation succeeded.
        """
        # Ensure directories exist
        SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Find the Python executable
        python_path = sys.executable

        # Build exec command
        exec_start = f"{python_path} -m aio.daemon.server"
        if vault_path:
            exec_start += f" --vault {vault_path}"

        # Create service unit content
        service_content = dedent(f"""\
            [Unit]
            Description=AIO Daemon - Task Management Server
            After=network.target

            [Service]
            Type=simple
            ExecStart={exec_start}
            Restart=always
            RestartSec=5
            StandardOutput=append:{LOG_DIR}/daemon.log
            StandardError=append:{LOG_DIR}/daemon.log
            Environment=PATH=/usr/local/bin:/usr/bin:/bin

            [Install]
            WantedBy=default.target
        """)

        # Write service file
        SERVICE_PATH.write_text(service_content)

        # Reload systemd
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
        )

        # Enable the service
        result = subprocess.run(
            ["systemctl", "--user", "enable", SERVICE_NAME],
            capture_output=True,
            text=True,
        )

        return result.returncode == 0

    def uninstall(self) -> bool:
        """Uninstall the daemon service.

        Returns:
            True if uninstallation succeeded.
        """
        if not SERVICE_PATH.exists():
            return True

        # Stop the service first
        subprocess.run(
            ["systemctl", "--user", "stop", SERVICE_NAME],
            capture_output=True,
            text=True,
        )

        # Disable the service
        subprocess.run(
            ["systemctl", "--user", "disable", SERVICE_NAME],
            capture_output=True,
            text=True,
        )

        # Remove service file
        SERVICE_PATH.unlink(missing_ok=True)

        # Reload systemd
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
        )

        return True

    def is_installed(self) -> bool:
        """Check if the service is installed.

        Returns:
            True if the service is installed.
        """
        return SERVICE_PATH.exists()

    def start(self) -> bool:
        """Start the service.

        Returns:
            True if start succeeded.
        """
        if not self.is_installed():
            return False

        result = subprocess.run(
            ["systemctl", "--user", "start", SERVICE_NAME],
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
            ["systemctl", "--user", "stop", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def restart(self) -> bool:
        """Restart the service.

        Returns:
            True if restart succeeded.
        """
        if not self.is_installed():
            return False

        result = subprocess.run(
            ["systemctl", "--user", "restart", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
