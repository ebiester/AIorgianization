"""Config CLI commands for AIorgianization."""

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.tree import Tree

from aio.services.vault import VaultService

console = Console()


def _get_nested_value(d: dict[str, Any], key: str) -> Any:
    """Get a nested value from a dictionary using dot notation.

    Args:
        d: The dictionary to search.
        key: Dot-separated key path, e.g. "dashboard.showOverdue".

    Returns:
        The value if found, None otherwise.
    """
    parts = key.split(".")
    current = d
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_nested_value(d: dict[str, Any], key: str, value: Any) -> None:
    """Set a nested value in a dictionary using dot notation.

    Args:
        d: The dictionary to modify.
        key: Dot-separated key path, e.g. "dashboard.showOverdue".
        value: The value to set.
    """
    parts = key.split(".")
    current = d
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _parse_value(value: str) -> Any:
    """Parse a string value into appropriate Python type.

    Args:
        value: String value from command line.

    Returns:
        Parsed value (bool, int, list, or string).
    """
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # List (comma-separated)
    if "," in value:
        return [v.strip() for v in value.split(",") if v.strip()]

    # String
    return value


def _format_value(value: Any) -> str:
    """Format a value for display.

    Args:
        value: The value to format.

    Returns:
        Formatted string representation.
    """
    if value is None:
        return "[dim]not set[/dim]"
    if isinstance(value, bool):
        return "[green]true[/green]" if value else "[red]false[/red]"
    if isinstance(value, list):
        if not value:
            return "[dim]empty[/dim]"
        return ", ".join(str(v) for v in value)
    return str(value)


def _render_dict_tree(tree: Tree, d: dict[str, Any], prefix: str = "") -> None:
    """Recursively render a dictionary as a tree.

    Args:
        tree: The Rich Tree object to add to.
        d: The dictionary to render.
        prefix: Key prefix for nested values.
    """
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            branch = tree.add(f"[cyan]{key}[/cyan]")
            _render_dict_tree(branch, value, full_key)
        else:
            tree.add(f"[cyan]{key}[/cyan]: {_format_value(value)}")


@click.group()
def config() -> None:
    """View and modify configuration."""
    pass


@config.command(name="show")
@click.argument("key", required=False)
@click.pass_context
def config_show(ctx: click.Context, key: str | None) -> None:
    """Show configuration values.

    If KEY is provided, show only that value. Otherwise show all config.

    Examples:
        aio config show              # Show all config
        aio config show vault        # Show vault section
        aio config show vault.path   # Show specific value
    """
    vault_path = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    config_data = vault_service.get_config()

    if key:
        value = _get_nested_value(config_data, key)
        if value is None:
            console.print(f"[yellow]Key '{key}' is not set[/yellow]")
        elif isinstance(value, dict):
            tree = Tree(f"[bold cyan]{key}[/bold cyan]")
            _render_dict_tree(tree, value)
            console.print(tree)
        else:
            console.print(f"{key}: {_format_value(value)}")
    else:
        if not config_data:
            console.print("[dim]No configuration set[/dim]")
            return

        tree = Tree("[bold]Configuration[/bold]")
        _render_dict_tree(tree, config_data)
        console.print(tree)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    Use dot notation for nested keys.

    Examples:
        aio config set vault ./my-vault
        aio config set dashboard.showOverdue true
    """
    vault_path = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    config_data = vault_service.get_config()

    parsed_value = _parse_value(value)

    # Convert relative paths to absolute for vault setting
    if key == "vault" and isinstance(parsed_value, str):
        parsed_value = str(Path(parsed_value).expanduser().resolve())

    _set_nested_value(config_data, key, parsed_value)

    vault_service.set_config(config_data)

    # Also update global config when setting vault.path
    if key in ("vault", "vault.path"):
        vault_service._save_global_config(Path(parsed_value))

    console.print(f"[green]Set {key} = {_format_value(parsed_value)}[/green]")


@config.command(name="unset")
@click.argument("key")
@click.pass_context
def config_unset(ctx: click.Context, key: str) -> None:
    """Remove a configuration value.

    Examples:
        aio config unset dashboard.showOverdue
    """
    vault_path = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    config_data = vault_service.get_config()

    # Navigate to parent and delete key
    parts = key.split(".")
    if len(parts) == 1:
        if key in config_data:
            del config_data[key]
            vault_service.set_config(config_data)
            console.print(f"[green]Removed {key}[/green]")
        else:
            console.print(f"[yellow]Key '{key}' not found[/yellow]")
    else:
        parent = _get_nested_value(config_data, ".".join(parts[:-1]))
        if parent is not None and isinstance(parent, dict) and parts[-1] in parent:
            del parent[parts[-1]]
            vault_service.set_config(config_data)
            console.print(f"[green]Removed {key}[/green]")
        else:
            console.print(f"[yellow]Key '{key}' not found[/yellow]")
