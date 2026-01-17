"""Context pack model for AIorgianization."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ContextPackCategory(str, Enum):
    """Context pack category values aligned with folder names."""

    DOMAIN = "domain"
    SYSTEM = "system"
    OPERATING = "operating"


# Map category to folder name
CATEGORY_FOLDERS = {
    ContextPackCategory.DOMAIN: "Domains",
    ContextPackCategory.SYSTEM: "Systems",
    ContextPackCategory.OPERATING: "Operating",
}


class ContextPack(BaseModel):
    """A context pack stored as a markdown file in the vault."""

    # Core identifiers
    id: str = Field(description="Slug ID (filename without .md)")
    type: str = Field(default="context-pack", description="Always 'context-pack'")
    category: ContextPackCategory

    # Title and content
    title: str = Field(description="Display title for the pack")
    description: str | None = Field(default=None, description="Brief description")
    body: str = Field(default="", description="Markdown content below frontmatter")

    # Metadata
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(
        default_factory=list,
        description="Links to ADRs, docs, URLs (e.g., [[ADRs/payment-provider]])",
    )

    # Timestamps
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        use_enum_values = True

    def frontmatter(self) -> dict[str, Any]:
        """Convert to frontmatter dictionary for YAML serialization.

        Returns:
            Dictionary suitable for YAML frontmatter.
        """
        category_value = (
            self.category.value
            if isinstance(self.category, ContextPackCategory)
            else self.category
        )
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "category": category_value,
            "title": self.title,
        }

        # Optional fields - only include if set
        if self.description:
            data["description"] = self.description
        if self.tags:
            data["tags"] = self.tags
        if self.sources:
            data["sources"] = self.sources

        # Always include timestamps
        data["created"] = self.created
        data["updated"] = self.updated

        return data

    def generate_filename(self) -> str:
        """Generate the filename for this context pack.

        Returns:
            Filename in format slug-id.md
        """
        return f"{self.id}.md"

    @property
    def folder_name(self) -> str:
        """Get the folder name for this pack's category.

        Returns:
            Folder name (e.g., 'Domains', 'Systems', 'Operating')
        """
        category = (
            self.category
            if isinstance(self.category, ContextPackCategory)
            else ContextPackCategory(self.category)
        )
        return CATEGORY_FOLDERS[category]
