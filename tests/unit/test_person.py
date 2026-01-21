"""Unit tests for Person model and PersonService."""

import pytest

from aio.exceptions import AmbiguousMatchError, PersonNotFoundError
from aio.models.person import Person
from aio.services.person import PersonService
from aio.services.vault import VaultService


class TestPersonModel:
    """Tests for Person Pydantic model."""

    def test_default_values(self) -> None:
        """Person should have sensible defaults."""
        person = Person(id="AB2C", name="John Doe")
        assert person.type == "person"
        assert person.body == ""
        assert person.team is None
        assert person.role is None

    def test_generate_filename(self) -> None:
        """generate_filename should create valid filename."""
        person = Person(id="AB2C", name="John Doe")
        filename = person.generate_filename()
        assert filename == "John-Doe.md"

    def test_frontmatter_basic(self) -> None:
        """frontmatter should include required fields."""
        person = Person(id="AB2C", name="John Doe")
        fm = person.frontmatter()
        assert fm["id"] == "AB2C"
        assert fm["type"] == "person"

    def test_frontmatter_optional_fields(self) -> None:
        """frontmatter should include optional fields when set."""
        person = Person(
            id="AB2C",
            name="John Doe",
            team="[[Teams/Engineering]]",
            role="Senior Engineer",
            email="john@example.com",
        )
        fm = person.frontmatter()
        assert fm["team"] == "[[Teams/Engineering]]"
        assert fm["role"] == "Senior Engineer"
        assert fm["email"] == "john@example.com"


class TestPersonService:
    """Tests for PersonService."""

    def test_create_person(self, vault_service: VaultService) -> None:
        """create should create a person file."""
        person_service = PersonService(vault_service)
        person = person_service.create("John Doe")

        assert person.name == "John Doe"
        assert len(person.id) == 4

    def test_create_person_with_details(self, vault_service: VaultService) -> None:
        """create should set optional fields."""
        person_service = PersonService(vault_service)
        person = person_service.create(
            "Jane Smith",
            team="[[Teams/Design]]",
            role="Designer",
            email="jane@example.com",
        )

        assert person.team == "[[Teams/Design]]"
        assert person.role == "Designer"
        assert person.email == "jane@example.com"

    def test_get_person_by_id(self, vault_service: VaultService) -> None:
        """get should retrieve person by ID."""
        person_service = PersonService(vault_service)
        created = person_service.create("John Doe")

        person = person_service.get(created.id)

        assert person.id == created.id
        assert person.name == "John Doe"

    def test_get_person_case_insensitive(self, vault_service: VaultService) -> None:
        """get should be case-insensitive for IDs."""
        person_service = PersonService(vault_service)
        created = person_service.create("John Doe")

        person = person_service.get(created.id.lower())
        assert person.id == created.id

    def test_get_person_not_found(self, vault_service: VaultService) -> None:
        """get should raise PersonNotFoundError."""
        person_service = PersonService(vault_service)
        with pytest.raises(PersonNotFoundError):
            person_service.get("ZZZZ")

    def test_find_by_id(self, vault_service: VaultService) -> None:
        """find should find person by ID."""
        person_service = PersonService(vault_service)
        created = person_service.create("John Doe")

        person = person_service.find(created.id)
        assert person.id == created.id

    def test_find_by_name(self, vault_service: VaultService) -> None:
        """find should find person by name substring."""
        person_service = PersonService(vault_service)
        created = person_service.create("John Doe")

        person = person_service.find("John")
        assert person.id == created.id

    def test_find_by_name_case_insensitive(self, vault_service: VaultService) -> None:
        """find should be case-insensitive for names."""
        person_service = PersonService(vault_service)
        created = person_service.create("John Doe")

        person = person_service.find("john")
        assert person.id == created.id

    def test_find_not_found(self, vault_service: VaultService) -> None:
        """find should raise PersonNotFoundError with suggestions."""
        person_service = PersonService(vault_service)
        person_service.create("John Doe")

        with pytest.raises(PersonNotFoundError):
            person_service.find("NonExistent")

    def test_find_ambiguous(self, vault_service: VaultService) -> None:
        """find should raise AmbiguousMatchError for multiple matches."""
        person_service = PersonService(vault_service)
        person_service.create("John Doe")
        person_service.create("John Smith")

        with pytest.raises(AmbiguousMatchError):
            person_service.find("John")

    def test_exists(self, vault_service: VaultService) -> None:
        """exists should return True for existing person."""
        person_service = PersonService(vault_service)
        person_service.create("John Doe")

        assert person_service.exists("John-Doe")
        assert not person_service.exists("Jane Smith")

    def test_list_people(self, vault_service: VaultService) -> None:
        """list_people should return all people."""
        person_service = PersonService(vault_service)
        person_service.create("Alice")
        person_service.create("Bob")

        people = person_service.list_people()
        assert len(people) == 2
        assert "Alice" in people
        assert "Bob" in people

    def test_find_similar(self, vault_service: VaultService) -> None:
        """find_similar should return similar names."""
        person_service = PersonService(vault_service)
        person_service.create("John Doe")
        person_service.create("Jane Doe")

        similar = person_service.find_similar("Jon")
        assert len(similar) > 0
        assert "John-Doe" in similar
