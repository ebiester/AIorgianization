"""Unit tests for Task model and TaskService."""

from datetime import date, datetime

import pytest

from aio.exceptions import TaskNotFoundError
from aio.models.task import Task, TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService


class TestTaskModel:
    """Tests for Task Pydantic model."""

    def test_default_values(self) -> None:
        """Task should have sensible defaults."""
        task = Task(id="AB2C", title="Test Task")
        assert task.status == TaskStatus.INBOX
        assert task.type == "task"
        assert task.body == ""
        assert task.tags == []
        assert task.blocked_by == []

    def test_generate_filename(self) -> None:
        """generate_filename should create valid filename."""
        task = Task(
            id="AB2C",
            title="Review PR #123",
            created=datetime(2024, 1, 15, 10, 0, 0),
        )
        filename = task.generate_filename()
        assert filename == "2024-01-15-review-pr-123.md"

    def test_generate_filename_special_chars(self) -> None:
        """generate_filename should handle special characters."""
        task = Task(
            id="AB2C",
            title="Task with @#$ special! chars?",
            created=datetime(2024, 1, 15, 10, 0, 0),
        )
        filename = task.generate_filename()
        assert "@" not in filename
        assert "#" not in filename
        assert "?" not in filename

    def test_is_overdue(self) -> None:
        """is_overdue should detect past due dates."""
        task = Task(
            id="AB2C",
            title="Overdue Task",
            due=date.today() - date.resolution,
        )
        assert task.is_overdue

    def test_is_not_overdue_completed(self) -> None:
        """Completed tasks should not be overdue."""
        task = Task(
            id="AB2C",
            title="Completed Task",
            status=TaskStatus.COMPLETED,
            due=date.today() - date.resolution,
        )
        assert not task.is_overdue

    def test_frontmatter_basic(self) -> None:
        """frontmatter should include required fields."""
        task = Task(id="AB2C", title="Test", status=TaskStatus.NEXT)
        fm = task.frontmatter()
        assert fm["id"] == "AB2C"
        assert fm["type"] == "task"
        assert fm["status"] == "next"
        assert "created" in fm
        assert "updated" in fm

    def test_frontmatter_optional_fields(self) -> None:
        """frontmatter should include optional fields when set."""
        task = Task(
            id="AB2C",
            title="Test",
            due=date(2024, 1, 20),
            project="[[Projects/Test]]",
            tags=["backend", "api"],
        )
        fm = task.frontmatter()
        assert fm["due"] == date(2024, 1, 20)
        assert fm["project"] == "[[Projects/Test]]"
        assert fm["tags"] == ["backend", "api"]


class TestTaskService:
    """Tests for TaskService."""

    def test_create_task(self, vault_service: VaultService) -> None:
        """create should create a task file."""
        task_service = TaskService(vault_service)
        task = task_service.create("Test Task")

        assert task.title == "Test Task"
        assert task.status == TaskStatus.INBOX
        assert len(task.id) == 4

    def test_create_task_with_due(self, vault_service: VaultService) -> None:
        """create should set due date."""
        task_service = TaskService(vault_service)
        due = date.today()
        task = task_service.create("Test Task", due=due)

        assert task.due == due

    def test_create_task_with_project(self, vault_service: VaultService) -> None:
        """create should set project."""
        task_service = TaskService(vault_service)
        task = task_service.create("Test Task", project="[[Projects/Test]]")

        assert task.project == "[[Projects/Test]]"

    def test_get_task_by_id(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """get should retrieve task by ID."""
        task_service = TaskService(vault_service)
        task = task_service.get("AB2C")

        assert task.id == "AB2C"
        assert task.title == "Test Task"

    def test_get_task_not_found(self, vault_service: VaultService) -> None:
        """get should raise TaskNotFoundError."""
        task_service = TaskService(vault_service)
        with pytest.raises(TaskNotFoundError):
            task_service.get("ZZZZ")

    def test_find_by_id(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """find should find task by ID."""
        task_service = TaskService(vault_service)
        task = task_service.find("AB2C")
        assert task.id == "AB2C"

    def test_find_by_title(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """find should find task by title substring."""
        task_service = TaskService(vault_service)
        task = task_service.find("Test")
        assert task.id == "AB2C"

    def test_list_tasks_empty(self, vault_service: VaultService) -> None:
        """list_tasks should return empty list when no tasks."""
        task_service = TaskService(vault_service)
        tasks = task_service.list_tasks()
        assert tasks == []

    def test_list_tasks_by_status(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """list_tasks should filter by status."""
        task_service = TaskService(vault_service)
        inbox_tasks = task_service.list_tasks(status=TaskStatus.INBOX)
        next_tasks = task_service.list_tasks(status=TaskStatus.NEXT)

        assert len(inbox_tasks) == 1
        assert len(next_tasks) == 0

    def test_complete_task(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """complete should change status to completed."""
        task_service = TaskService(vault_service)
        task = task_service.complete("AB2C")

        assert task.status == TaskStatus.COMPLETED
        assert task.completed is not None

    def test_start_task(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """start should change status to next."""
        task_service = TaskService(vault_service)
        task = task_service.start("AB2C")

        assert task.status == TaskStatus.NEXT

    def test_defer_task(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """defer should change status to someday."""
        task_service = TaskService(vault_service)
        task = task_service.defer("AB2C")

        assert task.status == TaskStatus.SOMEDAY

    def test_wait_task(
        self, vault_service: VaultService, sample_task_file: None
    ) -> None:
        """wait should change status to waiting."""
        task_service = TaskService(vault_service)
        task = task_service.wait("AB2C", "Sarah")

        assert task.status == TaskStatus.WAITING
        assert "Sarah" in (task.waiting_on or "")
