"""Plugin management commands for AIorgianization CLI."""

import click
from rich.console import Console

from aio.services.vault import VaultService

console = Console()


@click.group()
def plugin() -> None:
    """Manage the AIO Obsidian plugin."""
    pass


@plugin.command()
@click.pass_context
def upgrade(ctx: click.Context) -> None:
    """Upgrade the AIO plugin in your Obsidian vault.

    Copies the latest plugin files to .obsidian/plugins/aio/
    and reloads the plugin configuration.
    """
    vault_path = ctx.obj.get("vault_path") if ctx.obj else None
    vault_service = VaultService(vault_path)

    if not vault_service.vault_path:
        console.print("[red]Error:[/red] No vault found. Run 'aio init <vault_path>' first.")
        raise click.Abort()

    try:
        plugin_dir = vault_service.install_plugin()
        console.print(f"[green]Plugin upgraded:[/green] {plugin_dir}")
        console.print("\nTo reload the plugin in Obsidian:")
        console.print("  • Toggle the plugin off and on in Settings → Community plugins")
        console.print("  • Or press Cmd+R (Mac) / Ctrl+R (Windows) to reload Obsidian")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from None


@plugin.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current plugin installation status."""
    vault_path = ctx.obj.get("vault_path") if ctx.obj else None
    vault_service = VaultService(vault_path)

    if not vault_service.vault_path:
        console.print("[red]Error:[/red] No vault found.")
        raise click.Abort()

    plugin_dir = vault_service.vault_path / ".obsidian" / "plugins" / "aio"

    if not plugin_dir.exists():
        console.print("[yellow]Plugin not installed[/yellow]")
        console.print("Run 'aio plugin upgrade' to install.")
        return

    main_js = plugin_dir / "main.js"
    manifest = plugin_dir / "manifest.json"

    if main_js.exists():
        import json
        from datetime import datetime

        mtime = datetime.fromtimestamp(main_js.stat().st_mtime)
        console.print(f"[green]Plugin installed:[/green] {plugin_dir}")
        console.print(f"  Last updated: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        if manifest.exists():
            with open(manifest) as f:
                data = json.load(f)
                console.print(f"  Version: {data.get('version', 'unknown')}")
    else:
        console.print("[yellow]Plugin directory exists but main.js missing[/yellow]")
        console.print("Run 'aio plugin upgrade' to reinstall.")
