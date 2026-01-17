"""Task model for AIorgianization."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status values aligned with folder names."""

    INBOX = "inbox"
    NEXT = "next"
    WAITING = "waiting"
    SCHEDULED = "scheduled"
    SOMEDAY = "someday"
    COMPLETED = "completed"


class TaskLocation(BaseModel):
    """Location reference for a task (file, line, URL)."""

    file: str | None = None
    line: int | None = None
    url: str | None = None


class Task(BaseModel):
    """A task stored as a markdown file in the vault."""

    # Core identifiers
    id: str = Field(description="4-character alphanumeric ID")
    type: str = Field(default="task", description="Always 'task'")
    status: TaskStatus = Field(default=TaskStatus.INBOX)

    # Title and content
    title: str = Field(description="Task title (from H1 heading)")
    body: str = Field(default="", description="Markdown content below frontmatter")

    # Dates
    due: date | None = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    completed: datetime | None = None

    # Relationships
    project: str | None = Field(
        default=None, description="Wikilink to project, e.g. [[Projects/Q4-Migration]]"
    )
    assigned_to: str | None = Field(
        default=None,
        alias="assignedTo",
        description="Wikilink to person assigned this task",
    )
    waiting_on: str | None = Field(
        default=None,
        alias="waitingOn",
        description="Wikilink to person we're waiting on",
    )

    # Dependencies
    blocked_by: list[str] = Field(
        default_factory=list,
        alias="blockedBy",
        description="Wikilinks to tasks that block this one",
    )
    blocks: list[str] = Field(
        default_factory=list, description="Wikilinks to tasks this blocks"
    )

    # Location
    location: TaskLocation | None = None

    # Metadata
    tags: list[str] = Field(default_factory=list)
    time_estimate: str | None = Field(default=None, alias="timeEstimate")
    jira_key: str | None = Field(default=None, alias="jiraKey")

    class Config:
        populate_by_name = True
        use_enum_values = True

    def frontmatter(self) -> dict[str, Any]:
        """Convert to frontmatter dictionary for YAML serialization.

        Returns:
            Dictionary suitable for YAML frontmatter.
        """
        # Explicitly convert status to string value for YAML serialization
        status_value = self.status.value if isinstance(self.status, TaskStatus) else self.status
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "status": status_value,
        }

        # Optional fields - only include if set
        if self.due:
            data["due"] = self.due
        if self.project:
            data["project"] = self.project
        if self.assigned_to:
            data["assignedTo"] = self.assigned_to
        if self.waiting_on:
            data["waitingOn"] = self.waiting_on
        if self.blocked_by:
            data["blockedBy"] = self.blocked_by
        if self.blocks:
            data["blocks"] = self.blocks
        if self.location:
            loc_dict = self.location.model_dump(exclude_none=True)
            if loc_dict:
                data["location"] = loc_dict
        if self.tags:
            data["tags"] = self.tags
        if self.time_estimate:
            data["timeEstimate"] = self.time_estimate
        if self.jira_key:
            data["jiraKey"] = self.jira_key

        # Always include timestamps
        data["created"] = self.created
        data["updated"] = self.updated
        if self.completed:
            data["completed"] = self.completed

        return data

    def generate_filename(self) -> str:
        """Generate the filename for this task.

        Returns:
            Filename in format YYYY-MM-DD-short-title.md
        """
        # Use created date for the filename
        date_str = self.created.strftime("%Y-%m-%d")

        # Slugify title: lowercase, replace spaces with hyphens, remove special chars
        slug = self.title.lower()
        slug = slug.replace(" ", "-")
        # Keep only alphanumeric and hyphens
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        # Collapse multiple hyphens
        while "--" in slug:
            slug = slug.replace("--", "-")
        # Trim to reasonable length
        slug = slug[:50].rstrip("-")

        return f"{date_str}-{slug}.md"

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.due and self.status != TaskStatus.COMPLETED:
            return self.due < date.today()
        return False

    @property
    def is_due_today(self) -> bool:
        """Check if task is due today."""
        if self.due:
            return self.due == date.today()
        return False
