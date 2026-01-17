"""Add command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import InvalidDateError, ProjectNotFoundError
from aio.models.task import TaskStatus
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import format_relative_date, parse_date

console = Console()


@click.command()
@click.argument("title")
@click.option("-d", "--due", help="Due date (e.g., 'tomorrow', 'friday', '2024-01-20')")
@click.option("-p", "--project", help="Project name or wikilink")
@click.option(
    "--create-project",
    is_flag=True,
    help="Create the project if it doesn't exist",
)
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
    create_project: bool,
    status: str,
    tag: tuple[str, ...],
) -> None:
    """Add a new task.

    TITLE is the task title.

    Examples:
        aio add "Review PR"
        aio add "Team meeting prep" -d tomorrow
        aio add "Design API" -d friday -p "Q4 Migration"
        aio add "New feature" -p "New Project" --create-project
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    project_service = ProjectService(vault_service)

    # Parse due date
    due_date = None
    if due:
        try:
            due_date = parse_date(due)
        except InvalidDateError as e:
            console.print(f"[red]Invalid date:[/red] {e}")
            raise click.Abort() from None

    # Validate or create project
    project_link = None
    if project:
        # Extract project name from wikilink if provided
        project_name = project
        if project.startswith("[[") and project.endswith("]]"):
            # Extract name from [[Projects/Name]] or [[Name]]
            inner = project[2:-2]
            project_name = inner.split("/")[-1] if "/" in inner else inner

        # Check if project exists
        if not project_service.exists(project_name):
            if create_project:
                # Create the project
                project_service.create(project_name)
                console.print(f"[green]Created project:[/green] {project_name}")
            else:
                # Error with suggestions
                try:
                    project_service.validate_or_suggest(project_name)
                except ProjectNotFoundError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    console.print(
                        f"\nTo create this project, use:\n"
                        f"  aio add \"{title}\" -p \"{project_name}\" --create-project"
                    )
                    raise click.Abort() from None

        # Format as wikilink
        project_link = f"[[Projects/{project_name}]]"

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
