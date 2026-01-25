"""Command handlers for the AIO daemon.

These handlers are shared between the Unix socket and HTTP transports.
They operate on the VaultCache for fast reads and use services for writes.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from aio.daemon.cache import VaultCache
from aio.daemon.protocol import ErrorCode, JsonRpcResponse, exception_to_error_code
from aio.exceptions import AioError, InvalidDateError
from aio.models.context_pack import ContextPackCategory
from aio.models.project import ProjectStatus
from aio.models.task import Task, TaskStatus
from aio.services.context_pack import ContextPackService
from aio.services.dashboard import DashboardService
from aio.services.file import FileService
from aio.services.person import PersonService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import parse_date

logger = logging.getLogger(__name__)


@dataclass
class HandlerContext:
    """Context providing access to services and cache for handlers."""

    vault_service: VaultService
    task_service: TaskService
    project_service: ProjectService
    person_service: PersonService
    dashboard_service: DashboardService
    context_pack_service: ContextPackService
    file_service: FileService
    cache: VaultCache


def task_to_dict(task: Task) -> dict[str, Any]:
    """Convert a Task to a dictionary for JSON serialization.

    Args:
        task: The task to convert.

    Returns:
        Dictionary representation of the task.
    """
    status_value = task.status.value if isinstance(task.status, TaskStatus) else task.status
    result: dict[str, Any] = {
        "id": task.id,
        "title": task.title,
        "status": status_value,
        "created": task.created.isoformat(),
        "updated": task.updated.isoformat(),
        "is_overdue": task.is_overdue,
        "is_due_today": task.is_due_today,
    }
    if task.due:
        result["due"] = task.due.isoformat()
    if task.project:
        result["project"] = task.project
    if task.waiting_on:
        result["waiting_on"] = task.waiting_on
    if task.assigned_to:
        result["assigned_to"] = task.assigned_to
    if task.tags:
        result["tags"] = task.tags
    if task.time_estimate:
        result["time_estimate"] = task.time_estimate
    if task.completed:
        result["completed"] = task.completed.isoformat()
    return result


# Handler functions


async def handle_list_tasks(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """List tasks with optional filtering.

    Args:
        ctx: Handler context.
        params: Parameters including optional 'status' and 'project'.

    Returns:
        Dictionary with 'tasks' list and 'count'.
    """
    status_str = params.get("status")
    project = params.get("project")

    # Use cache for fast lookups
    if status_str == "today":
        tasks = ctx.cache.list_tasks_today()
    elif status_str == "overdue":
        tasks = ctx.cache.list_tasks_overdue()
    elif status_str:
        tasks = ctx.cache.list_tasks(TaskStatus(status_str))
    else:
        tasks = ctx.cache.list_tasks()

    # Filter by project if specified
    if project:
        project_lower = project.lower()
        tasks = [
            t for t in tasks
            if t.project and project_lower in t.project.lower()
        ]

    return {
        "tasks": [task_to_dict(t) for t in tasks],
        "count": len(tasks),
    }


async def handle_get_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Get a single task by ID or query.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' (ID or title substring).

    Returns:
        Task dictionary.
    """
    query = params["query"]

    # Try cache first for ID lookup
    task = ctx.cache.get_task(query)
    if task:
        return {"task": task_to_dict(task)}

    # Fall back to service for title search
    task = ctx.task_service.find(query)
    return {"task": task_to_dict(task)}


async def handle_add_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Create a new task.

    Args:
        ctx: Handler context.
        params: Parameters including 'title' and optional 'due', 'project', 'status', 'assign'.

    Returns:
        Created task dictionary.
    """
    title = params["title"]
    due_str = params.get("due")
    project = params.get("project")
    status_str = params.get("status", "inbox")

    due_date = None
    if due_str:
        due_date = parse_date(due_str)

    project_link = None
    if project:
        if project.startswith("[["):
            project_link = project
        else:
            found_project = ctx.project_service.find(project)
            project_slug = ctx.project_service.get_slug(found_project.title)
            project_link = f"[[AIO/Projects/{project_slug}]]"

    task = ctx.task_service.create(
        title=title,
        due=due_date,
        project=project_link,
        status=TaskStatus(status_str),
    )

    # Delegate task if assign provided
    if assign := params.get("assign"):
        person = ctx.person_service.find(assign)
        person_slug = ctx.person_service.get_slug(person.name)
        person_link = f"[[AIO/People/{person_slug}]]"
        task = ctx.task_service.wait(task.id, person_link)

    # Refresh cache to include new task
    await ctx.cache.refresh()

    return {"task": task_to_dict(task)}


async def handle_complete_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Mark a task as completed.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' (ID or title substring).

    Returns:
        Updated task dictionary.
    """
    query = params["query"]
    task = ctx.task_service.complete(query)
    await ctx.cache.refresh()
    return {"task": task_to_dict(task)}


async def handle_start_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Move a task to Next status.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' (ID or title substring).

    Returns:
        Updated task dictionary.
    """
    query = params["query"]
    task = ctx.task_service.start(query)
    await ctx.cache.refresh()
    return {"task": task_to_dict(task)}


async def handle_defer_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Move a task to Someday status.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' (ID or title substring).

    Returns:
        Updated task dictionary.
    """
    query = params["query"]
    task = ctx.task_service.defer(query)
    await ctx.cache.refresh()
    return {"task": task_to_dict(task)}


async def handle_delegate_task(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Delegate a task to a person.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' and 'person'.

    Returns:
        Updated task dictionary.
    """
    query = params["query"]
    person_query = params["person"]

    person = ctx.person_service.find(person_query)
    person_link = f"[[AIO/People/{ctx.person_service.get_slug(person.name)}]]"
    task = ctx.task_service.wait(query, person_link)
    await ctx.cache.refresh()

    return {
        "task": task_to_dict(task),
        "delegated_to": person.name,
    }


async def handle_get_dashboard(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Get the daily dashboard content.

    Args:
        ctx: Handler context.
        params: Parameters including optional 'date'.

    Returns:
        Dashboard content.
    """
    date_str = params.get("date")
    for_date = date.today()
    if date_str:
        try:
            for_date = parse_date(date_str)
        except InvalidDateError:
            for_date = date.today()

    content = ctx.dashboard_service.generate(for_date)
    return {"content": content, "date": for_date.isoformat()}


async def handle_list_projects(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """List all projects.

    Args:
        ctx: Handler context.
        params: Parameters including optional 'status'.

    Returns:
        List of projects.
    """
    status_str = params.get("status")
    status = ProjectStatus(status_str) if status_str else None

    projects = ctx.project_service.list_all(status=status)
    return {
        "projects": [
            {
                "id": p.id,
                "title": p.title,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "team": p.team,
            }
            for p in projects
        ],
        "count": len(projects),
    }


async def handle_create_project(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Create a new project.

    Args:
        ctx: Handler context.
        params: Parameters including 'name' and optional 'status', 'team'.

    Returns:
        Created project dictionary.
    """
    name = params["name"]
    status_str = params.get("status", "active")
    team = params.get("team")

    status = ProjectStatus(status_str)
    project = ctx.project_service.create(name=name, status=status, team=team)

    return {
        "id": project.id,
        "title": project.title,
        "status": project.status.value if hasattr(project.status, "value") else project.status,
        "team": team,
    }


async def handle_list_people(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """List all people.

    Args:
        ctx: Handler context.
        params: Parameters (currently unused).

    Returns:
        List of people.
    """
    people = ctx.person_service.list_all()
    return {
        "people": [
            {
                "id": p.id,
                "name": p.name,
                "team": p.team,
                "role": p.role,
            }
            for p in people
        ],
        "count": len(people),
    }


async def handle_create_person(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Create a new person.

    Args:
        ctx: Handler context.
        params: Parameters including 'name' and optional 'team', 'role', 'email'.

    Returns:
        Created person dictionary.
    """
    name = params["name"]
    team = params.get("team")
    role = params.get("role")
    email = params.get("email")

    person = ctx.person_service.create(name=name, team=team, role=role, email=email)

    return {
        "id": person.id,
        "name": person.name,
        "team": team,
        "role": role,
        "email": email,
    }


async def handle_get_context(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Get context pack content.

    Args:
        ctx: Handler context.
        params: Parameters including 'packs' (list of pack names).

    Returns:
        Combined context content.
    """
    packs = params.get("packs", [])
    if not packs:
        return {"content": "", "packs_found": []}

    content_parts = []
    packs_found = []
    context_base = ctx.vault_service.aio_path / "Context-Packs"

    for pack_name in packs:
        found = False
        for subdir in ["Domains", "Systems", "Operating"]:
            pack_path = context_base / subdir / f"{pack_name}.md"
            if pack_path.exists():
                content = pack_path.read_text(encoding="utf-8")
                content_parts.append(f"# Context: {pack_name}\n\n{content}")
                packs_found.append(pack_name)
                found = True
                break

        if not found:
            pack_path = context_base / f"{pack_name}.md"
            if pack_path.exists():
                content = pack_path.read_text(encoding="utf-8")
                content_parts.append(f"# Context: {pack_name}\n\n{content}")
                packs_found.append(pack_name)

    return {
        "content": "\n\n---\n\n".join(content_parts),
        "packs_found": packs_found,
    }


async def handle_list_context_packs(
    ctx: HandlerContext, params: dict[str, Any]
) -> dict[str, Any]:
    """List available context packs.

    Args:
        ctx: Handler context.
        params: Parameters including optional 'category'.

    Returns:
        List of context packs.
    """
    category_str = params.get("category")
    category = ContextPackCategory(category_str) if category_str else None

    packs = ctx.context_pack_service.list_packs(category)
    return {
        "packs": [
            {
                "id": p.id,
                "title": p.title,
                "category": p.category.value if hasattr(p.category, "value") else p.category,
                "description": p.description,
                "tags": p.tags,
            }
            for p in packs
        ],
        "count": len(packs),
    }


async def handle_create_context_pack(
    ctx: HandlerContext, params: dict[str, Any]
) -> dict[str, Any]:
    """Create a new context pack.

    Args:
        ctx: Handler context.
        params: Parameters including 'title', 'category', and optional
            'content', 'description', 'tags'.

    Returns:
        Created context pack dictionary.
    """
    title = params["title"]
    category = ContextPackCategory(params["category"])
    content = params.get("content")
    description = params.get("description")
    tags = params.get("tags")

    pack = ctx.context_pack_service.create(
        title=title,
        category=category,
        content=content,
        description=description,
        tags=tags,
    )

    return {
        "id": pack.id,
        "title": pack.title,
        "category": pack.category.value if hasattr(pack.category, "value") else pack.category,
        "description": description,
        "tags": tags,
    }


async def handle_add_to_context_pack(
    ctx: HandlerContext, params: dict[str, Any]
) -> dict[str, Any]:
    """Add content to a context pack.

    Args:
        ctx: Handler context.
        params: Parameters including 'pack', 'content', and optional 'section'.

    Returns:
        Updated context pack info.
    """
    pack_id = params["pack"]
    content = params["content"]
    section = params.get("section")

    pack = ctx.context_pack_service.append(pack_id, content, section)

    return {
        "id": pack.id,
        "title": pack.title,
        "section": section,
    }


async def handle_add_file_to_context_pack(
    ctx: HandlerContext, params: dict[str, Any]
) -> dict[str, Any]:
    """Add file content to a context pack.

    Args:
        ctx: Handler context.
        params: Parameters including 'pack', 'file', and optional 'section'.

    Returns:
        Updated context pack info.
    """
    pack_id = params["pack"]
    file_path = params["file"]
    section = params.get("section")

    pack = ctx.context_pack_service.append_file(pack_id, file_path, section)

    return {
        "id": pack.id,
        "title": pack.title,
        "file": file_path,
        "section": section,
    }


async def handle_file_get(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Get file contents.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' (ID, title, or path).

    Returns:
        File content.
    """
    query = params["query"]
    content = ctx.file_service.get(query)
    return {"content": content}


async def handle_file_set(ctx: HandlerContext, params: dict[str, Any]) -> dict[str, Any]:
    """Set file contents.

    Args:
        ctx: Handler context.
        params: Parameters including 'query' and 'content'.

    Returns:
        File operation result.
    """
    query = params["query"]
    content = params["content"]

    resolved_path, backup_path = ctx.file_service.set(query, content)

    try:
        relative_file = str(resolved_path.relative_to(ctx.vault_service.vault_path))
    except ValueError:
        relative_file = str(resolved_path)

    result: dict[str, Any] = {"file": relative_file}
    if backup_path:
        try:
            relative_backup = str(backup_path.relative_to(ctx.vault_service.vault_path))
        except ValueError:
            relative_backup = str(backup_path)
        result["backup"] = relative_backup

    return result


# Handler registry

HANDLERS: dict[str, Any] = {
    # Task operations
    "list_tasks": handle_list_tasks,
    "get_task": handle_get_task,
    "add_task": handle_add_task,
    "complete_task": handle_complete_task,
    "start_task": handle_start_task,
    "defer_task": handle_defer_task,
    "delegate_task": handle_delegate_task,
    # Dashboard
    "get_dashboard": handle_get_dashboard,
    # Projects
    "list_projects": handle_list_projects,
    "create_project": handle_create_project,
    # People
    "list_people": handle_list_people,
    "create_person": handle_create_person,
    # Context packs
    "get_context": handle_get_context,
    "list_context_packs": handle_list_context_packs,
    "create_context_pack": handle_create_context_pack,
    "add_to_context_pack": handle_add_to_context_pack,
    "add_file_to_context_pack": handle_add_file_to_context_pack,
    # File operations
    "file_get": handle_file_get,
    "file_set": handle_file_set,
}


async def dispatch_request(
    ctx: HandlerContext,
    method: str,
    params: dict[str, Any] | None,
    request_id: int | str | None = None,
) -> JsonRpcResponse:
    """Dispatch a request to the appropriate handler.

    Args:
        ctx: Handler context with services and cache.
        method: The method name to call.
        params: Method parameters.
        request_id: The request ID to echo back.

    Returns:
        JSON-RPC response.
    """
    handler = HANDLERS.get(method)
    if handler is None:
        return JsonRpcResponse.error_response(
            ErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {method}",
            request_id=request_id,
        )

    try:
        result = await handler(ctx, params or {})
        return JsonRpcResponse.success(result, request_id=request_id)
    except AioError as e:
        code = exception_to_error_code(e)
        return JsonRpcResponse.error_response(
            code,
            str(e),
            request_id=request_id,
        )
    except Exception as e:
        logger.exception("Error handling request %s", method)
        return JsonRpcResponse.error_response(
            ErrorCode.INTERNAL_ERROR,
            str(e),
            request_id=request_id,
        )
