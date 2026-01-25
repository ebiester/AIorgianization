"""Service management for the AIO daemon.

Provides integration with system service managers:
- launchd on macOS
- systemd on Linux
"""

from aio.daemon.service.base import ServiceManager, get_service_manager

__all__ = ["ServiceManager", "get_service_manager"]
