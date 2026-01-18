"""Project service for operations on project markdown files."""

import logging
from datetime import datetime
from difflib import SequenceMatcher

from aio.exceptions import ProjectNotFoundError
from aio.models.project import Project, ProjectStatus
from aio.services.id_service import EntityType, IdService
from aio.services.vault import VaultService
from aio.utils.frontmatter import write_frontmatter

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project operations."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the project service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service
        self._id_service = IdService(vault_service)

    def list_projects(self) -> list[str]:
        """List all project names.

        Returns:
            List of project names (without path or extension).
        """
        self.vault.ensure_initialized()
        projects_folder = self.vault.projects_folder()

        if not projects_folder.exists():
            return []

        projects: list[str] = []
        for filepath in projects_folder.glob("*.md"):
            # Use stem (filename without extension) as project name
            projects.append(filepath.stem)

        return sorted(projects)

    def exists(self, name: str) -> bool:
        """Check if a project exists.

        Args:
            name: Project name to check.

        Returns:
            True if the project exists.
        """
        self.vault.ensure_initialized()
        projects_folder = self.vault.projects_folder()

        # Normalize the name to match how we'd store it
        normalized = self._normalize_name(name)

        # Check for exact match or slug match
        for filepath in projects_folder.glob("*.md"):
            if self._normalize_name(filepath.stem) == normalized:
                return True

        return False

    def find_similar(self, name: str, max_suggestions: int = 3) -> list[str]:
        """Find projects with similar names.

        Args:
            name: Project name to match against.
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of similar project names, sorted by similarity.
        """
        existing = self.list_projects()
        if not existing:
            return []

        name_lower = name.lower()

        # Calculate similarity scores
        scored: list[tuple[float, str]] = []
        for project in existing:
            # Use SequenceMatcher for fuzzy matching
            ratio = SequenceMatcher(None, name_lower, project.lower()).ratio()
            # Also check if one contains the other
            if name_lower in project.lower() or project.lower() in name_lower:
                ratio = max(ratio, 0.7)  # Boost substring matches
            if ratio > 0.4:  # Only include somewhat similar matches
                scored.append((ratio, project))

        # Sort by similarity (descending) and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored[:max_suggestions]]

    def validate_or_suggest(self, name: str) -> None:
        """Validate that a project exists, or raise with suggestions.

        Args:
            name: Project name to validate.

        Raises:
            ProjectNotFoundError: If project doesn't exist, with suggestions.
        """
        if self.exists(name):
            return

        suggestions = self.find_similar(name)
        raise ProjectNotFoundError(name, suggestions)

    def create(
        self,
        name: str,
        status: ProjectStatus = ProjectStatus.ACTIVE,
        team: str | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name/title.
            status: Initial status (default: active).
            team: Optional team wikilink.

        Returns:
            The created project.
        """
        self.vault.ensure_initialized()

        project = Project(
            id=self._id_service.generate_unique_id(EntityType.PROJECT),
            title=name,
            status=status,
            team=team,
            created=datetime.now(),
        )

        # Generate content
        body = f"# {name}\n\n## Overview\n\n## Goals\n\n## Tasks\n\n## Notes\n"
        project.body = body

        # Write file
        folder = self.vault.projects_folder()
        filename = project.generate_filename()
        filepath = folder / filename

        write_frontmatter(filepath, project.frontmatter(), body)

        return project

    def _normalize_name(self, name: str) -> str:
        """Normalize a project name for comparison.

        Args:
            name: Name to normalize.

        Returns:
            Lowercase name with spaces and hyphens normalized.
        """
        return name.lower().replace("-", " ").replace("_", " ")

    def get_slug(self, name: str) -> str:
        """Get the slug (filename stem) for a project name.

        Args:
            name: Project name.

        Returns:
            Slugified name matching what would be used in filename.
        """
        slug = name.replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug
