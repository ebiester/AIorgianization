"""4-character ID generation for tasks, projects, and people.

IDs use characters that are unambiguous when read aloud or in various fonts.
Excludes: 0 (zero), 1 (one), I (capital i), O (capital o)
"""

import random
import re

# 32 unambiguous characters
ID_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ID_LENGTH = 4
ID_PATTERN = re.compile(f"^[{ID_CHARS}]{{{ID_LENGTH}}}$", re.IGNORECASE)


def generate_id() -> str:
    """Generate a random 4-character ID.

    Returns:
        A 4-character uppercase alphanumeric ID.
    """
    return "".join(random.choices(ID_CHARS, k=ID_LENGTH))


def is_valid_id(id_str: str) -> bool:
    """Check if a string is a valid ID.

    Args:
        id_str: The string to validate.

    Returns:
        True if the string matches the ID pattern (case-insensitive).
    """
    return bool(ID_PATTERN.match(id_str))


def normalize_id(id_str: str) -> str:
    """Normalize an ID to uppercase.

    Args:
        id_str: The ID string to normalize.

    Returns:
        The ID in uppercase.

    Raises:
        ValueError: If the ID is not valid.
    """
    if not is_valid_id(id_str):
        raise ValueError(f"Invalid ID: {id_str}")
    return id_str.upper()
