"""Integration tests for CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from aio.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestInitCommand:
    """Tests for aio init command."""

    def test_init_creates_structure(self, runner: CliRunner, temp_vault: Path) -> None:
        """init should create AIO directory structure."""
        result = runner.invoke(cli, ["init", str(temp_vault)])

        assert result.exit_code == 0
        assert "Initialized AIO structure" in result.output
        assert (temp_vault / "AIO" / "Tasks" / "Inbox").is_dir()

    def test_init_not_a_vault(self, runner: CliRunner, tmp_path: Path) -> None:
        """init should fail for non-vault directories."""
        not_a_vault = tmp_path / "not_a_vault"
        not_a_vault.mkdir()

        result = runner.invoke(cli, ["init", str(not_a_vault)])

        assert result.exit_code != 0


class TestAddCommand:
    """Tests for aio add command."""

    def test_add_task(self, runner: CliRunner, initialized_vault: Path) -> None:
        """add should create a task."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "add", "Test Task"]
        )

        assert result.exit_code == 0
        assert "Created task:" in result.output
        assert "Test Task" in result.output

    def test_add_task_with_due(self, runner: CliRunner, initialized_vault: Path) -> None:
        """add should accept due date."""
        result = runner.invoke(
            cli,
            ["--vault", str(initialized_vault), "add", "Test Task", "-d", "tomorrow"],
        )

        assert result.exit_code == 0
        assert "Due:" in result.output

    def test_add_task_with_project(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """add should accept project (creating it if needed)."""
        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "add", "Test Task",
                "-p", "MyProject",
                "--create-project",
            ],
        )

        assert result.exit_code == 0
        assert "Project:" in result.output


class TestListCommand:
    """Tests for aio list command."""

    def test_list_empty(self, runner: CliRunner, initialized_vault: Path) -> None:
        """list should show message when no tasks."""
        result = runner.invoke(cli, ["--vault", str(initialized_vault), "list"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_list_with_task(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """list should show tasks."""
        result = runner.invoke(cli, ["--vault", str(initialized_vault), "list"])

        assert result.exit_code == 0
        assert "AB2C" in result.output
        assert "Test Task" in result.output

    def test_list_inbox(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """list inbox should filter by status."""
        result = runner.invoke(cli, ["--vault", str(initialized_vault), "list", "inbox"])

        assert result.exit_code == 0
        assert "AB2C" in result.output


class TestDoneCommand:
    """Tests for aio done command."""

    def test_done_by_id(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """done should complete task by ID."""
        result = runner.invoke(cli, ["--vault", str(initialized_vault), "done", "AB2C"])

        assert result.exit_code == 0
        assert "Completed:" in result.output

    def test_done_by_title(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """done should complete task by title."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "done", "Test Task"]
        )

        assert result.exit_code == 0
        assert "Completed:" in result.output

    def test_done_not_found(self, runner: CliRunner, initialized_vault: Path) -> None:
        """done should fail for unknown task."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "done", "ZZZZ"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestStatusCommands:
    """Tests for status change commands."""

    def test_start_command(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """start should move task to next."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "start", "AB2C"]
        )

        assert result.exit_code == 0
        assert "Started:" in result.output

    def test_defer_command(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """defer should move task to someday."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "defer", "AB2C"]
        )

        assert result.exit_code == 0
        assert "Deferred:" in result.output

    def test_wait_command(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """wait should move task to waiting (creating person if needed)."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "wait", "AB2C", "Sarah", "--create-person"]
        )

        assert result.exit_code == 0
        assert "Waiting:" in result.output


class TestDashboardCommand:
    """Tests for aio dashboard command."""

    def test_dashboard_stdout(self, runner: CliRunner, initialized_vault: Path) -> None:
        """dashboard --stdout should print content."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "dashboard", "--stdout"]
        )

        assert result.exit_code == 0
        assert "Quick Links" in result.output

    def test_dashboard_save(self, runner: CliRunner, initialized_vault: Path) -> None:
        """dashboard should save file."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "dashboard"]
        )

        assert result.exit_code == 0
        assert "Dashboard saved:" in result.output


class TestFileCommands:
    """Tests for aio file get/set commands."""

    def test_file_get_command(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """file get should output file contents."""
        # Create a test file
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("Hello from test file!", encoding="utf-8")

        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "file", "get", "AIO/test.md"]
        )

        assert result.exit_code == 0
        assert "Hello from test file!" in result.output

    def test_file_get_not_found(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """file get should fail for missing files."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "file", "get", "nonexistent.md"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_file_set_command_with_backup(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """file set should create backup and update file."""
        # Create original file
        test_file = initialized_vault / "AIO" / "test.md"
        test_file.write_text("original content", encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "file", "set", "AIO/test.md",
                "-c", "new content",
            ],
        )

        assert result.exit_code == 0
        assert "Backup created:" in result.output
        assert "File updated:" in result.output

        # Verify file was updated
        assert test_file.read_text(encoding="utf-8") == "new content"

        # Verify backup exists
        backup_folder = initialized_vault / "AIO" / "Backup" / "AIO"
        assert backup_folder.exists()
        backup_files = list(backup_folder.glob("test-*.md"))
        assert len(backup_files) == 1
        assert backup_files[0].read_text(encoding="utf-8") == "original content"

    def test_file_set_new_file_no_backup(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """file set should create new file without backup."""
        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "file", "set", "AIO/new-file.md",
                "-c", "brand new content",
            ],
        )

        assert result.exit_code == 0
        assert "File updated:" in result.output
        # Should not mention backup for new files
        assert "Backup created:" not in result.output

        # Verify file was created
        new_file = initialized_vault / "AIO" / "new-file.md"
        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "brand new content"

    def test_file_set_from_input_file(
        self, runner: CliRunner, initialized_vault: Path, tmp_path: Path
    ) -> None:
        """file set should read content from input file."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("content from source file", encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "file", "set", "AIO/target.md",
                "-f", str(source_file),
            ],
        )

        assert result.exit_code == 0
        target_file = initialized_vault / "AIO" / "target.md"
        assert target_file.read_text(encoding="utf-8") == "content from source file"

    def test_file_set_outside_vault_fails(
        self, runner: CliRunner, initialized_vault: Path
    ) -> None:
        """file set should reject paths outside vault."""
        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "file", "set", "../outside.txt",
                "-c", "malicious content",
            ],
        )

        assert result.exit_code != 0
        assert "outside vault" in result.output.lower()

    def test_file_get_by_id(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """file get should work with task ID."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "file", "get", "AB2C"]
        )

        assert result.exit_code == 0
        assert "Test Task" in result.output

    def test_file_get_by_title(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """file get should work with title substring."""
        result = runner.invoke(
            cli, ["--vault", str(initialized_vault), "file", "get", "Test Task"]
        )

        assert result.exit_code == 0
        assert "id: AB2C" in result.output

    def test_file_set_by_id(
        self, runner: CliRunner, initialized_vault: Path, sample_task_file: Path
    ) -> None:
        """file set should work with task ID."""
        result = runner.invoke(
            cli,
            [
                "--vault", str(initialized_vault),
                "file", "set", "AB2C",
                "-c", "Updated by ID",
            ],
        )

        assert result.exit_code == 0
        assert "Backup created:" in result.output
        assert "File updated:" in result.output

        # Verify content was updated
        assert "Updated by ID" in sample_task_file.read_text(encoding="utf-8")
