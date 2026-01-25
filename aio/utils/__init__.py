"""Utility functions."""

from aio.utils.dates import format_relative_date, parse_date
from aio.utils.ids import generate_id, is_valid_id


def get_slug(name: str) -> str:
    """Convert a name to a URL/filename-safe slug.

    Args:
        name: The name to slugify.

    Returns:
        Slugified name with spaces converted to hyphens and
        non-alphanumeric characters removed.
    """
    slug = name.replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


__all__ = ["generate_id", "is_valid_id", "parse_date", "format_relative_date", "get_slug"]
