"""ID index service for fast ID lookups with caching.

The ID index stores all known IDs in a JSON file inside the vault's .aio/ directory.
This enables fast collision detection without scanning the entire vault on every
ID generation.

The index includes a fingerprint of the vault's relevant directories to detect
when the index is stale and needs rebuilding.
"""

import contextlib
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aio.models.task import TaskStatus
from aio.utils.frontmatter import read_frontmatter

if TYPE_CHECKING:
    from aio.services.vault import VaultService

logger = logging.getLogger(__name__)

INDEX_FILENAME = "id-index.json"
INDEX_VERSION = 1


@dataclass
class IdIndex:
    """In-memory representation of the ID index."""

    task_ids: set[str] = field(default_factory=set)
    project_ids: set[str] = field(default_factory=set)
    person_ids: set[str] = field(default_factory=set)
    fingerprint: str = ""
    updated_at: datetime | None = None

    def all_ids(self) -> set[str]:
        """Get all IDs across all entity types."""
        return self.task_ids | self.project_ids | self.person_ids


class IdIndexService:
    """Service for managing the ID index."""

    def __init__(self, vault_service: "VaultService") -> None:
        """Initialize the ID index service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service
        self._cached_index: IdIndex | None = None

    @property
    def index_path(self) -> Path:
        """Get the path to the id-index.json file."""
        return self.vault.config_path / INDEX_FILENAME

    def load(self) -> IdIndex:
        """Load the ID index from disk.

        Returns:
            The loaded index, or an empty index if file doesn't exist or is invalid.
        """
        if not self.index_path.exists():
            return IdIndex()

        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return self._parse_index_data(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load ID index: %s", e)
            return IdIndex()

    def _parse_index_data(self, data: dict[str, Any]) -> IdIndex:
        """Parse index data from JSON.

        Args:
            data: Parsed JSON data.

        Returns:
            IdIndex populated from the data.
        """
        # Normalize all IDs to uppercase
        task_ids = {id_.upper() for id_ in data.get("taskIds", [])}
        project_ids = {id_.upper() for id_ in data.get("projectIds", [])}
        person_ids = {id_.upper() for id_ in data.get("personIds", [])}

        updated_at = None
        if "updatedAt" in data:
            with contextlib.suppress(ValueError, AttributeError):
                updated_at = datetime.fromisoformat(
                    data["updatedAt"].replace("Z", "+00:00")
                )

        return IdIndex(
            task_ids=task_ids,
            project_ids=project_ids,
            person_ids=person_ids,
            fingerprint=data.get("fingerprint", ""),
            updated_at=updated_at,
        )

    def save(self, index: IdIndex) -> None:
        """Save the ID index to disk.

        Args:
            index: The index to save.
        """
        # Ensure config directory exists
        self.vault.config_path.mkdir(parents=True, exist_ok=True)

        # Compute fresh fingerprint
        fingerprint = self._compute_fingerprint()

        data = {
            "version": INDEX_VERSION,
            "updatedAt": datetime.now(UTC).isoformat(),
            "fingerprint": fingerprint,
            "taskIds": sorted(index.task_ids),
            "projectIds": sorted(index.project_ids),
            "personIds": sorted(index.person_ids),
        }

        # Atomic write: write to temp file then rename
        temp_path = self.index_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.rename(self.index_path)

        # Update cached index
        index.fingerprint = fingerprint
        index.updated_at = datetime.now(UTC)
        self._cached_index = index

    def rebuild(self) -> IdIndex:
        """Rebuild the ID index by scanning the vault.

        Scans all relevant directories for entity IDs:
        - Tasks: All status folders, Completed/YYYY/MM, Archive/Tasks/*
        - Projects: Projects/, Archive/Projects/
        - People: People/, Archive/People/

        Returns:
            The rebuilt index.
        """
        logger.info("Rebuilding ID index from vault...")
        index = IdIndex()

        # Scan tasks
        self._scan_task_ids(index)

        # Scan projects
        self._scan_project_ids(index)

        # Scan people
        self._scan_person_ids(index)

        # Save to disk
        self.save(index)

        logger.info(
            "ID index rebuilt: %d tasks, %d projects, %d people",
            len(index.task_ids),
            len(index.project_ids),
            len(index.person_ids),
        )

        return index

    def _scan_task_ids(self, index: IdIndex) -> None:
        """Scan all task locations for IDs.

        Args:
            index: Index to populate with task IDs.
        """
        # Active task folders
        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            if folder.exists():
                self._scan_folder_for_ids(folder, index.task_ids)

                # For completed, also scan year/month subfolders
                if status == TaskStatus.COMPLETED:
                    for year_dir in folder.iterdir():
                        if year_dir.is_dir() and year_dir.name.isdigit():
                            for month_dir in year_dir.iterdir():
                                if month_dir.is_dir():
                                    self._scan_folder_for_ids(month_dir, index.task_ids)

        # Archive task folders
        for status in TaskStatus:
            archive_folder = self.vault.archive_folder("Tasks", status.value)
            if archive_folder.exists():
                self._scan_folder_for_ids(archive_folder, index.task_ids)

    def _scan_project_ids(self, index: IdIndex) -> None:
        """Scan project locations for IDs.

        Args:
            index: Index to populate with project IDs.
        """
        # Active projects
        projects_folder = self.vault.projects_folder()
        if projects_folder.exists():
            self._scan_folder_for_ids(projects_folder, index.project_ids)

        # Archived projects
        archive_projects = self.vault.archive_folder("Projects")
        if archive_projects.exists():
            self._scan_folder_for_ids(archive_projects, index.project_ids)

    def _scan_person_ids(self, index: IdIndex) -> None:
        """Scan people locations for IDs.

        Args:
            index: Index to populate with person IDs.
        """
        # Active people
        people_folder = self.vault.people_folder()
        if people_folder.exists():
            self._scan_folder_for_ids(people_folder, index.person_ids)

        # Archived people
        archive_people = self.vault.archive_folder("People")
        if archive_people.exists():
            self._scan_folder_for_ids(archive_people, index.person_ids)

    def _scan_folder_for_ids(self, folder: Path, ids: set[str]) -> None:
        """Scan a folder for entity IDs in markdown files.

        Args:
            folder: Folder to scan.
            ids: Set to add found IDs to.
        """
        for filepath in folder.glob("*.md"):
            try:
                metadata, _ = read_frontmatter(filepath)
                if "id" in metadata and metadata["id"]:
                    # Normalize to uppercase
                    ids.add(str(metadata["id"]).upper())
            except Exception as e:
                logger.debug("Failed to read ID from %s: %s", filepath, e)

    def is_stale(self) -> bool:
        """Check if the index is stale and needs rebuilding.

        The index is considered stale if:
        - The index file doesn't exist
        - The fingerprint doesn't match the current vault state

        Returns:
            True if the index should be rebuilt.
        """
        if not self.index_path.exists():
            return True

        index = self.load()
        if not index.fingerprint:
            return True

        current_fingerprint = self._compute_fingerprint()
        return index.fingerprint != current_fingerprint

    def _compute_fingerprint(self) -> str:
        """Compute a fingerprint of the vault's ID-relevant directories.

        The fingerprint is based on the modification times and file counts
        of directories that contain entity files. This allows detecting
        when files have been added, removed, or modified.

        Returns:
            A hash string representing the current vault state.
        """
        fingerprint_data: list[str] = []

        # Collect mtimes from task folders
        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            self._add_folder_to_fingerprint(folder, fingerprint_data)

            # Completed subfolders
            if status == TaskStatus.COMPLETED and folder.exists():
                for year_dir in folder.iterdir():
                    if year_dir.is_dir() and year_dir.name.isdigit():
                        for month_dir in year_dir.iterdir():
                            if month_dir.is_dir():
                                self._add_folder_to_fingerprint(
                                    month_dir, fingerprint_data
                                )

        # Archive task folders
        for status in TaskStatus:
            archive_folder = self.vault.archive_folder("Tasks", status.value)
            self._add_folder_to_fingerprint(archive_folder, fingerprint_data)

        # Projects
        self._add_folder_to_fingerprint(
            self.vault.projects_folder(), fingerprint_data
        )
        self._add_folder_to_fingerprint(
            self.vault.archive_folder("Projects"), fingerprint_data
        )

        # People
        self._add_folder_to_fingerprint(
            self.vault.people_folder(), fingerprint_data
        )
        self._add_folder_to_fingerprint(
            self.vault.archive_folder("People"), fingerprint_data
        )

        # Hash the collected data
        combined = "|".join(sorted(fingerprint_data))
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _add_folder_to_fingerprint(
        self, folder: Path, fingerprint_data: list[str]
    ) -> None:
        """Add a folder's state to the fingerprint data.

        Args:
            folder: Folder to fingerprint.
            fingerprint_data: List to append fingerprint components to.
        """
        if not folder.exists():
            return

        try:
            # Include folder mtime
            folder_mtime = folder.stat().st_mtime
            fingerprint_data.append(f"{folder}:{folder_mtime}")

            # Include file count and combined file mtimes
            md_files = list(folder.glob("*.md"))
            file_count = len(md_files)
            file_mtimes = sum(f.stat().st_mtime for f in md_files)
            fingerprint_data.append(f"{folder}:files:{file_count}:{file_mtimes}")
        except OSError as e:
            logger.debug("Failed to fingerprint %s: %s", folder, e)

    def contains(self, id_: str) -> bool:
        """Check if an ID exists in the index.

        Args:
            id_: The ID to check (case-insensitive).

        Returns:
            True if the ID exists in any entity type.
        """
        index = self.get_or_rebuild()
        return id_.upper() in index.all_ids()

    def add_task_id(self, id_: str) -> None:
        """Add a task ID to the index and persist.

        Args:
            id_: The task ID to add.
        """
        index = self.get_or_rebuild()
        index.task_ids.add(id_.upper())
        self.save(index)

    def add_project_id(self, id_: str) -> None:
        """Add a project ID to the index and persist.

        Args:
            id_: The project ID to add.
        """
        index = self.get_or_rebuild()
        index.project_ids.add(id_.upper())
        self.save(index)

    def add_person_id(self, id_: str) -> None:
        """Add a person ID to the index and persist.

        Args:
            id_: The person ID to add.
        """
        index = self.get_or_rebuild()
        index.person_ids.add(id_.upper())
        self.save(index)

    def get_or_rebuild(self) -> IdIndex:
        """Get the index, rebuilding if stale or missing.

        Returns:
            The current (possibly rebuilt) index.
        """
        if self._cached_index is not None and not self.is_stale():
            return self._cached_index

        if self.is_stale():
            return self.rebuild()

        self._cached_index = self.load()
        return self._cached_index
