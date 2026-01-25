"""Main CLI entry point for AIorgianization."""

import sys
from pathlib import Path

import click
from rich.console import Console

from aio.cli.add import add
from aio.cli.archive import archive
from aio.cli.config import config
from aio.cli.daemon_cmd import daemon
from aio.cli.dashboard import dashboard
from aio.cli.done import done
from aio.cli.file import file
from aio.cli.index import index
from aio.cli.init import init
from aio.cli.list import list_tasks
from aio.cli.plugin import plugin
from aio.cli.status import defer, start, wait
from aio.exceptions import AioError

console = Console()


@click.group()
@click.option("--vault", "-v", type=click.Path(exists=True, path_type=Path), help="Path to vault")
@click.option("--debug/--no-debug", default=False, help="Show debug information")
@click.pass_context
def cli(ctx: click.Context, vault: Path | None, debug: bool) -> None:
    """AIorgianization - Task management for engineering managers.

    An Obsidian-native task management system with CLI and MCP integration.
    """
    ctx.ensure_object(dict)
    ctx.obj["vault_path"] = vault
    ctx.obj["debug"] = debug


@cli.command()
@click.pass_context
def help(ctx: click.Context) -> None:
    """Show this help message."""
    click.echo(ctx.parent.get_help())


# Register commands
cli.add_command(init)
cli.add_command(add)
cli.add_command(list_tasks, name="list")
cli.add_command(done)
cli.add_command(start)
cli.add_command(defer)
cli.add_command(wait)
cli.add_command(dashboard)
cli.add_command(archive)
cli.add_command(config)
cli.add_command(file)
cli.add_command(daemon)
cli.add_command(plugin)
cli.add_command(index)


def main() -> None:
    """Main entry point with error handling."""
    try:
        cli()
    except AioError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        if "--debug" in sys.argv:
            raise
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
