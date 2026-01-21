"""Unit tests for FileService."""

import re
from pathlib import Path

import pytest

from aio.exceptions import AmbiguousMatchError, FileOutsideVaultError
from aio.services.file import FileService
from aio.services.vault import VaultService


@pytest.fixture
def file_service(vault_service: VaultService) -> FileService:
    """Create a FileService for testing."""
    return FileService(vault_service)


def create_task_file(
    vault: Path,
    task_id: str,
    title: str,
    status: str = "inbox",
) -> Path:
    """Helper to create a task file with frontmatter."""
    folder = vault / "AIO" / "Tasks" / status.capitalize()
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"2024-01-15-{title.lower().replace(' ', '-')}.md"
    filepath = folder / filename
    content = f"""---
id: {task_id}
type: task
status: {status}
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# {title}

## Notes
Test content.
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


class TestFileGet:
    """Tests for FileService.get()."""

    def test_get_file_returns_contents(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should return the file contents."""
        # Create a test file
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("Hello, world!", encoding="utf-8")

        content = file_service.get("AIO/test.md")

        assert content == "Hello, world!"

    def test_get_file_with_relative_path(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should work with relative paths."""
        test_file = initialized_vault / "some" / "nested" / "file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("nested content", encoding="utf-8")

        content = file_service.get("some/nested/file.txt")

        assert content == "nested content"

    def test_get_file_not_found_raises(self, file_service: FileService) -> None:
        """get() should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            file_service.get("nonexistent/file.md")

    def test_get_file_outside_vault_raises(
        self, file_service: FileService
    ) -> None:
        """get() should raise FileOutsideVaultError for paths outside vault."""
        with pytest.raises(FileOutsideVaultError):
            file_service.get("../outside.txt")

    def test_get_file_with_path_traversal_raises(
        self, file_service: FileService
    ) -> None:
        """get() should block path traversal attempts."""
        with pytest.raises(FileOutsideVaultError):
            file_service.get("AIO/../../../etc/passwd")


class TestFileSet:
    """Tests for FileService.set()."""

    def test_set_file_creates_backup(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should create a backup when overwriting existing file."""
        # Create original file
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("original content", encoding="utf-8")

        resolved_path, backup_path = file_service.set("AIO/test.md", "new content")

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8") == "original content"
        assert resolved_path == test_file

    def test_set_file_backup_preserves_structure(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() backup should preserve the relative path structure."""
        # Create nested file
        nested_dir = initialized_vault / "AIO" / "Tasks" / "Inbox"
        nested_dir.mkdir(parents=True, exist_ok=True)
        test_file = nested_dir / "test-task.md"
        test_file.write_text("task content", encoding="utf-8")

        _, backup_path = file_service.set("AIO/Tasks/Inbox/test-task.md", "new task")

        # Backup should be in AIO/Backup/AIO/Tasks/Inbox/
        assert backup_path is not None
        expected_parent = (
            initialized_vault / "AIO" / "Backup" / "AIO" / "Tasks" / "Inbox"
        )
        assert backup_path.parent == expected_parent

    def test_set_file_backup_has_timestamp(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() backup filename should include timestamp."""
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("original", encoding="utf-8")

        _, backup_path = file_service.set("AIO/test.md", "new")

        assert backup_path is not None
        # Filename should match pattern: test-YYYYMMDD-HHMMSS.md
        pattern = r"^test-\d{8}-\d{6}\.md$"
        assert re.match(pattern, backup_path.name), (
            f"Filename {backup_path.name} doesn't match expected pattern"
        )

    def test_set_file_writes_new_content(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should write the new content to the file."""
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("original content", encoding="utf-8")

        file_service.set("AIO/test.md", "new content")

        assert test_file.read_text(encoding="utf-8") == "new content"

    def test_set_file_creates_new_file_no_backup(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should create file without backup when file doesn't exist."""
        resolved_path, backup_path = file_service.set(
            "AIO/new-file.md", "brand new content"
        )

        assert backup_path is None
        new_file = initialized_vault / "AIO" / "new-file.md"
        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "brand new content"
        assert resolved_path == new_file

    def test_set_file_creates_parent_directories(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should create parent directories if they don't exist."""
        _, backup_path = file_service.set("new/nested/path/file.md", "content")

        assert backup_path is None
        new_file = initialized_vault / "new" / "nested" / "path" / "file.md"
        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "content"

    def test_set_file_outside_vault_raises(
        self, file_service: FileService
    ) -> None:
        """set() should raise FileOutsideVaultError for paths outside vault."""
        with pytest.raises(FileOutsideVaultError):
            file_service.set("../outside.txt", "malicious content")

    def test_set_file_atomic_write(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should write atomically (no partial writes on failure)."""
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("original", encoding="utf-8")

        # Write new content
        file_service.set("AIO/test.md", "new content")

        # Verify content is complete (not partial)
        assert test_file.read_text(encoding="utf-8") == "new content"
        # No .tmp file should remain
        assert not (test_file.with_suffix(".md.tmp")).exists()


class TestResolvePath:
    """Tests for FileService._resolve_path()."""

    def test_resolve_relative_path(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """_resolve_path() should resolve relative paths to vault root."""
        resolved = file_service._resolve_path("AIO/test.md")
        assert resolved == initialized_vault / "AIO" / "test.md"

    def test_resolve_absolute_path_inside_vault(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """_resolve_path() should accept absolute paths within vault."""
        absolute = initialized_vault / "AIO" / "test.md"
        resolved = file_service._resolve_path(str(absolute))
        assert resolved == absolute

    def test_resolve_path_outside_vault_raises(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """_resolve_path() should reject paths outside vault."""
        outside = initialized_vault.parent / "outside.txt"
        with pytest.raises(FileOutsideVaultError):
            file_service._resolve_path(str(outside))


class TestQueryLookup:
    """Tests for flexible file lookup by ID, title, or path."""

    def test_get_by_id(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should find file by 4-char ID."""
        create_task_file(initialized_vault, "AB2C", "My Test Task")

        content = file_service.get("AB2C")

        assert "My Test Task" in content
        assert "id: AB2C" in content

    def test_get_by_id_case_insensitive(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should find file by ID case-insensitively."""
        create_task_file(initialized_vault, "XY9Z", "Another Task")

        content = file_service.get("xy9z")

        assert "Another Task" in content

    def test_get_by_title(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should find file by title substring."""
        create_task_file(initialized_vault, "TT2X", "Review Pull Request")

        content = file_service.get("Pull Request")

        assert "Review Pull Request" in content

    def test_get_by_title_case_insensitive(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should find file by title case-insensitively."""
        create_task_file(initialized_vault, "TT3Y", "Fix Database Issue")

        content = file_service.get("database issue")

        assert "Fix Database Issue" in content

    def test_get_by_path_still_works(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should still work with explicit paths."""
        task_file = create_task_file(initialized_vault, "PP4Z", "Path Test")
        relative_path = task_file.relative_to(initialized_vault)

        content = file_service.get(str(relative_path))

        assert "Path Test" in content

    def test_get_ambiguous_title_raises(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """get() should raise AmbiguousMatchError for multiple title matches."""
        create_task_file(initialized_vault, "AM5W", "Review Code Alpha")
        create_task_file(initialized_vault, "AM6V", "Review Code Beta")

        with pytest.raises(AmbiguousMatchError) as exc_info:
            file_service.get("Review Code")

        assert "Review Code" in str(exc_info.value)

    def test_set_by_id(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should update file found by ID."""
        task_file = create_task_file(initialized_vault, "SE2X", "Update Me")
        original_content = task_file.read_text(encoding="utf-8")

        resolved_path, backup_path = file_service.set("SE2X", "new content")

        assert resolved_path == task_file
        assert backup_path is not None
        assert task_file.read_text(encoding="utf-8") == "new content"
        assert backup_path.read_text(encoding="utf-8") == original_content

    def test_set_by_title(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should update file found by title."""
        task_file = create_task_file(initialized_vault, "SE22", "Unique Title Here")

        resolved_path, backup_path = file_service.set("Unique Title", "updated")

        assert resolved_path == task_file
        assert task_file.read_text(encoding="utf-8") == "updated"

    def test_set_new_file_by_path(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should create new file when path doesn't match any ID/title."""
        resolved_path, backup_path = file_service.set(
            "AIO/brand-new.md", "new file content"
        )

        assert backup_path is None
        assert resolved_path.exists()
        assert resolved_path.read_text(encoding="utf-8") == "new file content"

    def test_id_not_found_falls_back_to_path(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """set() should treat non-matching ID-like string as path for new file."""
        # ZZZZ looks like an ID but doesn't exist, but with .md it looks like path
        resolved_path, backup_path = file_service.set("AIO/ZZZZ.md", "content")

        assert resolved_path.exists()
        assert resolved_path.name == "ZZZZ.md"

    def test_backups_not_matched_by_title(
        self, file_service: FileService, initialized_vault: Path
    ) -> None:
        """Title search should skip files in Backup folder."""
        # Create a task and back it up
        create_task_file(initialized_vault, "BK2X", "Backup Test Task")

        # Modify to create backup (preserve title in new content)
        new_content = """---
id: BK2X
type: task
status: inbox
---

# Backup Test Task

Modified content here.
"""
        file_service.set("BK2X", new_content)

        # Now search by title - should find original file, not the backup
        content = file_service.get("Backup Test Task")
        assert "Modified content here" in content  # Should get the current version
