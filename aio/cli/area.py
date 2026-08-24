"""Area commands for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.services.project import ProjectService
from aio.services.vault import VaultService

console = Console()


@click.group()
def area() -> None:
    """Manage ongoing areas of responsibility."""


@area.command("create")
@click.argument("name")
@click.option("--team", help="Optional team wikilink")
@click.pass_context
def create_area(ctx: click.Context, name: str, team: str | None) -> None:
    """Create an area in AIO/Areas/."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    area_item = ProjectService(VaultService(vault_path)).create_area(name, team=team)

    console.print(f"[green]Created area:[/green] {area_item.title}")
    console.print(f"  ID: [cyan]{area_item.id}[/cyan]")

