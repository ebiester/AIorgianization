"""Person service for operations on person markdown files."""

import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from aio.exceptions import AmbiguousMatchError, PersonNotFoundError
from aio.models.person import Person
from aio.services.id_service import EntityType, IdService
from aio.services.vault import VaultService
from aio.utils import get_slug
from aio.utils.frontmatter import read_frontmatter, write_frontmatter
from aio.utils.ids import is_valid_id, normalize_id

logger = logging.getLogger(__name__)


class PersonService:
    """Service for person operations."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the person service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service
        self._id_service = IdService(vault_service)

    def list_people(self) -> list[str]:
        """List all person names.

        Returns:
            List of person names (without path or extension).
        """
        self.vault.ensure_initialized()
        people_folder = self.vault.people_folder()

        if not people_folder.exists():
            return []

        people: list[str] = []
        for filepath in people_folder.glob("*.md"):
            # Use stem (filename without extension) as person name
            people.append(filepath.stem)

        return sorted(people)

    def list_all(self) -> list["Person"]:
        """List all people as full objects.

        Returns:
            List of Person objects.
        """
        self.vault.ensure_initialized()
        people_folder = self.vault.people_folder()

        if not people_folder.exists():
            return []

        people: list[Person] = []
        for filepath in people_folder.glob("*.md"):
            try:
                metadata, content = read_frontmatter(filepath)
                person = self._read_person(filepath, metadata, content)
                people.append(person)
            except Exception as e:
                logger.debug("Failed to read person file %s: %s", filepath, e)

        return sorted(people, key=lambda p: p.name.lower())

    def exists(self, name: str) -> bool:
        """Check if a person exists.

        Args:
            name: Person name to check.

        Returns:
            True if the person exists.
        """
        self.vault.ensure_initialized()
        people_folder = self.vault.people_folder()

        # Normalize the name to match how we'd store it
        normalized = self._normalize_name(name)

        # Check for exact match or slug match
        for filepath in people_folder.glob("*.md"):
            if self._normalize_name(filepath.stem) == normalized:
                return True

        return False

    def find_similar(self, name: str, max_suggestions: int = 3) -> list[str]:
        """Find people with similar names.

        Args:
            name: Person name to match against.
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of similar person names, sorted by similarity.
        """
        existing = self.list_people()
        if not existing:
            return []

        name_lower = name.lower()

        # Calculate similarity scores
        scored: list[tuple[float, str]] = []
        for person in existing:
            # Use SequenceMatcher for fuzzy matching
            ratio = SequenceMatcher(None, name_lower, person.lower()).ratio()
            # Also check if one contains the other
            if name_lower in person.lower() or person.lower() in name_lower:
                ratio = max(ratio, 0.7)  # Boost substring matches
            if ratio > 0.4:  # Only include somewhat similar matches
                scored.append((ratio, person))

        # Sort by similarity (descending) and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored[:max_suggestions]]

    def validate_or_suggest(self, name: str) -> None:
        """Validate that a person exists, or raise with suggestions.

        Args:
            name: Person name to validate.

        Raises:
            PersonNotFoundError: If person doesn't exist, with suggestions.
        """
        if self.exists(name):
            return

        suggestions = self.find_similar(name)
        raise PersonNotFoundError(name, suggestions)

    def get(self, person_id: str) -> Person:
        """Get a person by ID.

        Args:
            person_id: The 4-character person ID.

        Returns:
            The person.

        Raises:
            PersonNotFoundError: If the person is not found.
        """
        person_id = normalize_id(person_id)
        person = self._find_person_by_id(person_id)
        if not person:
            raise PersonNotFoundError(person_id)
        return person

    def find(self, query: str) -> Person:
        """Find a person by ID or name substring.

        Args:
            query: Person ID (4 chars) or name substring.

        Returns:
            The matching person.

        Raises:
            PersonNotFoundError: If no person matches.
            AmbiguousMatchError: If multiple people match.
        """
        # If it looks like an ID, try ID lookup first
        if is_valid_id(query):
            try:
                return self.get(query)
            except PersonNotFoundError:
                pass  # Fall through to name search

        # Search by name
        matches = self._find_people_by_name(query)
        if not matches:
            suggestions = self.find_similar(query)
            raise PersonNotFoundError(query, suggestions)
        if len(matches) > 1:
            raise AmbiguousMatchError(query, [p.id for p in matches])
        return matches[0]

    def _find_person_by_id(self, person_id: str) -> Person | None:
        """Find a person by their ID.

        Args:
            person_id: The person ID to find (normalized).

        Returns:
            The Person, or None if not found.
        """
        person_id = person_id.upper()
        people_folder = self.vault.people_folder()

        if not people_folder.exists():
            return None

        for filepath in people_folder.glob("*.md"):
            try:
                metadata, content = read_frontmatter(filepath)
                if metadata.get("id", "").upper() == person_id:
                    return self._read_person(filepath, metadata, content)
            except Exception as e:
                logger.debug("Failed to read person file %s: %s", filepath, e)

        return None

    def _find_people_by_name(self, query: str) -> list[Person]:
        """Find people by name substring.

        Args:
            query: Name substring to search for.

        Returns:
            List of matching people.
        """
        query_lower = query.lower()
        matches: list[Person] = []
        people_folder = self.vault.people_folder()

        if not people_folder.exists():
            return matches

        for filepath in people_folder.glob("*.md"):
            try:
                metadata, content = read_frontmatter(filepath)
                # Check both filename (stem) and name in frontmatter
                name = metadata.get("name", filepath.stem)
                if query_lower in name.lower() or query_lower in filepath.stem.lower():
                    matches.append(self._read_person(filepath, metadata, content))
            except Exception as e:
                logger.debug("Failed to read person file %s: %s", filepath, e)

        return matches

    def _read_person(
        self, filepath: Path, metadata: dict[str, Any], content: str
    ) -> Person:
        """Read a person from parsed file data.

        Args:
            filepath: Path to the person file.
            metadata: Parsed frontmatter.
            content: File content.

        Returns:
            The Person object.
        """
        return Person(
            id=metadata.get("id", "????"),
            type=metadata.get("type", "person"),
            name=metadata.get("name", filepath.stem),
            body=content,
            team=metadata.get("team"),
            role=metadata.get("role"),
            email=metadata.get("email"),
        )

    def create(
        self,
        name: str,
        team: str | None = None,
        role: str | None = None,
        email: str | None = None,
    ) -> Person:
        """Create a new person.

        Args:
            name: Person's full name.
            team: Optional team wikilink.
            role: Optional role/title.
            email: Optional email address.

        Returns:
            The created person.
        """
        self.vault.ensure_initialized()

        person = Person(
            id=self._id_service.generate_unique_id(EntityType.PERSON),
            name=name,
            team=team,
            role=role,
            email=email,
        )

        # Generate content with Dataview query for delegated tasks
        # Use link() to match wikilinks stored in waitingOn frontmatter
        slug = get_slug(name)
        body = f"""# {name}

## Notes

## Tasks Delegated

```dataview
TABLE due AS "Due", status AS "Status"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/{slug}")) AND status != "completed"
SORT due ASC
```

## Previously Completed Tasks

```dataview
TABLE due AS "Due", completed AS "Completed"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/{slug}")) AND status = "completed"
SORT completed DESC
```

## Interactions
"""
        person.body = body

        # Write file
        folder = self.vault.people_folder()
        filename = person.generate_filename()
        filepath = folder / filename

        if filepath.exists():
            raise FileExistsError(
                f"Cannot create person: file already exists at {filepath}. "
                f"Another person may have a conflicting name."
            )

        write_frontmatter(filepath, person.frontmatter(), body)

        return person

    def _normalize_name(self, name: str) -> str:
        """Normalize a person name for comparison.

        Args:
            name: Name to normalize.

        Returns:
            Lowercase name with spaces and hyphens normalized.
        """
        return name.lower().replace("-", " ").replace("_", " ")

    def get_slug(self, name: str) -> str:
        """Get the slug (filename stem) for a person name.

        Args:
            name: Person name.

        Returns:
            Slugified name matching what would be used in filename.
        """
        slug = name.replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug
