"""CLI commands for ID index management."""

from pathlib import Path

import click
from rich.console import Console

from aio.services.id_index import IdIndex, IdIndexService
from aio.services.vault import VaultService

console = Console()


@click.group()
def index() -> None:
    """Manage the ID index for collision detection."""


@index.command()
@click.option(
    "--check-collisions",
    is_flag=True,
    help="Check for ID collisions across all entities",
)
@click.pass_context
def rebuild(ctx: click.Context, check_collisions: bool) -> None:
    """Rebuild the ID index from the vault.

    Scans all tasks, projects, and people (including completed and archived)
    to rebuild the ID index. This is useful for:

    - Recovery from a corrupted or missing index
    - After manual edits to files
    - After syncing from another device

    Example:
        aio index rebuild
        aio index rebuild --check-collisions
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)

    try:
        vault_service.ensure_initialized()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e

    console.print("[dim]Rebuilding ID index...[/dim]")

    index_service = IdIndexService(vault_service)
    result = index_service.rebuild()

    console.print("[green]Index rebuilt successfully![/green]")
    console.print(f"  Tasks: {len(result.task_ids)}")
    console.print(f"  Projects: {len(result.project_ids)}")
    console.print(f"  People: {len(result.person_ids)}")

    if check_collisions:
        _check_for_collisions(vault_service, result)


@index.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current ID index status.

    Displays information about the ID index including:
    - Whether the index exists
    - Last update time
    - Count of IDs by type
    - Whether the index is stale

    Example:
        aio index status
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)

    try:
        vault_service.ensure_initialized()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e

    index_service = IdIndexService(vault_service)

    if not index_service.index_path.exists():
        console.print("[yellow]No ID index found.[/yellow]")
        console.print("Run [bold]aio index rebuild[/bold] to create one.")
        return

    index = index_service.load()
    is_stale = index_service.is_stale()

    console.print("[bold]ID Index Status[/bold]")
    console.print(f"  Path: {index_service.index_path}")

    if index.updated_at:
        console.print(f"  Last updated: {index.updated_at.isoformat()}")

    console.print(f"  Tasks: {len(index.task_ids)}")
    console.print(f"  Projects: {len(index.project_ids)}")
    console.print(f"  People: {len(index.person_ids)}")

    if is_stale:
        console.print(
            "\n[yellow]Index is stale.[/yellow] "
            "Run [bold]aio index rebuild[/bold] to update."
        )
    else:
        console.print("\n[green]Index is up to date.[/green]")


def _check_for_collisions(
    vault_service: VaultService,  # noqa: ARG001
    index: IdIndex,
) -> None:
    """Check for ID collisions and report them.

    Args:
        vault_service: The vault service (reserved for future use).
        index: The rebuilt index.
    """
    # This is a placeholder for more sophisticated collision detection
    # For now, we just report the counts
    all_ids = index.all_ids()
    total = len(index.task_ids) + len(index.project_ids) + len(index.person_ids)

    if len(all_ids) < total:
        collisions = total - len(all_ids)
        console.print(f"\n[yellow]Warning:[/yellow] Found {collisions} potential ID collision(s)!")
        console.print("Some IDs may be shared across entity types.")
    else:
        console.print("\n[green]No ID collisions detected.[/green]")
