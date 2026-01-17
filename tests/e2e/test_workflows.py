"""End-to-end workflow tests for AIorgianization."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from aio.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestTaskLifecycleWorkflow:
    """Test complete task lifecycle: add -> list -> start -> done."""

    def test_full_task_lifecycle(self, runner: CliRunner, temp_vault: Path) -> None:
        """Test adding, listing, starting, and completing a task."""
        # Step 1: Initialize vault
        result = runner.invoke(cli, ["init", str(temp_vault)])
        assert result.exit_code == 0

        # Step 2: Add a task
        result = runner.invoke(
            cli,
            ["--vault", str(temp_vault), "add", "Review the Q4 roadmap", "-d", "tomorrow"],
        )
        assert result.exit_code == 0
        assert "Created task:" in result.output

        # Extract task ID from output
        for line in result.output.split("\n"):
            if "ID:" in line:
                task_id = line.split("ID:")[1].strip()
                # Remove any ANSI codes
                task_id = "".join(c for c in task_id if c.isalnum())[:4]
                break

        # Step 3: List tasks - should be in inbox
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "inbox"])
        assert result.exit_code == 0
        assert "Review the Q4 roadmap" in result.output

        # Step 4: Start the task (move to next)
        result = runner.invoke(cli, ["--vault", str(temp_vault), "start", task_id])
        assert result.exit_code == 0
        assert "Started:" in result.output

        # Step 5: Verify task is in next
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "next"])
        assert result.exit_code == 0
        assert "Review the Q4 roadmap" in result.output

        # Step 6: Complete the task
        result = runner.invoke(cli, ["--vault", str(temp_vault), "done", task_id])
        assert result.exit_code == 0
        assert "Completed:" in result.output

        # Step 7: Verify task is no longer in active list
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list"])
        assert result.exit_code == 0
        assert "No tasks found" in result.output


class TestDelegationWorkflow:
    """Test delegation workflow: add -> wait -> follow up."""

    def test_delegation_workflow(self, runner: CliRunner, temp_vault: Path) -> None:
        """Test adding a task and delegating it."""
        # Initialize
        runner.invoke(cli, ["init", str(temp_vault)])

        # Add a task
        result = runner.invoke(
            cli, ["--vault", str(temp_vault), "add", "Design API schema"]
        )
        assert result.exit_code == 0

        # Extract ID
        for line in result.output.split("\n"):
            if "ID:" in line:
                task_id = line.split("ID:")[1].strip()
                task_id = "".join(c for c in task_id if c.isalnum())[:4]
                break

        # Delegate to Sarah
        result = runner.invoke(
            cli, ["--vault", str(temp_vault), "wait", task_id, "Sarah"]
        )
        assert result.exit_code == 0
        assert "Waiting on: Sarah" in result.output

        # Verify in waiting list
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "waiting"])
        assert result.exit_code == 0
        assert "Design API schema" in result.output


class TestDeferWorkflow:
    """Test defer workflow: add -> defer -> reactivate."""

    def test_defer_workflow(self, runner: CliRunner, temp_vault: Path) -> None:
        """Test deferring and reactivating a task."""
        # Initialize
        runner.invoke(cli, ["init", str(temp_vault)])

        # Add a task
        result = runner.invoke(
            cli, ["--vault", str(temp_vault), "add", "Refactor authentication"]
        )
        assert result.exit_code == 0

        # Extract ID
        for line in result.output.split("\n"):
            if "ID:" in line:
                task_id = line.split("ID:")[1].strip()
                task_id = "".join(c for c in task_id if c.isalnum())[:4]
                break

        # Defer the task
        result = runner.invoke(cli, ["--vault", str(temp_vault), "defer", task_id])
        assert result.exit_code == 0
        assert "Deferred:" in result.output

        # Verify in someday list
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "someday"])
        assert result.exit_code == 0
        # Title may be wrapped in Rich table output
        assert "Refactor" in result.output and "authentication" in result.output

        # Reactivate the task
        result = runner.invoke(cli, ["--vault", str(temp_vault), "start", task_id])
        assert result.exit_code == 0
        assert "Started:" in result.output

        # Verify in next list
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "next"])
        assert result.exit_code == 0
        # Title may be wrapped in Rich table output
        assert "Refactor" in result.output and "authentication" in result.output


class TestMultipleTasksWorkflow:
    """Test workflow with multiple tasks."""

    def test_multiple_tasks(self, runner: CliRunner, temp_vault: Path) -> None:
        """Test managing multiple tasks."""
        # Initialize
        runner.invoke(cli, ["init", str(temp_vault)])

        # Add multiple tasks
        tasks = [
            ("Task 1: Review PR", "tomorrow"),
            ("Task 2: Write tests", None),
            ("Task 3: Deploy feature", "friday"),
        ]

        task_ids = []
        for title, due in tasks:
            args = ["--vault", str(temp_vault), "add", title]
            if due:
                args.extend(["-d", due])
            result = runner.invoke(cli, args)
            assert result.exit_code == 0

            for line in result.output.split("\n"):
                if "ID:" in line:
                    task_id = line.split("ID:")[1].strip()
                    task_id = "".join(c for c in task_id if c.isalnum())[:4]
                    task_ids.append(task_id)
                    break

        # Verify all in inbox
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "inbox"])
        assert result.exit_code == 0
        assert "3 task(s)" in result.output

        # Start first task
        runner.invoke(cli, ["--vault", str(temp_vault), "start", task_ids[0]])

        # Defer second task
        runner.invoke(cli, ["--vault", str(temp_vault), "defer", task_ids[1]])

        # Complete third task
        runner.invoke(cli, ["--vault", str(temp_vault), "done", task_ids[2]])

        # Verify final states
        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "next"])
        assert "Task 1" in result.output

        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "someday"])
        assert "Task 2" in result.output

        result = runner.invoke(cli, ["--vault", str(temp_vault), "list", "inbox"])
        assert "No tasks found" in result.output
