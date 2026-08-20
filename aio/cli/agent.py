"""Machine-readable CLI commands for chat agents and skills."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from aio.exceptions import AmbiguousMatchError, PersonNotFoundError, ProjectNotFoundError
from aio.models.task import Task, TaskStatus
from aio.services.dashboard import DashboardService
from aio.services.open_brain import OpenBrainService
from aio.services.person import PersonService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.services.vault_index import VaultIndex
from aio.utils import get_slug
from aio.utils.dates import parse_date


def _emit(payload: dict[str, Any], *, error: bool = False) -> None:
    """Write one JSON document to stdout or stderr."""
    click.echo(json.dumps(payload, indent=2, default=str), err=error)


def _execute(operation: Callable[[], dict[str, Any]]) -> None:
    """Execute an agent operation with a stable JSON envelope."""
    try:
        _emit({"ok": True, **operation()})
    except Exception as exc:
        error: dict[str, Any] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if isinstance(exc, AmbiguousMatchError):
            error["matches"] = exc.matches
        _emit({"ok": False, "error": error}, error=True)
        raise click.exceptions.Exit(1) from None


def _services(ctx: click.Context) -> tuple[VaultService, TaskService]:
    """Create direct services for the selected vault."""
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault = VaultService(vault_path)
    return vault, TaskService(vault)


def _task_data(task: Task) -> dict[str, Any]:
    """Serialize a task for agent consumption."""
    data = task.model_dump(mode="json", by_alias=False)
    data["is_overdue"] = task.is_overdue
    data["is_due_today"] = task.is_due_today
    return data


def _project_link(projects: ProjectService, query: str, create: bool) -> str:
    """Resolve a project query to an AIO wikilink."""
    cleaned = query.removeprefix("[[").removesuffix("]]").split("/")[-1]
    try:
        project = projects.find(cleaned)
    except ProjectNotFoundError:
        if not create:
            raise
        project = projects.create(cleaned)
    return f"[[AIO/Projects/{get_slug(project.title)}]]"


def _person_link(people: PersonService, query: str, create: bool) -> str:
    """Resolve a person query to an AIO wikilink."""
    cleaned = query.removeprefix("[[").removesuffix("]]").split("/")[-1]
    try:
        person = people.find(cleaned)
    except PersonNotFoundError:
        if not create:
            raise
        person = people.create(cleaned)
    return f"[[AIO/People/{get_slug(person.name)}]]"


@click.group()
def agent() -> None:
    """Run non-interactive AIO operations with JSON input/output."""


@agent.command("list")
@click.argument(
    "filter",
    required=False,
    type=click.Choice(
        ["inbox", "next", "waiting", "someday", "scheduled", "today", "overdue", "all"]
    ),
)
@click.option("-p", "--project", help="Filter by project")
@click.option("--completed", is_flag=True, help="Include completed tasks")
@click.pass_context
def list_tasks(
    ctx: click.Context,
    filter: str | None,
    project: str | None,
    completed: bool,
) -> None:
    """List tasks as JSON."""

    def operation() -> dict[str, Any]:
        _, tasks = _services(ctx)
        if filter == "today":
            found = tasks.list_today()
        elif filter == "overdue":
            found = tasks.list_overdue()
        elif filter == "all":
            found = tasks.list_tasks(project=project, include_completed=completed)
        elif filter:
            found = tasks.list_tasks(
                status=TaskStatus(filter), project=project, include_completed=completed
            )
        else:
            found = tasks.list_tasks(project=project, include_completed=completed)
        return {"tasks": [_task_data(task) for task in found], "count": len(found)}

    _execute(operation)


@agent.command()
@click.argument("title")
@click.option("-d", "--due", help="Natural-language or ISO due date")
@click.option("-p", "--project", help="Project name or wikilink")
@click.option("--create-project", is_flag=True, help="Create a missing project")
@click.option(
    "-s",
    "--status",
    type=click.Choice(["inbox", "next", "scheduled", "someday"]),
    default="inbox",
    show_default=True,
)
@click.option("-t", "--tag", multiple=True, help="Add a tag")
@click.option("-a", "--assign", help="Delegate to a person")
@click.option("--create-person", is_flag=True, help="Create a missing assignee")
@click.option("--notes", help="Markdown context for the Notes section")
@click.pass_context
def add(
    ctx: click.Context,
    title: str,
    due: str | None,
    project: str | None,
    create_project: bool,
    status: str,
    tag: tuple[str, ...],
    assign: str | None,
    create_person: bool,
    notes: str | None,
) -> None:
    """Create a task and return it as JSON."""

    def operation() -> dict[str, Any]:
        vault, tasks = _services(ctx)
        project_link = None
        if project:
            project_link = _project_link(ProjectService(vault), project, create_project)
        person_link = None
        if assign:
            person_link = _person_link(PersonService(vault), assign, create_person)
        task = tasks.create(
            title=title,
            due=parse_date(due) if due else None,
            project=project_link,
            status=TaskStatus(status),
            tags=list(tag),
            notes=notes,
        )
        if person_link:
            task = tasks.wait(task.id, person_link)
        return {"task": _task_data(task)}

    _execute(operation)


def _change_status(ctx: click.Context, query: str, action: str) -> dict[str, Any]:
    """Apply one task status transition."""
    _, tasks = _services(ctx)
    method = {
        "complete": tasks.complete,
        "start": tasks.start,
        "defer": tasks.defer,
    }[action]
    return {"task": _task_data(method(query))}


@agent.command()
@click.argument("query")
@click.pass_context
def complete(ctx: click.Context, query: str) -> None:
    """Complete a task by ID or unambiguous title query."""
    _execute(lambda: _change_status(ctx, query, "complete"))


@agent.command()
@click.argument("query")
@click.pass_context
def start(ctx: click.Context, query: str) -> None:
    """Move a task to Next."""
    _execute(lambda: _change_status(ctx, query, "start"))


@agent.command()
@click.argument("query")
@click.pass_context
def defer(ctx: click.Context, query: str) -> None:
    """Move a task to Someday."""
    _execute(lambda: _change_status(ctx, query, "defer"))


@agent.command()
@click.argument("query")
@click.argument("person", required=False)
@click.option("--create-person", is_flag=True, help="Create a missing person")
@click.pass_context
def wait(ctx: click.Context, query: str, person: str | None, create_person: bool) -> None:
    """Move a task to Waiting, optionally for a person."""

    def operation() -> dict[str, Any]:
        vault, tasks = _services(ctx)
        person_link = None
        if person:
            person_link = _person_link(PersonService(vault), person, create_person)
        return {"task": _task_data(tasks.wait(query, person_link))}

    _execute(operation)


@agent.command()
@click.option("--date", "date_str", help="Natural-language or ISO dashboard date")
@click.pass_context
def dashboard(ctx: click.Context, date_str: str | None) -> None:
    """Return generated dashboard Markdown as JSON."""

    def operation() -> dict[str, Any]:
        vault, tasks = _services(ctx)
        content = DashboardService(vault, tasks).generate(
            parse_date(date_str) if date_str else None
        )
        return {"content": content}

    _execute(operation)


@agent.command()
@click.argument("query")
@click.option("--scope", help="Limit results to a vault-relative folder")
@click.option("--limit", type=click.IntRange(1, 50), default=10, show_default=True)
@click.pass_context
def search(ctx: click.Context, query: str, scope: str | None, limit: int) -> None:
    """Search current vault content and return ranked results."""

    def operation() -> dict[str, Any]:
        vault, _ = _services(ctx)
        index = VaultIndex(vault)
        index.reconcile()
        results = index.search(query, scope, limit)
        return {"results": results, "count": len(results)}

    _execute(operation)


@agent.command()
@click.argument("query")
@click.option("--max-chars", type=click.IntRange(1000, 100000), default=20000)
@click.pass_context
def resume(ctx: click.Context, query: str, max_chars: int) -> None:
    """Assemble bounded working context for one task."""

    def operation() -> dict[str, Any]:
        vault, tasks = _services(ctx)
        return {"context": OpenBrainService(vault, tasks).resume(query, max_chars)}

    _execute(operation)


@agent.command("link-context")
@click.argument("query")
@click.argument("targets", nargs=-1, required=True)
@click.pass_context
def link_context(ctx: click.Context, query: str, targets: tuple[str, ...]) -> None:
    """Link existing vault documents to a task."""

    def operation() -> dict[str, Any]:
        _, tasks = _services(ctx)
        task = tasks.link_context(query, list(targets))
        return {"task": _task_data(task)}

    _execute(operation)


@agent.command("record-work")
@click.argument("query")
@click.argument("outcome")
@click.option("--current-state")
@click.option("--decisions")
@click.option("--next-action")
@click.option("--reference", "references", multiple=True)
@click.option("--harness", default="codex", show_default=True)
@click.pass_context
def record_work(
    ctx: click.Context,
    query: str,
    outcome: str,
    current_state: str | None,
    decisions: str | None,
    next_action: str | None,
    references: tuple[str, ...],
    harness: str,
) -> None:
    """Append a structured work-log entry to a task."""

    def operation() -> dict[str, Any]:
        _, tasks = _services(ctx)
        task = tasks.record_work(
            query=query,
            outcome=outcome,
            current_state=current_state,
            decisions=decisions,
            next_action=next_action,
            references=list(references),
            harness=harness,
        )
        return {"task": _task_data(task)}

    _execute(operation)


@agent.command("promote-knowledge")
@click.argument("query")
@click.argument("target")
@click.option(
    "--category",
    type=click.Choice(["adr", "project", "area", "context-pack", "person"]),
    required=True,
)
@click.option("--content", required=True)
@click.option("--section")
@click.option("--provenance")
@click.pass_context
def promote_knowledge(
    ctx: click.Context,
    query: str,
    target: str,
    category: str,
    content: str,
    section: str | None,
    provenance: str | None,
) -> None:
    """Promote observed task knowledge into a canonical vault note."""

    def operation() -> dict[str, Any]:
        vault, tasks = _services(ctx)
        path = OpenBrainService(vault, tasks).promote(
            query, target, category, content, section, provenance
        )
        return {"path": path}

    _execute(operation)


@agent.command("index-status")
@click.pass_context
def index_status(ctx: click.Context) -> None:
    """Return derived search-index health."""

    def operation() -> dict[str, Any]:
        vault, _ = _services(ctx)
        return {"index": VaultIndex(vault).status()}

    _execute(operation)
