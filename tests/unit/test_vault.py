"""Unit tests for VaultService."""

from pathlib import Path

import pytest

from aio.exceptions import VaultNotFoundError, VaultNotInitializedError
from aio.services.vault import VaultService


class TestVaultService:
    """Tests for VaultService."""

    def test_initialize_creates_structure(self, temp_vault: Path) -> None:
        """init should create AIO directory structure."""
        vault_service = VaultService()
        vault_service.initialize(temp_vault)

        assert (temp_vault / "AIO").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Inbox").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Next").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Waiting").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Scheduled").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Someday").is_dir()
        assert (temp_vault / "AIO" / "Tasks" / "Completed").is_dir()
        assert (temp_vault / "AIO" / "Projects").is_dir()
        assert (temp_vault / "AIO" / "People").is_dir()
        assert (temp_vault / "AIO" / "Dashboard").is_dir()
        assert (temp_vault / "AIO" / "Archive").is_dir()
        assert (temp_vault / ".aio" / "config.yaml").is_file()

    def test_initialize_not_a_vault_raises(self, tmp_path: Path) -> None:
        """init should raise for non-vault directories."""
        not_a_vault = tmp_path / "not_a_vault"
        not_a_vault.mkdir()

        vault_service = VaultService()
        with pytest.raises(VaultNotFoundError):
            vault_service.initialize(not_a_vault)

    def test_is_initialized_true(self, initialized_vault: Path) -> None:
        """is_initialized should return True for initialized vaults."""
        vault_service = VaultService(initialized_vault)
        assert vault_service.is_initialized()

    def test_is_initialized_false(self, temp_vault: Path) -> None:
        """is_initialized should return False before init."""
        vault_service = VaultService(temp_vault)
        assert not vault_service.is_initialized()

    def test_ensure_initialized_raises(self, temp_vault: Path) -> None:
        """ensure_initialized should raise for uninitialized vault."""
        vault_service = VaultService(temp_vault)
        with pytest.raises(VaultNotInitializedError):
            vault_service.ensure_initialized()

    def test_tasks_folder(self, initialized_vault: Path) -> None:
        """tasks_folder should return correct path."""
        vault_service = VaultService(initialized_vault)
        assert vault_service.tasks_folder("inbox") == initialized_vault / "AIO" / "Tasks" / "Inbox"
        assert vault_service.tasks_folder("next") == initialized_vault / "AIO" / "Tasks" / "Next"

    def test_completed_folder_creates_structure(self, initialized_vault: Path) -> None:
        """completed_folder should create year/month structure."""
        vault_service = VaultService(initialized_vault)
        folder = vault_service.completed_folder(2024, 1)

        assert folder == initialized_vault / "AIO" / "Tasks" / "Completed" / "2024" / "01"
        assert folder.is_dir()

    def test_archive_folder(self, initialized_vault: Path) -> None:
        """archive_folder should return correct path."""
        vault_service = VaultService(initialized_vault)

        assert vault_service.archive_folder("Tasks", "inbox") == (
            initialized_vault / "AIO" / "Archive" / "Tasks" / "Inbox"
        )
        assert vault_service.archive_folder("Projects") == (
            initialized_vault / "AIO" / "Archive" / "Projects"
        )
