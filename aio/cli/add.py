"""Add command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import AmbiguousMatchError, InvalidDateError, ProjectNotFoundError
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
        project_query = project
        if project.startswith("[[") and project.endswith("]]"):
            # Extract name from [[Projects/Name]] or [[Name]]
            inner = project[2:-2]
            project_query = inner.split("/")[-1] if "/" in inner else inner

        # Try to find project by ID or name
        try:
            found_project = project_service.find(project_query)
            project_slug = project_service.get_slug(found_project.title)
            project_link = f"[[AIO/Projects/{project_slug}]]"
        except ProjectNotFoundError as e:
            if create_project:
                # Create the project with the query as name
                project_service.create(project_query)
                console.print(f"[green]Created project:[/green] {project_query}")
                project_slug = project_service.get_slug(project_query)
                project_link = f"[[AIO/Projects/{project_slug}]]"
            else:
                console.print(f"[red]Error:[/red] {e}")
                console.print(
                    f"\nTo create this project, use:\n"
                    f'  aio add "{title}" -p "{project_query}" --create-project'
                )
                raise click.Abort() from None
        except AmbiguousMatchError as e:
            console.print(f"[red]Multiple projects match '{project_query}':[/red]")
            for match_id in e.matches:
                console.print(f"  - {match_id}")
            raise click.Abort() from None

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
