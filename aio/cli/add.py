"""Add command for AIorgianization CLI."""

from datetime import date
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from aio.cli.client import DaemonClient, DaemonError, DaemonUnavailableError
from aio.daemon.protocol import ErrorCode
from aio.exceptions import (
    AmbiguousMatchError,
    InvalidDateError,
    PersonNotFoundError,
    ProjectNotFoundError,
)
from aio.models.task import TaskStatus
from aio.services.person import PersonService
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
@click.option(
    "-a",
    "--assign",
    help="Delegate task to a person (moves to Waiting status)",
)
@click.pass_context
def add(
    ctx: click.Context,
    title: str,
    due: str | None,
    project: str | None,
    create_project: bool,
    status: str,
    tag: tuple[str, ...],
    assign: str | None,
) -> None:
    """Add a new task.

    TITLE is the task title.

    Examples:
        aio add "Review PR"
        aio add "Team meeting prep" -d tomorrow
        aio add "Design API" -d friday -p "Q4 Migration"
        aio add "New feature" -p "New Project" --create-project
        aio add "Review PR" --assign Sarah
    """
    # Use direct for --create-project or tags (daemon doesn't support these yet)
    if create_project or tag:
        _add_direct(ctx, title, due, project, create_project, status, tag, assign)
        return

    # Try daemon first
    client = DaemonClient()
    try:
        if client.is_running():
            _add_via_daemon(client, title, due, project, status, assign)
            return
    except DaemonUnavailableError:
        pass

    # Fallback: direct execution
    _add_direct(ctx, title, due, project, create_project, status, tag, assign)


def _add_via_daemon(
    client: DaemonClient,
    title: str,
    due: str | None,
    project: str | None,
    status: str,
    assign: str | None,
) -> None:
    """Add task via daemon."""
    # Extract project name from wikilink if provided
    project_query = None
    if project:
        project_query = project
        if project.startswith("[[") and project.endswith("]]"):
            inner = project[2:-2]
            project_query = inner.split("/")[-1] if "/" in inner else inner

    try:
        result = client.add_task(
            title=title,
            due=due,
            project=project_query,
            status=status,
            assign=assign,
        )
        task = result["task"]
        _display_created_task(task, due)
    except DaemonError as e:
        if e.code == ErrorCode.INVALID_DATE:
            console.print(f"[red]Invalid date:[/red] {due}")
            raise click.Abort() from None
        elif e.code == ErrorCode.PROJECT_NOT_FOUND:
            console.print(f"[red]Project not found:[/red] {project_query}")
            console.print(
                f"\nTo create this project, use:\n"
                f'  aio add "{title}" -p "{project_query}" --create-project'
            )
            raise click.Abort() from None
        elif e.code == ErrorCode.AMBIGUOUS_MATCH:
            console.print("[red]Multiple matches[/red]")
            raise click.Abort() from None
        elif e.code == ErrorCode.PERSON_NOT_FOUND:
            console.print(f"[red]Person not found:[/red] {assign}")
            raise click.Abort() from None
        raise


def _display_created_task(task: dict[str, Any], due_str: str | None) -> None:
    """Display created task info."""
    console.print(f"[green]Created task:[/green] {task['title']}")
    console.print(f"  ID: [cyan]{task['id']}[/cyan]")
    console.print(f"  Status: {task['status']}")
    if task.get("waiting_on"):
        console.print(f"  Waiting on: {task['waiting_on']}")
    if task.get("due"):
        due_date = date.fromisoformat(task["due"])
        console.print(f"  Due: {format_relative_date(due_date)}")
    if task.get("project"):
        console.print(f"  Project: {task['project']}")


def _add_direct(
    ctx: click.Context,
    title: str,
    due: str | None,
    project: str | None,
    create_project: bool,
    status: str,
    tag: tuple[str, ...],
    assign: str | None,
) -> None:
    """Add task via direct service call."""
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

    # Delegate task if --assign provided
    if assign:
        person_service = PersonService(vault_service)
        try:
            person = person_service.find(assign)
        except PersonNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort() from None
        except AmbiguousMatchError as e:
            console.print(f"[red]Multiple people match '{assign}':[/red]")
            for match_id in e.matches:
                console.print(f"  - {match_id}")
            raise click.Abort() from None
        person_slug = person_service.get_slug(person.name)
        person_link = f"[[AIO/People/{person_slug}]]"
        task = task_service.wait(task.id, person_link)

    # Display result
    console.print(f"[green]Created task:[/green] {task.title}")
    console.print(f"  ID: [cyan]{task.id}[/cyan]")
    # Cast to str in case status is TaskStatus enum (after wait())
    status_display = task.status.value if hasattr(task.status, "value") else task.status
    console.print(f"  Status: {status_display}")
    if task.waiting_on:
        console.print(f"  Waiting on: {task.waiting_on}")
    if due_date:
        console.print(f"  Due: {format_relative_date(due_date)}")
    if project_link:
        console.print(f"  Project: {project_link}")
    if tag:
        console.print(f"  Tags: {', '.join(tag)}")
