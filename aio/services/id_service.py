"""ID service for generating unique IDs with collision detection."""

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from aio.utils.frontmatter import read_frontmatter
from aio.utils.ids import generate_id

if TYPE_CHECKING:
    from aio.services.vault import VaultService

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities that have IDs."""

    TASK = "task"
    PROJECT = "project"
    PERSON = "person"


class IdService:
    """Service for generating unique IDs across all entity types."""

    def __init__(self, vault_service: "VaultService") -> None:
        """Initialize the ID service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service

    def generate_unique_id(self, entity_type: EntityType) -> str:
        """Generate a unique ID for an entity type.

        Checks for collisions with existing entities and retries if needed.

        Args:
            entity_type: The type of entity to generate an ID for.

        Returns:
            A unique 4-character ID.

        Raises:
            RuntimeError: If unable to generate a unique ID after max attempts.
        """
        max_attempts = 100
        existing_ids = self._get_existing_ids(entity_type)

        for _ in range(max_attempts):
            new_id = generate_id()
            if new_id not in existing_ids:
                return new_id

        raise RuntimeError(
            f"Failed to generate unique {entity_type.value} ID after {max_attempts} attempts"
        )

    def _get_existing_ids(self, entity_type: EntityType) -> set[str]:
        """Get all existing IDs for an entity type.

        Args:
            entity_type: The type of entity.

        Returns:
            Set of existing IDs.
        """
        if entity_type == EntityType.TASK:
            return self._get_task_ids()
        elif entity_type == EntityType.PROJECT:
            return self._get_project_ids()
        elif entity_type == EntityType.PERSON:
            return self._get_person_ids()
        else:
            return set()

    def _get_task_ids(self) -> set[str]:
        """Get all existing task IDs across all status folders."""
        from aio.models.task import TaskStatus

        ids: set[str] = set()
        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    self._extract_id_from_file(filepath, ids)
        return ids

    def _get_project_ids(self) -> set[str]:
        """Get all existing project IDs."""
        ids: set[str] = set()
        folder = self.vault.projects_folder()
        if folder.exists():
            for filepath in folder.glob("*.md"):
                self._extract_id_from_file(filepath, ids)
        return ids

    def _get_person_ids(self) -> set[str]:
        """Get all existing person IDs."""
        ids: set[str] = set()
        folder = self.vault.people_folder()
        if folder.exists():
            for filepath in folder.glob("*.md"):
                self._extract_id_from_file(filepath, ids)
        return ids

    def _extract_id_from_file(self, filepath: Path, ids: set[str]) -> None:
        """Extract ID from a file's frontmatter and add to the set.

        Args:
            filepath: Path to the markdown file.
            ids: Set to add the ID to.
        """
        try:
            metadata, _ = read_frontmatter(filepath)
            if "id" in metadata:
                ids.add(metadata["id"])
        except Exception as e:
            logger.debug("Failed to read ID from %s: %s", filepath, e)
