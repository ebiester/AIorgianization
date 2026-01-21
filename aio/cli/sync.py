"""Sync CLI commands for AIorgianization."""

import click
from rich.console import Console
from rich.table import Table

from aio.services.jira import JiraSyncService
from aio.services.task import TaskService
from aio.services.vault import VaultService

console = Console()


@click.group()
def sync() -> None:
    """Sync tasks with external services."""
    pass


@sync.command(name="jira")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without making changes")
@click.pass_context
def sync_jira(ctx: click.Context, dry_run: bool) -> None:
    """Sync tasks from Jira.

    Imports issues assigned to you from configured Jira projects.
    Creates new tasks or updates existing ones based on Jira state.

    Jira is the source of truth - local changes will be overwritten.
    """
    vault_path = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    jira_service = JiraSyncService(vault_service, task_service)

    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/yellow]\n")

    with console.status("[bold blue]Syncing with Jira..."):
        result = jira_service.sync(dry_run=dry_run)

    # Display results
    if result.total_processed == 0 and not result.has_errors:
        console.print("[green]No issues to sync.[/green]")
        return

    console.print()
    console.print(f"[bold]{result.summary()}[/bold]")
    console.print()

    if result.created > 0:
        console.print(f"[green]Created {result.created} new task(s)[/green]")
        for task_id in result.created_tasks:
            console.print(f"  - {task_id}")

    if result.updated > 0:
        console.print(f"[blue]Updated {result.updated} task(s)[/blue]")
        for task_id in result.updated_tasks:
            console.print(f"  - {task_id}")

    if result.moved > 0:
        console.print(f"[yellow]Moved {result.moved} task(s) to new status[/yellow]")

    if result.skipped > 0:
        console.print(f"[dim]Skipped {result.skipped} unchanged task(s)[/dim]")

    if result.has_errors:
        console.print()
        console.print("[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  [red]- {error}[/red]")


@sync.command(name="status")
@click.pass_context
def sync_status(ctx: click.Context) -> None:
    """Show sync status and configuration."""
    vault_path = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)
    jira_service = JiraSyncService(vault_service, task_service)

    status = jira_service.get_status()

    table = Table(title="Jira Sync Status", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    # Configuration status
    if status["configured"]:
        table.add_row("Status", "[green]Configured[/green]")
    elif status["enabled"]:
        table.add_row("Status", "[yellow]Partially configured[/yellow]")
    else:
        table.add_row("Status", "[red]Not configured[/red]")

    table.add_row("Enabled", "[green]Yes[/green]" if status["enabled"] else "[red]No[/red]")
    table.add_row("Base URL", status["base_url"] or "[dim]Not set[/dim]")
    table.add_row("Email", status["email"] or "[dim]Not set[/dim]")
    projects_str = ", ".join(status["projects"]) if status["projects"] else "[dim]None[/dim]"
    table.add_row("Projects", projects_str)

    # Sync state
    table.add_row("", "")  # Separator
    table.add_row("Last Sync", status["last_sync"] or "[dim]Never[/dim]")
    table.add_row("Synced Issues", str(status["synced_count"]))

    console.print(table)

    # Show recent errors if any
    if status["recent_errors"]:
        console.print()
        console.print("[red]Recent Errors:[/red]")
        for error in status["recent_errors"]:
            console.print(f"  - {error}")

    # Configuration hints
    if not status["configured"]:
        console.print()
        console.print("[yellow]To configure Jira sync:[/yellow]")
        console.print("  aio config set jira.enabled true")
        console.print("  aio config set jira.baseUrl https://your-company.atlassian.net")
        console.print("  aio config set jira.email your@email.com")
        console.print("  aio config set jira.projects PROJ1,PROJ2")
        console.print("  export JIRA_API_TOKEN=your-api-token")
