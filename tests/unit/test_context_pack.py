"""Unit tests for ContextPack model and ContextPackService."""

from pathlib import Path

import pytest

from aio.exceptions import ContextPackExistsError, ContextPackNotFoundError
from aio.models.context_pack import (
    CATEGORY_FOLDERS,
    ContextPack,
    ContextPackCategory,
)
from aio.services.context_pack import ContextPackService
from aio.services.vault import VaultService


class TestContextPackModel:
    """Tests for ContextPack Pydantic model."""

    def test_default_values(self) -> None:
        """ContextPack should have sensible defaults."""
        pack = ContextPack(
            id="payments",
            category=ContextPackCategory.DOMAIN,
            title="Payments Domain",
        )
        assert pack.type == "context-pack"
        assert pack.body == ""
        assert pack.tags == []
        assert pack.sources == []
        assert pack.description is None

    def test_generate_filename(self) -> None:
        """generate_filename should return id.md."""
        pack = ContextPack(
            id="auth-service",
            category=ContextPackCategory.SYSTEM,
            title="Auth Service",
        )
        filename = pack.generate_filename()
        assert filename == "auth-service.md"

    def test_folder_name_domain(self) -> None:
        """folder_name should return correct folder for domain."""
        pack = ContextPack(
            id="payments",
            category=ContextPackCategory.DOMAIN,
            title="Payments",
        )
        assert pack.folder_name == "Domains"

    def test_folder_name_system(self) -> None:
        """folder_name should return correct folder for system."""
        pack = ContextPack(
            id="auth-service",
            category=ContextPackCategory.SYSTEM,
            title="Auth Service",
        )
        assert pack.folder_name == "Systems"

    def test_folder_name_operating(self) -> None:
        """folder_name should return correct folder for operating."""
        pack = ContextPack(
            id="definition-of-done",
            category=ContextPackCategory.OPERATING,
            title="Definition of Done",
        )
        assert pack.folder_name == "Operating"

    def test_frontmatter_basic(self) -> None:
        """frontmatter should include required fields."""
        pack = ContextPack(
            id="payments",
            category=ContextPackCategory.DOMAIN,
            title="Payments Domain",
        )
        fm = pack.frontmatter()
        assert fm["id"] == "payments"
        assert fm["type"] == "context-pack"
        assert fm["category"] == "domain"
        assert fm["title"] == "Payments Domain"
        assert "created" in fm
        assert "updated" in fm

    def test_frontmatter_optional_fields(self) -> None:
        """frontmatter should include optional fields when set."""
        pack = ContextPack(
            id="payments",
            category=ContextPackCategory.DOMAIN,
            title="Payments Domain",
            description="Business context for payments",
            tags=["payments", "finance"],
            sources=["[[ADRs/payment-provider]]", "https://stripe.com/docs"],
        )
        fm = pack.frontmatter()
        assert fm["description"] == "Business context for payments"
        assert fm["tags"] == ["payments", "finance"]
        assert fm["sources"] == ["[[ADRs/payment-provider]]", "https://stripe.com/docs"]

    def test_frontmatter_excludes_empty_optional(self) -> None:
        """frontmatter should not include empty optional fields."""
        pack = ContextPack(
            id="payments",
            category=ContextPackCategory.DOMAIN,
            title="Payments",
        )
        fm = pack.frontmatter()
        assert "description" not in fm
        assert "tags" not in fm
        assert "sources" not in fm


class TestCategoryFolders:
    """Tests for category folder mapping."""

    def test_all_categories_mapped(self) -> None:
        """All categories should have folder mappings."""
        for category in ContextPackCategory:
            assert category in CATEGORY_FOLDERS

    def test_folder_names(self) -> None:
        """Folder names should be correct."""
        assert CATEGORY_FOLDERS[ContextPackCategory.DOMAIN] == "Domains"
        assert CATEGORY_FOLDERS[ContextPackCategory.SYSTEM] == "Systems"
        assert CATEGORY_FOLDERS[ContextPackCategory.OPERATING] == "Operating"


class TestContextPackService:
    """Tests for ContextPackService."""

    def test_create_pack(self, vault_service: VaultService) -> None:
        """create should create a context pack file."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.create(
            title="Payments Domain",
            category=ContextPackCategory.DOMAIN,
        )

        assert pack.title == "Payments Domain"
        assert pack.id == "payments-domain"
        assert pack.category == ContextPackCategory.DOMAIN

        # Verify file was created
        pack_path = (
            vault_service.aio_path
            / "Context-Packs"
            / "Domains"
            / "payments-domain.md"
        )
        assert pack_path.exists()

    def test_create_pack_with_content(self, vault_service: VaultService) -> None:
        """create should set initial content."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.create(
            title="Auth Service",
            category=ContextPackCategory.SYSTEM,
            content="## Architecture\n\nMicroservice-based auth.",
        )

        assert "## Architecture" in pack.body
        assert "Microservice-based auth" in pack.body

    def test_create_pack_with_description(self, vault_service: VaultService) -> None:
        """create should set description."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.create(
            title="Payments",
            category=ContextPackCategory.DOMAIN,
            description="Business context for payments",
        )

        assert pack.description == "Business context for payments"

    def test_create_pack_with_tags(self, vault_service: VaultService) -> None:
        """create should set tags."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.create(
            title="Payments",
            category=ContextPackCategory.DOMAIN,
            tags=["payments", "finance"],
        )

        assert pack.tags == ["payments", "finance"]

    def test_create_duplicate_raises_error(self, vault_service: VaultService) -> None:
        """create should raise error if pack already exists."""
        pack_service = ContextPackService(vault_service)
        pack_service.create(title="Payments", category=ContextPackCategory.DOMAIN)

        with pytest.raises(ContextPackExistsError):
            pack_service.create(title="Payments", category=ContextPackCategory.DOMAIN)

    def test_get_pack_by_id(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """get should retrieve pack by ID."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.get("test-pack")

        assert pack.id == "test-pack"
        assert pack.title == "Test Pack"

    def test_get_pack_not_found(self, vault_service: VaultService) -> None:
        """get should raise ContextPackNotFoundError."""
        pack_service = ContextPackService(vault_service)
        with pytest.raises(ContextPackNotFoundError):
            pack_service.get("nonexistent")

    def test_find_by_id(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """find should find pack by ID."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.find("test-pack")
        assert pack.id == "test-pack"

    def test_find_by_title(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """find should find pack by title substring."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.find("Test")
        assert pack.id == "test-pack"

    def test_list_packs_empty(self, vault_service: VaultService) -> None:
        """list_packs should return empty list when no packs."""
        pack_service = ContextPackService(vault_service)
        packs = pack_service.list_packs()
        assert packs == []

    def test_list_packs_all(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """list_packs should return all packs."""
        pack_service = ContextPackService(vault_service)
        packs = pack_service.list_packs()
        assert len(packs) == 1

    def test_list_packs_by_category(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """list_packs should filter by category."""
        pack_service = ContextPackService(vault_service)
        domain_packs = pack_service.list_packs(category=ContextPackCategory.DOMAIN)
        system_packs = pack_service.list_packs(category=ContextPackCategory.SYSTEM)

        assert len(domain_packs) == 1
        assert len(system_packs) == 0

    def test_append_content(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """append should add content to pack."""
        pack_service = ContextPackService(vault_service)
        original = pack_service.get("test-pack")
        original_len = len(original.body)

        pack = pack_service.append("test-pack", "## New Section\n\nNew content here.")

        assert len(pack.body) > original_len
        assert "## New Section" in pack.body
        assert "New content here" in pack.body

    def test_append_to_section(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """append should add content under specific section."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.append(
            "test-pack",
            "- New item",
            section="Notes",
        )

        assert "- New item" in pack.body

    def test_append_file(self, vault_service: VaultService) -> None:
        """append_file should copy file content into pack."""
        pack_service = ContextPackService(vault_service)

        # Create pack and source file
        pack_service.create(title="Test", category=ContextPackCategory.DOMAIN)

        source_file = vault_service.aio_path / "ADRs" / "test-adr.md"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("# Test ADR\n\nThis is a test ADR.", encoding="utf-8")

        # Append file
        updated = pack_service.append_file("test", "ADRs/test-adr.md")

        assert "# Test ADR" in updated.body
        assert "> From:" in updated.body

    def test_add_source(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """add_source should add source reference."""
        pack_service = ContextPackService(vault_service)
        pack = pack_service.add_source("test-pack", "[[ADRs/new-adr]]")

        assert "[[ADRs/new-adr]]" in pack.sources

    def test_add_source_no_duplicate(
        self, vault_service: VaultService, sample_context_pack: Path
    ) -> None:
        """add_source should not add duplicate sources."""
        pack_service = ContextPackService(vault_service)
        pack_service.add_source("test-pack", "[[ADRs/new-adr]]")
        pack = pack_service.add_source("test-pack", "[[ADRs/new-adr]]")

        # Count occurrences
        count = pack.sources.count("[[ADRs/new-adr]]")
        assert count == 1


@pytest.fixture
def sample_context_pack(initialized_vault: Path) -> Path:
    """Create a sample context pack file in the vault.

    Returns:
        Path to the created pack file.
    """
    pack_content = """---
id: test-pack
type: context-pack
category: domain
title: Test Pack
description: A test context pack
tags:
  - test
sources: []
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Test Pack

## Overview
This is a test context pack.

## Notes
Some notes here.
"""
    pack_path = initialized_vault / "AIO" / "Context-Packs" / "Domains" / "test-pack.md"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack_content, encoding="utf-8")
    return pack_path
