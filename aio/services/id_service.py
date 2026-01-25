"""ID service for generating unique IDs with collision detection.

Uses the ID index service for fast lookups and to ensure uniqueness across
active, completed, and archived entities.
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING

from aio.services.id_index import IdIndexService
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
    """Service for generating unique IDs across all entity types.

    This service uses the ID index for fast collision detection and ensures
    that new IDs are unique across all active, completed, and archived entities.
    """

    def __init__(self, vault_service: "VaultService") -> None:
        """Initialize the ID service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service
        self._index_service = IdIndexService(vault_service)

    def generate_unique_id(self, entity_type: EntityType) -> str:
        """Generate a unique ID for an entity type.

        Checks for collisions using the ID index (which includes active,
        completed, and archived entities) and retries if needed.

        After generating a unique ID, it is immediately added to the index
        to prevent race conditions in concurrent ID generation.

        Args:
            entity_type: The type of entity to generate an ID for.

        Returns:
            A unique 4-character ID.

        Raises:
            RuntimeError: If unable to generate a unique ID after max attempts.
        """
        max_attempts = 100

        # Get or rebuild the index to ensure we have current data
        index = self._index_service.get_or_rebuild()
        all_ids = index.all_ids()

        for _ in range(max_attempts):
            new_id = generate_id()
            if new_id not in all_ids:
                # Add to index immediately to prevent duplicates
                self._add_id_to_index(entity_type, new_id)
                return new_id

        raise RuntimeError(
            f"Failed to generate unique {entity_type.value} ID after {max_attempts} attempts"
        )

    def _add_id_to_index(self, entity_type: EntityType, new_id: str) -> None:
        """Add a new ID to the index.

        Args:
            entity_type: The type of entity.
            new_id: The ID to add.
        """
        if entity_type == EntityType.TASK:
            self._index_service.add_task_id(new_id)
        elif entity_type == EntityType.PROJECT:
            self._index_service.add_project_id(new_id)
        elif entity_type == EntityType.PERSON:
            self._index_service.add_person_id(new_id)
