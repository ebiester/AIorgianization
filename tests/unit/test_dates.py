"""Unit tests for date parsing and formatting."""

from datetime import date, timedelta

import pytest

from aio.exceptions import InvalidDateError
from aio.utils.dates import (
    format_relative_date,
    is_due_this_week,
    is_due_today,
    is_overdue,
    parse_date,
)


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_iso_date(self) -> None:
        """ISO format dates should parse correctly."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_tomorrow(self) -> None:
        """'tomorrow' should parse to tomorrow's date."""
        result = parse_date("tomorrow")
        assert result == date.today() + timedelta(days=1)

    def test_parse_today(self) -> None:
        """'today' should parse to today's date."""
        result = parse_date("today")
        assert result == date.today()

    def test_parse_in_days(self) -> None:
        """'in X days' should parse correctly."""
        result = parse_date("in 3 days")
        assert result == date.today() + timedelta(days=3)

    def test_empty_string_raises(self) -> None:
        """Empty string should raise InvalidDateError."""
        with pytest.raises(InvalidDateError):
            parse_date("")
        with pytest.raises(InvalidDateError):
            parse_date("   ")

    def test_invalid_date_raises(self) -> None:
        """Invalid date strings should raise InvalidDateError."""
        with pytest.raises(InvalidDateError):
            parse_date("not a date")


class TestFormatRelativeDate:
    """Tests for format_relative_date function."""

    def test_today(self) -> None:
        """Today's date should format as 'today'."""
        assert format_relative_date(date.today()) == "today"

    def test_tomorrow(self) -> None:
        """Tomorrow's date should format as 'tomorrow'."""
        assert format_relative_date(date.today() + timedelta(days=1)) == "tomorrow"

    def test_yesterday(self) -> None:
        """Yesterday's date should format as 'yesterday'."""
        assert format_relative_date(date.today() - timedelta(days=1)) == "yesterday"

    def test_days_ago(self) -> None:
        """Past dates should format as 'X days ago'."""
        result = format_relative_date(date.today() - timedelta(days=5))
        assert "days ago" in result


class TestDateChecks:
    """Tests for date check functions."""

    def test_is_overdue_past_date(self) -> None:
        """Past dates should be overdue."""
        assert is_overdue(date.today() - timedelta(days=1))

    def test_is_overdue_today(self) -> None:
        """Today's date should not be overdue."""
        assert not is_overdue(date.today())

    def test_is_overdue_future(self) -> None:
        """Future dates should not be overdue."""
        assert not is_overdue(date.today() + timedelta(days=1))

    def test_is_due_today_true(self) -> None:
        """Today's date should be due today."""
        assert is_due_today(date.today())

    def test_is_due_today_false(self) -> None:
        """Other dates should not be due today."""
        assert not is_due_today(date.today() + timedelta(days=1))
        assert not is_due_today(date.today() - timedelta(days=1))

    def test_is_due_this_week(self) -> None:
        """Dates within 7 days should be due this week."""
        assert is_due_this_week(date.today())
        assert is_due_this_week(date.today() + timedelta(days=3))
        assert is_due_this_week(date.today() + timedelta(days=7))

    def test_not_due_this_week(self) -> None:
        """Dates beyond 7 days should not be due this week."""
        assert not is_due_this_week(date.today() + timedelta(days=8))
        assert not is_due_this_week(date.today() - timedelta(days=1))
