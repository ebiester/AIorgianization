"""Status change commands for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

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
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.start(query)
        console.print(f"[green]Started:[/green] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print(f"  Status: [green]next[/green]")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort()
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort()


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
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.defer(query)
        console.print(f"[yellow]Deferred:[/yellow] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print(f"  Status: [dim]someday[/dim]")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort()
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort()


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
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    person_service = PersonService(vault_service)

    # Validate or create person if specified
    person_link = None
    if person:
        # Extract person name from wikilink if provided
        person_name = person
        if person.startswith("[[") and person.endswith("]]"):
            # Extract name from [[People/Name]] or [[Name]]
            inner = person[2:-2]
            person_name = inner.split("/")[-1] if "/" in inner else inner

        # Check if person exists
        if not person_service.exists(person_name):
            if create_person:
                # Create the person
                person_service.create(person_name)
                console.print(f"[green]Created person:[/green] {person_name}")
            else:
                # Error with suggestions
                try:
                    person_service.validate_or_suggest(person_name)
                except PersonNotFoundError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    console.print(
                        f"\nTo create this person, use:\n"
                        f'  aio wait "{query}" "{person_name}" --create-person'
                    )
                    raise click.Abort() from None

        # Format as wikilink using the slug (matches actual filename)
        person_slug = person_service.get_slug(person_name)
        person_link = f"[[AIO/People/{person_slug}]]"

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
