"""Status change commands for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.cli.client import DaemonClient, DaemonError, DaemonUnavailableError
from aio.daemon.protocol import ErrorCode
from aio.exceptions import AmbiguousMatchError, PersonNotFoundError, TaskNotFoundError
from aio.services.person import PersonService
from aio.services.task import TaskService
from aio.services.vault import VaultService

console = Console()


@click.command()
@click.argument("query")
@click.pass_context
def start(ctx: click.Context, query: str) -> None:
    """Move a task to Next status.

    QUERY can be a task ID (e.g., AB2C) or a title substring.

    Examples:
        aio start AB2C
        aio start "design API"
    """
    # Try daemon first
    client = DaemonClient()
    try:
        if client.is_running():
            _start_via_daemon(client, query)
            return
    except DaemonUnavailableError:
        pass

    # Fallback: direct execution
    _start_direct(ctx, query)


def _start_via_daemon(client: DaemonClient, query: str) -> None:
    """Start task via daemon."""
    try:
        result = client.start_task(query)
        task = result["task"]
        console.print(f"[green]Started:[/green] {task['title']}")
        console.print(f"  ID: [cyan]{task['id']}[/cyan]")
        console.print("  Status: [green]next[/green]")
    except DaemonError as e:
        if e.code == ErrorCode.TASK_NOT_FOUND:
            console.print(f"[red]Task not found:[/red] {query}")
            raise click.Abort() from None
        elif e.code == ErrorCode.AMBIGUOUS_MATCH:
            console.print(f"[red]Multiple matches for '{query}':[/red]")
            raise click.Abort() from None
        raise


def _start_direct(ctx: click.Context, query: str) -> None:
    """Start task via direct service call."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.start(query)
        console.print(f"[green]Started:[/green] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print("  Status: [green]next[/green]")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort() from None


@click.command()
@click.argument("query")
@click.pass_context
def defer(ctx: click.Context, query: str) -> None:
    """Move a task to Someday status.

    QUERY can be a task ID (e.g., AB2C) or a title substring.

    Examples:
        aio defer AB2C
        aio defer "refactor"
    """
    # Try daemon first
    client = DaemonClient()
    try:
        if client.is_running():
            _defer_via_daemon(client, query)
            return
    except DaemonUnavailableError:
        pass

    # Fallback: direct execution
    _defer_direct(ctx, query)


def _defer_via_daemon(client: DaemonClient, query: str) -> None:
    """Defer task via daemon."""
    try:
        result = client.defer_task(query)
        task = result["task"]
        console.print(f"[yellow]Deferred:[/yellow] {task['title']}")
        console.print(f"  ID: [cyan]{task['id']}[/cyan]")
        console.print("  Status: [dim]someday[/dim]")
    except DaemonError as e:
        if e.code == ErrorCode.TASK_NOT_FOUND:
            console.print(f"[red]Task not found:[/red] {query}")
            raise click.Abort() from None
        elif e.code == ErrorCode.AMBIGUOUS_MATCH:
            console.print(f"[red]Multiple matches for '{query}':[/red]")
            raise click.Abort() from None
        raise


def _defer_direct(ctx: click.Context, query: str) -> None:
    """Defer task via direct service call."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.defer(query)
        console.print(f"[yellow]Deferred:[/yellow] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print("  Status: [dim]someday[/dim]")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort() from None


@click.command()
@click.argument("query")
@click.argument("person", required=False)
@click.option(
    "--create-person",
    is_flag=True,
    help="Create the person if they don't exist",
)
@click.pass_context
def wait(
    ctx: click.Context, query: str, person: str | None, create_person: bool
) -> None:
    """Move a task to Waiting status.

    QUERY can be a task ID (e.g., AB2C) or a title substring.
    PERSON is an optional name to set as waitingOn.

    Examples:
        aio wait AB2C Sarah
        aio wait "design" John
        aio wait AB2C "New Person" --create-person
    """
    # For --create-person, always use direct (needs multiple service calls)
    if create_person:
        _wait_direct(ctx, query, person, create_person)
        return

    # Try daemon first for simple delegate case
    client = DaemonClient()
    try:
        if client.is_running() and person:
            _wait_via_daemon(client, query, person)
            return
    except DaemonUnavailableError:
        pass

    # Fallback: direct execution
    _wait_direct(ctx, query, person, create_person)


def _wait_via_daemon(client: DaemonClient, query: str, person: str) -> None:
    """Delegate task via daemon."""
    # Extract person name from wikilink if provided
    person_query = person
    if person.startswith("[[") and person.endswith("]]"):
        inner = person[2:-2]
        person_query = inner.split("/")[-1] if "/" in inner else inner

    try:
        result = client.delegate_task(query, person_query)
        task = result["task"]
        delegated_to = result.get("delegated_to", person_query)
        console.print(f"[yellow]Waiting:[/yellow] {task['title']}")
        console.print(f"  ID: [cyan]{task['id']}[/cyan]")
        console.print("  Status: [yellow]waiting[/yellow]")
        console.print(f"  Waiting on: {delegated_to}")
    except DaemonError as e:
        if e.code == ErrorCode.TASK_NOT_FOUND:
            console.print(f"[red]Task not found:[/red] {query}")
            raise click.Abort() from None
        elif e.code == ErrorCode.AMBIGUOUS_MATCH:
            console.print(f"[red]Multiple matches for '{query}':[/red]")
            raise click.Abort() from None
        elif e.code == ErrorCode.PERSON_NOT_FOUND:
            console.print(f"[red]Person not found:[/red] {person_query}")
            console.print(
                f"\nTo create this person, use:\n"
                f'  aio wait "{query}" "{person_query}" --create-person'
            )
            raise click.Abort() from None
        raise


def _wait_direct(
    ctx: click.Context, query: str, person: str | None, create_person: bool
) -> None:
    """Wait on task via direct service call."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    person_service = PersonService(vault_service)

    # Validate or create person if specified
    person_link = None
    if person:
        # Extract person name from wikilink if provided
        person_query = person
        if person.startswith("[[") and person.endswith("]]"):
            # Extract name from [[People/Name]] or [[Name]]
            inner = person[2:-2]
            person_query = inner.split("/")[-1] if "/" in inner else inner

        # Try to find person by ID or name
        try:
            found_person = person_service.find(person_query)
            person_slug = person_service.get_slug(found_person.name)
            person_link = f"[[AIO/People/{person_slug}]]"
        except PersonNotFoundError as e:
            if create_person:
                # Create the person with the query as name
                person_service.create(person_query)
                console.print(f"[green]Created person:[/green] {person_query}")
                person_slug = person_service.get_slug(person_query)
                person_link = f"[[AIO/People/{person_slug}]]"
            else:
                console.print(f"[red]Error:[/red] {e}")
                console.print(
                    f"\nTo create this person, use:\n"
                    f'  aio wait "{query}" "{person_query}" --create-person'
                )
                raise click.Abort() from None
        except AmbiguousMatchError as e:
            console.print(f"[red]Multiple people match '{person_query}':[/red]")
            for match_id in e.matches:
                console.print(f"  - {match_id}")
            raise click.Abort() from None

    try:
        task = task_service.wait(query, person_link)
        console.print(f"[yellow]Waiting:[/yellow] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print("  Status: [yellow]waiting[/yellow]")
        if person_link:
            console.print(f"  Waiting on: {person_link}")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort() from None
