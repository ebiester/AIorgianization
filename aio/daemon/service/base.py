"""Base service manager interface."""

import platform
from abc import ABC, abstractmethod
from pathlib import Path


class ServiceManager(ABC):
    """Abstract base class for system service managers."""

    @abstractmethod
    def install(self, vault_path: Path | None = None) -> bool:
        """Install the daemon as a system service.

        Args:
            vault_path: Optional vault path to use.

        Returns:
            True if installation succeeded.
        """
        pass

    @abstractmethod
    def uninstall(self) -> bool:
        """Uninstall the daemon service.

        Returns:
            True if uninstallation succeeded.
        """
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if the service is installed.

        Returns:
            True if the service is installed.
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the service.

        Returns:
            True if start succeeded.
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the service.

        Returns:
            True if stop succeeded.
        """
        pass

    @abstractmethod
    def restart(self) -> bool:
        """Restart the service.

        Returns:
            True if restart succeeded.
        """
        pass


def get_service_manager() -> ServiceManager:
    """Get the appropriate service manager for the current platform.

    Returns:
        ServiceManager instance for the current platform.

    Raises:
        NotImplementedError: If the platform is not supported.
    """
    system = platform.system()

    if system == "Darwin":
        from aio.daemon.service.launchd import LaunchdServiceManager

        return LaunchdServiceManager()
    elif system == "Linux":
        from aio.daemon.service.systemd import SystemdServiceManager

        return SystemdServiceManager()
    else:
        raise NotImplementedError(f"Service management not supported on {system}")
