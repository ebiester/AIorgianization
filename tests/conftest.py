"""Pytest fixtures for AIorgianization tests."""

from datetime import date, datetime
from pathlib import Path

import pytest

from aio.services.vault import VaultService


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for UAT test tracking."""
    config.addinivalue_line(
        "markers",
        "uat(id): Mark test with UAT case ID (e.g., @pytest.mark.uat('UAT-003'))",
    )


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault with .obsidian folder.

    Returns:
        Path to the temporary vault.
    """
    vault = tmp_path / "TestVault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


@pytest.fixture
def initialized_vault(temp_vault: Path) -> Path:
    """Create an initialized vault with AIO structure.

    Returns:
        Path to the initialized vault.
    """
    vault_service = VaultService(temp_vault)
    vault_service.initialize()
    return temp_vault


@pytest.fixture
def vault_service(initialized_vault: Path) -> VaultService:
    """Create a VaultService for the initialized vault.

    Returns:
        Configured VaultService.
    """
    return VaultService(initialized_vault)


@pytest.fixture
def sample_task_file(initialized_vault: Path) -> Path:
    """Create a sample task file in the vault.

    Returns:
        Path to the created task file.
    """
    task_content = """---
id: AB2C
type: task
status: inbox
due: 2024-01-20
project: "[[Projects/Test-Project]]"
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Test Task

## Notes
This is a test task.
"""
    task_path = initialized_vault / "AIO" / "Tasks" / "Inbox" / "2024-01-15-test-task.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path


@pytest.fixture
def today() -> date:
    """Get today's date for tests."""
    return date.today()


@pytest.fixture
def now() -> datetime:
    """Get current datetime for tests."""
    return datetime.now()
