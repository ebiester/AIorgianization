"""Unit tests for Project model and ProjectService."""

from datetime import date

import pytest

from aio.exceptions import AmbiguousMatchError, ProjectNotFoundError
from aio.models.project import Project, ProjectStatus
from aio.services.project import ProjectService
from aio.services.vault import VaultService


class TestProjectModel:
    """Tests for Project Pydantic model."""

    def test_default_values(self) -> None:
        """Project should have sensible defaults."""
        project = Project(id="AB2C", title="Test Project")
        assert project.status == ProjectStatus.ACTIVE
        assert project.type == "project"
        assert project.category == "project"
        assert project.body == ""

    def test_generate_filename(self) -> None:
        """generate_filename should create valid filename."""
        project = Project(id="AB2C", title="Q4 Migration")
        filename = project.generate_filename()
        assert filename == "Q4-Migration.md"

    def test_generate_filename_special_chars(self) -> None:
        """generate_filename should handle special characters."""
        project = Project(id="AB2C", title="Project with @#$ special! chars?")
        filename = project.generate_filename()
        assert "@" not in filename
        assert "#" not in filename
        assert "?" not in filename

    def test_frontmatter_basic(self) -> None:
        """frontmatter should include required fields."""
        project = Project(id="AB2C", title="Test", status=ProjectStatus.ACTIVE)
        fm = project.frontmatter()
        assert fm["id"] == "AB2C"
        assert fm["type"] == "project"
        assert fm["status"] == "active"
        assert "created" in fm

    def test_frontmatter_optional_fields(self) -> None:
        """frontmatter should include optional fields when set."""
        project = Project(
            id="AB2C",
            title="Test",
            team="[[Teams/Engineering]]",
            target_date=date(2024, 12, 31),
        )
        fm = project.frontmatter()
        assert fm["team"] == "[[Teams/Engineering]]"
        assert fm["targetDate"] == date(2024, 12, 31)


class TestProjectService:
    """Tests for ProjectService."""

    def test_create_project(self, vault_service: VaultService) -> None:
        """create should create a project file."""
        project_service = ProjectService(vault_service)
        project = project_service.create("Q4 Migration")

        assert project.title == "Q4 Migration"
        assert project.status == ProjectStatus.ACTIVE
        assert len(project.id) == 4

    def test_create_project_with_status(self, vault_service: VaultService) -> None:
        """create should set status."""
        project_service = ProjectService(vault_service)
        project = project_service.create("Test", status=ProjectStatus.ON_HOLD)

        assert project.status == ProjectStatus.ON_HOLD

    def test_get_project_by_id(self, vault_service: VaultService) -> None:
        """get should retrieve project by ID."""
        project_service = ProjectService(vault_service)
        created = project_service.create("Q4 Migration")

        project = project_service.get(created.id)

        assert project.id == created.id
        assert project.title == "Q4 Migration"

    def test_get_project_case_insensitive(self, vault_service: VaultService) -> None:
        """get should be case-insensitive for IDs."""
        project_service = ProjectService(vault_service)
        created = project_service.create("Q4 Migration")

        project = project_service.get(created.id.lower())
        assert project.id == created.id

    def test_get_project_not_found(self, vault_service: VaultService) -> None:
        """get should raise ProjectNotFoundError."""
        project_service = ProjectService(vault_service)
        with pytest.raises(ProjectNotFoundError):
            project_service.get("ZZZZ")

    def test_find_by_id(self, vault_service: VaultService) -> None:
        """find should find project by ID."""
        project_service = ProjectService(vault_service)
        created = project_service.create("Q4 Migration")

        project = project_service.find(created.id)
        assert project.id == created.id

    def test_find_by_name(self, vault_service: VaultService) -> None:
        """find should find project by name substring."""
        project_service = ProjectService(vault_service)
        created = project_service.create("Q4 Migration")

        project = project_service.find("Migration")
        assert project.id == created.id

    def test_find_by_name_case_insensitive(self, vault_service: VaultService) -> None:
        """find should be case-insensitive for names."""
        project_service = ProjectService(vault_service)
        created = project_service.create("Q4 Migration")

        project = project_service.find("migration")
        assert project.id == created.id

    def test_find_not_found(self, vault_service: VaultService) -> None:
        """find should raise ProjectNotFoundError with suggestions."""
        project_service = ProjectService(vault_service)
        project_service.create("Q4 Migration")

        with pytest.raises(ProjectNotFoundError):
            project_service.find("NonExistent")

    def test_find_ambiguous(self, vault_service: VaultService) -> None:
        """find should raise AmbiguousMatchError for multiple matches."""
        project_service = ProjectService(vault_service)
        project_service.create("Q4 Migration A")
        project_service.create("Q4 Migration B")

        with pytest.raises(AmbiguousMatchError):
            project_service.find("Q4 Migration")

    def test_exists(self, vault_service: VaultService) -> None:
        """exists should return True for existing project."""
        project_service = ProjectService(vault_service)
        project_service.create("Q4 Migration")

        assert project_service.exists("Q4-Migration")
        assert not project_service.exists("Q5 Migration")

    def test_list_projects(self, vault_service: VaultService) -> None:
        """list_projects should return all projects."""
        project_service = ProjectService(vault_service)
        project_service.create("Project A")
        project_service.create("Project B")

        projects = project_service.list_projects()
        assert len(projects) == 2
        assert "Project-A" in projects
        assert "Project-B" in projects

    def test_find_similar(self, vault_service: VaultService) -> None:
        """find_similar should return similar names."""
        project_service = ProjectService(vault_service)
        project_service.create("Q4 Migration")
        project_service.create("Q4 Release")

        similar = project_service.find_similar("Q4 Migrat")
        assert len(similar) > 0
        assert "Q4-Migration" in similar
