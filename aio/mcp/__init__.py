"""MCP server for Claude/Cursor integration."""

from aio.mcp.server import (
    ServiceRegistry,
    get_context_pack_service,
    get_dashboard_service,
    get_jira_service,
    get_registry,
    get_task_service,
    get_vault_service,
    main,
    server,
)

__all__ = [
    "ServiceRegistry",
    "get_registry",
    "get_vault_service",
    "get_task_service",
    "get_dashboard_service",
    "get_jira_service",
    "get_context_pack_service",
    "server",
    "main",
]
