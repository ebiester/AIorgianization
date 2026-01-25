"""Unit tests for ID index service."""

import json
import time
from pathlib import Path

from aio.services.id_index import IdIndex, IdIndexService
from aio.services.vault import VaultService


def skip_if_not_implemented() -> None:
    """Skip test if IdIndexService is not yet implemented."""
    # IdIndexService is now implemented, so this is a no-op.
    # Keeping the function for backwards compatibility with test structure.
    pass


class TestIdIndexLoad:
    """Tests for loading the ID index."""

    def test_load_returns_empty_index_when_file_missing(
        self, vault_service: VaultService
    ) -> None:
        """load() should return empty index when id-index.json doesn't exist."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        index = service.load()

        assert index is not None
        assert index.task_ids == set()
        assert index.project_ids == set()
        assert index.person_ids == set()

    def test_load_reads_existing_index(
        self, vault_service: VaultService
    ) -> None:
        """load() should read and parse existing id-index.json."""
        skip_if_not_implemented()
        # Create index file
        index_path = vault_service.config_path / "id-index.json"
        index_data = {
            "version": 1,
            "updatedAt": "2024-06-01T12:00:00Z",
            "fingerprint": "abc123",
            "taskIds": ["AB2C", "XY9Z"],
            "projectIds": ["PR01"],
            "personIds": ["PE01"],
        }
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        service = IdIndexService(vault_service)
        index = service.load()

        assert "AB2C" in index.task_ids
        assert "XY9Z" in index.task_ids
        assert "PR01" in index.project_ids
        assert "PE01" in index.person_ids

    def test_load_handles_corrupted_json(
        self, vault_service: VaultService
    ) -> None:
        """load() should return empty index when JSON is corrupted."""
        skip_if_not_implemented()
        index_path = vault_service.config_path / "id-index.json"
        index_path.write_text("not valid json {{{", encoding="utf-8")

        service = IdIndexService(vault_service)
        index = service.load()

        # Should return empty index, not crash
        assert index.task_ids == set()

    def test_load_handles_missing_fields(
        self, vault_service: VaultService
    ) -> None:
        """load() should handle index with missing optional fields."""
        skip_if_not_implemented()
        index_path = vault_service.config_path / "id-index.json"
        index_data = {
            "version": 1,
            "taskIds": ["AB2C"],
            # Missing projectIds, personIds, fingerprint, updatedAt
        }
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        service = IdIndexService(vault_service)
        index = service.load()

        assert "AB2C" in index.task_ids
        assert index.project_ids == set()
        assert index.person_ids == set()


class TestIdIndexSave:
    """Tests for saving the ID index."""

    def test_save_creates_index_file(
        self, vault_service: VaultService
    ) -> None:
        """save() should create id-index.json in .aio/ directory."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        index = IdIndex(
            task_ids={"AB2C", "XY9Z"},
            project_ids={"PR01"},
            person_ids={"PE01"},
        )
        service.save(index)

        index_path = vault_service.config_path / "id-index.json"
        assert index_path.exists()

        data = json.loads(index_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert set(data["taskIds"]) == {"AB2C", "XY9Z"}
        assert set(data["projectIds"]) == {"PR01"}
        assert set(data["personIds"]) == {"PE01"}
        assert "updatedAt" in data
        assert "fingerprint" in data

    def test_save_creates_config_dir_if_missing(
        self, temp_vault: Path
    ) -> None:
        """save() should create .aio/ directory if it doesn't exist."""
        skip_if_not_implemented()
        # temp_vault doesn't have .aio/ initialized
        vault_service = VaultService(temp_vault)

        service = IdIndexService(vault_service)
        index = IdIndex(task_ids={"AB2C"})
        service.save(index)

        assert vault_service.config_path.exists()
        assert (vault_service.config_path / "id-index.json").exists()

    def test_save_overwrites_existing_index(
        self, vault_service: VaultService
    ) -> None:
        """save() should overwrite existing index file."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)

        # Save first index
        index1 = IdIndex(task_ids={"OLD1"})
        service.save(index1)

        # Save second index
        index2 = IdIndex(task_ids={"NEW1", "NEW2"})
        service.save(index2)

        # Load and verify
        loaded = service.load()
        assert "OLD1" not in loaded.task_ids
        assert "NEW1" in loaded.task_ids
        assert "NEW2" in loaded.task_ids


class TestIdIndexRebuild:
    """Tests for rebuilding the ID index from disk."""

    def test_rebuild_scans_active_task_folders(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan all active task status folders."""
        skip_if_not_implemented()
        # Create tasks in different status folders
        _create_task_file(vault_service, "Inbox", "TSK1")
        _create_task_file(vault_service, "Next", "TSK2")
        _create_task_file(vault_service, "Waiting", "TSK3")
        _create_task_file(vault_service, "Someday", "TSK4")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "TSK1" in index.task_ids
        assert "TSK2" in index.task_ids
        assert "TSK3" in index.task_ids
        assert "TSK4" in index.task_ids

    def test_rebuild_scans_completed_subfolders(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan Completed/YYYY/MM subfolders."""
        skip_if_not_implemented()
        # Create completed tasks in year/month subfolders
        completed_folder = vault_service.tasks_folder("completed")
        year_folder = completed_folder / "2024" / "01"
        year_folder.mkdir(parents=True)
        _create_task_file_in_folder(year_folder, "CMP1")

        year_folder2 = completed_folder / "2024" / "06"
        year_folder2.mkdir(parents=True)
        _create_task_file_in_folder(year_folder2, "CMP2")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "CMP1" in index.task_ids
        assert "CMP2" in index.task_ids

    def test_rebuild_scans_archive_task_folders(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan Archive/Tasks/* folders."""
        skip_if_not_implemented()
        # Create archived tasks
        archive_inbox = vault_service.archive_folder("Tasks", "inbox")
        archive_inbox.mkdir(parents=True, exist_ok=True)
        _create_task_file_in_folder(archive_inbox, "ARC1")

        archive_next = vault_service.archive_folder("Tasks", "next")
        archive_next.mkdir(parents=True, exist_ok=True)
        _create_task_file_in_folder(archive_next, "ARC2")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "ARC1" in index.task_ids
        assert "ARC2" in index.task_ids

    def test_rebuild_scans_projects(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan Projects folder."""
        skip_if_not_implemented()
        _create_project_file(vault_service, "PRJ1")
        _create_project_file(vault_service, "PRJ2")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "PRJ1" in index.project_ids
        assert "PRJ2" in index.project_ids

    def test_rebuild_scans_archive_projects(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan Archive/Projects folder."""
        skip_if_not_implemented()
        archive_projects = vault_service.archive_folder("Projects")
        archive_projects.mkdir(parents=True, exist_ok=True)
        _create_entity_file_in_folder(archive_projects, "APRJ", "project")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "APRJ" in index.project_ids

    def test_rebuild_scans_people(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan People folder."""
        skip_if_not_implemented()
        _create_person_file(vault_service, "PER1")
        _create_person_file(vault_service, "PER2")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "PER1" in index.person_ids
        assert "PER2" in index.person_ids

    def test_rebuild_scans_archive_people(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should scan Archive/People folder."""
        skip_if_not_implemented()
        archive_people = vault_service.archive_folder("People")
        archive_people.mkdir(parents=True, exist_ok=True)
        _create_entity_file_in_folder(archive_people, "APER", "person")

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "APER" in index.person_ids

    def test_rebuild_normalizes_ids_to_uppercase(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should normalize all IDs to uppercase."""
        skip_if_not_implemented()
        # Create file with lowercase ID
        tasks_folder = vault_service.tasks_folder("inbox")
        task_file = tasks_folder / "test-task.md"
        task_file.write_text(
            "---\nid: ab2c\ntype: task\nstatus: inbox\n---\n# Test",
            encoding="utf-8",
        )

        service = IdIndexService(vault_service)
        index = service.rebuild()

        assert "AB2C" in index.task_ids
        assert "ab2c" not in index.task_ids

    def test_rebuild_saves_index_to_disk(
        self, vault_service: VaultService
    ) -> None:
        """rebuild() should save the rebuilt index to disk."""
        skip_if_not_implemented()
        _create_task_file(vault_service, "Inbox", "TSK1")

        service = IdIndexService(vault_service)
        service.rebuild()

        # Verify file exists
        index_path = vault_service.config_path / "id-index.json"
        assert index_path.exists()

        # Verify content
        data = json.loads(index_path.read_text(encoding="utf-8"))
        assert "TSK1" in data["taskIds"]


class TestIdIndexStaleness:
    """Tests for staleness detection."""

    def test_is_stale_returns_true_when_no_index(
        self, vault_service: VaultService
    ) -> None:
        """is_stale() should return True when index file doesn't exist."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        assert service.is_stale() is True

    def test_is_stale_returns_true_when_fingerprint_mismatch(
        self, vault_service: VaultService
    ) -> None:
        """is_stale() should return True when vault fingerprint changed."""
        skip_if_not_implemented()
        # Create initial index
        service = IdIndexService(vault_service)
        _create_task_file(vault_service, "Inbox", "TSK1")
        service.rebuild()

        # Modify vault (add new file) - need to wait for mtime to change
        time.sleep(0.1)
        _create_task_file(vault_service, "Inbox", "TSK2")

        # Index should now be stale
        assert service.is_stale() is True

    def test_is_stale_returns_false_when_fingerprint_matches(
        self, vault_service: VaultService
    ) -> None:
        """is_stale() should return False when vault unchanged."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        _create_task_file(vault_service, "Inbox", "TSK1")
        service.rebuild()

        # Without modifying vault, should not be stale
        assert service.is_stale() is False


class TestIdIndexContains:
    """Tests for checking if an ID exists in the index."""

    def test_contains_task_id(
        self, vault_service: VaultService
    ) -> None:
        """contains() should find task IDs."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        _create_task_file(vault_service, "Inbox", "TSK1")
        service.rebuild()

        assert service.contains("TSK1") is True
        assert service.contains("XXXX") is False

    def test_contains_is_case_insensitive(
        self, vault_service: VaultService
    ) -> None:
        """contains() should be case-insensitive."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        _create_task_file(vault_service, "Inbox", "TSK1")
        service.rebuild()

        assert service.contains("tsk1") is True
        assert service.contains("Tsk1") is True

    def test_contains_checks_all_entity_types(
        self, vault_service: VaultService
    ) -> None:
        """contains() should check tasks, projects, and people."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        _create_task_file(vault_service, "Inbox", "TSK1")
        _create_project_file(vault_service, "PRJ1")
        _create_person_file(vault_service, "PER1")
        service.rebuild()

        assert service.contains("TSK1") is True
        assert service.contains("PRJ1") is True
        assert service.contains("PER1") is True


class TestIdIndexAdd:
    """Tests for adding IDs to the index."""

    def test_add_task_id(
        self, vault_service: VaultService
    ) -> None:
        """add_task_id() should add ID and persist."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        service.add_task_id("NEW1")

        # Reload and verify
        service2 = IdIndexService(vault_service)
        index = service2.load()
        assert "NEW1" in index.task_ids

    def test_add_project_id(
        self, vault_service: VaultService
    ) -> None:
        """add_project_id() should add ID and persist."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        service.add_project_id("PRJ1")

        service2 = IdIndexService(vault_service)
        index = service2.load()
        assert "PRJ1" in index.project_ids

    def test_add_person_id(
        self, vault_service: VaultService
    ) -> None:
        """add_person_id() should add ID and persist."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        service.add_person_id("PER1")

        service2 = IdIndexService(vault_service)
        index = service2.load()
        assert "PER1" in index.person_ids

    def test_add_normalizes_to_uppercase(
        self, vault_service: VaultService
    ) -> None:
        """add methods should normalize IDs to uppercase."""
        skip_if_not_implemented()
        service = IdIndexService(vault_service)
        service.add_task_id("abc1")

        index = service.load()
        assert "ABC1" in index.task_ids
        assert "abc1" not in index.task_ids


class TestIdIndexGetOrRebuild:
    """Tests for get_or_rebuild convenience method."""

    def test_get_or_rebuild_rebuilds_when_no_index(
        self, vault_service: VaultService
    ) -> None:
        """get_or_rebuild() should rebuild when no index exists."""
        skip_if_not_implemented()
        _create_task_file(vault_service, "Inbox", "TSK1")

        service = IdIndexService(vault_service)
        index = service.get_or_rebuild()

        assert "TSK1" in index.task_ids

    def test_get_or_rebuild_returns_cached_when_fresh(
        self, vault_service: VaultService
    ) -> None:
        """get_or_rebuild() should return cached index when not stale."""
        skip_if_not_implemented()
        _create_task_file(vault_service, "Inbox", "TSK1")

        service = IdIndexService(vault_service)
        service.rebuild()

        # Second call should use cache
        index = service.get_or_rebuild()
        assert "TSK1" in index.task_ids

    def test_get_or_rebuild_rebuilds_when_stale(
        self, vault_service: VaultService
    ) -> None:
        """get_or_rebuild() should rebuild when index is stale."""
        skip_if_not_implemented()
        _create_task_file(vault_service, "Inbox", "TSK1")

        service = IdIndexService(vault_service)
        service.rebuild()

        # Add new file to make index stale
        time.sleep(0.1)
        _create_task_file(vault_service, "Inbox", "TSK2")

        # Should rebuild and find new task
        index = service.get_or_rebuild()
        assert "TSK1" in index.task_ids
        assert "TSK2" in index.task_ids


# Helper functions for creating test files


def _create_task_file(vault_service: VaultService, status: str, task_id: str) -> Path:
    """Create a task file in the given status folder."""
    folder = vault_service.tasks_folder(status.lower())
    folder.mkdir(parents=True, exist_ok=True)
    return _create_entity_file_in_folder(folder, task_id, "task", status.lower())


def _create_task_file_in_folder(folder: Path, task_id: str) -> Path:
    """Create a task file in an arbitrary folder."""
    return _create_entity_file_in_folder(folder, task_id, "task", "completed")


def _create_project_file(vault_service: VaultService, project_id: str) -> Path:
    """Create a project file."""
    folder = vault_service.projects_folder()
    folder.mkdir(parents=True, exist_ok=True)
    return _create_entity_file_in_folder(folder, project_id, "project")


def _create_person_file(vault_service: VaultService, person_id: str) -> Path:
    """Create a person file."""
    folder = vault_service.people_folder()
    folder.mkdir(parents=True, exist_ok=True)
    return _create_entity_file_in_folder(folder, person_id, "person")


def _create_entity_file_in_folder(
    folder: Path, entity_id: str, entity_type: str, status: str | None = None
) -> Path:
    """Create an entity file with frontmatter."""
    filename = f"test-{entity_id.lower()}.md"
    filepath = folder / filename

    frontmatter_lines = [
        "---",
        f"id: {entity_id}",
        f"type: {entity_type}",
    ]
    if status:
        frontmatter_lines.append(f"status: {status}")
    frontmatter_lines.extend([
        "---",
        f"# Test {entity_type.title()} {entity_id}",
    ])

    filepath.write_text("\n".join(frontmatter_lines), encoding="utf-8")
    return filepath
