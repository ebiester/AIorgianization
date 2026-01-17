"""Add command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import InvalidDateError
from aio.models.task import TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import format_relative_date, parse_date

console = Console()


@click.command()
@click.argument("title")
@click.option("-d", "--due", help="Due date (e.g., 'tomorrow', 'friday', '2024-01-20')")
@click.option("-p", "--project", help="Project name or wikilink")
@click.option(
    "-s",
    "--status",
    type=click.Choice(["inbox", "next", "scheduled", "someday"]),
    default="inbox",
    help="Initial status (default: inbox)",
)
@click.option("-t", "--tag", multiple=True, help="Add tag(s)")
@click.pass_context
def add(
    ctx: click.Context,
    title: str,
    due: str | None,
    project: str | None,
    status: str,
    tag: tuple[str, ...],
) -> None:
    """Add a new task.

    TITLE is the task title.

    Examples:
        aio add "Review PR"
        aio add "Team meeting prep" -d tomorrow
        aio add "Design API" -d friday -p "Q4 Migration"
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    # Parse due date
    due_date = None
    if due:
        try:
            due_date = parse_date(due)
        except InvalidDateError as e:
            console.print(f"[red]Invalid date:[/red] {e}")
            raise click.Abort()

    # Format project as wikilink if needed
    project_link = None
    if project:
        if not project.startswith("[["):
            project_link = f"[[Projects/{project}]]"
        else:
            project_link = project

    # Create task
    task = task_service.create(
        title=title,
        due=due_date,
        project=project_link,
        status=TaskStatus(status),
        tags=list(tag),
    )

    # Display result
    console.print(f"[green]Created task:[/green] {task.title}")
    console.print(f"  ID: [cyan]{task.id}[/cyan]")
    console.print(f"  Status: {task.status}")
    if due_date:
        console.print(f"  Due: {format_relative_date(due_date)}")
    if project_link:
        console.print(f"  Project: {project_link}")
    if tag:
        console.print(f"  Tags: {', '.join(tag)}")
