from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .design_store import DesignStore, DesignStoreFilesystem
from .design_store_sqlite import DesignStoreSQLite


class ArtifactConfig:
    """Loads and manages Artifact Core backend configuration."""

    DEFAULT_PATH = Path.home() / ".idseconfig.json"
    LOCAL_CONFIG_NAME = ".idseconfig.json"

    def __init__(self, config_path: Optional[Path] = None, backend_override: Optional[str] = None):
        self.config_path = config_path or self._resolve_config_path()
        self.backend_override = backend_override
        self.config = self._load()

    @classmethod
    def _resolve_config_path(cls) -> Path:
        """
        Resolve config path with per-project priority.

        Resolution order:
        1. .idse/.idseconfig.json (project-local)
        2. ~/.idseconfig.json (global fallback)
        """
        local_candidate = Path.cwd() / ".idse" / cls.LOCAL_CONFIG_NAME
        if local_candidate.exists():
            return local_candidate
        return cls.DEFAULT_PATH

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with self.config_path.open("r") as f:
                config = json.load(f)
        else:
            config = {}

        return config

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w") as f:
            json.dump(self.config, f, indent=2)

    def get_storage_backend(self) -> str:
        """Return backend for local source-of-truth storage operations."""
        if self.backend_override in {"sqlite", "filesystem"}:
            return self.backend_override

        env_storage = os.getenv("IDSE_STORAGE_BACKEND")
        if env_storage in {"sqlite", "filesystem"}:
            return env_storage

        configured_storage = self.config.get("storage_backend")
        if configured_storage in {"sqlite", "filesystem"}:
            return configured_storage

        # Legacy compatibility: artifact_backend/backed used to represent storage.
        legacy_backend = self.config.get("artifact_backend") or self.config.get("backend")
        if legacy_backend in {"sqlite", "filesystem"}:
            return legacy_backend

        # SQLite is authoritative by default.
        return "sqlite"

    def get_sync_backend(self) -> str:
        """Return backend for sync commands (push/pull/test/tools/describe)."""
        if self.backend_override in {"sqlite", "filesystem", "notion"}:
            return self.backend_override

        env_sync = os.getenv("IDSE_SYNC_BACKEND") or os.getenv("IDSE_ARTIFACT_BACKEND")
        if env_sync in {"sqlite", "filesystem", "notion"}:
            return env_sync

        configured_sync = self.config.get("sync_backend")
        if configured_sync in {"sqlite", "filesystem", "notion"}:
            return configured_sync

        # Legacy compatibility for old configs.
        legacy_backend = self.config.get("artifact_backend") or self.config.get("backend")
        if legacy_backend in {"sqlite", "filesystem", "notion"}:
            return legacy_backend

        # Safe default for sync if no explicit target has been configured.
        return "filesystem"

    def get_backend(self) -> str:
        """
        Backward-compatible alias.

        Historically this represented the single artifact backend. We now keep this
        as storage backend to preserve behavior for non-sync commands.
        """
        return self.get_storage_backend()

    def get_design_store(self, idse_root: Optional[Path] = None, purpose: str = "storage") -> DesignStore:
        if purpose not in {"storage", "sync"}:
            raise ValueError(f"Unknown design store purpose: {purpose}")
        backend = self.get_storage_backend() if purpose == "storage" else self.get_sync_backend()
        if backend == "filesystem":
            base_path = self.config.get("base_path")
            if base_path:
                return DesignStoreFilesystem(Path(base_path))
            if not idse_root:
                raise ValueError("Filesystem backend requires idse_root or base_path.")
            return DesignStoreFilesystem(idse_root)

        if backend == "sqlite":
            sqlite_config = self.config.get("sqlite", {})
            db_path_value = (
                sqlite_config.get("db_path")
                or self.config.get("sqlite_db_path")
                or self.config.get("db_path")
            )
            idse_root_value = sqlite_config.get("idse_root")

            db_path = Path(db_path_value) if db_path_value else None
            idse_root_path = Path(idse_root_value) if idse_root_value else idse_root

            if not idse_root_path and not db_path:
                raise ValueError("SQLite backend requires idse_root or db_path.")
            if not idse_root_path and db_path:
                idse_root_path = db_path.parent
            db_path_final = db_path or (Path(idse_root_path) / "idse.db")
            if not db_path_final.exists():
                legacy = (Path(idse_root_path) / "projects").exists()
                if legacy:
                    raise FileNotFoundError(
                        "Legacy project detected. Run 'idse migrate' to convert to SQLite."
                    )
                raise FileNotFoundError(
                    "Database not found. Run 'idse init' or 'idse migrate'."
                )

            return DesignStoreSQLite(db_path=db_path_final, idse_root=idse_root_path)

        if backend == "notion":
            notion_config = self.config.get("notion", {})
            database_id = (
                notion_config.get("database_id")
                or self.config.get("notion_database_id")
            )
            database_view_id = (
                notion_config.get("database_view_id")
                or self.config.get("notion_database_view_id")
            )
            database_view_url = (
                notion_config.get("database_view_url")
                or notion_config.get("view_url")
                or self.config.get("notion_database_view_url")
            )
            parent_data_source_url = (
                notion_config.get("parent_data_source_url")
                or notion_config.get("parentDataSourceUrl")
                or self.config.get("notion_parent_data_source_url")
            )
            data_source_id = (
                notion_config.get("data_source_id")
                or notion_config.get("parentDataSourceId")
                or self.config.get("notion_data_source_id")
            )
            if not database_id:
                raise ValueError("Notion backend requires notion database_id.")
            credentials_dir = (
                notion_config.get("credentials_dir")
                or self.config.get("credentials_dir")
            )
            tool_names = notion_config.get("tool_names")
            properties = notion_config.get("properties")
            mcp = notion_config.get("mcp", {})

            from .design_store_notion import NotionDesignStore

            return NotionDesignStore(
                database_id=database_id,
                database_view_id=database_view_id,
                database_view_url=database_view_url,
                parent_data_source_url=parent_data_source_url,
                data_source_id=data_source_id,
                credentials_dir=credentials_dir,
                tool_names=tool_names,
                properties=properties,
                mcp_config=mcp,
            )

        raise ValueError(f"Unknown artifact backend: {backend}")
