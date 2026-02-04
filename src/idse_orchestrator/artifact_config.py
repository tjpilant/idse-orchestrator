from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .design_store import DesignStore, DesignStoreFilesystem


class ArtifactConfig:
    """Loads and manages Artifact Core backend configuration."""

    DEFAULT_PATH = Path.home() / ".idseconfig.json"

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_PATH
        self.config = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with self.config_path.open("r") as f:
                config = json.load(f)
        else:
            config = {}

        env_backend = os.getenv("IDSE_ARTIFACT_BACKEND")
        if env_backend:
            config["artifact_backend"] = env_backend

        return config

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w") as f:
            json.dump(self.config, f, indent=2)

    def get_backend(self) -> str:
        return (
            self.config.get("artifact_backend")
            or self.config.get("backend")
            or "filesystem"
        )

    def get_design_store(self, idse_root: Optional[Path] = None) -> DesignStore:
        backend = self.get_backend()
        if backend == "filesystem":
            base_path = self.config.get("base_path")
            if base_path:
                return DesignStoreFilesystem(Path(base_path))
            if not idse_root:
                raise ValueError("Filesystem backend requires idse_root or base_path.")
            return DesignStoreFilesystem(idse_root)

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
