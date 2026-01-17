"""Jira-related models for AIorgianization."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JiraConfig(BaseModel):
    """Configuration for Jira integration."""

    enabled: bool = Field(default=False, description="Whether Jira sync is enabled")
    base_url: str | None = Field(
        default=None, alias="baseUrl", description="Jira instance URL, e.g. https://company.atlassian.net"
    )
    email: str | None = Field(default=None, description="Jira account email")
    projects: list[str] = Field(
        default_factory=list, description="Project keys to sync, e.g. ['PLAT', 'ALPHA']"
    )
    sync_interval: int = Field(
        default=15, alias="syncInterval", description="Sync interval in minutes"
    )

    class Config:
        populate_by_name = True

    def is_configured(self) -> bool:
        """Check if Jira is fully configured.

        Returns:
            True if all required fields are set.
        """
        return bool(self.enabled and self.base_url and self.email and self.projects)


class JiraIssue(BaseModel):
    """Represents a Jira issue fetched from the API."""

    key: str = Field(description="Jira issue key, e.g. PLAT-123")
    summary: str = Field(description="Issue summary/title")
    status: str = Field(description="Jira status name")
    issue_type: str = Field(alias="issueType", description="Issue type, e.g. Task, Bug, Story")
    priority: str | None = Field(default=None, description="Priority name")
    assignee_email: str | None = Field(default=None, alias="assigneeEmail")
    assignee_name: str | None = Field(default=None, alias="assigneeName")
    due_date: str | None = Field(default=None, alias="dueDate", description="Due date in YYYY-MM-DD format")
    project_key: str = Field(alias="projectKey", description="Project key")
    description: str | None = Field(default=None, description="Issue description")
    labels: list[str] = Field(default_factory=list)
    epic_key: str | None = Field(default=None, alias="epicKey", description="Parent epic key")
    url: str = Field(description="Full URL to the issue")
    updated: datetime = Field(description="Last updated timestamp")

    class Config:
        populate_by_name = True

    @classmethod
    def from_jira_issue(cls, issue: Any, base_url: str) -> "JiraIssue":
        """Create a JiraIssue from a jira library Issue object.

        Args:
            issue: The jira library Issue object.
            base_url: The Jira instance base URL.

        Returns:
            A JiraIssue instance.
        """
        fields = issue.fields

        # Extract assignee info
        assignee_email = None
        assignee_name = None
        if fields.assignee:
            assignee_email = getattr(fields.assignee, "emailAddress", None)
            assignee_name = getattr(fields.assignee, "displayName", None)

        # Extract priority
        priority = None
        if fields.priority:
            priority = fields.priority.name

        # Extract due date
        due_date = None
        if fields.duedate:
            due_date = fields.duedate

        # Extract epic key (customfield may vary by instance)
        epic_key = None
        # Common custom field names for epic link
        for field_name in ["parent", "customfield_10014", "customfield_10008"]:
            epic_field = getattr(fields, field_name, None)
            if epic_field:
                if hasattr(epic_field, "key"):
                    epic_key = epic_field.key
                elif isinstance(epic_field, str):
                    epic_key = epic_field
                break

        # Extract labels
        labels = list(fields.labels) if fields.labels else []

        return cls(
            key=issue.key,
            summary=fields.summary,
            status=fields.status.name,
            issue_type=fields.issuetype.name,
            priority=priority,
            assignee_email=assignee_email,
            assignee_name=assignee_name,
            due_date=due_date,
            project_key=issue.key.split("-")[0],
            description=fields.description,
            labels=labels,
            epic_key=epic_key,
            url=f"{base_url.rstrip('/')}/browse/{issue.key}",
            updated=datetime.fromisoformat(fields.updated.replace("Z", "+00:00")),
        )


class JiraSyncState(BaseModel):
    """Tracks the state of Jira synchronization."""

    last_sync: datetime | None = Field(default=None, alias="lastSync")
    synced_issues: dict[str, datetime] = Field(
        default_factory=dict,
        alias="syncedIssues",
        description="Map of issue key to last sync time",
    )
    errors: list[str] = Field(default_factory=list, description="Recent sync errors")

    class Config:
        populate_by_name = True


class SyncResult(BaseModel):
    """Result of a Jira sync operation."""

    created: int = Field(default=0, description="Number of tasks created")
    updated: int = Field(default=0, description="Number of tasks updated")
    moved: int = Field(default=0, description="Number of tasks moved to different status")
    skipped: int = Field(default=0, description="Number of issues skipped")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    created_tasks: list[str] = Field(
        default_factory=list, alias="createdTasks", description="IDs of created tasks"
    )
    updated_tasks: list[str] = Field(
        default_factory=list, alias="updatedTasks", description="IDs of updated tasks"
    )

    class Config:
        populate_by_name = True

    @property
    def total_processed(self) -> int:
        """Total number of issues processed."""
        return self.created + self.updated + self.skipped

    @property
    def has_errors(self) -> bool:
        """Check if there were any errors."""
        return len(self.errors) > 0

    def summary(self) -> str:
        """Generate a human-readable summary.

        Returns:
            Summary string of the sync result.
        """
        parts = []
        if self.created > 0:
            parts.append(f"{self.created} created")
        if self.updated > 0:
            parts.append(f"{self.updated} updated")
        if self.moved > 0:
            parts.append(f"{self.moved} moved")
        if self.skipped > 0:
            parts.append(f"{self.skipped} skipped")

        if not parts:
            return "No changes"

        result = f"Synced: {', '.join(parts)}"
        if self.has_errors:
            result += f" ({len(self.errors)} errors)"
        return result
