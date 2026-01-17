"""Context pack service for CRUD operations on context pack markdown files."""

import re
from datetime import datetime
from pathlib import Path

from aio.exceptions import ContextPackExistsError, ContextPackNotFoundError
from aio.models.context_pack import CATEGORY_FOLDERS, ContextPack, ContextPackCategory
from aio.services.vault import VaultService
from aio.utils.frontmatter import read_frontmatter, write_frontmatter


class ContextPackService:
    """Service for context pack CRUD operations."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the context pack service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service

    def context_packs_folder(self, category: ContextPackCategory | None = None) -> Path:
        """Get the context packs folder path.

        Args:
            category: Optional category to get specific subfolder.

        Returns:
            Path to the context packs folder or category subfolder.
        """
        base = self.vault.aio_path / "Context-Packs"
        if category:
            return base / CATEGORY_FOLDERS[category]
        return base

    def list_packs(
        self, category: ContextPackCategory | None = None
    ) -> list[ContextPack]:
        """List all context packs.

        Args:
            category: Optional category filter.

        Returns:
            List of context packs.
        """
        self.vault.ensure_initialized()
        packs: list[ContextPack] = []

        if category:
            categories = [category]
        else:
            categories = list(ContextPackCategory)

        for cat in categories:
            folder = self.context_packs_folder(cat)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    try:
                        pack = self._read_pack_file(filepath, cat)
                        packs.append(pack)
                    except Exception:
                        pass

        # Sort by title
        packs.sort(key=lambda p: p.title.lower())
        return packs

    def get(self, pack_id: str) -> ContextPack:
        """Get a context pack by ID.

        Args:
            pack_id: The pack ID (filename without .md).

        Returns:
            The context pack.

        Raises:
            ContextPackNotFoundError: If the pack is not found.
        """
        filepath, category = self._find_pack_file(pack_id)
        if not filepath or not category:
            raise ContextPackNotFoundError(f"Context pack not found: {pack_id}")
        return self._read_pack_file(filepath, category)

    def find(self, query: str) -> ContextPack:
        """Find a context pack by ID or title substring.

        Args:
            query: Pack ID or title substring.

        Returns:
            The matching context pack.

        Raises:
            ContextPackNotFoundError: If no pack matches.
        """
        # Try exact ID match first
        try:
            return self.get(query)
        except ContextPackNotFoundError:
            pass

        # Try ID match (case-insensitive)
        query_lower = query.lower()
        for cat in ContextPackCategory:
            folder = self.context_packs_folder(cat)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    if filepath.stem.lower() == query_lower:
                        return self._read_pack_file(filepath, cat)

        # Search by title substring
        matches: list[ContextPack] = []
        for cat in ContextPackCategory:
            folder = self.context_packs_folder(cat)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    try:
                        pack = self._read_pack_file(filepath, cat)
                        if query_lower in pack.title.lower():
                            matches.append(pack)
                    except Exception:
                        pass

        if not matches:
            raise ContextPackNotFoundError(f"No context pack found matching: {query}")
        if len(matches) == 1:
            return matches[0]
        # Return first match for simplicity (could add AmbiguousMatchError if needed)
        return matches[0]

    def create(
        self,
        title: str,
        category: ContextPackCategory,
        content: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> ContextPack:
        """Create a new context pack.

        Args:
            title: Display title for the pack.
            category: Pack category (domain, system, operating).
            content: Optional initial markdown content.
            description: Optional brief description.
            tags: Optional list of tags.

        Returns:
            The created context pack.

        Raises:
            ContextPackExistsError: If a pack with this ID already exists.
        """
        self.vault.ensure_initialized()

        # Generate ID from title (slugify)
        pack_id = self._slugify(title)

        # Check if pack already exists
        existing, _ = self._find_pack_file(pack_id)
        if existing:
            raise ContextPackExistsError(
                f"Context pack '{pack_id}' already exists. "
                "Use append() to add content to it."
            )

        now = datetime.now()
        pack = ContextPack(
            id=pack_id,
            category=category,
            title=title,
            description=description,
            tags=tags or [],
            created=now,
            updated=now,
        )

        # Generate content
        body = f"# {title}\n\n"
        if content:
            body += content
        else:
            body += "## Overview\n\n"
        pack.body = body

        # Write file
        folder = self.context_packs_folder(category)
        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / pack.generate_filename()

        write_frontmatter(filepath, pack.frontmatter(), body)

        return pack

    def append(
        self,
        pack_id: str,
        content: str,
        section: str | None = None,
    ) -> ContextPack:
        """Append content to an existing context pack.

        Args:
            pack_id: The pack ID or name.
            content: Markdown content to append.
            section: Optional section heading to append under (e.g., "Key Concepts").
                    If not found or not specified, appends to end.

        Returns:
            The updated context pack.

        Raises:
            ContextPackNotFoundError: If the pack is not found.
        """
        pack = self.find(pack_id)
        filepath, _ = self._find_pack_file(pack.id)
        if not filepath:
            raise ContextPackNotFoundError(f"Context pack file not found: {pack.id}")

        # Update body
        if section:
            pack.body = self._append_to_section(pack.body, content, section)
        else:
            # Append to end
            pack.body = pack.body.rstrip() + "\n\n" + content

        # Update timestamp
        pack.updated = datetime.now()

        # Write back
        write_frontmatter(filepath, pack.frontmatter(), pack.body)

        return pack

    def append_file(
        self,
        pack_id: str,
        file_path: str,
        section: str | None = None,
    ) -> ContextPack:
        """Append a file's content to an existing context pack.

        Args:
            pack_id: The pack ID or name.
            file_path: Path to the file in the vault (relative to AIO/ or absolute).
            section: Optional section heading to append under.

        Returns:
            The updated context pack.

        Raises:
            ContextPackNotFoundError: If the pack is not found.
            FileNotFoundError: If the source file is not found.
        """
        # Resolve file path
        if Path(file_path).is_absolute():
            source_path = Path(file_path)
        else:
            # Try relative to AIO folder first
            source_path = self.vault.aio_path / file_path
            if not source_path.exists():
                # Try relative to vault root
                source_path = self.vault.vault_path / file_path

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        # Read source file content
        file_content = source_path.read_text(encoding="utf-8")

        # Create attribution header
        relative_path = source_path.relative_to(self.vault.vault_path)
        wikilink = f"[[{relative_path.with_suffix('').as_posix()}]]"
        attributed_content = f"> From: {wikilink}\n\n{file_content}"

        # Append with attribution
        return self.append(pack_id, attributed_content, section)

    def add_source(self, pack_id: str, source: str) -> ContextPack:
        """Add a source reference to a context pack.

        Args:
            pack_id: The pack ID or name.
            source: Source reference (wikilink, URL, etc.).

        Returns:
            The updated context pack.

        Raises:
            ContextPackNotFoundError: If the pack is not found.
        """
        pack = self.find(pack_id)
        filepath, _ = self._find_pack_file(pack.id)
        if not filepath:
            raise ContextPackNotFoundError(f"Context pack file not found: {pack.id}")

        # Add source if not already present
        if source not in pack.sources:
            pack.sources.append(source)

        # Update timestamp
        pack.updated = datetime.now()

        # Write back
        write_frontmatter(filepath, pack.frontmatter(), pack.body)

        return pack

    def _find_pack_file(
        self, pack_id: str
    ) -> tuple[Path | None, ContextPackCategory | None]:
        """Find a context pack file by its ID.

        Args:
            pack_id: The pack ID to find.

        Returns:
            Tuple of (path, category) or (None, None) if not found.
        """
        pack_id_lower = pack_id.lower()

        for cat in ContextPackCategory:
            folder = self.context_packs_folder(cat)
            if folder.exists():
                # Exact match
                filepath = folder / f"{pack_id}.md"
                if filepath.exists():
                    return filepath, cat

                # Case-insensitive match
                for filepath in folder.glob("*.md"):
                    if filepath.stem.lower() == pack_id_lower:
                        return filepath, cat

        return None, None

    def _read_pack_file(self, filepath: Path, category: ContextPackCategory) -> ContextPack:
        """Read a context pack from a markdown file.

        Args:
            filepath: Path to the pack file.
            category: The pack's category.

        Returns:
            The parsed context pack.
        """
        metadata, content = read_frontmatter(filepath)

        # Extract title from first H1 heading or frontmatter
        title = metadata.get("title") or self._extract_title(content, filepath)

        # Parse timestamps
        created = datetime.now()
        if "created" in metadata:
            created_val = metadata["created"]
            if isinstance(created_val, datetime):
                created = created_val
            elif isinstance(created_val, str):
                created = datetime.fromisoformat(created_val)

        updated = datetime.now()
        if "updated" in metadata:
            updated_val = metadata["updated"]
            if isinstance(updated_val, datetime):
                updated = updated_val
            elif isinstance(updated_val, str):
                updated = datetime.fromisoformat(updated_val)

        return ContextPack(
            id=metadata.get("id", filepath.stem),
            type=metadata.get("type", "context-pack"),
            category=ContextPackCategory(metadata.get("category", category.value)),
            title=title,
            description=metadata.get("description"),
            tags=metadata.get("tags", []),
            sources=metadata.get("sources", []),
            body=content,
            created=created,
            updated=updated,
        )

    def _extract_title(self, content: str, filepath: Path) -> str:
        """Extract title from content or filename.

        Args:
            content: Markdown content.
            filepath: Path to use as fallback.

        Returns:
            The pack title.
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fall back to filename
        return filepath.stem.replace("-", " ").title()

    def _slugify(self, title: str) -> str:
        """Convert a title to a URL-friendly slug.

        Args:
            title: The title to slugify.

        Returns:
            A lowercase, hyphenated slug.
        """
        slug = title.lower()
        slug = slug.replace(" ", "-")
        # Keep only alphanumeric and hyphens
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        # Collapse multiple hyphens
        while "--" in slug:
            slug = slug.replace("--", "-")
        # Trim to reasonable length
        slug = slug[:50].rstrip("-")
        return slug

    def _append_to_section(self, body: str, content: str, section: str) -> str:
        """Append content after a section heading.

        Args:
            body: The current body content.
            content: Content to append.
            section: Section heading to find (without ##).

        Returns:
            Updated body content.
        """
        # Look for ## Section heading
        pattern = rf"(## {re.escape(section)}.*?)(\n## |\Z)"
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)

        if match:
            # Found the section, insert before the next section or end
            insert_pos = match.end(1)
            return body[:insert_pos] + "\n\n" + content + body[insert_pos:]
        else:
            # Section not found, append to end
            return body.rstrip() + "\n\n" + content
