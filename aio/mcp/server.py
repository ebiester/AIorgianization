"""MCP server for AIorgianization.

Exposes vault operations to Claude/Cursor via the Model Context Protocol.
"""

import asyncio
import signal
import sys
from datetime import date
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from aio.exceptions import AioError, InvalidDateError, JiraError
from aio.models.context_pack import ContextPackCategory
from aio.models.project import ProjectStatus
from aio.models.task import TaskStatus
from aio.services.context_pack import ContextPackService
from aio.services.dashboard import DashboardService
from aio.services.jira import JiraSyncService
from aio.services.person import PersonService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import parse_date


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
        self._jira_service: JiraSyncService | None = None
        self._context_pack_service: ContextPackService | None = None

    def reset(self) -> None:
        """Reset all services. Useful for testing."""
        self._vault_service = None
        self._task_service = None
        self._project_service = None
        self._person_service = None
        self._dashboard_service = None
        self._jira_service = None
        self._context_pack_service = None

    def set_vault_service(self, service: VaultService) -> None:
        """Override the vault service. Useful for testing."""
        self._vault_service = service

    def set_task_service(self, service: TaskService) -> None:
        """Override the task service. Useful for testing."""
        self._task_service = service

    def set_dashboard_service(self, service: DashboardService) -> None:
        """Override the dashboard service. Useful for testing."""
        self._dashboard_service = service

    def set_jira_service(self, service: JiraSyncService) -> None:
        """Override the Jira service. Useful for testing."""
        self._jira_service = service

    def set_context_pack_service(self, service: ContextPackService) -> None:
        """Override the context pack service. Useful for testing."""
        self._context_pack_service = service

    def set_person_service(self, service: PersonService) -> None:
        """Override the person service. Useful for testing."""
        self._person_service = service

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
    def jira_service(self) -> JiraSyncService:
        """Get the Jira service, creating it lazily if needed."""
        if self._jira_service is None:
            self._jira_service = JiraSyncService(self.vault_service, self.task_service)
        return self._jira_service

    @property
    def context_pack_service(self) -> ContextPackService:
        """Get the context pack service, creating it lazily if needed."""
        if self._context_pack_service is None:
            self._context_pack_service = ContextPackService(self.vault_service)
        return self._context_pack_service


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


def get_jira_service() -> JiraSyncService:
    """Get the Jira sync service."""
    return _registry.jira_service


def get_context_pack_service() -> ContextPackService:
    """Get the context pack service."""
    return _registry.context_pack_service


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
            name="aio_sync_jira",
            description=(
                "Sync tasks from Jira. "
                "Imports issues assigned to you from configured projects."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, show what would be synced without making changes",
                    },
                },
            },
        ),
        Tool(
            name="aio_jira_status",
            description="Get Jira sync status and configuration",
            inputSchema={
                "type": "object",
                "properties": {},
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
        elif name == "aio_sync_jira":
            return await handle_sync_jira(arguments)
        elif name == "aio_jira_status":
            return await handle_jira_status(arguments)
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
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except JiraError as e:
        return [TextContent(type="text", text=f"Jira error: {e}")]
    except AioError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def handle_add_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_task tool."""
    task_service = get_task_service()
    project_service = get_project_service()

    title = args["title"]
    due_str = args.get("due")
    project = args.get("project")
    status_str = args.get("status", "inbox")

    due_date = None
    if due_str:
        try:
            due_date = parse_date(due_str)
        except InvalidDateError as e:
            return [TextContent(type="text", text=f"Invalid date: {e}")]

    project_link = None
    if project:
        # Find project by ID or name
        if project.startswith("[["):
            project_link = project
        else:
            found_project = project_service.find(project)
            project_slug = project_service.get_slug(found_project.title)
            project_link = f"[[AIO/Projects/{project_slug}]]"

    task = task_service.create(
        title=title,
        due=due_date,
        project=project_link,
        status=TaskStatus(status_str),
    )

    result = f"Created task: {task.title}\nID: {task.id}\nStatus: {task.status}"
    if due_date:
        result += f"\nDue: {due_date.isoformat()}"
    if project_link:
        result += f"\nProject: {project_link}"

    return [TextContent(type="text", text=result)]


async def handle_list_tasks(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_list_tasks tool."""
    task_service = get_task_service()

    status_str = args.get("status")
    project = args.get("project")

    if status_str == "today":
        tasks = task_service.list_today()
    elif status_str == "overdue":
        tasks = task_service.list_overdue()
    elif status_str:
        tasks = task_service.list_tasks(status=TaskStatus(status_str), project=project)
    else:
        tasks = task_service.list_tasks(project=project)

    if not tasks:
        return [TextContent(type="text", text="No tasks found.")]

    lines = [f"Found {len(tasks)} task(s):", ""]
    for task in tasks:
        due_str = f" (due: {task.due.isoformat()})" if task.due else ""
        overdue = " [OVERDUE]" if task.is_overdue else ""
        lines.append(f"- [{task.id}] {task.title} ({task.status}){due_str}{overdue}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_complete_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_complete_task tool."""
    task_service = get_task_service()
    query = args["query"]

    task = task_service.complete(query)
    return [TextContent(type="text", text=f"Completed: {task.title} ({task.id})")]


async def handle_start_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_start_task tool."""
    task_service = get_task_service()
    query = args["query"]

    task = task_service.start(query)
    return [TextContent(type="text", text=f"Started: {task.title} ({task.id})\nStatus: next")]


async def handle_defer_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_defer_task tool."""
    task_service = get_task_service()
    query = args["query"]

    task = task_service.defer(query)
    return [TextContent(type="text", text=f"Deferred: {task.title} ({task.id})\nStatus: someday")]


async def handle_get_dashboard(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_get_dashboard tool."""
    dashboard_service = get_dashboard_service()

    date_str = args.get("date")
    for_date = date.today()
    if date_str:
        try:
            for_date = parse_date(date_str)
        except InvalidDateError:
            for_date = date.today()

    content = dashboard_service.generate(for_date)
    return [TextContent(type="text", text=content)]


async def handle_get_context(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_get_context tool."""
    vault_service = get_vault_service()
    packs = args.get("packs", [])

    if not packs:
        return [TextContent(type="text", text="No context packs specified.")]

    content_parts = []
    context_base = vault_service.aio_path / "Context-Packs"

    for pack_name in packs:
        # Search in subdirectories
        found = False
        for subdir in ["Domains", "Systems", "Operating"]:
            pack_path = context_base / subdir / f"{pack_name}.md"
            if pack_path.exists():
                content = pack_path.read_text(encoding="utf-8")
                content_parts.append(f"# Context: {pack_name}\n\n{content}")
                found = True
                break

        if not found:
            # Try direct path
            pack_path = context_base / f"{pack_name}.md"
            if pack_path.exists():
                content = pack_path.read_text(encoding="utf-8")
                content_parts.append(f"# Context: {pack_name}\n\n{content}")
            else:
                content_parts.append(f"# Context: {pack_name}\n\n(Not found)")

    return [TextContent(type="text", text="\n\n---\n\n".join(content_parts))]


async def handle_sync_jira(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_sync_jira tool."""
    jira_service = get_jira_service()
    dry_run = args.get("dry_run", False)

    result = jira_service.sync(dry_run=dry_run)

    lines = []
    if dry_run:
        lines.append("Dry run - no changes made")
        lines.append("")

    lines.append(result.summary())

    if result.created > 0:
        lines.append(f"\nCreated {result.created} task(s):")
        for task_id in result.created_tasks:
            lines.append(f"  - {task_id}")

    if result.updated > 0:
        lines.append(f"\nUpdated {result.updated} task(s):")
        for task_id in result.updated_tasks:
            lines.append(f"  - {task_id}")

    if result.has_errors:
        lines.append("\nErrors:")
        for error in result.errors:
            lines.append(f"  - {error}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_jira_status(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_jira_status tool."""
    jira_service = get_jira_service()
    status = jira_service.get_status()

    lines = ["Jira Sync Status", ""]

    if status["configured"]:
        lines.append("Status: Configured")
    elif status["enabled"]:
        lines.append("Status: Partially configured")
    else:
        lines.append("Status: Not configured")

    lines.append(f"Enabled: {'Yes' if status['enabled'] else 'No'}")
    lines.append(f"Base URL: {status['base_url'] or 'Not set'}")
    lines.append(f"Email: {status['email'] or 'Not set'}")
    lines.append(f"Projects: {', '.join(status['projects']) if status['projects'] else 'None'}")
    lines.append(f"Last Sync: {status['last_sync'] or 'Never'}")
    lines.append(f"Synced Issues: {status['synced_count']}")

    if status["recent_errors"]:
        lines.append("\nRecent Errors:")
        for error in status["recent_errors"]:
            lines.append(f"  - {error}")

    if not status["configured"]:
        lines.append("\nTo configure Jira sync:")
        lines.append("  aio config set jira.enabled true")
        lines.append("  aio config set jira.baseUrl https://your-company.atlassian.net")
        lines.append("  aio config set jira.email your@email.com")
        lines.append("  aio config set jira.projects PROJ1,PROJ2")
        lines.append("  export JIRA_API_TOKEN=your-api-token")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_list_context_packs(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_list_context_packs tool."""
    context_pack_service = get_context_pack_service()

    category_str = args.get("category")
    category = ContextPackCategory(category_str) if category_str else None

    packs = context_pack_service.list_packs(category)

    if not packs:
        return [TextContent(type="text", text="No context packs found.")]

    lines = [f"Found {len(packs)} context pack(s):", ""]
    for pack in packs:
        desc = f" - {pack.description}" if pack.description else ""
        tags = f" [{', '.join(pack.tags)}]" if pack.tags else ""
        lines.append(f"- [{pack.category}] {pack.title} ({pack.id}){desc}{tags}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_add_to_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_to_context_pack tool."""
    context_pack_service = get_context_pack_service()

    pack_id = args["pack"]
    content = args["content"]
    section = args.get("section")

    pack = context_pack_service.append(pack_id, content, section)

    section_msg = f" under section '{section}'" if section else ""
    return [TextContent(
        type="text",
        text=f"Added content to context pack: {pack.title} ({pack.id}){section_msg}",
    )]


async def handle_add_file_to_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_add_file_to_context_pack tool."""
    context_pack_service = get_context_pack_service()

    pack_id = args["pack"]
    file_path = args["file"]
    section = args.get("section")

    pack = context_pack_service.append_file(pack_id, file_path, section)

    section_msg = f" under section '{section}'" if section else ""
    return [TextContent(
        type="text",
        text=f"Added file '{file_path}' to context pack: {pack.title} ({pack.id}){section_msg}",
    )]


async def handle_create_context_pack(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_context_pack tool."""
    context_pack_service = get_context_pack_service()

    title = args["title"]
    category = ContextPackCategory(args["category"])
    content = args.get("content")
    description = args.get("description")
    tags = args.get("tags")

    pack = context_pack_service.create(
        title=title,
        category=category,
        content=content,
        description=description,
        tags=tags,
    )

    result = f"Created context pack: {pack.title}\nID: {pack.id}\nCategory: {pack.category}"
    if description:
        result += f"\nDescription: {description}"
    if tags:
        result += f"\nTags: {', '.join(tags)}"

    return [TextContent(type="text", text=result)]


async def handle_create_project(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_project tool."""
    project_service = get_project_service()

    name = args["name"]
    status_str = args.get("status", "active")
    team = args.get("team")

    status = ProjectStatus(status_str)

    project = project_service.create(
        name=name,
        status=status,
        team=team,
    )

    result = f"Created project: {project.title}\nID: {project.id}\nStatus: {project.status}"
    if team:
        result += f"\nTeam: {team}"

    return [TextContent(type="text", text=result)]


async def handle_create_person(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_create_person tool."""
    person_service = get_person_service()

    name = args["name"]
    team = args.get("team")
    role = args.get("role")
    email = args.get("email")

    person = person_service.create(
        name=name,
        team=team,
        role=role,
        email=email,
    )

    result = f"Created person: {person.name}\nID: {person.id}"
    if team:
        result += f"\nTeam: {team}"
    if role:
        result += f"\nRole: {role}"
    if email:
        result += f"\nEmail: {email}"

    return [TextContent(type="text", text=result)]


async def handle_delegate_task(args: dict[str, Any]) -> list[TextContent]:
    """Handle aio_delegate_task tool."""
    task_service = get_task_service()
    person_service = get_person_service()

    query = args["query"]
    person_query = args["person"]

    # Find the person by ID or name
    person = person_service.find(person_query)
    person_link = f"[[AIO/People/{person_service.get_slug(person.name)}]]"

    # Delegate the task (move to waiting with person)
    task = task_service.wait(query, person_link)

    return [TextContent(
        type="text",
        text=f"Delegated: {task.title} ({task.id})\nWaiting on: {person.name}\nStatus: waiting",
    )]


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
