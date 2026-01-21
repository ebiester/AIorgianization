"""Archive command for AIorgianization CLI."""

from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import InvalidDateError, TaskNotFoundError
from aio.models.project import ProjectStatus
from aio.models.task import TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import parse_date
from aio.utils.frontmatter import read_frontmatter, write_frontmatter

console = Console()


@click.group()
def archive() -> None:
    """Archive tasks, projects, areas, or people."""
    pass


@archive.command("task")
@click.argument("query")
@click.pass_context
def archive_task(ctx: click.Context, query: str) -> None:
    """Archive a single task.

    QUERY can be a task ID or title substring.

    Example:
        aio archive task AB2C
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    try:
        task = task_service.archive(query)
        console.print(f"[green]Archived:[/green] {task.title}")
        console.print(f"  ID: [cyan]{task.id}[/cyan]")
    except TaskNotFoundError:
        console.print(f"[red]Task not found:[/red] {query}")
        raise click.Abort() from None


@archive.command("tasks")
@click.option("--before", required=True, help="Archive tasks completed before this date")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.pass_context
def archive_tasks_before(ctx: click.Context, before: str, dry_run: bool) -> None:
    """Archive completed tasks before a date.

    Examples:
        aio archive tasks --before 2024-01-01
        aio archive tasks --before "6 months ago"
        aio archive tasks --before "6 months ago" --dry-run
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    task_service = TaskService(vault_service)

    # Parse date
    try:
        cutoff_date = parse_date(before)
    except InvalidDateError as e:
        console.print(f"[red]Invalid date:[/red] {e}")
        raise click.Abort() from None

    # Get completed tasks
    tasks = task_service.list_tasks(status=TaskStatus.COMPLETED, include_completed=True)

    # Filter by completion date
    to_archive = []
    for task in tasks:
        if task.completed and task.completed.date() < cutoff_date:
            to_archive.append(task)

    if not to_archive:
        console.print(f"[dim]No completed tasks found before {cutoff_date}[/dim]")
        return

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] Would archive {len(to_archive)} task(s):\n")
        for task in to_archive:
            completed_str = task.completed.date().isoformat() if task.completed else "?"
            console.print(f"  - [{task.id}] {task.title} (completed: {completed_str})")
        return

    # Archive tasks
    archived_count = 0
    for task in to_archive:
        try:
            task_service.archive(task.id)
            archived_count += 1
        except Exception as e:
            console.print(f"[red]Failed to archive {task.id}:[/red] {e}")

    console.print(f"[green]Archived {archived_count} task(s)[/green]")


@archive.command("project")
@click.argument("name")
@click.option("--with-tasks", is_flag=True, help="Also archive linked tasks")
@click.pass_context
def archive_project(ctx: click.Context, name: str, with_tasks: bool) -> None:
    """Archive a project.

    NAME is the project name.

    Example:
        aio archive project "Q4 Migration"
        aio archive project "Q4 Migration" --with-tasks
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)

    # Find project file
    projects_folder = vault_service.projects_folder()
    project_file = None

    for f in projects_folder.glob("*.md"):
        if name.lower() in f.stem.lower():
            project_file = f
            break

    if not project_file:
        console.print(f"[red]Project not found:[/red] {name}")
        raise click.Abort()

    # Update project status to archived
    metadata, content = read_frontmatter(project_file)
    metadata["status"] = ProjectStatus.ARCHIVED.value
    write_frontmatter(project_file, metadata, content)

    # Archive project file
    archive_folder = vault_service.archive_folder("Projects")
    archive_folder.mkdir(parents=True, exist_ok=True)
    dest = archive_folder / project_file.name
    project_file.rename(dest)
    console.print(f"[green]Archived project:[/green] {project_file.stem}")

    if with_tasks:
        task_service = TaskService(vault_service)
        tasks = task_service.list_tasks(project=name, include_completed=True)
        for task in tasks:
            try:
                task_service.archive(task.id)
                console.print(f"  Archived task: {task.title}")
            except Exception:
                pass
