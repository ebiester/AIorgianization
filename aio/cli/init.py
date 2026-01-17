"""Init command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.services.vault import VaultService

console = Console()


@click.command()
@click.argument("vault_path", type=click.Path(exists=True, path_type=Path))
def init(vault_path: Path) -> None:
    """Initialize AIO directory structure in an Obsidian vault.

    VAULT_PATH is the path to your Obsidian vault (must contain .obsidian folder).
    """
    vault_service = VaultService()

    try:
        vault_path = vault_service.initialize(vault_path)
        console.print(f"[green]Initialized AIO structure in:[/green] {vault_path}")
        console.print("\nCreated folders:")
        console.print("  AIO/Tasks/Inbox/")
        console.print("  AIO/Tasks/Next/")
        console.print("  AIO/Tasks/Waiting/")
        console.print("  AIO/Tasks/Scheduled/")
        console.print("  AIO/Tasks/Someday/")
        console.print("  AIO/Tasks/Completed/")
        console.print("  AIO/Projects/")
        console.print("  AIO/People/")
        console.print("  AIO/Areas/")
        console.print("  AIO/Dashboard/")
        console.print("  AIO/Archive/...")
        console.print("  .aio/config.yaml")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
