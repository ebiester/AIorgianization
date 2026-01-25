"""Done command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.cli.client import DaemonClient, DaemonError, DaemonUnavailableError
from aio.daemon.protocol import ErrorCode
from aio.exceptions import AmbiguousMatchError, TaskNotFoundError
from aio.services.task import TaskService
from aio.services.vault import VaultService

console = Console()


@click.command()
@click.argument("query")
@click.pass_context
def done(ctx: click.Context, query: str) -> None:
    """Mark a task as completed.

    QUERY can be a task ID (e.g., AB2C) or a title substring.

    Examples:
        aio done AB2C
        aio done "review PR"
    """
    # Try daemon first for fast response
    client = DaemonClient()
    try:
        if client.is_running():
            _done_via_daemon(client, query)
            return
    except DaemonUnavailableError:
        pass  # Fall through to direct execution

    # Fallback: direct execution
    _done_direct(ctx, query)


def _done_via_daemon(client: DaemonClient, query: str) -> None:
    """Mark task complete via daemon.

    Args:
        client: Connected daemon client.
        query: Task ID or title substring.
    """
    try:
        result = client.complete_task(query)
        task = result["task"]
        console.print(f"[green]Completed:[/green] {task['title']}")
        console.print(f"  ID: [cyan]{task['id']}[/cyan]")
        console.print("  Moved to: Tasks/Completed/")
    except DaemonError as e:
        if e.code == ErrorCode.TASK_NOT_FOUND:
            console.print(f"[red]Task not found:[/red] {query}")
            raise click.Abort() from None
        elif e.code == ErrorCode.AMBIGUOUS_MATCH:
            console.print(f"[red]Multiple matches for '{query}':[/red]")
            console.print("\nUse the task ID to be more specific.")
            raise click.Abort() from None
        else:
            # Re-raise for other errors
            raise


def _done_direct(ctx: click.Context, query: str) -> None:
    """Mark task complete via direct service call.

    Args:
        ctx: Click context with vault_path.
        query: Task ID or title substring.
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.complete(query)
        console.print(f"[green]Completed:[/green] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
        console.print("  Moved to: Tasks/Completed/")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Multiple matches for '{query}':[/red]")
        for match_id in e.matches:
            console.print(f"  - {match_id}")
        console.print("\nUse the task ID to be more specific.")
        raise click.Abort() from None
