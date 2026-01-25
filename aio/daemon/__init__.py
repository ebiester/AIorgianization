"""AIO Daemon - Persistent server for all AIO clients.

The daemon serves as the single source of truth for all AIO clients
(CLI, MCP/Cursor, Obsidian plugin), eliminating duplicate business logic
and enabling fast response times through in-memory caching.
"""

from aio.daemon.cache import VaultCache
from aio.daemon.handlers import HandlerContext, dispatch_request
from aio.daemon.protocol import (
    ErrorCode,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
)
from aio.daemon.server import AioDaemon

__all__ = [
    "AioDaemon",
    "VaultCache",
    "HandlerContext",
    "dispatch_request",
    "ErrorCode",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
]
