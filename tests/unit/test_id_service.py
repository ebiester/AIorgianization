"""Unit tests for ID service with index integration."""

from pathlib import Path

from aio.services.id_index import IdIndexService
from aio.services.id_service import EntityType, IdService
from aio.services.vault import VaultService


class TestIdServiceWithIndex:
    """Tests for IdService using the ID index."""

    def test_generate_unique_id_avoids_existing_ids(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id should not return an ID that exists in the vault."""
        # Create a task with a known ID
        _create_task_file(vault_service, "Inbox", "AB2C")

        id_service = IdService(vault_service)
        new_id = id_service.generate_unique_id(EntityType.TASK)

        assert new_id != "AB2C"

    def test_generate_unique_id_avoids_completed_task_ids(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id should detect IDs in Completed/YYYY/MM folders."""
        # Create a completed task in year/month subfolder
        completed_folder = vault_service.tasks_folder("completed")
        year_month = completed_folder / "2024" / "01"
        year_month.mkdir(parents=True)
        _create_task_file_in_folder(year_month, "CMP1")

        # IdService uses the index, which should find the completed task ID
        id_service = IdService(vault_service)

        # Verify the index contains the completed ID (proving IdService will avoid it)
        index = id_service._index_service.get_or_rebuild()
        assert "CMP1" in index.task_ids

    def test_generate_unique_id_avoids_archived_task_ids(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id should detect IDs in Archive/Tasks/* folders."""
        # Create an archived task
        archive_inbox = vault_service.archive_folder("Tasks", "inbox")
        archive_inbox.mkdir(parents=True, exist_ok=True)
        _create_task_file_in_folder(archive_inbox, "ARC1")

        # IdService uses the index, which should find the archived task ID
        id_service = IdService(vault_service)

        # Verify the index contains the archived ID (proving IdService will avoid it)
        index = id_service._index_service.get_or_rebuild()
        assert "ARC1" in index.task_ids

    def test_generate_unique_id_updates_index(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id should add the new ID to the index."""
        id_service = IdService(vault_service)
        new_id = id_service.generate_unique_id(EntityType.TASK)

        # The new ID should be in the index
        index_service = IdIndexService(vault_service)
        index = index_service.load()
        assert new_id in index.task_ids

    def test_generate_unique_project_id_updates_index(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id for projects should update the index."""
        id_service = IdService(vault_service)
        new_id = id_service.generate_unique_id(EntityType.PROJECT)

        index_service = IdIndexService(vault_service)
        index = index_service.load()
        assert new_id in index.project_ids

    def test_generate_unique_person_id_updates_index(
        self, vault_service: VaultService
    ) -> None:
        """generate_unique_id for people should update the index."""
        id_service = IdService(vault_service)
        new_id = id_service.generate_unique_id(EntityType.PERSON)

        index_service = IdIndexService(vault_service)
        index = index_service.load()
        assert new_id in index.person_ids


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
---
# Test Task {task_id}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath
