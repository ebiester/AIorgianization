"""Project commands for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from aio.exceptions import AmbiguousMatchError, ProjectNotFoundError
from aio.models.project import ProjectStatus
from aio.models.task import Task, TaskStatus
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils import get_slug

console = Console()


@click.group()
def project() -> None:
    """Manage projects and their tasks."""


@project.command("create")
@click.argument("name")
@click.option(
    "--status",
    type=click.Choice(["active", "on-hold"]),
    default="active",
    help="Initial project status (default: active)",
)
@click.option("--team", help="Optional team wikilink")
@click.pass_context
def create_project(
    ctx: click.Context,
    name: str,
    status: str,
    team: str | None,
) -> None:
    """Create a project in AIO/Projects/."""
    project_service, _ = _services(ctx)
    item = project_service.create(name, status=ProjectStatus(status), team=team)

    console.print(f"[green]Created project:[/green] {item.title}")
    console.print(f"  ID: [cyan]{item.id}[/cyan]")


@project.command("list")
@click.pass_context
def list_projects(ctx: click.Context) -> None:
    """List projects with active task counts."""
    project_service, task_service = _services(ctx)
    projects = project_service.list_all()
    tasks = task_service.list_tasks(include_completed=True)

    if not projects:
        console.print("[dim]No projects found[/dim]")
        return

    table = Table(title="Projects")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Project", min_width=20)
    table.add_column("Status", width=12)
    table.add_column("Next", justify="right")
    table.add_column("Waiting", justify="right")
    table.add_column("Open", justify="right")
    table.add_column("Completed", justify="right")

    for item in projects:
        project_tasks = _tasks_for_project(tasks, item.title)
        next_count = _count_status(project_tasks, TaskStatus.NEXT)
        waiting_count = _count_status(project_tasks, TaskStatus.WAITING)
        completed_count = _count_status(project_tasks, TaskStatus.COMPLETED)
        open_count = len([
            task for task in project_tasks if task.status != TaskStatus.COMPLETED
        ])
        table.add_row(
            item.id,
            item.title,
            str(item.status),
            str(next_count),
            str(waiting_count),
            str(open_count),
            str(completed_count),
        )

    console.print(table)


@project.command("show")
@click.argument("query")
@click.pass_context
def show_project(ctx: click.Context, query: str) -> None:
    """Show project details and related tasks."""
    project_service, task_service = _services(ctx)

    try:
        item = project_service.find(query)
    except ProjectNotFoundError as e:
        console.print(f"[red]Project not found:[/red] {query}")
        if e.suggestions:
            console.print("Did you mean?")
            for suggestion in e.suggestions:
                console.print(f"  - {suggestion}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple projects match '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort() from None

    tasks = _tasks_for_project(
        task_service.list_tasks(include_completed=True),
        item.title,
    )

    console.print(f"[bold]{item.title}[/bold]")
    console.print(f"  ID: [cyan]{item.id}[/cyan]")
    console.print(f"  Status: {item.status}")
    if item.team:
        console.print(f"  Team: {item.team}")
    if item.target_date:
        console.print(f"  Target: {item.target_date.isoformat()}")

    if not tasks:
        console.print("\n[dim]No tasks for this project[/dim]")
        return

    table = Table(title="Project Tasks")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Status", width=10)
    table.add_column("Title", min_width=20)
    table.add_column("Due", width=12)

    for task in tasks:
        due = task.due.isoformat() if task.due else ""
        table.add_row(task.id, str(task.status), task.title, due)

    console.print()
    console.print(table)


def _services(ctx: click.Context) -> tuple[ProjectService, TaskService]:
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    return ProjectService(vault_service), TaskService(vault_service)


def _tasks_for_project(tasks: list[Task], project_title: str) -> list[Task]:
    slug = get_slug(project_title).lower()
    title = project_title.lower()
    return [
        task for task in tasks
        if task.project and (slug in task.project.lower() or title in task.project.lower())
    ]


def _count_status(tasks: list[Task], status: TaskStatus) -> int:
    return len([task for task in tasks if task.status == status])
