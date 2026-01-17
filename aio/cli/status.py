"""Status change commands for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import AmbiguousMatchError, TaskNotFoundError
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
@click.pass_context
def wait(ctx: click.Context, query: str, person: str | None) -> None:
    """Move a task to Waiting status.

    QUERY can be a task ID (e.g., AB2C) or a title substring.
    PERSON is an optional name to set as waitingOn.

    Examples:
        aio wait AB2C Sarah
        aio wait "design" John
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.wait(query, person)
        console.print(f"[yellow]Waiting:[/yellow] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print(f"  Status: [yellow]waiting[/yellow]")
        if person:
            console.print(f"  Waiting on: {person}")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort()
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        raise click.Abort()
