"""MCP server for AIorgianization.

Exposes vault operations to Claude/Cursor via the Model Context Protocol.
Uses shared handlers from the daemon for consistent business logic.
"""

import asyncio
import signal
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from aio.daemon.cache import VaultCache
from aio.daemon.handlers import (
    HandlerContext,
)
from aio.daemon.handlers import (
    handle_add_file_to_context_pack as daemon_add_file_to_context_pack,
)
from aio.daemon.handlers import (
    handle_add_task as daemon_add_task,
)
from aio.daemon.handlers import (
    handle_add_to_context_pack as daemon_add_to_context_pack,
)
from aio.daemon.handlers import (
    handle_complete_task as daemon_complete_task,
)
from aio.daemon.handlers import (
    handle_create_context_pack as daemon_create_context_pack,
)
from aio.daemon.handlers import (
    handle_create_person as daemon_create_person,
)
from aio.daemon.handlers import (
    handle_create_project as daemon_create_project,
)
from aio.daemon.handlers import (
    handle_defer_task as daemon_defer_task,
)
from aio.daemon.handlers import (
    handle_delegate_task as daemon_delegate_task,
)
from aio.daemon.handlers import (
    handle_file_get as daemon_file_get,
)
from aio.daemon.handlers import (
    handle_file_set as daemon_file_set,
)
from aio.daemon.handlers import (
    handle_get_context as daemon_get_context,
)
from aio.daemon.handlers import (
    handle_get_dashboard as daemon_get_dashboard,
)
from aio.daemon.handlers import (
    handle_list_context_packs as daemon_list_context_packs,
)
from aio.daemon.handlers import (
    handle_list_tasks as daemon_list_tasks,
)
from aio.daemon.handlers import (
    handle_start_task as daemon_start_task,
)
from aio.exceptions import AioError, FileOutsideVaultError, InvalidDateError
from aio.models.task import TaskStatus
from aio.services.context_pack import ContextPackService
from aio.services.dashboard import DashboardService
from aio.services.file import FileService
from aio.services.person import PersonService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService


class ServiceRegistry:
    """Registry for service instances with dependency injection support.

    Provides lazy initialization of services and allows overriding
    services for testing purposes.
    """

    def __init__(self) -> None:
        self._vault_service: VaultService | None = None
        self._task_service: TaskService | None = None
        self._project_service: ProjectService | None = None
        self._person_service: PersonService | None = None
        self._dashboard_service: DashboardService | None = None
        self._context_pack_service: ContextPackService | None = None
        self._file_service: FileService | None = None

    def reset(self) -> None:
        """Reset all services and cache. Useful for testing."""
        global _cache
        self._vault_service = None
        self._task_service = None
        self._project_service = None
        self._person_service = None
        self._dashboard_service = None
        self._context_pack_service = None
        self._file_service = None
        # Also reset the cache since it depends on services
        _cache = None

    def set_vault_service(self, service: VaultService) -> None:
        """Override the vault service. Useful for testing."""
        self._vault_service = service

    def set_task_service(self, service: TaskService) -> None:
        """Override the task service. Useful for testing."""
        self._task_service = service

    def set_dashboard_service(self, service: DashboardService) -> None:
        """Override the dashboard service. Useful for testing."""
        self._dashboard_service = service

    def set_context_pack_service(self, service: ContextPackService) -> None:
        """Override the context pack service. Useful for testing."""
        self._context_pack_service = service

    def set_person_service(self, service: PersonService) -> None:
        """Override the person service. Useful for testing."""
        self._person_service = service

    def set_file_service(self, service: FileService) -> None:
        """Override the file service. Useful for testing."""
        self._file_service = service

    @property
    def vault_service(self) -> VaultService:
        """Get the vault service, creating it lazily if needed."""
        if self._vault_service is None:
            self._vault_service = VaultService()
        return self._vault_service

    @property
    def task_service(self) -> TaskService:
        """Get the task service, creating it lazily if needed."""
        if self._task_service is None:
            self._task_service = TaskService(self.vault_service)
        return self._task_service

    @property
    def project_service(self) -> ProjectService:
        """Get the project service, creating it lazily if needed."""
        if self._project_service is None:
            self._project_service = ProjectService(self.vault_service)
        return self._project_service

    @property
    def person_service(self) -> PersonService:
        """Get the person service, creating it lazily if needed."""
        if self._person_service is None:
            self._person_service = PersonService(self.vault_service)
        return self._person_service

    @property
    def dashboard_service(self) -> DashboardService:
        """Get the dashboard service, creating it lazily if needed."""
        if self._dashboard_service is None:
            self._dashboard_service = DashboardService(
                self.vault_service, self.task_service
            )
        return self._dashboard_service

    @property
    def context_pack_service(self) -> ContextPackService:
        """Get the context pack service, creating it lazily if needed."""
        if self._context_pack_service is None:
            self._context_pack_service = ContextPackService(self.vault_service)
        return self._context_pack_service

    @property
    def file_service(self) -> FileService:
        """Get the file service, creating it lazily if needed."""
        if self._file_service is None:
            self._file_service = FileService(self.vault_service)
        return self._file_service


# Global registry instance
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return _registry


def get_vault_service() -> VaultService:
    """Get the vault service."""
    return _registry.vault_service


def get_task_service() -> TaskService:
    """Get the task service."""
    return _registry.task_service


def get_project_service() -> ProjectService:
    """Get the project service."""
    return _registry.project_service


def get_person_service() -> PersonService:
    """Get the person service."""
    return _registry.person_service


def get_dashboard_service() -> DashboardService:
    """Get the dashboard service."""
    return _registry.dashboard_service


def get_context_pack_service() -> ContextPackService:
    """Get the context pack service."""
    return _registry.context_pack_service


def get_file_service() -> FileService:
    """Get the file service."""
    return _registry.file_service


# Global cache instance (lazy initialized)
_cache: VaultCache | None = None


def reset_cache() -> None:
    """Reset the global cache.

    Call this when the registry is reset or the vault changes.
    """
    global _cache
    _cache = None


def get_cache() -> VaultCache:
    """Get the vault cache, creating and populating it lazily if needed.

    The MCP server uses a non-watching cache since each request is stateless.
    The cache is populated on first access for performance but doesn't
    automatically refresh.
    """
    global _cache
    if _cache is None:
        _cache = VaultCache(
            _registry.vault_service,
            _registry.task_service,
        )
        _cache.refresh_sync()  # Populate immediately
    return _cache


def get_handler_context() -> HandlerContext:
    """Get a HandlerContext using the global registry and cache.

    This bridges the ServiceRegistry pattern used by MCP with the
    HandlerContext pattern used by daemon handlers.
    """
    return HandlerContext(
        vault_service=_registry.vault_service,
        task_service=_registry.task_service,
        project_service=_registry.project_service,
        person_service=_registry.person_service,
        dashboard_service=_registry.dashboard_service,
        context_pack_service=_registry.context_pack_service,
        file_service=_registry.file_service,
        cache=get_cache(),
    )


# Create MCP server
server = Server("aio")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="aio_add_task",
            description="Create a new task in the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "due": {
                        "type": "string",
                        "description": "Due date (e.g., 'tomorrow', 'friday', '2024-01-20')",
                    },
                    "project": {"type": "string", "description": "Project ID or name"},
                    "status": {
                        "type": "string",
                        "enum": ["inbox", "next", "scheduled", "someday"],
                        "description": "Initial status (default: inbox)",
                    },
                    "assign": {
                        "type": "string",
                        "description": "Person to delegate task to (moves to Waiting status)",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="aio_list_tasks",
            description="List tasks from the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "inbox", "next", "waiting", "scheduled",
                            "someday", "today", "overdue",
                        ],
                        "description": "Filter by status",
                    },
                    "project": {"type": "string", "description": "Filter by project ID or name"},
                },
            },
        ),
        Tool(
            name="aio_complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task ID or title substring",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="aio_start_task",
            description="Move a task to Next status",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task ID or title substring",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="aio_defer_task",
            description="Move a task to Someday status",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task ID or title substring",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="aio_get_dashboard",
            description="Get the daily dashboard with overdue, due today, and waiting items",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date for dashboard (default: today)",
                    },
                },
            },
        ),
        Tool(
            name="aio_get_context",
            description="Get context pack content for AI assistance",
            inputSchema={
                "type": "object",
                "properties": {
                    "packs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of context pack names to retrieve",
                    },
                },
                "required": ["packs"],
            },
        ),
        Tool(
            name="aio_list_context_packs",
            description="List available context packs for AI assistance",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["domain", "system", "operating"],
                        "description": "Filter by category (optional)",
                    },
                },
            },
        ),
        Tool(
            name="aio_add_to_context_pack",
            description="Add content to an existing context pack",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack": {
                        "type": "string",
                        "description": "Context pack name or ID (e.g., 'payments', 'auth-service')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content to add to the pack",
                    },
                    "section": {
                        "type": "string",
                        "description": (
                            "Section heading to append under (e.g., 'Key Concepts'). "
                            "If not specified, appends to end."
                        ),
                    },
                },
                "required": ["pack", "content"],
            },
        ),
        Tool(
            name="aio_add_file_to_context_pack",
            description="Copy a file's content into an existing context pack",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack": {
                        "type": "string",
                        "description": "Context pack name or ID",
                    },
                    "file": {
                        "type": "string",
                        "description": (
                            "Path to the file in the vault "
                            "(e.g., 'ADRs/2024-01-payment-provider.md')"
                        ),
                    },
                    "section": {
                        "type": "string",
                        "description": "Section heading to append under (optional)",
                    },
                },
                "required": ["pack", "file"],
            },
        ),
        Tool(
            name="aio_create_context_pack",
            description="Create a new context pack file",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Display title for the pack",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["domain", "system", "operating"],
                        "description": (
                            "Pack category: 'domain' for business domains, "
                            "'system' for technical systems, 'operating' for processes"
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "Initial markdown content (optional)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description for the pack (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization (optional)",
                    },
                },
                "required": ["title", "category"],
            },
        ),
        Tool(
            name="aio_create_project",
            description="Create a new project in the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name/title",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "on-hold", "completed", "archived"],
                        "description": "Initial status (default: active)",
                    },
                    "team": {
                        "type": "string",
                        "description": "Team name (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="aio_create_person",
            description="Create a new person in the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's full name",
                    },
                    "team": {
                        "type": "string",
                        "description": "Team name (optional)",
                    },
                    "role": {
                        "type": "string",
                        "description": "Role/title (optional)",
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="aio_delegate_task",
            description=(
                "Delegate a task to a person "
                "(moves to Waiting status with person set as waitingOn)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task ID or title substring",
                    },
                    "person": {
                        "type": "string",
                        "description": "Person name or ID to delegate to",
                    },
                },
                "required": ["query", "person"],
            },
        ),
        Tool(
            name="aio_file_get",
            description=(
                "Get the contents of a file in the vault. "
                "Query by file ID (4-char), title substring, or path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "File ID (4-char), title substring, "
                            "or path relative to vault root"
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="aio_file_set",
            description=(
                "Set file contents with automatic backup. "
                "Query by file ID (4-char), title substring, or path. "
                "Creates a timestamped backup before overwriting existing files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "File ID (4-char), title substring, "
                            "or path relative to vault root"
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "New file contents",
                    },
                },
                "required": ["query", "content"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool invocations."""
    try:
        if name == "aio_add_task":
            return await handle_add_task(arguments)
        elif name == "aio_list_tasks":
            return await handle_list_tasks(arguments)
        elif name == "aio_complete_task":
            return await handle_complete_task(arguments)
        elif name == "aio_start_task":
            return await handle_start_task(arguments)
        elif name == "aio_defer_task":
            return await handle_defer_task(arguments)
        elif name == "aio_get_dashboard":
            return await handle_get_dashboard(arguments)
        elif name == "aio_get_context":
            return await handle_get_context(arguments)
        elif name == "aio_list_context_packs":
            return await handle_list_context_packs(arguments)
        elif name == "aio_add_to_context_pack":
            return await handle_add_to_context_pack(arguments)
        elif name == "aio_add_file_to_context_pack":
            return await handle_add_file_to_context_pack(arguments)
        elif name == "aio_create_context_pack":
            return await handle_create_context_pack(arguments)
        elif name == "aio_create_project":
            return await handle_create_project(arguments)
        elif name == "aio_create_person":
            return await handle_create_person(arguments)
        elif name == "aio_delegate_task":
            return await handle_delegate_task(arguments)
        elif name == "aio_file_get":
            return await handle_file_get(arguments)
        elif name == "aio_file_set":
            return await handle_file_set(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except FileOutsideVaultError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except AioError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ============================================================================
# Handler implementations - thin wrappers around daemon handlers
# ============================================================================
#
# These handlers delegate to the shared daemon handlers and convert the
# dict results to MCP's TextContent format. This eliminates duplicate
# business logic between MCP and daemon.


def _format_task_result(task: dict[str, Any]) -> str:
    """Format a task dict as human-readable text."""
    lines = [f"Task: {task['title']}", f"ID: {task['id']}", f"Status: {task['status']}"]
    if task.get("due"):
        lines.append(f"Due: {task['due']}")
    if task.get("project"):
        lines.append(f"Project: {task['project']}")
    if task.get("waiting_on"):
        lines.append(f"Waiting on: {task['waiting_on']}")
    return "\n".join(lines)


def _format_task_list_result(result: dict[str, Any]) -> str:
    """Format a list_tasks result as human-readable text."""
    tasks = result.get("tasks", [])
    if not tasks:
        return "No tasks found."

    lines = [f"Found {len(tasks)} task(s):", ""]
    for task in tasks:
        due_str = f" (due: {task['due']})" if task.get("due") else ""
        overdue = " [OVERDUE]" if task.get("is_overdue") else ""
        lines.append(f"- [{task['id']}] {task['title']} ({task['status']}){due_str}{overdue}")
    return "\n".join(lines)


async def handle_add_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_task tool using daemon handler."""
    ctx = get_handler_context()
    try:
        result = await daemon_add_task(ctx, args)
    except InvalidDateError as e:
        return [TextContent(type="text", text=f"Invalid date: {e}")]
    task = result["task"]

    text = f"Created task: {task['title']}\nID: {task['id']}\nStatus: {task['status']}"
    if task.get("waiting_on"):
        text += f"\nWaiting on: {task['waiting_on']}"
    if task.get("due"):
        text += f"\nDue: {task['due']}"
    if task.get("project"):
        text += f"\nProject: {task['project']}"

    return [TextContent(type="text", text=text)]


async def handle_list_tasks(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_list_tasks tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_list_tasks(ctx, args)
    return [TextContent(type="text", text=_format_task_list_result(result))]


async def handle_complete_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_complete_task tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_complete_task(ctx, args)
    task = result["task"]
    return [TextContent(type="text", text=f"Completed: {task['title']} ({task['id']})")]


async def handle_start_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_start_task tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_start_task(ctx, args)
    task = result["task"]
    return [TextContent(type="text", text=f"Started: {task['title']} ({task['id']})\nStatus: next")]


async def handle_defer_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_defer_task tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_defer_task(ctx, args)
    task = result["task"]
    return [TextContent(
        type="text",
        text=f"Deferred: {task['title']} ({task['id']})\nStatus: someday",
    )]


async def handle_get_dashboard(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_get_dashboard tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_get_dashboard(ctx, args)
    return [TextContent(type="text", text=result["content"])]


async def handle_get_context(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_get_context tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_get_context(ctx, args)

    content = result.get("content", "")
    if not content:
        return [TextContent(type="text", text="No context packs specified.")]
    return [TextContent(type="text", text=content)]


async def handle_list_context_packs(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_list_context_packs tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_list_context_packs(ctx, args)

    packs = result.get("packs", [])
    if not packs:
        return [TextContent(type="text", text="No context packs found.")]

    lines = [f"Found {len(packs)} context pack(s):", ""]
    for pack in packs:
        desc = f" - {pack['description']}" if pack.get("description") else ""
        tags = f" [{', '.join(pack['tags'])}]" if pack.get("tags") else ""
        lines.append(f"- [{pack['category']}] {pack['title']} ({pack['id']}){desc}{tags}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_add_to_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_to_context_pack tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_add_to_context_pack(ctx, args)

    section_msg = f" under section '{result['section']}'" if result.get("section") else ""
    return [TextContent(
        type="text",
        text=f"Added content to context pack: {result['title']} ({result['id']}){section_msg}",
    )]


async def handle_add_file_to_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_file_to_context_pack tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_add_file_to_context_pack(ctx, args)

    section_msg = f" under section '{result['section']}'" if result.get("section") else ""
    file_path = result.get("file", args.get("file", ""))
    pack_title = result["title"]
    pack_id = result["id"]
    text = f"Added file '{file_path}' to context pack: {pack_title} ({pack_id}){section_msg}"
    return [TextContent(type="text", text=text)]


async def handle_create_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_context_pack tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_create_context_pack(ctx, args)

    pack_title = result["title"]
    pack_id = result["id"]
    pack_category = result["category"]
    text = f"Created context pack: {pack_title}\nID: {pack_id}\nCategory: {pack_category}"
    if result.get("description"):
        text += f"\nDescription: {result['description']}"
    if result.get("tags"):
        text += f"\nTags: {', '.join(result['tags'])}"

    return [TextContent(type="text", text=text)]


async def handle_create_project(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_project tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_create_project(ctx, args)

    text = f"Created project: {result['title']}\nID: {result['id']}\nStatus: {result['status']}"
    if result.get("team"):
        text += f"\nTeam: {result['team']}"

    return [TextContent(type="text", text=text)]


async def handle_create_person(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_person tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_create_person(ctx, args)

    text = f"Created person: {result['name']}\nID: {result['id']}"
    if result.get("team"):
        text += f"\nTeam: {result['team']}"
    if result.get("role"):
        text += f"\nRole: {result['role']}"
    if result.get("email"):
        text += f"\nEmail: {result['email']}"

    return [TextContent(type="text", text=text)]


async def handle_delegate_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_delegate_task tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_delegate_task(ctx, args)
    task = result["task"]
    person_name = result.get("delegated_to", task.get("waiting_on", ""))

    task_title = task["title"]
    task_id = task["id"]
    text = f"Delegated: {task_title} ({task_id})\nWaiting on: {person_name}\nStatus: waiting"
    return [TextContent(type="text", text=text)]


async def handle_file_get(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_file_get tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_file_get(ctx, args)
    return [TextContent(type="text", text=result["content"])]


async def handle_file_set(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_file_set tool using daemon handler."""
    ctx = get_handler_context()
    result = await daemon_file_set(ctx, args)

    if result.get("backup"):
        text = f"Backup created: {result['backup']}\nFile updated: {result['file']}"
    else:
        text = f"File created: {result['file']} (no backup needed - new file)"

    return [TextContent(type="text", text=text)]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available MCP resources."""
    return [
        Resource(
            uri="aio://tasks/inbox",
            name="Inbox Tasks",
            description="Unprocessed tasks in the inbox",
            mimeType="text/plain",
        ),
        Resource(
            uri="aio://tasks/next",
            name="Next Actions",
            description="Tasks ready to work on",
            mimeType="text/plain",
        ),
        Resource(
            uri="aio://tasks/waiting",
            name="Waiting For",
            description="Delegated tasks",
            mimeType="text/plain",
        ),
        Resource(
            uri="aio://tasks/today",
            name="Today's Tasks",
            description="Tasks due today and overdue",
            mimeType="text/plain",
        ),
        Resource(
            uri="aio://projects",
            name="Active Projects",
            description="List of active projects",
            mimeType="text/plain",
        ),
        Resource(
            uri="aio://dashboard",
            name="Daily Dashboard",
            description="Today's dashboard",
            mimeType="text/markdown",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    task_service = get_task_service()
    vault_service = get_vault_service()

    if uri == "aio://tasks/inbox":
        tasks = task_service.list_tasks(status=TaskStatus.INBOX)
        return _format_task_list(tasks, "Inbox")
    elif uri == "aio://tasks/next":
        tasks = task_service.list_tasks(status=TaskStatus.NEXT)
        return _format_task_list(tasks, "Next Actions")
    elif uri == "aio://tasks/waiting":
        tasks = task_service.list_tasks(status=TaskStatus.WAITING)
        return _format_task_list(tasks, "Waiting For")
    elif uri == "aio://tasks/today":
        tasks = task_service.list_today()
        return _format_task_list(tasks, "Today")
    elif uri == "aio://projects":
        projects_folder = vault_service.projects_folder()
        projects = list(projects_folder.glob("*.md"))
        lines = ["# Active Projects", ""]
        for p in projects:
            lines.append(f"- [[AIO/Projects/{p.stem}]]")
        return "\n".join(lines)
    elif uri == "aio://dashboard":
        dashboard_service = get_dashboard_service()
        return dashboard_service.generate()
    else:
        return f"Unknown resource: {uri}"


def _format_task_list(tasks: list[Any], title: str) -> str:
    """Format a list of tasks as text."""
    lines = [f"# {title}", "", f"{len(tasks)} task(s)", ""]
    for task in tasks:
        due = f" (due: {task.due.isoformat()})" if task.due else ""
        lines.append(f"- [{task.id}] {task.title}{due}")
    return "\n".join(lines)


async def run_server() -> None:
    """Run the MCP server."""
    # Print startup message to stderr (stdout is reserved for MCP protocol)
    print("AIO MCP server starting...", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        print("AIO MCP server ready", file=sys.stderr)
        await server.run(read_stream, write_stream, server.create_initialization_options())


def _handle_shutdown(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    print("\nAIO MCP server shutting down...", file=sys.stderr)
    sys.exit(0)


def main() -> None:
    """Entry point for aio-mcp command."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        # Handle case where signal handler doesn't catch it
        print("\nAIO MCP server shutting down...", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
