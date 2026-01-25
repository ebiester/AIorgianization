"""Integration tests for ID index and collision detection."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from aio.cli.main import cli
from aio.services.id_index import IdIndexService
from aio.services.task import TaskService
from aio.services.vault import VaultService


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestIdIndexRebuildCli:
    """Integration tests for aio index rebuild command."""

    def test_rebuild_creates_index(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """aio index rebuild should create an index file."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "index", "rebuild"]
        )

        assert result.exit_code == 0
        assert "Index rebuilt successfully!" in result.output

        # Verify index file exists
        index_path = initialized_vault / ".aio" / "id-index.json"
        assert index_path.exists()

    def test_rebuild_finds_all_tasks(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """aio index rebuild should find tasks in all locations."""
        vault_service = VaultService(initialized_vault)

        # Create tasks in various locations
        _create_task_file(vault_service, "Inbox", "TSK1")
        _create_task_file(vault_service, "Next", "TSK2")
        _create_task_file(vault_service, "Waiting", "TSK3")

        # Create completed task in year/month subfolder
        completed_folder = vault_service.tasks_folder("completed")
        year_month = completed_folder / "2024" / "01"
        year_month.mkdir(parents=True)
        _create_task_file_in_folder(year_month, "CMP1")

        # Create archived task
        archive_folder = vault_service.archive_folder("Tasks", "inbox")
        archive_folder.mkdir(parents=True, exist_ok=True)
        _create_task_file_in_folder(archive_folder, "ARC1")

        # Run rebuild
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "index", "rebuild"]
        )

        assert result.exit_code == 0
        assert "Tasks: 5" in result.output

    def test_status_shows_index_info(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """aio index status should show index information."""
        # First rebuild to create index
        runner.invoke(
            cli, ["--vault", str(initialized_vault), "index", "rebuild"]
        )

        # Then check status
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "index", "status"]
        )

        assert result.exit_code == 0
        assert "ID Index Status" in result.output
        assert "Tasks:" in result.output
        assert "Index is up to date." in result.output


class TestIdCollisionDetection:
    """Integration tests for ID collision detection across locations."""

    def test_new_task_avoids_completed_task_id(
        self, initialized_vault: Path
    ) -> None:
        """Creating a new task should not reuse a completed task's ID."""
        vault_service = VaultService(initialized_vault)
        task_service = TaskService(vault_service)

        # Create a completed task with a known ID
        completed_folder = vault_service.tasks_folder("completed")
        year_month = completed_folder / "2024" / "01"
        year_month.mkdir(parents=True)
        _create_task_file_in_folder(year_month, "COMP")

        # Rebuild index to include the completed task
        index_service = IdIndexService(vault_service)
        index = index_service.rebuild()
        assert "COMP" in index.task_ids

        # Create multiple new tasks and verify none get the completed ID
        for i in range(10):
            task = task_service.create(title=f"Test Task {i}")
            assert task.id != "COMP", "New task should not reuse completed task's ID"

    def test_new_task_avoids_archived_task_id(
        self, initialized_vault: Path
    ) -> None:
        """Creating a new task should not reuse an archived task's ID."""
        vault_service = VaultService(initialized_vault)
        task_service = TaskService(vault_service)

        # Create an archived task with a known ID
        archive_folder = vault_service.archive_folder("Tasks", "inbox")
        archive_folder.mkdir(parents=True, exist_ok=True)
        _create_task_file_in_folder(archive_folder, "ARCH")

        # Rebuild index to include the archived task
        index_service = IdIndexService(vault_service)
        index = index_service.rebuild()
        assert "ARCH" in index.task_ids

        # Create multiple new tasks and verify none get the archived ID
        for i in range(10):
            task = task_service.create(title=f"Test Task {i}")
            assert task.id != "ARCH", "New task should not reuse archived task's ID"

    def test_index_persists_across_service_instances(
        self, initialized_vault: Path
    ) -> None:
        """ID index should persist and be readable by new service instances."""
        vault_service = VaultService(initialized_vault)

        # First instance creates tasks and adds to index
        task_service1 = TaskService(vault_service)
        task1 = task_service1.create(title="Task 1")
        task2 = task_service1.create(title="Task 2")

        # Second instance should see the same IDs in the index
        index_service2 = IdIndexService(vault_service)
        index = index_service2.load()

        assert task1.id in index.task_ids
        assert task2.id in index.task_ids

    def test_index_detects_manual_file_additions(
        self, initialized_vault: Path
    ) -> None:
        """Index should detect when files are manually added to vault."""
        vault_service = VaultService(initialized_vault)

        # Create initial index
        index_service = IdIndexService(vault_service)
        index_service.rebuild()

        # Manually add a file (simulating user action)
        _create_task_file(vault_service, "Inbox", "MANU")

        # Index should now be stale
        assert index_service.is_stale() is True

        # Rebuild should find the new ID
        index = index_service.rebuild()
        assert "MANU" in index.task_ids


class TestCrossEntityCollisions:
    """Tests for collision detection across entity types."""

    def test_collision_check_reports_cross_type_duplicates(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """Collision check should detect IDs shared across entity types."""
        vault_service = VaultService(initialized_vault)

        # Create a task and a project with the same ID (simulating a bug)
        _create_task_file(vault_service, "Inbox", "DUPE")
        _create_project_file(vault_service, "DUPE")

        # Run rebuild with collision check
        result = runner.invoke(
            cli,
            ["--vault", str(initialized_vault), "index", "rebuild", "--check-collisions"],
        )

        assert result.exit_code == 0
        # The collision should be detected
        assert "collision" in result.output.lower()


# Helper functions


def _create_task_file(vault_service: VaultService, status: str, task_id: str) -> Path:
    """Create a task file in the given status folder."""
    folder = vault_service.tasks_folder(status.lower())
    folder.mkdir(parents=True, exist_ok=True)
    return _create_task_file_in_folder(folder, task_id)


def _create_task_file_in_folder(folder: Path, task_id: str) -> Path:
    """Create a task file in an arbitrary folder."""
    filename = f"test-{task_id.lower()}.md"
    filepath = folder / filename
    content = f"""---
id: {task_id}
type: task
status: inbox
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---
# Test Task {task_id}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def _create_project_file(vault_service: VaultService, project_id: str) -> Path:
    """Create a project file."""
    folder = vault_service.projects_folder()
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"test-{project_id.lower()}.md"
    filepath = folder / filename
    content = f"""---
id: {project_id}
type: project
status: active
---
# Test Project {project_id}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath
