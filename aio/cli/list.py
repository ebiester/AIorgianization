"""List command for AIorgianization CLI."""

from datetime import date
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from aio.cli.client import DaemonClient, DaemonUnavailableError
from aio.models.task import Task, TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import format_relative_date

console = Console()


@click.command("list")
@click.argument(
    "filter",
    required=False,
    type=click.Choice(
        ["inbox", "next", "waiting", "someday", "scheduled", "today", "overdue", "all"]
    ),
)
@click.option("-p", "--project", help="Filter by project")
@click.option("--completed", is_flag=True, help="Include completed tasks")
@click.pass_context
def list_tasks(
    ctx: click.Context,
    filter: str | None,
    project: str | None,
    completed: bool,
) -> None:
    """List tasks with optional filtering.

    FILTER options:
        inbox     - Unprocessed items
        next      - Ready to work on
        waiting   - Delegated items
        someday   - Deferred items
        scheduled - Calendar-bound items
        today     - Due today + overdue
        overdue   - Past due date
        all       - All tasks

    Examples:
        aio list              # All active tasks
        aio list inbox        # Only inbox
        aio list today        # Due today + overdue
        aio list -p Migration # Tasks for a project
    """
    # Try daemon first for fast response
    client = DaemonClient()
    try:
        if client.is_running():
            _list_tasks_via_daemon(client, filter, project, completed)
            return
    except DaemonUnavailableError:
        pass  # Fall through to direct execution

    # Fallback: direct execution (slower but always works)
    _list_tasks_direct(ctx, filter, project, completed)


def _list_tasks_via_daemon(
    client: DaemonClient,
    filter: str | None,
    project: str | None,
    completed: bool,
) -> None:
    """List tasks using the daemon.

    Args:
        client: Connected daemon client.
        filter: Status filter or special filter (today, overdue, all).
        project: Optional project filter.
        completed: Whether to include completed tasks.
    """
    # Build params for daemon call
    params: dict[str, Any] = {}
    if filter and filter not in ("all",):
        params["status"] = filter
    if project:
        params["project"] = project

    result = client.call("list_tasks", params if params else None)
    tasks_data = result.get("tasks", [])

    # Filter out completed if not requested (daemon doesn't have this filter)
    if not completed:
        tasks_data = [t for t in tasks_data if t.get("status") != "completed"]

    if not tasks_data:
        console.print("[dim]No tasks found[/dim]")
        return

    # Display using the same table format
    _display_tasks_table_from_dicts(tasks_data, filter or "all")


def _list_tasks_direct(
    ctx: click.Context,
    filter: str | None,
    project: str | None,
    completed: bool,
) -> None:
    """List tasks using direct service calls (fallback).

    Args:
        ctx: Click context with vault_path.
        filter: Status filter or special filter.
        project: Optional project filter.
        completed: Whether to include completed tasks.
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    # Get tasks based on filter
    if filter == "today":
        tasks = task_service.list_today()
    elif filter == "overdue":
        tasks = task_service.list_overdue()
    elif filter == "all":
        tasks = task_service.list_tasks(include_completed=completed, project=project)
    elif filter:
        tasks = task_service.list_tasks(
            status=TaskStatus(filter),
            project=project,
            include_completed=completed,
        )
    else:
        tasks = task_service.list_tasks(project=project, include_completed=completed)

    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    # Display as table
    _display_tasks_table(tasks, filter or "all")


def _display_tasks_table(tasks: list[Task], view_name: str) -> None:
    """Display tasks as a rich table.

    Args:
        tasks: List of tasks to display.
        view_name: Name of the current view.
    """
    table = Table(title=f"Tasks ({view_name})")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Status", width=10)
    table.add_column("Title", min_width=20)
    table.add_column("Due", width=12)
    table.add_column("Project", width=15)

    for task in tasks:
        # Format due date with color
        due_str = ""
        if task.due:
            due_str = format_relative_date(task.due)
            if task.is_overdue:
                due_str = f"[red]{due_str}[/red]"
            elif task.is_due_today:
                due_str = f"[yellow]{due_str}[/yellow]"

        # Format status with color
        status_colors = {
            "inbox": "blue",
            "next": "green",
            "waiting": "yellow",
            "scheduled": "magenta",
            "someday": "dim",
            "completed": "dim",
        }
        color = status_colors.get(task.status, "white")
        status_str = f"[{color}]{task.status}[/{color}]"

        # Format project (strip wikilink brackets)
        project_str = ""
        if task.project:
            project_str = task.project.replace("[[", "").replace("]]", "")
            # Shorten path
            if "/" in project_str:
                project_str = project_str.split("/")[-1]

        table.add_row(
            task.id,
            status_str,
            task.title,
            due_str,
            project_str,
        )

    console.print(table)
    console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")


def _display_tasks_table_from_dicts(tasks: list[dict[str, Any]], view_name: str) -> None:
    """Display tasks from daemon response as a rich table.

    Args:
        tasks: List of task dictionaries from daemon.
        view_name: Name of the current view.
    """
    table = Table(title=f"Tasks ({view_name})")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Status", width=10)
    table.add_column("Title", min_width=20)
    table.add_column("Due", width=12)
    table.add_column("Project", width=15)

    for task in tasks:
        # Format due date with color
        due_str = ""
        if due := task.get("due"):
            # Parse ISO date string from daemon
            due_date = date.fromisoformat(due) if isinstance(due, str) else due
            due_str = format_relative_date(due_date)
            if task.get("is_overdue"):
                due_str = f"[red]{due_str}[/red]"
            elif task.get("is_due_today"):
                due_str = f"[yellow]{due_str}[/yellow]"

        # Format status with color
        status = task.get("status", "")
        status_colors = {
            "inbox": "blue",
            "next": "green",
            "waiting": "yellow",
            "scheduled": "magenta",
            "someday": "dim",
            "completed": "dim",
        }
        color = status_colors.get(status, "white")
        status_str = f"[{color}]{status}[/{color}]"

        # Format project (strip wikilink brackets)
        project_str = ""
        if project := task.get("project"):
            project_str = project.replace("[[", "").replace("]]", "")
            # Shorten path
            if "/" in project_str:
                project_str = project_str.split("/")[-1]

        table.add_row(
            task.get("id", ""),
            status_str,
            task.get("title", ""),
            due_str,
            project_str,
        )

    console.print(table)
    console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")
