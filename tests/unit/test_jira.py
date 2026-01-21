"""Unit tests for Jira models and JiraSyncService."""

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aio.exceptions import JiraConfigError
from aio.models.jira import JiraConfig, JiraIssue, JiraSyncState, SyncResult
from aio.models.task import TaskStatus
from aio.services.jira import JIRA_STATUS_MAP, JiraSyncService
from aio.services.task import TaskService
from aio.services.vault import VaultService


class TestJiraConfig:
    """Tests for JiraConfig model."""

    def test_default_values(self) -> None:
        """JiraConfig should have sensible defaults."""
        config = JiraConfig()
        assert config.enabled is False
        assert config.base_url is None
        assert config.email is None
        assert config.projects == []
        assert config.sync_interval == 15

    def test_is_configured_false(self) -> None:
        """is_configured should return False when not fully configured."""
        config = JiraConfig(enabled=True)
        assert not config.is_configured()

    def test_is_configured_true(self) -> None:
        """is_configured should return True when fully configured."""
        config = JiraConfig(
            enabled=True,
            base_url="https://company.atlassian.net",
            email="user@company.com",
            projects=["PROJ1"],
        )
        assert config.is_configured()

    def test_from_dict_with_aliases(self) -> None:
        """JiraConfig should parse aliased fields."""
        data = {
            "enabled": True,
            "baseUrl": "https://company.atlassian.net",
            "email": "user@company.com",
            "projects": ["PROJ"],
            "syncInterval": 30,
        }
        config = JiraConfig(**data)
        assert config.base_url == "https://company.atlassian.net"
        assert config.sync_interval == 30


class TestJiraIssue:
    """Tests for JiraIssue model."""

    def test_basic_creation(self) -> None:
        """JiraIssue should be creatable with required fields."""
        issue = JiraIssue(
            key="PROJ-123",
            summary="Test Issue",
            status="To Do",
            issue_type="Task",
            project_key="PROJ",
            url="https://company.atlassian.net/browse/PROJ-123",
            updated=datetime.now(),
        )
        assert issue.key == "PROJ-123"
        assert issue.summary == "Test Issue"

    def test_from_jira_issue(self) -> None:
        """from_jira_issue should parse jira library Issue object."""
        # Create a mock Jira issue object
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-456"
        mock_issue.fields.summary = "Mock Issue"
        mock_issue.fields.status.name = "In Progress"
        mock_issue.fields.issuetype.name = "Bug"
        mock_issue.fields.priority = MagicMock(name="High")
        mock_issue.fields.priority.name = "High"
        mock_issue.fields.assignee = MagicMock()
        mock_issue.fields.assignee.emailAddress = "user@company.com"
        mock_issue.fields.assignee.displayName = "Test User"
        mock_issue.fields.duedate = "2024-01-20"
        mock_issue.fields.description = "Test description"
        mock_issue.fields.labels = ["backend", "urgent"]
        # Epic link fields - must be explicitly set to None to prevent MagicMock auto-creation
        mock_issue.fields.parent = None
        mock_issue.fields.customfield_10014 = None
        mock_issue.fields.customfield_10008 = None
        mock_issue.fields.updated = "2024-01-15T10:00:00+00:00"

        issue = JiraIssue.from_jira_issue(mock_issue, "https://company.atlassian.net")

        assert issue.key == "PROJ-456"
        assert issue.summary == "Mock Issue"
        assert issue.status == "In Progress"
        assert issue.issue_type == "Bug"
        assert issue.priority == "High"
        assert issue.assignee_email == "user@company.com"
        assert issue.due_date == "2024-01-20"
        assert issue.labels == ["backend", "urgent"]
        assert issue.url == "https://company.atlassian.net/browse/PROJ-456"


class TestSyncResult:
    """Tests for SyncResult model."""

    def test_default_values(self) -> None:
        """SyncResult should have zero counts by default."""
        result = SyncResult()
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.errors == []

    def test_total_processed(self) -> None:
        """total_processed should sum created, updated, and skipped."""
        result = SyncResult(created=2, updated=3, skipped=5)
        assert result.total_processed == 10

    def test_has_errors(self) -> None:
        """has_errors should detect errors."""
        result = SyncResult()
        assert not result.has_errors

        result.errors.append("Test error")
        assert result.has_errors

    def test_summary_no_changes(self) -> None:
        """summary should report no changes."""
        result = SyncResult()
        assert result.summary() == "No changes"

    def test_summary_with_changes(self) -> None:
        """summary should report changes."""
        result = SyncResult(created=2, updated=3)
        summary = result.summary()
        assert "2 created" in summary
        assert "3 updated" in summary


class TestJiraStatusMapping:
    """Tests for Jira status mapping."""

    def test_todo_statuses(self) -> None:
        """To Do statuses should map to INBOX."""
        assert JIRA_STATUS_MAP["to do"] == TaskStatus.INBOX
        assert JIRA_STATUS_MAP["backlog"] == TaskStatus.INBOX
        assert JIRA_STATUS_MAP["open"] == TaskStatus.INBOX

    def test_in_progress_statuses(self) -> None:
        """In Progress statuses should map to NEXT."""
        assert JIRA_STATUS_MAP["in progress"] == TaskStatus.NEXT
        assert JIRA_STATUS_MAP["started"] == TaskStatus.NEXT

    def test_review_statuses(self) -> None:
        """Review statuses should map to WAITING."""
        assert JIRA_STATUS_MAP["in review"] == TaskStatus.WAITING
        assert JIRA_STATUS_MAP["blocked"] == TaskStatus.WAITING

    def test_done_statuses(self) -> None:
        """Done statuses should map to COMPLETED."""
        assert JIRA_STATUS_MAP["done"] == TaskStatus.COMPLETED
        assert JIRA_STATUS_MAP["closed"] == TaskStatus.COMPLETED


class TestJiraSyncService:
    """Tests for JiraSyncService."""

    @pytest.fixture
    def jira_service(self, vault_service: VaultService) -> JiraSyncService:
        """Create a JiraSyncService for testing."""
        task_service = TaskService(vault_service)
        return JiraSyncService(vault_service, task_service)

    def test_config_from_vault(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """config should read from vault config."""
        # Set up config
        jira_service.vault.set_config({
            "jira": {
                "enabled": True,
                "baseUrl": "https://test.atlassian.net",
                "email": "test@example.com",
                "projects": ["TEST"],
            }
        })

        config = jira_service.config
        assert config.enabled is True
        assert config.base_url == "https://test.atlassian.net"

    def test_map_jira_status(self, jira_service: JiraSyncService) -> None:
        """map_jira_status should convert Jira status to TaskStatus."""
        assert jira_service.map_jira_status("To Do") == TaskStatus.INBOX
        assert jira_service.map_jira_status("IN PROGRESS") == TaskStatus.NEXT
        assert jira_service.map_jira_status("Done") == TaskStatus.COMPLETED
        # Unknown status should default to INBOX
        assert jira_service.map_jira_status("Unknown Status") == TaskStatus.INBOX

    def test_sync_state_persistence(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """Sync state should be saved and loaded correctly."""
        state = JiraSyncState(
            last_sync=datetime(2024, 1, 15, 10, 0, 0),
            synced_issues={"PROJ-123": datetime(2024, 1, 15, 10, 0, 0)},
        )
        jira_service.save_sync_state(state)

        loaded = jira_service.get_sync_state()
        assert loaded.last_sync is not None
        assert "PROJ-123" in loaded.synced_issues

    def test_get_jira_client_not_configured(
        self, jira_service: JiraSyncService
    ) -> None:
        """get_jira_client should raise when not configured."""
        with pytest.raises(JiraConfigError) as exc_info:
            jira_service.get_jira_client()
        assert "not configured" in str(exc_info.value).lower()

    def test_get_jira_client_no_token(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """get_jira_client should raise when token is missing."""
        jira_service.vault.set_config({
            "jira": {
                "enabled": True,
                "baseUrl": "https://test.atlassian.net",
                "email": "test@example.com",
                "projects": ["TEST"],
            }
        })

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(JiraConfigError) as exc_info:
                jira_service.get_jira_client()
            assert "JIRA_API_TOKEN" in str(exc_info.value)

    def test_find_task_by_jira_key_not_found(
        self, jira_service: JiraSyncService
    ) -> None:
        """find_task_by_jira_key should return None when not found."""
        result = jira_service.find_task_by_jira_key("NONEXISTENT-123")
        assert result is None

    def test_find_task_by_jira_key_found(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """find_task_by_jira_key should find existing task."""
        # Create a task with jiraKey
        task_content = """---
id: JR01
type: task
status: next
jiraKey: PROJ-999
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Jira Task

## Notes
"""
        task_path = initialized_vault / "AIO" / "Tasks" / "Next" / "2024-01-15-jira-task.md"
        task_path.write_text(task_content, encoding="utf-8")

        result = jira_service.find_task_by_jira_key("PROJ-999")
        assert result is not None
        assert result.jira_key == "PROJ-999"
        assert result.id == "JR01"

    def test_create_task_from_issue(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """create_task_from_issue should create a task file."""
        issue = JiraIssue(
            key="TEST-100",
            summary="Test Jira Issue",
            status="In Progress",
            issue_type="Task",
            priority="High",
            project_key="TEST",
            description="This is a test issue",
            labels=["backend"],
            url="https://test.atlassian.net/browse/TEST-100",
            updated=datetime.now(),
            due_date="2024-02-01",
        )

        task = jira_service.create_task_from_issue(issue)

        assert task.title == "Test Jira Issue"
        assert task.jira_key == "TEST-100"
        assert task.status == TaskStatus.NEXT  # In Progress maps to NEXT
        assert task.due == date(2024, 2, 1)
        assert "backend" in task.tags

    def test_get_status(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """get_status should return current sync status."""
        jira_service.vault.set_config({
            "jira": {
                "enabled": True,
                "baseUrl": "https://test.atlassian.net",
                "email": "test@example.com",
                "projects": ["TEST", "PROJ"],
            }
        })

        status = jira_service.get_status()
        assert status["enabled"] is True
        assert status["configured"] is True
        assert status["base_url"] == "https://test.atlassian.net"
        assert status["projects"] == ["TEST", "PROJ"]

    def test_sync_dry_run(
        self, jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """sync with dry_run should not modify files."""
        jira_service.vault.set_config({
            "jira": {
                "enabled": True,
                "baseUrl": "https://test.atlassian.net",
                "email": "test@example.com",
                "projects": ["TEST"],
            }
        })

        # Mock the Jira client and fetch
        mock_issue = JiraIssue(
            key="TEST-1",
            summary="Test Issue",
            status="To Do",
            issue_type="Task",
            project_key="TEST",
            url="https://test.atlassian.net/browse/TEST-1",
            updated=datetime.now(),
        )

        with patch.object(jira_service, "fetch_assigned_issues", return_value=[mock_issue]):
            result = jira_service.sync(dry_run=True)

        assert result.created == 1
        assert result.created_tasks == []  # No actual tasks created in dry run

        # Verify no task file was created
        task = jira_service.find_task_by_jira_key("TEST-1")
        assert task is None


class TestJiraSyncIntegration:
    """Integration-style tests for Jira sync (still using mocks)."""

    @pytest.fixture
    def configured_jira_service(
        self, vault_service: VaultService, initialized_vault: Path
    ) -> JiraSyncService:
        """Create a configured JiraSyncService."""
        task_service = TaskService(vault_service)
        service = JiraSyncService(vault_service, task_service)

        vault_service.set_config({
            "jira": {
                "enabled": True,
                "baseUrl": "https://test.atlassian.net",
                "email": "test@example.com",
                "projects": ["TEST"],
            }
        })

        return service

    def test_full_sync_creates_tasks(
        self, configured_jira_service: JiraSyncService
    ) -> None:
        """Full sync should create tasks from Jira issues."""
        mock_issues = [
            JiraIssue(
                key="TEST-1",
                summary="First Issue",
                status="To Do",
                issue_type="Task",
                project_key="TEST",
                url="https://test.atlassian.net/browse/TEST-1",
                updated=datetime.now(),
            ),
            JiraIssue(
                key="TEST-2",
                summary="Second Issue",
                status="In Progress",
                issue_type="Bug",
                project_key="TEST",
                url="https://test.atlassian.net/browse/TEST-2",
                updated=datetime.now(),
            ),
        ]

        with patch.object(
            configured_jira_service, "fetch_assigned_issues", return_value=mock_issues
        ):
            result = configured_jira_service.sync()

        assert result.created == 2
        assert len(result.created_tasks) == 2

        # Verify tasks were created
        task1 = configured_jira_service.find_task_by_jira_key("TEST-1")
        task2 = configured_jira_service.find_task_by_jira_key("TEST-2")

        assert task1 is not None
        assert task1.title == "First Issue"
        assert task1.status == TaskStatus.INBOX

        assert task2 is not None
        assert task2.title == "Second Issue"
        assert task2.status == TaskStatus.NEXT

    def test_sync_updates_existing_tasks(
        self, configured_jira_service: JiraSyncService, initialized_vault: Path
    ) -> None:
        """Sync should update existing tasks when Jira data changes."""
        # Create an existing task
        task_content = """---
id: EX01
type: task
status: inbox
jiraKey: TEST-99
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Old Title

## Notes
"""
        task_path = initialized_vault / "AIO" / "Tasks" / "Inbox" / "2024-01-15-old-title.md"
        task_path.write_text(task_content, encoding="utf-8")

        # Jira issue with updated data
        mock_issue = JiraIssue(
            key="TEST-99",
            summary="New Title From Jira",
            status="In Progress",  # Status changed
            issue_type="Task",
            project_key="TEST",
            url="https://test.atlassian.net/browse/TEST-99",
            updated=datetime.now(),  # Recent update
        )

        with patch.object(
            configured_jira_service, "fetch_assigned_issues", return_value=[mock_issue]
        ):
            result = configured_jira_service.sync()

        assert result.updated == 1
        assert result.moved == 1  # Status changed, so task was moved

        # Verify task was updated
        task = configured_jira_service.find_task_by_jira_key("TEST-99")
        assert task is not None
        assert task.title == "New Title From Jira"
        assert task.status == TaskStatus.NEXT
