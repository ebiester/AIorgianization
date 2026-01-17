"""Unit tests for ID generation."""

import pytest

from aio.utils.ids import ID_CHARS, generate_id, is_valid_id, normalize_id


class TestGenerateId:
    """Tests for generate_id function."""

    def test_generates_4_char_id(self) -> None:
        """IDs should be exactly 4 characters."""
        task_id = generate_id()
        assert len(task_id) == 4

    def test_uses_valid_characters(self) -> None:
        """IDs should only use characters from ID_CHARS."""
        for _ in range(100):
            task_id = generate_id()
            for char in task_id:
                assert char in ID_CHARS

    def test_is_uppercase(self) -> None:
        """Generated IDs should be uppercase."""
        for _ in range(100):
            task_id = generate_id()
            assert task_id == task_id.upper()

    def test_excludes_ambiguous_chars(self) -> None:
        """IDs should not contain 0, 1, I, or O."""
        for _ in range(100):
            task_id = generate_id()
            assert "0" not in task_id
            assert "1" not in task_id
            assert "I" not in task_id
            assert "O" not in task_id


class TestIsValidId:
    """Tests for is_valid_id function."""

    def test_valid_ids(self) -> None:
        """Valid IDs should return True."""
        assert is_valid_id("AB2C")
        assert is_valid_id("WXYZ")
        assert is_valid_id("2345")

    def test_valid_ids_case_insensitive(self) -> None:
        """Lowercase IDs should be valid."""
        assert is_valid_id("ab2c")
        assert is_valid_id("AbCd")

    def test_invalid_length(self) -> None:
        """IDs with wrong length should be invalid."""
        assert not is_valid_id("ABC")
        assert not is_valid_id("ABCDE")
        assert not is_valid_id("")

    def test_invalid_chars(self) -> None:
        """IDs with invalid characters should be invalid."""
        assert not is_valid_id("AB0C")  # Contains 0
        assert not is_valid_id("AB1C")  # Contains 1
        assert not is_valid_id("ABIC")  # Contains I
        assert not is_valid_id("ABOC")  # Contains O
        assert not is_valid_id("AB-C")  # Contains hyphen


class TestNormalizeId:
    """Tests for normalize_id function."""

    def test_normalizes_to_uppercase(self) -> None:
        """IDs should be normalized to uppercase."""
        assert normalize_id("ab2c") == "AB2C"
        assert normalize_id("AbCd") == "ABCD"

    def test_already_uppercase(self) -> None:
        """Uppercase IDs should remain unchanged."""
        assert normalize_id("AB2C") == "AB2C"

    def test_invalid_id_raises(self) -> None:
        """Invalid IDs should raise ValueError."""
        with pytest.raises(ValueError):
            normalize_id("invalid")
        with pytest.raises(ValueError):
            normalize_id("AB0C")
