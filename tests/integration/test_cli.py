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
