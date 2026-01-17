"""Natural language date parsing and formatting."""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import dateparser

from aio.exceptions import InvalidDateError

if TYPE_CHECKING:
    pass


def parse_date(date_str: str) -> date:
    """Parse a natural language date string.

    Supports formats like:
    - "tomorrow", "today", "yesterday"
    - "next monday", "friday"
    - "in 3 days", "in a week"
    - "end of week", "end of month"
    - ISO format: "2024-01-15"

    Args:
        date_str: A natural language date string.

    Returns:
        A date object.

    Raises:
        InvalidDateError: If the date string cannot be parsed.
    """
    if not date_str or not date_str.strip():
        raise InvalidDateError("Date string cannot be empty")

    # Try parsing with dateparser
    result = dateparser.parse(
        date_str,
        settings={
            "PREFER_DATES_FROM": "future",
            "PREFER_DAY_OF_MONTH": "first",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if result is None:
        raise InvalidDateError(f"Could not parse date: {date_str}")

    return result.date()


def format_relative_date(d: date) -> str:
    """Format a date as a relative string for display.

    Args:
        d: The date to format.

    Returns:
        A human-readable relative date string.
    """
    today = date.today()
    delta = (d - today).days

    if delta < -1:
        return f"{abs(delta)} days ago"
    elif delta == -1:
        return "yesterday"
    elif delta == 0:
        return "today"
    elif delta == 1:
        return "tomorrow"
    elif delta < 7:
        return d.strftime("%A")  # Day name
    elif delta < 14:
        return "next " + d.strftime("%A")
    else:
        return d.strftime("%b %d")  # "Jan 15"


def is_overdue(d: date) -> bool:
    """Check if a date is in the past.

    Args:
        d: The date to check.

    Returns:
        True if the date is before today.
    """
    return d < date.today()


def is_due_today(d: date) -> bool:
    """Check if a date is today.

    Args:
        d: The date to check.

    Returns:
        True if the date is today.
    """
    return d == date.today()


def is_due_this_week(d: date) -> bool:
    """Check if a date is within the next 7 days.

    Args:
        d: The date to check.

    Returns:
        True if the date is within the next 7 days (including today).
    """
    today = date.today()
    return today <= d <= today + timedelta(days=7)


def format_iso_date(d: date) -> str:
    """Format a date as ISO 8601.

    Args:
        d: The date to format.

    Returns:
        ISO 8601 formatted date string (YYYY-MM-DD).
    """
    return d.isoformat()


def format_iso_datetime(dt: datetime) -> str:
    """Format a datetime as ISO 8601.

    Args:
        dt: The datetime to format.

    Returns:
        ISO 8601 formatted datetime string.
    """
    return dt.isoformat()
