"""YAML frontmatter parsing and generation for markdown files."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import frontmatter


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Read a markdown file and parse its frontmatter.

    Args:
        path: Path to the markdown file.

    Returns:
        A tuple of (frontmatter dict, content string).
    """
    with open(path, encoding="utf-8") as f:
        post = frontmatter.load(f)
    return dict(post.metadata), post.content


def write_frontmatter(path: Path, metadata: dict[str, Any], content: str) -> None:
    """Write a markdown file with frontmatter atomically.

    Args:
        path: Path to write to.
        metadata: Frontmatter dictionary.
        content: Markdown content.
    """
    # Convert dates/datetimes to ISO strings for YAML
    clean_metadata = _serialize_metadata(metadata)

    post = frontmatter.Post(content, **clean_metadata)
    output = frontmatter.dumps(post)

    # Atomic write: write to temp file then rename
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(output, encoding="utf-8")
    temp_path.rename(path)


def _serialize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Serialize metadata values for YAML.

    Converts dates and datetimes to ISO strings.

    Args:
        metadata: The metadata dictionary.

    Returns:
        Serialized metadata.
    """
    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _serialize_metadata(value)
        elif isinstance(value, list):
            result[key] = [
                v.isoformat() if isinstance(v, (date, datetime)) else v for v in value
            ]
        else:
            result[key] = value
    return result


def parse_wikilink(link: str) -> str | None:
    """Extract the path from an Obsidian wikilink.

    Args:
        link: A string that may be a wikilink like "[[Projects/MyProject]]".

    Returns:
        The path inside the brackets, or None if not a wikilink.
    """
    if link and link.startswith("[[") and link.endswith("]]"):
        return link[2:-2]
    return None


def make_wikilink(path: str) -> str:
    """Create an Obsidian wikilink from a path.

    Args:
        path: The path to link to.

    Returns:
        A wikilink string like "[[Projects/MyProject]]".
    """
    return f"[[{path}]]"
