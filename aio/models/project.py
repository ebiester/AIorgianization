"""Project model for AIorgianization."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(str, Enum):
    """Project status values."""

    ACTIVE = "active"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(BaseModel):
    """A project stored as a markdown file in the vault."""

    # Core fields
    id: str = Field(description="4-char alphanumeric ID")
    type: str = Field(default="project")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    category: str = Field(default="project", description="project or area (PARA)")

    # Title and content
    title: str = Field(description="Project title (from H1 heading)")
    body: str = Field(default="", description="Markdown content below frontmatter")

    # Team and dates
    team: str | None = Field(default=None, description="Wikilink to team")
    target_date: date | None = Field(default=None, alias="targetDate")

    # Timestamps
    created: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    def frontmatter(self) -> dict[str, Any]:
        """Convert to frontmatter dictionary."""
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "category": self.category,
        }

        if self.team:
            data["team"] = self.team
        if self.target_date:
            data["targetDate"] = self.target_date
        data["created"] = self.created

        return data

    def generate_filename(self) -> str:
        """Generate the filename for this project.

        Returns:
            Filename in format Title-Slug.md
        """
        # Slugify title
        slug = self.title
        slug = slug.replace(" ", "-")
        # Keep only alphanumeric and hyphens
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        while "--" in slug:
            slug = slug.replace("--", "-")

        return f"{slug}.md"
