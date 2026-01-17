"""Dashboard command for AIorgianization CLI."""

from datetime import date
from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import InvalidDateError
from aio.services.dashboard import DashboardService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import parse_date

console = Console()


@click.command()
@click.option("--date", "date_str", help="Generate for specific date (default: today)")
@click.option("--stdout", is_flag=True, help="Print to stdout instead of saving file")
@click.pass_context
def dashboard(ctx: click.Context, date_str: str | None, stdout: bool) -> None:
    """Generate the daily dashboard.

    Creates or updates the dashboard file in AIO/Dashboard/.

    Examples:
        aio dashboard                    # Today's dashboard
        aio dashboard --date 2024-01-15  # Specific date
        aio dashboard --stdout           # Print without saving
    """
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
            raise click.Abort()

    if stdout:
        content = dashboard_service.generate(for_date)
        console.print(content)
    else:
        filepath = dashboard_service.save(for_date)
        console.print(f"[green]Dashboard saved:[/green] {filepath}")
