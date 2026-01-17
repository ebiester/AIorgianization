"""Person model for AIorgianization."""

from typing import Any

from pydantic import BaseModel, Field


class Person(BaseModel):
    """A person (team member) stored as a markdown file in the vault."""

    # Core fields
    type: str = Field(default="person")
    name: str = Field(description="Person's full name")
    body: str = Field(default="", description="Markdown content below frontmatter")

    # Contact and team info
    team: str | None = None
    role: str | None = None
    email: str | None = None
    jira_account_id: str | None = Field(default=None, alias="jiraAccountId")

    class Config:
        populate_by_name = True

    def frontmatter(self) -> dict[str, Any]:
        """Convert to frontmatter dictionary."""
        data: dict[str, Any] = {"type": self.type}

        if self.team:
            data["team"] = self.team
        if self.role:
            data["role"] = self.role
        if self.email:
            data["email"] = self.email
        if self.jira_account_id:
            data["jiraAccountId"] = self.jira_account_id

        return data

    def generate_filename(self) -> str:
        """Generate the filename for this person.

        Returns:
            Filename based on name.
        """
        # Use first name or full name slug
        slug = self.name.replace(" ", "-")
        return f"{slug}.md"
