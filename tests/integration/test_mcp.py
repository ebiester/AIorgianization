"""Integration tests for MCP server."""

import asyncio
from pathlib import Path

import pytest

from aio.exceptions import ProjectNotFoundError
from aio.mcp.server import (
    ServiceRegistry,
    call_tool,
    get_registry,
    handle_add_task,
    handle_list_tasks,
    handle_complete_task,
    handle_start_task,
    handle_defer_task,
    handle_get_dashboard,
    handle_create_project,
    handle_create_person,
)
from aio.services.dashboard import DashboardService
from aio.services.project import ProjectService
from aio.services.task import TaskService
from aio.services.vault import VaultService


@pytest.fixture
def mcp_registry(initialized_vault: Path) -> ServiceRegistry:
    """Create a service registry configured for testing.

    Returns:
        Configured ServiceRegistry with test vault.
    """
    registry = get_registry()
    registry.reset()
    vault_service = VaultService(initialized_vault)
    registry.set_vault_service(vault_service)
    task_service = TaskService(vault_service)
    registry.set_task_service(task_service)
    dashboard_service = DashboardService(vault_service, task_service)
    registry.set_dashboard_service(dashboard_service)

    # Create a test project for project-related tests
    project_service = ProjectService(vault_service)
    project_service.create("TestProject")

    yield registry
    registry.reset()


class TestServiceRegistry:
    """Tests for the ServiceRegistry class."""

    def test_registry_reset(self, initialized_vault: Path) -> None:
        """reset should clear all cached services."""
        registry = ServiceRegistry()
        vault_service = VaultService(initialized_vault)
        registry.set_vault_service(vault_service)

        assert registry._vault_service is not None
        registry.reset()
        assert registry._vault_service is None

    def test_registry_lazy_initialization(self) -> None:
        """Services should be created lazily on access."""
        registry = ServiceRegistry()
        # Don't access any services yet
        assert registry._vault_service is None
        assert registry._task_service is None

    def test_registry_service_override(self, initialized_vault: Path) -> None:
        """set_*_service should override service instances."""
        registry = ServiceRegistry()
        vault_service = VaultService(initialized_vault)
        registry.set_vault_service(vault_service)

        assert registry.vault_service is vault_service


class TestAddTaskTool:
    """Tests for the aio_add_task MCP tool."""

    def test_add_task_basic(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task should create a task."""
        result = asyncio.run(handle_add_task({"title": "Test MCP Task"}))

        assert len(result) == 1
        assert "Created task:" in result[0].text
        assert "Test MCP Task" in result[0].text
        assert "ID:" in result[0].text

    def test_add_task_with_due(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task should accept due date."""
        result = asyncio.run(handle_add_task({
            "title": "Task with due date",
            "due": "tomorrow",
        }))

        assert len(result) == 1
        assert "Created task:" in result[0].text
        assert "Due:" in result[0].text

    def test_add_task_with_project(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task should accept project."""
        result = asyncio.run(handle_add_task({
            "title": "Task with project",
            "project": "TestProject",
        }))

        assert len(result) == 1
        assert "Created task:" in result[0].text
        assert "Project:" in result[0].text
        assert "TestProject" in result[0].text

    def test_add_task_with_nonexistent_project(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task should raise error for non-existent project."""
        with pytest.raises(ProjectNotFoundError) as exc_info:
            asyncio.run(handle_add_task({
                "title": "Task with missing project",
                "project": "NonExistentProject",
            }))

        assert "NonExistentProject" in str(exc_info.value)

    def test_add_task_nonexistent_project_via_mcp(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task via MCP should return error message for non-existent project."""
        result = asyncio.run(call_tool("aio_add_task", {
            "title": "Task with missing project",
            "project": "NonExistentProject",
        }))

        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "NonExistentProject" in result[0].text
        assert "Project not found" in result[0].text

    def test_add_task_invalid_date(self, mcp_registry: ServiceRegistry) -> None:
        """aio_add_task should handle invalid dates."""
        result = asyncio.run(handle_add_task({
            "title": "Task with bad date",
            "due": "not-a-date-xyz",
        }))

        assert len(result) == 1
        assert "Invalid date" in result[0].text


class TestListTasksTool:
    """Tests for the aio_list_tasks MCP tool."""

    def test_list_tasks_empty(self, mcp_registry: ServiceRegistry) -> None:
        """aio_list_tasks should handle empty task list."""
        result = asyncio.run(handle_list_tasks({}))

        assert len(result) == 1
        assert "No tasks found" in result[0].text

    def test_list_tasks_with_task(self, mcp_registry: ServiceRegistry) -> None:
        """aio_list_tasks should list created tasks."""
        # Create a task first
        asyncio.run(handle_add_task({"title": "Task to list"}))

        result = asyncio.run(handle_list_tasks({}))

        assert len(result) == 1
        assert "Found 1 task" in result[0].text
        assert "Task to list" in result[0].text

    def test_list_tasks_by_status(self, mcp_registry: ServiceRegistry) -> None:
        """aio_list_tasks should filter by status."""
        asyncio.run(handle_add_task({"title": "Inbox task"}))

        result = asyncio.run(handle_list_tasks({"status": "inbox"}))

        assert len(result) == 1
        assert "Found 1 task" in result[0].text
        assert "Inbox task" in result[0].text

    def test_list_tasks_empty_status(self, mcp_registry: ServiceRegistry) -> None:
        """aio_list_tasks should return empty for non-matching status."""
        asyncio.run(handle_add_task({"title": "Inbox task"}))

        result = asyncio.run(handle_list_tasks({"status": "next"}))

        assert len(result) == 1
        assert "No tasks found" in result[0].text


class TestCompleteTaskTool:
    """Tests for the aio_complete_task MCP tool."""

    def test_complete_task_by_id(self, mcp_registry: ServiceRegistry) -> None:
        """aio_complete_task should complete by ID."""
        # Create a task and extract the ID
        add_result = asyncio.run(handle_add_task({"title": "Task to complete"}))
        # Parse ID from "ID: XXXX" line
        lines = add_result[0].text.split("\n")
        task_id = None
        for line in lines:
            if line.startswith("ID:"):
                task_id = line.split(":")[1].strip()
                break

        assert task_id is not None

        result = asyncio.run(handle_complete_task({"query": task_id}))

        assert len(result) == 1
        assert "Completed:" in result[0].text
        assert "Task to complete" in result[0].text

    def test_complete_task_by_title(self, mcp_registry: ServiceRegistry) -> None:
        """aio_complete_task should complete by title."""
        asyncio.run(handle_add_task({"title": "Complete me"}))

        result = asyncio.run(handle_complete_task({"query": "Complete me"}))

        assert len(result) == 1
        assert "Completed:" in result[0].text

    def test_complete_task_not_found(self, mcp_registry: ServiceRegistry) -> None:
        """aio_complete_task should raise TaskNotFoundError for unknown task."""
        from aio.exceptions import TaskNotFoundError

        with pytest.raises(TaskNotFoundError) as exc_info:
            asyncio.run(handle_complete_task({"query": "ZZZZ"}))

        assert "ZZZZ" in str(exc_info.value)


class TestStartTaskTool:
    """Tests for the aio_start_task MCP tool."""

    def test_start_task(self, mcp_registry: ServiceRegistry) -> None:
        """aio_start_task should move task to next status."""
        asyncio.run(handle_add_task({"title": "Task to start"}))

        result = asyncio.run(handle_start_task({"query": "Task to start"}))

        assert len(result) == 1
        assert "Started:" in result[0].text
        assert "next" in result[0].text.lower()


class TestDeferTaskTool:
    """Tests for the aio_defer_task MCP tool."""

    def test_defer_task(self, mcp_registry: ServiceRegistry) -> None:
        """aio_defer_task should move task to someday status."""
        asyncio.run(handle_add_task({"title": "Task to defer"}))

        result = asyncio.run(handle_defer_task({"query": "Task to defer"}))

        assert len(result) == 1
        assert "Deferred:" in result[0].text
        assert "someday" in result[0].text.lower()


class TestGetDashboardTool:
    """Tests for the aio_get_dashboard MCP tool."""

    def test_get_dashboard(self, mcp_registry: ServiceRegistry) -> None:
        """aio_get_dashboard should return dashboard content."""
        result = asyncio.run(handle_get_dashboard({}))

        assert len(result) == 1
        assert "Quick Links" in result[0].text

    def test_get_dashboard_with_date(self, mcp_registry: ServiceRegistry) -> None:
        """aio_get_dashboard should accept date parameter."""
        result = asyncio.run(handle_get_dashboard({"date": "2024-06-15"}))

        assert len(result) == 1
        # Dashboard should still generate even with custom date
        assert len(result[0].text) > 0


class TestCreateProjectTool:
    """Tests for the aio_create_project MCP tool."""

    def test_create_project_basic(self, mcp_registry: ServiceRegistry) -> None:
        """aio_create_project should create a project."""
        result = asyncio.run(handle_create_project({"name": "New Project"}))

        assert len(result) == 1
        assert "Created project:" in result[0].text
        assert "New Project" in result[0].text
        assert "ID:" in result[0].text
        assert "Status: active" in result[0].text

    def test_create_project_with_status(self, mcp_registry: ServiceRegistry) -> None:
        """aio_create_project should accept status."""
        result = asyncio.run(handle_create_project({
            "name": "On Hold Project",
            "status": "on-hold",
        }))

        assert len(result) == 1
        assert "Created project:" in result[0].text
        assert "Status: on-hold" in result[0].text

    def test_create_project_with_team(self, mcp_registry: ServiceRegistry) -> None:
        """aio_create_project should accept team."""
        result = asyncio.run(handle_create_project({
            "name": "Team Project",
            "team": "Engineering",
        }))

        assert len(result) == 1
        assert "Created project:" in result[0].text
        assert "Team: Engineering" in result[0].text


class TestCreatePersonTool:
    """Tests for the aio_create_person MCP tool."""

    def test_create_person_basic(self, mcp_registry: ServiceRegistry) -> None:
        """aio_create_person should create a person."""
        result = asyncio.run(handle_create_person({"name": "John Doe"}))

        assert len(result) == 1
        assert "Created person:" in result[0].text
        assert "John Doe" in result[0].text
        assert "ID:" in result[0].text

    def test_create_person_with_details(self, mcp_registry: ServiceRegistry) -> None:
        """aio_create_person should accept all optional fields."""
        result = asyncio.run(handle_create_person({
            "name": "Jane Smith",
            "team": "Product",
            "role": "Product Manager",
            "email": "jane@example.com",
        }))

        assert len(result) == 1
        assert "Created person:" in result[0].text
        assert "Jane Smith" in result[0].text
        assert "Team: Product" in result[0].text
        assert "Role: Product Manager" in result[0].text
        assert "Email: jane@example.com" in result[0].text
