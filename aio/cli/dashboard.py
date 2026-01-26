"""Dashboard command for AIorgianization CLI."""

from datetime import date
from pathlib import Path

import click
from rich.console import Console

from aio.cli.client import DaemonClient, DaemonUnavailableError
from aio.exceptions import InvalidDateError
from aio.services.dashboard import DashboardService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import parse_date

console = Console()


@click.command()
@click.option("--date", "date_str", help="Generate for specific date (default: today)")
@click.option("--stdout", is_flag=True, help="Print to stdout instead of saving file")
@click.option(
    "--standalone",
    is_flag=True,
    help="Save as standalone file instead of embedding in daily note",
)
@click.pass_context
def dashboard(
    ctx: click.Context, date_str: str | None, stdout: bool, standalone: bool
) -> None:
    """Generate the daily dashboard.

    By default, embeds the dashboard in your daily note (if it exists).
    Falls back to creating a standalone file in AIO/Dashboard/ if the
    daily note is not found.

    Examples:
        aio dashboard                    # Embed in daily note (or standalone fallback)
        aio dashboard --standalone       # Force standalone file
        aio dashboard --date 2024-01-15  # Specific date
        aio dashboard --stdout           # Print without saving
    """
    # For --stdout only, try daemon first
    if stdout:
        client = DaemonClient()
        try:
            if client.is_running():
                _dashboard_via_daemon(client, date_str)
                return
        except DaemonUnavailableError:
            pass

    # Fallback or save mode: use direct
    _dashboard_direct(ctx, date_str, stdout, standalone)


def _dashboard_via_daemon(client: DaemonClient, date_str: str | None) -> None:
    """Get dashboard via daemon (stdout only)."""
    result = client.get_dashboard(date_str)
    content = result.get("content", "")
    console.print(content)


def _dashboard_direct(
    ctx: click.Context, date_str: str | None, stdout: bool, standalone: bool
) -> None:
    """Generate dashboard via direct service call."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    dashboard_service = DashboardService(vault_service, task_service)

    # Parse date if provided
    for_date = date.today()
    if date_str:
        try:
            for_date = parse_date(date_str)
        except InvalidDateError as e:
            console.print(f"[red]Invalid date:[/red] {e}")
            raise click.Abort() from None

    if stdout:
        # Print callout format (for embedding) by default
        content = dashboard_service.generate_callout(for_date)
        console.print(content)
    elif standalone:
        # Explicit standalone mode
        filepath = dashboard_service.save(for_date)
        console.print(f"[green]Dashboard saved:[/green] {filepath}")
    else:
        # Default: try to embed in daily note, fallback to standalone
        filepath = dashboard_service.embed_in_daily_note(for_date)
        if filepath:
            console.print(f"[green]Dashboard embedded in:[/green] {filepath}")
        else:
            # Daily note doesn't exist - fallback to standalone
            filepath = dashboard_service.save(for_date)
            console.print(
                f"[yellow]Daily note not found, saving standalone:[/yellow] {filepath}"
            )
