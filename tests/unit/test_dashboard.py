"""Unit tests for DashboardService."""

from datetime import date
from pathlib import Path

import pytest

from aio.services.dashboard import DashboardService
from aio.services.task import TaskService
from aio.services.vault import VaultService


class TestDashboardService:
    """Tests for DashboardService."""

    @pytest.fixture
    def dashboard_service(self, initialized_vault: Path) -> DashboardService:
        """Create a DashboardService for testing."""
        vault_service = VaultService(initialized_vault)
        task_service = TaskService(vault_service)
        return DashboardService(vault_service, task_service)

    def test_generate_returns_markdown(self, dashboard_service: DashboardService) -> None:
        """generate should return markdown content."""
        content = dashboard_service.generate()
        assert "---" in content  # frontmatter
        assert "type: dashboard" in content

    def test_generate_callout_wraps_in_callout(
        self, dashboard_service: DashboardService
    ) -> None:
        """generate_callout should wrap content in Obsidian callout."""
        content = dashboard_service.generate_callout()
        assert content.startswith("> [!aio-dashboard]")
        # All content lines should start with >
        for line in content.split("\n"):
            assert line.startswith(">")

    def test_generate_callout_uses_custom_callout_type(
        self, initialized_vault: Path
    ) -> None:
        """generate_callout should use callout type from config."""
        vault_service = VaultService(initialized_vault)
        # Set custom callout type in config
        config = vault_service.get_config()
        config["dashboard"] = {"callout_type": "info"}
        vault_service.set_config(config)

        task_service = TaskService(vault_service)
        dashboard_service = DashboardService(vault_service, task_service)

        content = dashboard_service.generate_callout()
        assert content.startswith("> [!info]")

    def test_save_creates_file(
        self, dashboard_service: DashboardService, initialized_vault: Path
    ) -> None:
        """save should create dashboard file."""
        test_date = date(2024, 1, 15)
        filepath = dashboard_service.save(test_date)

        assert filepath.exists()
        assert filepath.name == "2024-01-15.md"
        assert filepath.parent == initialized_vault / "AIO" / "Dashboard"


class TestDailyNoteIntegration:
    """Tests for daily note embedding."""

    @pytest.fixture
    def vault_with_daily_note(self, initialized_vault: Path) -> Path:
        """Create a vault with a daily note containing the callout marker."""
        # Create Daily folder
        daily_folder = initialized_vault / "Daily"
        daily_folder.mkdir()

        # Create today's daily note with callout placeholder
        today = date.today()
        daily_note = daily_folder / f"{today.isoformat()}.md"
        daily_note.write_text(
            """# Daily Note

## Morning
- Wake up

## Tasks
> [!aio-dashboard]
> Dashboard placeholder

## Notes
- Some notes here
""",
            encoding="utf-8",
        )
        return initialized_vault

    @pytest.fixture
    def dashboard_service_with_daily(
        self, vault_with_daily_note: Path
    ) -> DashboardService:
        """Create DashboardService with daily note configured."""
        vault_service = VaultService(vault_with_daily_note)
        task_service = TaskService(vault_service)
        return DashboardService(vault_service, task_service)

    def test_embed_in_daily_note_replaces_callout(
        self, dashboard_service_with_daily: DashboardService, vault_with_daily_note: Path
    ) -> None:
        """embed_in_daily_note should replace the callout content."""
        filepath = dashboard_service_with_daily.embed_in_daily_note()

        assert filepath is not None
        content = filepath.read_text(encoding="utf-8")

        # Original content should be preserved
        assert "# Daily Note" in content
        assert "## Morning" in content
        assert "## Notes" in content
        assert "- Some notes here" in content

        # Callout should be updated (not the placeholder text)
        assert "Dashboard placeholder" not in content
        assert "> [!aio-dashboard]" in content
        # Should have quick links from dashboard
        assert "Quick Links" in content

    def test_embed_in_daily_note_returns_none_if_not_found(
        self, initialized_vault: Path
    ) -> None:
        """embed_in_daily_note should return None if daily note doesn't exist."""
        vault_service = VaultService(initialized_vault)
        task_service = TaskService(vault_service)
        dashboard_service = DashboardService(vault_service, task_service)

        result = dashboard_service.embed_in_daily_note()
        assert result is None

    def test_embed_appends_if_no_callout_marker(
        self, initialized_vault: Path
    ) -> None:
        """embed_in_daily_note should append if no callout marker exists."""
        # Create Daily folder and note without callout
        daily_folder = initialized_vault / "Daily"
        daily_folder.mkdir()
        today = date.today()
        daily_note = daily_folder / f"{today.isoformat()}.md"
        daily_note.write_text(
            """# Daily Note

## Tasks
- Do something

## Notes
""",
            encoding="utf-8",
        )

        vault_service = VaultService(initialized_vault)
        task_service = TaskService(vault_service)
        dashboard_service = DashboardService(vault_service, task_service)

        filepath = dashboard_service.embed_in_daily_note()

        assert filepath is not None
        content = filepath.read_text(encoding="utf-8")

        # Original content preserved
        assert "# Daily Note" in content
        assert "- Do something" in content

        # Dashboard appended
        assert "> [!aio-dashboard]" in content


class TestVaultDailyNoteSettings:
    """Tests for daily note settings in VaultService."""

    def test_get_daily_note_settings_defaults(self, initialized_vault: Path) -> None:
        """get_daily_note_settings should return defaults when no config."""
        vault_service = VaultService(initialized_vault)
        settings = vault_service.get_daily_note_settings()

        assert settings["folder"] == "Daily"
        assert settings["format"] == "YYYY-MM-DD"
        assert settings["callout"] == "aio-dashboard"

    def test_get_daily_note_settings_from_aio_config(
        self, initialized_vault: Path
    ) -> None:
        """get_daily_note_settings should read from AIO config."""
        vault_service = VaultService(initialized_vault)
        config = vault_service.get_config()
        config["dashboard"] = {
            "daily_note_folder": "Journal",
            "daily_note_format": "YYYY/MM/DD",
            "callout_type": "note",
        }
        vault_service.set_config(config)

        settings = vault_service.get_daily_note_settings()

        assert settings["folder"] == "Journal"
        assert settings["format"] == "YYYY/MM/DD"
        assert settings["callout"] == "note"

    def test_get_daily_note_settings_from_obsidian(
        self, initialized_vault: Path
    ) -> None:
        """get_daily_note_settings should read from Obsidian config."""
        # Create Obsidian daily-notes.json
        daily_notes_config = initialized_vault / ".obsidian" / "daily-notes.json"
        daily_notes_config.write_text(
            '{"folder": "Journal", "format": "YYYY-MM-DD-dddd"}',
            encoding="utf-8",
        )

        vault_service = VaultService(initialized_vault)
        settings = vault_service.get_daily_note_settings()

        assert settings["folder"] == "Journal"
        assert settings["format"] == "YYYY-MM-DD-dddd"

    def test_aio_config_overrides_obsidian(self, initialized_vault: Path) -> None:
        """AIO config should take priority over Obsidian settings."""
        # Create Obsidian daily-notes.json
        daily_notes_config = initialized_vault / ".obsidian" / "daily-notes.json"
        daily_notes_config.write_text(
            '{"folder": "FromObsidian", "format": "YYYY-MM-DD"}',
            encoding="utf-8",
        )

        # Set AIO config (should take priority)
        vault_service = VaultService(initialized_vault)
        config = vault_service.get_config()
        config["dashboard"] = {"daily_note_folder": "FromAIO"}
        vault_service.set_config(config)

        settings = vault_service.get_daily_note_settings()
        assert settings["folder"] == "FromAIO"

    def test_get_daily_note_path(self, initialized_vault: Path) -> None:
        """get_daily_note_path should return correct path for date."""
        vault_service = VaultService(initialized_vault)
        test_date = date(2024, 1, 15)

        path = vault_service.get_daily_note_path(test_date)

        assert path == initialized_vault / "Daily" / "2024-01-15.md"

    def test_get_daily_note_path_custom_format(self, initialized_vault: Path) -> None:
        """get_daily_note_path should support custom date formats."""
        vault_service = VaultService(initialized_vault)
        config = vault_service.get_config()
        config["dashboard"] = {
            "daily_note_folder": "Journal",
            "daily_note_format": "YYYY/MM-DD",
        }
        vault_service.set_config(config)

        test_date = date(2024, 1, 15)
        path = vault_service.get_daily_note_path(test_date)

        assert path == initialized_vault / "Journal" / "2024/01-15.md"
