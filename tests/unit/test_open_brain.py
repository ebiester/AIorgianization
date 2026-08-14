"""Tests for task-centred retrieval, work logs, and derived indexing."""

from aio.services.open_brain import OpenBrainService
from aio.services.task import TaskService
from aio.services.vault_index import VaultIndex


def test_index_search_and_backlinks(vault_service) -> None:
    """The disposable index finds content and explicit wikilink relationships."""
    note = vault_service.projects_folder() / "Roadmap.md"
    note.write_text("# Roadmap\n\nShip the resilient widget.\n", encoding="utf-8")
    source = vault_service.areas_folder() / "Engineering.md"
    source.write_text("# Engineering\n\nSee [[AIO/Projects/Roadmap]].\n", encoding="utf-8")

    index = VaultIndex(vault_service)
    assert index.reconcile()["indexed"] == 2
    assert index.search("resilient")[0]["path"] == "AIO/Projects/Roadmap.md"
    assert index.backlinks("AIO/Projects/Roadmap.md") == ["AIO/Areas/Engineering.md"]


def test_record_resume_and_promote(vault_service) -> None:
    """Work logging and promotion preserve provenance in canonical Markdown."""
    project = vault_service.projects_folder() / "Roadmap.md"
    project.write_text("# Roadmap\n\n", encoding="utf-8")
    tasks = TaskService(vault_service)
    task = tasks.create("Ship widget")
    tasks.link_context(task.id, ["AIO/Projects/Roadmap"])
    tasks.record_work(task.id, "Validated rollout", next_action="Publish release notes")

    brain = OpenBrainService(vault_service, tasks)
    resumed = brain.resume(task.id)
    assert resumed["task"]["last_worked"] is not None
    assert "Work Log" in resumed["task"]["body"]
    path = brain.promote(task.id, "Widget decision", "adr", "Use staged rollout.", None, None)
    assert path == "AIO/ADRs/Widget-decision.md"
    promoted = (vault_service.vault_path / path).read_text(encoding="utf-8")
    assert task.id in promoted
