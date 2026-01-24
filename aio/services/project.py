"""Project service for operations on project markdown files."""

import logging
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from aio.exceptions import AmbiguousMatchError, ProjectNotFoundError
from aio.models.project import Project, ProjectStatus
from aio.services.id_service import EntityType, IdService
from aio.services.vault import VaultService
from aio.utils.frontmatter import read_frontmatter, write_frontmatter
from aio.utils.ids import is_valid_id, normalize_id

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

    def get(self, project_id: str) -> Project:
        """Get a project by ID.

        Args:
            project_id: The 4-character project ID.

        Returns:
            The project.

        Raises:
            ProjectNotFoundError: If the project is not found.
        """
        project_id = normalize_id(project_id)
        project = self._find_project_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    def find(self, query: str) -> Project:
        """Find a project by ID or name substring.

        Args:
            query: Project ID (4 chars) or name substring.

        Returns:
            The matching project.

        Raises:
            ProjectNotFoundError: If no project matches.
            AmbiguousMatchError: If multiple projects match.
        """
        # If it looks like an ID, try ID lookup first
        if is_valid_id(query):
            try:
                return self.get(query)
            except ProjectNotFoundError:
                pass  # Fall through to name search

        # Search by name
        matches = self._find_projects_by_name(query)
        if not matches:
            suggestions = self.find_similar(query)
            raise ProjectNotFoundError(query, suggestions)
        if len(matches) > 1:
            raise AmbiguousMatchError(query, [p.id for p in matches])
        return matches[0]

    def _find_project_by_id(self, project_id: str) -> Project | None:
        """Find a project by its ID.

        Args:
            project_id: The project ID to find (normalized).

        Returns:
            The Project, or None if not found.
        """
        project_id = project_id.upper()
        projects_folder = self.vault.projects_folder()

        if not projects_folder.exists():
            return None

        for filepath in projects_folder.glob("*.md"):
            try:
                metadata, content = read_frontmatter(filepath)
                if metadata.get("id", "").upper() == project_id:
                    return self._read_project(filepath, metadata, content)
            except Exception as e:
                logger.debug("Failed to read project file %s: %s", filepath, e)

        return None

    def _find_projects_by_name(self, query: str) -> list[Project]:
        """Find projects by name substring.

        Args:
            query: Name substring to search for.

        Returns:
            List of matching projects.
        """
        query_lower = query.lower()
        matches: list[Project] = []
        projects_folder = self.vault.projects_folder()

        if not projects_folder.exists():
            return matches

        for filepath in projects_folder.glob("*.md"):
            try:
                metadata, content = read_frontmatter(filepath)
                # Check both filename (stem) and title in frontmatter
                title = metadata.get("title", filepath.stem)
                if query_lower in title.lower() or query_lower in filepath.stem.lower():
                    matches.append(self._read_project(filepath, metadata, content))
            except Exception as e:
                logger.debug("Failed to read project file %s: %s", filepath, e)

        return matches

    def _read_project(
        self, filepath: Path, metadata: dict[str, Any], content: str
    ) -> Project:
        """Read a project from parsed file data.

        Args:
            filepath: Path to the project file.
            metadata: Parsed frontmatter.
            content: File content.

        Returns:
            The Project object.
        """
        # Parse target_date if present
        target_date_val = metadata.get("targetDate")
        target_date = None
        if target_date_val:
            if isinstance(target_date_val, date):
                target_date = target_date_val
            elif isinstance(target_date_val, str):
                target_date = date.fromisoformat(target_date_val)

        # Parse created datetime
        created_val = metadata.get("created")
        created = datetime.now()
        if created_val:
            if isinstance(created_val, datetime):
                created = created_val
            elif isinstance(created_val, str):
                created = datetime.fromisoformat(created_val.replace("Z", "+00:00"))
                if created.tzinfo:
                    created = created.replace(tzinfo=None)

        return Project(
            id=metadata.get("id", "????"),
            type=metadata.get("type", "project"),
            status=ProjectStatus(metadata.get("status", "active")),
            category=metadata.get("category", "project"),
            title=metadata.get("title", filepath.stem),
            body=content,
            team=metadata.get("team"),
            target_date=target_date,
            created=created,
        )

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

        # Generate content with Dataview queries for tasks
        body = f"""# {name}

## Overview

## Goals

## Backlog

```dataview
TABLE due AS "Due", status AS "Status"
FROM "AIO/Tasks"
WHERE contains(project, link("AIO/Projects/{name}")) AND status != "completed"
SORT due ASC
```

## Previous Actions

```dataview
TABLE due AS "Due", completed AS "Completed"
FROM "AIO/Tasks"
WHERE contains(project, link("AIO/Projects/{name}")) AND status = "completed"
SORT completed DESC
```

## Supporting Material

## Notes
"""
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
