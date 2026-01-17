"""Vault discovery and file operations.

The vault is an Obsidian vault with the AIO directory structure initialized.
"""

import os
from pathlib import Path
from typing import Any

import yaml

from aio.exceptions import VaultNotFoundError, VaultNotInitializedError

# Default vault structure
AIO_FOLDERS = [
    "AIO/Dashboard",
    "AIO/Tasks/Inbox",
    "AIO/Tasks/Next",
    "AIO/Tasks/Waiting",
    "AIO/Tasks/Scheduled",
    "AIO/Tasks/Someday",
    "AIO/Tasks/Completed",
    "AIO/Projects",
    "AIO/Areas",
    "AIO/People",
    "AIO/Context-Packs/Domains",
    "AIO/Context-Packs/Systems",
    "AIO/Context-Packs/Operating",
    "AIO/ADRs",
    "AIO/Archive/Tasks/Inbox",
    "AIO/Archive/Tasks/Next",
    "AIO/Archive/Tasks/Waiting",
    "AIO/Archive/Tasks/Scheduled",
    "AIO/Archive/Tasks/Someday",
    "AIO/Archive/Projects",
    "AIO/Archive/Areas",
    "AIO/Archive/People",
]


class VaultService:
    """Service for vault discovery and file operations."""

    def __init__(self, vault_path: Path | None = None) -> None:
        """Initialize the vault service.

        Args:
            vault_path: Optional explicit path to the vault. If not provided,
                       will attempt to discover the vault.
        """
        self._vault_path = vault_path

    @property
    def vault_path(self) -> Path:
        """Get the vault path, discovering it if necessary.

        Returns:
            Path to the Obsidian vault root.

        Raises:
            VaultNotFoundError: If the vault cannot be found.
        """
        if self._vault_path is None:
            self._vault_path = self._discover_vault()
        return self._vault_path

    @property
    def aio_path(self) -> Path:
        """Get the AIO directory path."""
        return self.vault_path / "AIO"

    @property
    def config_path(self) -> Path:
        """Get the .aio config directory path."""
        return self.vault_path / ".aio"

    def _discover_vault(self) -> Path:
        """Discover the vault path.

        Search order:
        1. AIO_VAULT_PATH environment variable
        2. .aio/config.yaml in current directory
        3. Walk up to find .obsidian folder
        4. ~/.aio/config.yaml global config

        Returns:
            Path to the vault.

        Raises:
            VaultNotFoundError: If no vault can be found.
        """
        # 1. Environment variable
        env_path = os.environ.get("AIO_VAULT_PATH")
        if env_path:
            path = Path(env_path).expanduser()
            if self._is_vault(path):
                return path
            raise VaultNotFoundError(f"AIO_VAULT_PATH is set but not a valid vault: {path}")

        # 2. Local .aio/config.yaml
        local_config = Path.cwd() / ".aio" / "config.yaml"
        if local_config.exists():
            vault_path = self._read_config_vault_path(local_config)
            if vault_path and self._is_vault(vault_path):
                return vault_path

        # 3. Walk up to find .obsidian
        path = Path.cwd()
        while path != path.parent:
            if (path / ".obsidian").is_dir():
                return path
            path = path.parent

        # 4. Global config
        global_config = Path.home() / ".aio" / "config.yaml"
        if global_config.exists():
            vault_path = self._read_config_vault_path(global_config)
            if vault_path and self._is_vault(vault_path):
                return vault_path

        raise VaultNotFoundError(
            "Could not find vault. Set AIO_VAULT_PATH or run 'aio init <vault-path>'"
        )

    def _is_vault(self, path: Path) -> bool:
        """Check if a path is an Obsidian vault."""
        return path.is_dir() and (path / ".obsidian").is_dir()

    def _read_config_vault_path(self, config_path: Path) -> Path | None:
        """Read vault path from a config file."""
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "vault" in config and "path" in config["vault"]:
                    return Path(config["vault"]["path"]).expanduser()
        except Exception:
            pass
        return None

    def is_initialized(self) -> bool:
        """Check if the vault has been initialized with AIO structure.

        Returns:
            True if the AIO folder exists.
        """
        return self.aio_path.is_dir()

    def initialize(self, vault_path: Path | None = None) -> Path:
        """Initialize the AIO directory structure in a vault.

        Args:
            vault_path: Path to the Obsidian vault. If None, uses discovered vault.

        Returns:
            Path to the vault.

        Raises:
            VaultNotFoundError: If the path is not a valid Obsidian vault.
        """
        if vault_path:
            vault_path = vault_path.expanduser().resolve()
            if not self._is_vault(vault_path):
                raise VaultNotFoundError(f"Not a valid Obsidian vault: {vault_path}")
            self._vault_path = vault_path
        else:
            vault_path = self.vault_path

        # Create AIO folder structure
        for folder in AIO_FOLDERS:
            folder_path = vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

        # Create .aio config directory and default config in vault
        config_dir = vault_path / ".aio"
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / "config.yaml"
        if not config_file.exists():
            default_config = {
                "vault": {"path": str(vault_path)},
                "jira": {"enabled": False},
            }
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f, default_flow_style=False)

        # Also save to global config so vault can be found from anywhere
        self._save_global_config(vault_path)

        return vault_path

    def _save_global_config(self, vault_path: Path) -> None:
        """Save vault path to global config file.

        Args:
            vault_path: Path to the vault to save.
        """
        global_config_dir = Path.home() / ".aio"
        global_config_dir.mkdir(exist_ok=True)
        global_config_file = global_config_dir / "config.yaml"

        # Read existing global config or create new one
        global_config: dict[str, Any] = {}
        if global_config_file.exists():
            with open(global_config_file, encoding="utf-8") as f:
                global_config = yaml.safe_load(f) or {}

        # Update vault path
        if "vault" not in global_config:
            global_config["vault"] = {}
        global_config["vault"]["path"] = str(vault_path)

        with open(global_config_file, "w", encoding="utf-8") as f:
            yaml.dump(global_config, f, default_flow_style=False)

    def ensure_initialized(self) -> None:
        """Ensure the vault is initialized.

        Raises:
            VaultNotInitializedError: If the vault hasn't been initialized.
        """
        if not self.is_initialized():
            raise VaultNotInitializedError(
                f"Vault not initialized. Run 'aio init {self.vault_path}'"
            )

    def tasks_folder(self, status: str) -> Path:
        """Get the folder path for a task status.

        Args:
            status: Task status (inbox, next, waiting, scheduled, someday, completed).

        Returns:
            Path to the status folder.
        """
        # Capitalize first letter for folder name
        folder_name = status.capitalize()
        return self.aio_path / "Tasks" / folder_name

    def completed_folder(self, year: int, month: int) -> Path:
        """Get the folder path for completed tasks of a specific month.

        Args:
            year: Year (e.g., 2024).
            month: Month (1-12).

        Returns:
            Path to the year/month folder under Completed.
        """
        folder = self.aio_path / "Tasks" / "Completed" / str(year) / f"{month:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def projects_folder(self) -> Path:
        """Get the Projects folder path."""
        return self.aio_path / "Projects"

    def people_folder(self) -> Path:
        """Get the People folder path."""
        return self.aio_path / "People"

    def areas_folder(self) -> Path:
        """Get the Areas folder path."""
        return self.aio_path / "Areas"

    def dashboard_folder(self) -> Path:
        """Get the Dashboard folder path."""
        return self.aio_path / "Dashboard"

    def archive_folder(self, item_type: str, status: str | None = None) -> Path:
        """Get the archive folder path.

        Args:
            item_type: Type of item (Tasks, Projects, Areas, People).
            status: For tasks, the status subfolder.

        Returns:
            Path to the archive folder.
        """
        base = self.aio_path / "Archive" / item_type
        if status:
            return base / status.capitalize()
        return base

    def get_config(self) -> dict[str, Any]:
        """Read the vault configuration.

        Returns:
            Configuration dictionary.
        """
        config_file = self.config_path / "config.yaml"
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def set_config(self, config: dict[str, Any]) -> None:
        """Write the vault configuration.

        Args:
            config: Configuration dictionary to write.
        """
        config_file = self.config_path / "config.yaml"
        self.config_path.mkdir(exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)
