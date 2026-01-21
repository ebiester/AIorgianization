"""List command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

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
        status_str = task.status
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
