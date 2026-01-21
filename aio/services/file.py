"""File service for get/set operations with backup.

Provides safe file operations with automatic timestamped backups before writes.
Supports flexible file lookup by ID, title, or path.
"""

from datetime import datetime
from pathlib import Path

from aio.exceptions import AmbiguousMatchError, FileOutsideVaultError
from aio.services.vault import VaultService
from aio.utils.frontmatter import read_frontmatter
from aio.utils.ids import is_valid_id, normalize_id


class FileService:
    """Service for file get/set operations with automatic backup."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the file service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service

    def get(self, query: str) -> str:
        """Get the contents of a file in the vault.

        Args:
            query: File ID (4-char), title substring, or path relative to vault.

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileOutsideVaultError: If path resolves to outside the vault.
            AmbiguousMatchError: If query matches multiple files.
        """
        resolved = self._resolve_query(query)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {query}")

        return resolved.read_text(encoding="utf-8")

    def get_path(self, query: str) -> Path:
        """Resolve a query to a file path without reading content.

        Args:
            query: File ID (4-char), title substring, or path relative to vault.

        Returns:
            Resolved absolute path to the file.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileOutsideVaultError: If path resolves to outside the vault.
            AmbiguousMatchError: If query matches multiple files.
        """
        resolved = self._resolve_query(query)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {query}")

        return resolved

    def set(self, query: str, content: str) -> tuple[Path, Path | None]:
        """Set file contents with automatic backup.

        Creates a timestamped backup of the existing file before overwriting.
        If the file doesn't exist, creates it without backup.

        Args:
            query: File ID (4-char), title substring, or path relative to vault.
            content: New file contents.

        Returns:
            Tuple of (resolved file path, backup path or None if no backup needed).

        Raises:
            FileOutsideVaultError: If path resolves to outside the vault.
            AmbiguousMatchError: If query matches multiple files (for ID/title lookup).
        """
        # For set, we need special handling:
        # - If query looks like a path, allow creating new files
        # - If query is ID/title, file must exist (can't create by ID/title)
        resolved = self._resolve_query(query, allow_new_file=True)
        backup_path: Path | None = None

        # Create backup if file exists
        if resolved.exists():
            backup_path = self._create_backup(resolved)

        # Ensure parent directory exists
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Write new content atomically
        temp_path = resolved.with_suffix(resolved.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.rename(resolved)

        return resolved, backup_path

    def _resolve_query(self, query: str, allow_new_file: bool = False) -> Path:
        """Resolve a query to a file path.

        Tries to resolve in order:
        1. If query looks like an ID (4 chars), search for file with that ID
        2. If query looks like a path (contains / or ends with known extension),
           resolve as path
        3. Otherwise, search by title

        Args:
            query: File ID, title substring, or path.
            allow_new_file: If True, allow query to resolve to non-existent path
                           (for file creation). Only applies to path queries.

        Returns:
            Resolved absolute path.

        Raises:
            FileNotFoundError: If file doesn't exist (and allow_new_file is False).
            FileOutsideVaultError: If path resolves to outside the vault.
            AmbiguousMatchError: If query matches multiple files.
        """
        # Check if it looks like a path (contains separator or extension)
        looks_like_path = "/" in query or "\\" in query or query.endswith(".md")

        # If it looks like an ID and doesn't look like a path, try ID lookup first
        if is_valid_id(query) and not looks_like_path:
            found = self._find_file_by_id(query)
            if found:
                return found
            # If ID lookup fails, fall through to path/title

        # If it looks like a path, resolve as path
        if looks_like_path:
            resolved = self._resolve_path(query)
            if allow_new_file or resolved.exists():
                return resolved
            # Path doesn't exist, try title search as fallback
            # (user might have typed a title with / in it, though unlikely)

        # Try title search
        matches = self._find_files_by_title(query)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Return relative paths for cleaner error message
            vault_root = self.vault.vault_path.resolve()
            rel_paths = [str(m.relative_to(vault_root)) for m in matches]
            raise AmbiguousMatchError(query, rel_paths)

        # Nothing found - if it looks like a path and allow_new_file, treat as path
        if looks_like_path and allow_new_file:
            return self._resolve_path(query)

        raise FileNotFoundError(f"File not found: {query}")

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve and validate file path within vault.

        Args:
            file_path: Path relative to vault root, or absolute path.

        Returns:
            Resolved absolute path.

        Raises:
            FileOutsideVaultError: If path resolves to outside the vault.
        """
        vault_root = self.vault.vault_path.resolve()
        path = Path(file_path)

        # If relative, resolve relative to vault root
        resolved = (
            (vault_root / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )

        # Security check: ensure path is within vault
        try:
            resolved.relative_to(vault_root)
        except ValueError as e:
            raise FileOutsideVaultError(
                f"Path '{file_path}' resolves outside vault: {resolved}"
            ) from e

        return resolved

    def _find_file_by_id(self, file_id: str) -> Path | None:
        """Find a markdown file by its frontmatter ID.

        Args:
            file_id: The 4-character file ID.

        Returns:
            Path to the file, or None if not found.
        """
        file_id = normalize_id(file_id)
        aio_path = self.vault.aio_path

        # Search all markdown files in AIO directory
        for md_file in aio_path.rglob("*.md"):
            # Skip backup files
            if "/Backup/" in str(md_file) or "\\Backup\\" in str(md_file):
                continue
            try:
                metadata, _ = read_frontmatter(md_file)
                if metadata.get("id", "").upper() == file_id:
                    return md_file
            except Exception:
                continue  # Skip files that can't be parsed

        return None

    def _find_files_by_title(self, title_query: str) -> list[Path]:
        """Find markdown files by title substring.

        Args:
            title_query: Substring to search for in titles.

        Returns:
            List of matching file paths.
        """
        matches: list[Path] = []
        aio_path = self.vault.aio_path
        query_lower = title_query.lower()

        # Search all markdown files in AIO directory
        for md_file in aio_path.rglob("*.md"):
            # Skip backup files
            if "/Backup/" in str(md_file) or "\\Backup\\" in str(md_file):
                continue
            try:
                metadata, content = read_frontmatter(md_file)
                # Check frontmatter title
                title = metadata.get("title", "")
                if title and query_lower in title.lower():
                    matches.append(md_file)
                    continue
                # Check first heading in content
                for line in content.split("\n"):
                    if line.startswith("# "):
                        heading = line[2:].strip()
                        if query_lower in heading.lower():
                            matches.append(md_file)
                        break
            except Exception:
                continue  # Skip files that can't be parsed

        return matches

    def _create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of a file.

        Preserves the directory structure relative to vault root.

        Args:
            file_path: Absolute path to the file to backup.

        Returns:
            Path to the created backup file.
        """
        vault_root = self.vault.vault_path.resolve()
        backup_folder = self.vault.backup_folder()

        # Get path relative to vault root
        relative = file_path.relative_to(vault_root)

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = file_path.stem
        suffix = file_path.suffix
        backup_filename = f"{stem}-{timestamp}{suffix}"

        # Build backup path preserving directory structure
        backup_path = backup_folder / relative.parent / backup_filename
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy content to backup
        content = file_path.read_text(encoding="utf-8")
        backup_path.write_text(content, encoding="utf-8")

        return backup_path
