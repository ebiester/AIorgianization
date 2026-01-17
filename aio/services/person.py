"""Person service for operations on person markdown files."""

import logging
from difflib import SequenceMatcher

from aio.exceptions import PersonNotFoundError
from aio.models.person import Person
from aio.services.vault import VaultService
from aio.utils.frontmatter import write_frontmatter

logger = logging.getLogger(__name__)


class PersonService:
    """Service for person operations."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the person service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service

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
            name=name,
            team=team,
            role=role,
            email=email,
        )

        # Generate content with Dataview query for delegated tasks
        # Use link() to match wikilinks stored in waitingOn frontmatter
        body = f"""# {name}

## Notes

## Tasks Delegated

```dataview
TABLE due AS "Due", status AS "Status"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/{name}")) AND status != "completed"
SORT due ASC
```

## Previously Completed Tasks

```dataview
TABLE due AS "Due", completed AS "Completed"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/{name}")) AND status = "completed"
SORT completed DESC
```

## Interactions
"""
        person.body = body

        # Write file
        folder = self.vault.people_folder()
        filename = person.generate_filename()
        filepath = folder / filename

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
