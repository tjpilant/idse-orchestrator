from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import StdioServerParameters

from .artifact_database import hash_content
from .design_store_mcp import MCPDesignStoreAdapter


class NotionDesignStore(MCPDesignStoreAdapter):
    """Notion-backed DesignStore using the Notion MCP server."""

    DEFAULT_TOOL_NAMES = {
        "query_database": "notion-query-database-view",
        "fetch_page": "notion-fetch",
        "create_page": "notion-create-pages",
        "update_page": "notion-update-page",
        "append_children": "append_block_children",
        "update_data_source": "notion-update-data-source",
    }

    DEFAULT_PROPERTIES = {
        "title": {"name": "Title", "type": "title"},
        "idse_id": {"name": "IDSE_ID", "type": "rich_text"},
        "session": {"name": "Session", "type": "rich_text"},
        "stage": {"name": "Stage", "type": "select"},
        "status": {"name": "Status", "type": "status"},
        "upstream_artifact": {"name": "Upstream Artifact", "type": "relation"},
        "layer": {"name": "Layer", "type": "select"},
        "run_scope": {"name": "Run Scope", "type": "select"},
        "version": {"name": "Version", "type": "rich_text"},
        "feature_capability": {"name": "Feature / Capability", "type": "rich_text"},
        "content": {"name": "body", "type": "page_body"},
    }

    STATE_SESSION_ID = "__project__"
    STATE_STAGE = "session_state"

    def __init__(
        self,
        database_id: str,
        database_view_id: Optional[str] = None,
        database_view_url: Optional[str] = None,
        parent_data_source_url: Optional[str] = None,
        data_source_id: Optional[str] = None,
        credentials_dir: Optional[str] = None,
        tool_names: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Dict[str, str]]] = None,
        mcp_config: Optional[Dict[str, Any]] = None,
    ):
        self.database_id = database_id
        self.database_view_id = _normalize_uuid(database_view_id)
        self.database_view_url = _normalize_view_url(database_view_url)
        self.parent_data_source_url = parent_data_source_url
        self.data_source_id = data_source_id
        self.debug = False
        self.use_idse_id = True
        self._idse_schema_checked = False
        self.force_create = False
        self.last_write_skipped = False
        self.tool_names = {**self.DEFAULT_TOOL_NAMES, **(tool_names or {})}
        self.properties = self._normalize_properties(
            {**self.DEFAULT_PROPERTIES, **(properties or {})}
        )
        self.schema_map = NotionSchemaMap(self.properties)

        mcp_config = mcp_config or {}
        command = mcp_config.get("command", "npx")
        args = mcp_config.get(
            "args", ["-y", "mcp-remote", "https://mcp.notion.com/mcp"]
        )
        credentials_path = Path(
            credentials_dir or Path.cwd() / "mnt" / "mcp_credentials"
        )
        env = {"MCP_REMOTE_CONFIG_DIR": str(credentials_path)}
        env.update(mcp_config.get("env", {}))

        server_params = StdioServerParameters(command=command, args=args, env=env)
        super().__init__(server_params)

    def set_debug(self, enabled: bool) -> None:
        self.debug = enabled

    def set_force_create(self, enabled: bool) -> None:
        self.force_create = enabled

    def load_artifact(self, project: str, session_id: str, stage: str) -> str:
        page_id = self._resolve_page_id(project, session_id, stage)
        if not page_id:
            raise FileNotFoundError(
                f"Artifact not found: {project}/{session_id}/{stage}"
            )
        fetch = self._fetch_page(page_id)
        if self._content_type() == "page_body":
            content = _extract_page_body(fetch)
        else:
            content = self._extract_property_text(fetch, "content")

        # Keep SQLite source-of-truth aligned after pull.
        artifact_id = self._upsert_pulled_artifact(
            project, session_id, stage, content, page_id
        )
        self._sync_dependencies_from_pull(artifact_id, fetch)
        return content

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> None:
        self.last_write_skipped = False
        local_hash = hash_content(content)
        if not self.force_create and self._should_skip_push(project, session_id, stage, local_hash):
            self.last_write_skipped = True
            return

        page_id = None if self.force_create else self._resolve_page_id(project, session_id, stage)
        session_context = self._load_session_context(project, session_id)
        create_payload = self._build_create_properties(
            project=project,
            session_id=session_id,
            stage=stage,
            content=content,
            session_context=session_context,
        )
        update_payload = self._build_update_properties(
            project=project,
            session_id=session_id,
            stage=stage,
            content=content,
            session_context=session_context,
        )

        if page_id:
            # Existing pages are content-authoritative in Notion; only replace content.
            if self.tool_names.get("update_page"):
                if update_payload["content_payload"] is not None:
                    payload_content = {
                        "data": {
                            "page_id": page_id,
                            "command": "replace_content",
                            "new_str": update_payload["content_payload"],
                        }
                    }
                    if self.debug:
                        _debug_payload(self.tool_names["update_page"], payload_content)
                    result = self._call_tool(self.tool_names["update_page"], payload_content)
                    if self.debug:
                        _debug_result(self.tool_names["update_page"], result)
            self._save_push_metadata(
                project, session_id, stage, local_hash=local_hash, remote_id=page_id
            )
            self._sync_dependencies_to_remote(project, session_id, stage, page_id)
            return

        create_tool = self.tool_names["create_page"]
        if create_tool == "create_database_item":
            payload = {
                "database_id": self.database_id,
                "properties": create_payload["properties"],
            }
            if self.debug:
                _debug_payload(create_tool, payload)
            try:
                new_page = self._call_tool(create_tool, payload)
            except Exception:
                payload["properties"] = _drop_idse_id(payload["properties"], self.properties)
                new_page = self._call_tool(create_tool, payload)
            if self.debug:
                _debug_result(create_tool, new_page)
            if create_payload["content_payload"] is not None and self.tool_names.get("append_children"):
                page_id = _extract_page_id(new_page)
                if page_id:
                    self._cache_remote_id(project, session_id, stage, page_id)
                    append_payload = {
                        "block_id": page_id,
                        "children": _render_page_body(create_payload["content_payload"]),
                    }
                    if self.debug:
                        _debug_payload(self.tool_names["append_children"], append_payload)
                    result = self._call_tool(self.tool_names["append_children"], append_payload)
                    if self.debug:
                        _debug_result(self.tool_names["append_children"], result)
            self._save_push_metadata(
                project,
                session_id,
                stage,
                local_hash=local_hash,
                remote_id=_extract_page_id(new_page),
            )
            self._sync_dependencies_to_remote(
                project, session_id, stage, _extract_page_id(new_page)
            )
            return

        if create_tool == "notion-create-pages":
            payload = {
                "pages": [
                    {
                        "properties": _flatten_property_values(create_payload["properties"]),
                        "content": create_payload["content_payload"] or "",
                    }
                ]
            }
            if self.data_source_id:
                payload["parent"] = {"type": "data_source_id", "data_source_id": self.data_source_id}
            elif self.database_id:
                payload["parent"] = {"type": "database_id", "database_id": self.database_id}

            if self.debug:
                _debug_payload(create_tool, payload)
            try:
                result = self._call_tool(create_tool, payload)
            except Exception:
                payload["pages"][0]["properties"] = _drop_idse_id(
                    payload["pages"][0]["properties"], self.properties
                )
                result = self._call_tool(create_tool, payload)
            if self.debug:
                _debug_result(create_tool, result)
            created_page_id = _extract_page_id(result)
            if created_page_id:
                self._cache_remote_id(project, session_id, stage, created_page_id)
            self._save_push_metadata(
                project, session_id, stage, local_hash=local_hash, remote_id=created_page_id
            )
            self._sync_dependencies_to_remote(
                project, session_id, stage, created_page_id
            )
            return

        payload = {
            "parent": {"type": "database_id", "database_id": self.database_id},
            "properties": create_payload["properties"],
        }
        if create_payload["content_payload"] is not None:
            payload["content"] = create_payload["content_payload"]
        if self.debug:
            _debug_payload(create_tool, payload)
        result = self._call_tool(create_tool, payload)
        if self.debug:
            _debug_result(create_tool, result)
        created_page_id = _extract_page_id(result)
        if created_page_id:
            self._cache_remote_id(project, session_id, stage, created_page_id)
        self._save_push_metadata(
            project, session_id, stage, local_hash=local_hash, remote_id=created_page_id
        )
        self._sync_dependencies_to_remote(project, session_id, stage, created_page_id)

    def list_sessions(self, project: str) -> List[str]:
        _ = project  # Project is encoded in title, not a discrete Notion property.
        results = self._query_database(filters=[])
        sessions = set()
        for page in results:
            session = self._extract_property_text(page, "session")
            stage = self._extract_property_text(page, "stage")
            if session and stage != self.STATE_STAGE:
                sessions.add(session)
        return sorted(sessions)

    def load_state(self, project: str) -> Dict:
        try:
            raw = self.load_artifact(project, self.STATE_SESSION_ID, self.STATE_STAGE)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"State not found for project: {project}"
            ) from exc
        return json.loads(raw)

    def save_state(self, project: str, state: Dict) -> None:
        content = json.dumps(state, indent=2)
        self.save_artifact(project, self.STATE_SESSION_ID, self.STATE_STAGE, content)

    def validate_backend(self) -> Dict[str, Any]:
        checks: List[str] = []
        warnings: List[str] = []

        async def _validate(session):
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools} if tools else set()
            checks.append("Connected to Notion MCP server")

            required = [
                self.tool_names["query_database"],
                self.tool_names["create_page"],
                self.tool_names["update_page"],
            ]
            if self._content_type() == "page_body":
                required.append(self.tool_names["fetch_page"])
            missing = [name for name in required if name not in tool_names]
            if missing:
                available = ", ".join(sorted(tool_names)) or "none"
                raise RuntimeError(
                    f"Missing required MCP tools: {', '.join(missing)}. "
                    f"Configured: {self.tool_names}. Available: {available}"
                )
            checks.append("Required MCP tools available")

            query_payload = _resolve_query_payload(
                tools,
                self.tool_names["query_database"],
                self.database_id,
                self.database_view_id,
                self.database_view_url,
            )
            await self._call_tool_in_session(
                session, self.tool_names["query_database"], query_payload
            )
            checks.append("Notion database is reachable")

            for key in ("session", "stage", "content"):
                if key == "content" and self._content_type() == "page_body":
                    checks.append("Content stored in page body (no property check)")
                    continue
                if key == "title" and "title" not in self.properties:
                    continue
                payload = {
                    **query_payload,
                    "filter": self._property_filter(key, "__idse_validate__"),
                }
                await self._call_tool_in_session(
                    session,
                    self.tool_names["query_database"],
                    payload,
                )
                checks.append(f"Property '{self.properties[key]['name']}' exists")

        self._with_session(_validate)

        return {"ok": True, "checks": checks, "warnings": warnings}

    def describe_backend(self) -> Dict[str, Any]:
        """Return raw response from the query tool to inspect data source metadata."""
        payload = {}
        if self.database_view_url:
            payload["view_url"] = self.database_view_url
        elif self.database_view_id:
            v_id = self.database_view_id
            if len(v_id) == 32 and "-" not in v_id:
                v_id = f"{v_id[:8]}-{v_id[8:12]}-{v_id[12:16]}-{v_id[16:20]}-{v_id[20:]}"
            payload["view_url"] = f"view://{v_id}"
        else:
            raise RuntimeError("No database_view_url or database_view_id configured.")
        return self._call_tool(self.tool_names["query_database"], payload)

    def _query_database(self, filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {}
        query_tool = self.tool_names["query_database"]
        run_client_filter = False

        if query_tool == "notion-query-database-view":
            run_client_filter = True
            if self.database_view_url:
                payload["view_url"] = self.database_view_url
            elif self.database_view_id:
                # Use view:// scheme with dashed UUID
                v_id = self.database_view_id
                if len(v_id) == 32 and "-" not in v_id:
                    v_id = f"{v_id[:8]}-{v_id[8:12]}-{v_id[12:16]}-{v_id[16:20]}-{v_id[20:]}"
                
                payload["view_url"] = f"view://{v_id}"
            else:
                raise RuntimeError("Query tool requires view_url but none was configured.")
        else:
            if self.database_view_url:
                payload["view_url"] = self.database_view_url
            elif self.database_view_id:
                payload["database_view_id"] = self.database_view_id
            else:
                payload["database_id"] = self.database_id
            
            # Standard query_database supports filter
            if filters:
                payload["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        result = self._call_tool(self.tool_names["query_database"], payload)
        items = _extract_results(result)
        
        if run_client_filter and filters:
            return self._filter_items_locally(items, filters)
        return items

    def _filter_items_locally(
        self, items: List[Dict[str, Any]], filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        filtered = []
        for item in items:
            match = True
            for f in filters:
                prop_name = f.get("property")
                if not prop_name:
                    continue
                
                # Determine filter type and expected value
                filter_type = next((k for k in f.keys() if k != "property"), None)
                if not filter_type:
                    continue
                condition = f[filter_type]
                expected = condition.get("equals")
                if expected is None:
                    continue  # Skip unsupported filter types for now

                # Extract matching value from item
                item_props = item.get("properties", {})
                prop_val_obj = item_props.get(prop_name)
                text_val = ""
                
                if prop_val_obj:
                    # 'select' property
                    if filter_type == "select":
                        text_val = (prop_val_obj.get("select") or {}).get("name", "")
                    elif filter_type == "status":
                        text_val = (prop_val_obj.get("status") or {}).get("name", "")
                    # 'title' or 'rich_text' property
                    elif filter_type in ("title", "rich_text"):
                        # Value might be stored under the type name
                        type_key = prop_val_obj.get("type", filter_type)
                        content_list = prop_val_obj.get(type_key, [])
                        text_val = "".join(
                            [t.get("plain_text", "") for t in content_list]
                        )
                
                if text_val != expected:
                    match = False
                    break
            if match:
                filtered.append(item)
        return filtered

    def _property_filter(self, key: str, value: str) -> Dict[str, Any]:
        prop = self.properties[key]
        name = prop["name"]
        ptype = prop["type"]
        if ptype == "title":
            return {"property": name, "title": {"equals": value}}
        if ptype == "rich_text":
            return {"property": name, "rich_text": {"equals": value}}
        if ptype == "select":
            return {"property": name, "select": {"equals": value}}
        if ptype == "status":
            return {"property": name, "status": {"equals": value}}
        raise ValueError(f"Unsupported Notion property type: {ptype}")

    def _property_value(self, key: str, value: str) -> Dict[str, Any]:
        prop = self.properties[key]
        ptype = prop["type"]
        if ptype == "title":
            return {"title": [{"text": {"content": value}}]}
        if ptype == "rich_text":
            return {"rich_text": [{"text": {"content": value}}]}
        if ptype == "select":
            return {"select": {"name": value}}
        if ptype == "status":
            return {"status": {"name": value}}
        raise ValueError(f"Unsupported Notion property type: {ptype}")

    def _extract_property_text(self, page: Dict[str, Any], key: str) -> str:
        prop = self.properties[key]
        name = prop["name"]
        ptype = prop["type"]
        value = page.get("properties", {}).get(name)
        if not value:
            return ""
        if ptype == "select":
            return (value.get("select") or {}).get("name", "")
        if ptype == "status":
            return (value.get("status") or {}).get("name", "")
        if ptype in ("title", "rich_text"):
            items = value.get(ptype, [])
            return "".join([item.get("plain_text", "") for item in items])
        return ""

    def _extract_property_relation_ids(self, page: Dict[str, Any], key: str) -> List[str]:
        prop = self.properties.get(key)
        if not prop or prop.get("type") != "relation":
            return []
        value = page.get("properties", {}).get(prop["name"])
        if not value:
            return []
        return [
            item.get("id")
            for item in value.get("relation", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def _content_type(self) -> str:
        return self.properties["content"]["type"]

    def _fetch_page(self, page_id: str) -> Dict[str, Any]:
        tool = self.tool_names["fetch_page"]
        payload = {"id": page_id} if tool == "notion-fetch" else {"page_id": page_id}
        try:
            return self._call_tool(tool, payload)
        except Exception:
            # Fallback across MCP variants.
            alt_payload = {"page_id": page_id} if "id" in payload else {"id": page_id}
            return self._call_tool(tool, alt_payload)

    @staticmethod
    def _normalize_properties(properties: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        normalized: Dict[str, Dict[str, str]] = {}
        for key, prop in properties.items():
            ptype = prop.get("type", "").lower()
            if ptype == "text":
                ptype = "rich_text"
            normalized[key] = {**prop, "type": ptype}
        return normalized

    def _relation_property_name(self) -> Optional[str]:
        relation = self.properties.get("upstream_artifact")
        if not relation or relation.get("type") != "relation":
            return None
        return relation.get("name")

    def _build_notion_properties(
        self,
        *,
        project: str,
        session_id: str,
        stage: str,
        content: str,
        session_context: Optional[Dict[str, Any]] = None,
        write_mode: str = "create",
    ) -> Dict[str, Any]:
        mapped = self.schema_map.build_projection(
            project=project,
            session_id=session_id,
            stage=stage,
            content=content,
            include_idse_id=self.use_idse_id,
            content_type=self._content_type(),
            session_status=(session_context or {}).get("status"),
            tags=(session_context or {}).get("tags"),
            version=(session_context or {}).get("version"),
            feature_capability=(session_context or {}).get("feature_capability"),
            write_mode=write_mode,
        )

        payload: Dict[str, Any] = {"properties": {}, "content_payload": mapped["content_payload"]}
        for key, value in mapped["fields"].items():
            if key not in self.properties or value is None:
                continue
            payload["properties"][self.properties[key]["name"]] = self._property_value(key, value)
        return payload

    def _build_create_properties(
        self,
        *,
        project: str,
        session_id: str,
        stage: str,
        content: str,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._build_notion_properties(
            project=project,
            session_id=session_id,
            stage=stage,
            content=content,
            session_context=session_context,
            write_mode="create",
        )

    def _build_update_properties(
        self,
        *,
        project: str,
        session_id: str,
        stage: str,
        content: str,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._build_notion_properties(
            project=project,
            session_id=session_id,
            stage=stage,
            content=content,
            session_context=session_context,
            write_mode="update",
        )

    def _load_session_context(self, project: str, session_id: str) -> Dict[str, Any]:
        """Best-effort local context for computed Notion fields."""
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            session_meta = None
            for row in db.list_session_metadata(project):
                if row["session_id"] == session_id:
                    session_meta = row
                    break
            tags: List[str] = []
            if session_meta:
                with db._connect() as conn:
                    rows = conn.execute(
                        """
                        SELECT t.tag
                        FROM session_tags t
                        JOIN sessions s ON t.session_id = s.id
                        JOIN projects p ON s.project_id = p.id
                        WHERE p.name = ? AND s.session_id = ?
                        ORDER BY t.tag;
                        """,
                        (project, session_id),
                    ).fetchall()
                    tags = [row["tag"] for row in rows]
            return {
                "status": session_meta["status"] if session_meta else None,
                "tags": tags,
                "version": _derive_version(session_id),
                "feature_capability": session_meta["description"] if session_meta else None,
            }
        except Exception:
            return {}

    def _resolve_page_id(self, project: str, session_id: str, stage: str) -> Optional[str]:
        artifact_id = self._lookup_artifact_id(project, session_id, stage)
        if artifact_id is not None:
            try:
                from .artifact_database import ArtifactDatabase

                db = ArtifactDatabase(allow_create=False)
                meta = db.get_sync_metadata(artifact_id, "notion")
                remote_id = meta.get("remote_id") if meta else None
                if remote_id:
                    return remote_id
            except Exception:
                pass

        if self.use_idse_id and "idse_id" in self.properties:
            idse_results = self._query_database(
                [self._property_filter("idse_id", _make_idse_id(project, session_id, stage))]
            )
            page_id = _select_best_active_page_id(idse_results)
            if page_id:
                self._cache_remote_id(project, session_id, stage, page_id)
                return page_id

        filters = [
            self._property_filter("session", session_id),
            self._property_filter("stage", _format_stage_value(stage)),
        ]
        results = self._query_database(filters)
        page_id = _select_best_active_page_id(results)
        if page_id:
            self._cache_remote_id(project, session_id, stage, page_id)
        return page_id

    def _lookup_artifact_id(self, project: str, session_id: str, stage: str) -> Optional[int]:
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            return db.get_artifact_id(project, session_id, stage)
        except Exception:
            return None

    def _cache_remote_id(self, project: str, session_id: str, stage: str, remote_id: str) -> None:
        artifact_id = self._lookup_artifact_id(project, session_id, stage)
        if artifact_id is None:
            return
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            db.save_sync_metadata(artifact_id, "notion", remote_id=remote_id)
        except Exception:
            return

    def _should_skip_push(
        self, project: str, session_id: str, stage: str, local_hash: str
    ) -> bool:
        artifact_id = self._lookup_artifact_id(project, session_id, stage)
        if artifact_id is None:
            return False
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            meta = db.get_sync_metadata(artifact_id, "notion")
            if not meta:
                return False
            if not meta.get("remote_id"):
                return False
            return meta.get("last_push_hash") == local_hash
        except Exception:
            return False

    def _save_push_metadata(
        self,
        project: str,
        session_id: str,
        stage: str,
        *,
        local_hash: str,
        remote_id: Optional[str],
    ) -> None:
        artifact_id = self._lookup_artifact_id(project, session_id, stage)
        if artifact_id is None:
            return
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            db.save_sync_metadata(
                artifact_id,
                "notion",
                last_push_hash=local_hash,
                remote_id=remote_id,
            )
        except Exception:
            return

    def _upsert_pulled_artifact(
        self,
        project: str,
        session_id: str,
        stage: str,
        content: str,
        remote_id: Optional[str],
    ) -> Optional[int]:
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            db.save_artifact(project, session_id, stage, content)
            artifact_id = db.get_artifact_id(project, session_id, stage)
            if artifact_id is None:
                return None
            db.save_sync_metadata(
                artifact_id,
                "notion",
                last_pull_hash=hash_content(content),
                remote_id=remote_id,
            )
            return artifact_id
        except Exception:
            return None

    def _sync_dependencies_from_pull(
        self,
        artifact_id: Optional[int],
        page: Dict[str, Any],
    ) -> None:
        if artifact_id is None:
            return
        relation_ids = self._extract_property_relation_ids(page, "upstream_artifact")
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            mapped_artifact_ids = []
            for remote_id in relation_ids:
                depends_on_id = db.find_artifact_id_by_remote_id("notion", remote_id)
                if depends_on_id is not None:
                    mapped_artifact_ids.append(depends_on_id)
            db.replace_dependencies(
                artifact_id,
                mapped_artifact_ids,
                dependency_type="upstream",
            )
        except Exception:
            return

    def _sync_dependencies_to_remote(
        self,
        project: str,
        session_id: str,
        stage: str,
        page_id: Optional[str],
    ) -> None:
        relation_name = self._relation_property_name()
        if not page_id or not relation_name:
            return
        artifact_id = self._lookup_artifact_id(project, session_id, stage)
        if artifact_id is None:
            return
        try:
            from .artifact_database import ArtifactDatabase

            db = ArtifactDatabase(allow_create=False)
            relation_remote_ids: List[str] = []
            for dep in db.get_dependencies(artifact_id, direction="upstream"):
                dep_artifact_id = db.get_artifact_id(dep.project, dep.session_id, dep.stage)
                if dep_artifact_id is None:
                    continue
                dep_meta = db.get_sync_metadata(dep_artifact_id, "notion")
                remote_id = dep_meta.get("remote_id") if dep_meta else None
                if remote_id:
                    relation_remote_ids.append(remote_id)

            if not self.tool_names.get("update_page"):
                return
            payload = {
                "data": {
                    "page_id": page_id,
                    "command": "update_properties",
                    "properties": {relation_name: relation_remote_ids},
                }
            }
            self._call_tool(self.tool_names["update_page"], payload)
        except Exception:
            return


class NotionSchemaMap:
    """Maps canonical IDSE fields into a Notion property projection."""

    LAYER_TAGS = {"application", "domain", "data", "infrastructure", "platform", "ui"}
    RUN_SCOPE_TAGS = {"full", "feature", "module", "component", "task", "hotfix"}
    FIELD_MODES = {
        "title": "create_only",
        "idse_id": "always_sync",
        "session": "always_sync",
        "stage": "always_sync",
        "status": "optional",
        "layer": "optional",
        "run_scope": "optional",
        "version": "optional",
        "feature_capability": "optional",
        "content": "always_sync",
    }
    STATUS_VALUE_MAP = {
        "draft": "Draft",
        "in_progress": "In Review",
        "review": "In Review",
        "complete": "Locked",
        "archived": "Superseded",
    }

    def __init__(self, properties: Dict[str, Dict[str, str]]):
        self.properties = properties

    def build_projection(
        self,
        *,
        project: str,
        session_id: str,
        stage: str,
        content: str,
        include_idse_id: bool,
        content_type: str,
        write_mode: str = "create",
        session_status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
        feature_capability: Optional[str] = None,
    ) -> Dict[str, Any]:
        tag_list = tags or []
        fields: Dict[str, Optional[str]] = {
            "session": session_id,
            "stage": _format_stage_value(stage),
            "title": f"{session_id} – {_format_stage_value(stage)}",
            "status": self._map_status(session_status),
            "layer": self._derive_layer(tag_list),
            "run_scope": self._derive_run_scope(tag_list),
            "version": version,
            "feature_capability": feature_capability,
        }
        if include_idse_id:
            fields["idse_id"] = _make_idse_id(project, session_id, stage)
        if content_type != "page_body":
            fields["content"] = content
            content_payload = None
        else:
            content_payload = content
        selected = {
            key: value
            for key, value in fields.items()
            if self._include_field(key, write_mode)
        }
        return {"fields": selected, "content_payload": content_payload}

    def _derive_layer(self, tags: List[str]) -> Optional[str]:
        for tag in tags:
            lower = tag.lower()
            if lower in self.LAYER_TAGS:
                return tag.title()
        return None

    def _derive_run_scope(self, tags: List[str]) -> Optional[str]:
        for tag in tags:
            lower = tag.lower()
            if lower in self.RUN_SCOPE_TAGS:
                return tag.title()
        return None

    def _include_field(self, key: str, write_mode: str) -> bool:
        mode = self.FIELD_MODES.get(key, "optional")
        if mode == "always_sync":
            return True
        if mode == "create_only":
            return write_mode == "create"
        if mode == "optional":
            return True
        return True

    def _map_status(self, session_status: Optional[str]) -> Optional[str]:
        if not session_status:
            return None
        normalized = session_status.strip().lower()
        return self.STATUS_VALUE_MAP.get(normalized, session_status)


def _extract_results(result: Any) -> List[Dict[str, Any]]:
    if isinstance(result, dict):
        if "results" in result:
            return result["results"]
        if "items" in result:
            return result["items"]
    return []


def _render_page_body(content: str) -> List[Dict[str, Any]]:
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}],
            },
        }
    ]


def _extract_page_body(result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    blocks = result.get("blocks") or result.get("children") or []
    lines: List[str] = []
    for block in blocks:
        btype = block.get("type")
        if btype == "paragraph":
            texts = block.get("paragraph", {}).get("rich_text", [])
            lines.append("".join([t.get("plain_text", "") for t in texts]))
    return "\n\n".join([line for line in lines if line])


def _resolve_query_payload(
    tools: Any,
    query_tool_name: str,
    database_id: str,
    database_view_id: Optional[str],
    database_view_url: Optional[str],
) -> Dict[str, Any]:
    tool_list = getattr(tools, "tools", []) if tools else []
    match = next((tool for tool in tool_list if tool.name == query_tool_name), None)
    schema = getattr(match, "inputSchema", {}) or {}
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []

    if "view_url" in properties or "view_url" in required:
        if database_view_url:
            return {"view_url": database_view_url}
        if database_view_id:
            # Construct view:// URL with dashed UUIDs
            v_id = database_view_id
            if len(v_id) == 32 and "-" not in v_id:
                v_id = f"{v_id[:8]}-{v_id[8:12]}-{v_id[12:16]}-{v_id[16:20]}-{v_id[20:]}"
            return {"view_url": f"view://{v_id}"}
        raise RuntimeError(
            "Query tool requires view_url but none was configured."
        )
    if "database_view_id" in properties or "database_view_id" in required:
        if not database_view_id:
            raise RuntimeError(
                "Query tool requires database_view_id but none was configured."
            )
        return {"database_view_id": database_view_id}
    if "database_id" in properties or "database_id" in required:
        return {"database_id": database_id}
    if "data_source_id" in properties or "data_source_id" in required:
        return {"data_source_id": database_id}
    return {"database_id": database_id}


def _flatten_property_values(properties: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for name, value in properties.items():
        if isinstance(value, dict) and len(value) == 1:
            inner_key = next(iter(value.keys()))
            inner_val = value[inner_key]
            if inner_key in ("title", "rich_text") and isinstance(inner_val, list):
                # Handle both read (plain_text) and write (text.content) formats
                parts = []
                for item in inner_val:
                    if not isinstance(item, dict):
                        continue
                    if "plain_text" in item:
                        parts.append(item["plain_text"])
                    elif "text" in item and "content" in item["text"]:
                        parts.append(item["text"]["content"])
                flattened[name] = "".join(parts)
                continue
            if inner_key == "select" and isinstance(inner_val, dict):
                flattened[name] = inner_val.get("name", "")
                continue
            if inner_key == "status" and isinstance(inner_val, dict):
                flattened[name] = inner_val.get("name", "")
                continue
        flattened[name] = value
    return flattened


def _extract_page_id(result: Any) -> Optional[str]:
    if isinstance(result, dict):
        direct = result.get("id") or result.get("page_id")
        if isinstance(direct, str):
            return direct
        url_value = result.get("url")
        if isinstance(url_value, str):
            url_id = _extract_id_from_notion_url(url_value)
            if url_id:
                return url_id
        for key in ("results", "pages", "items", "data"):
            candidate = _extract_page_id(result.get(key))
            if candidate:
                return candidate
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        for item in result:
            candidate = _extract_page_id(item)
            if candidate:
                return candidate
    return None


def _extract_id_from_notion_url(url: str) -> Optional[str]:
    tail = url.rstrip("/").split("/")[-1]
    if len(tail) == 32 and all(c in "0123456789abcdefABCDEF" for c in tail):
        return tail
    return None


def _normalize_view_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    raw = value.strip()
    if raw.startswith("view://"):
        normalized = _normalize_uuid(raw.split("view://", 1)[1])
        return f"view://{normalized}" if normalized else raw
    # Accept bare UUID for convenience.
    normalized = _normalize_uuid(raw)
    if normalized:
        return f"view://{normalized}"
    # Accept full Notion URLs with ?v=<view_id>.
    if "?v=" in raw:
        try:
            view_part = raw.split("?v=", 1)[1].split("&", 1)[0]
            normalized = _normalize_uuid(view_part)
            if normalized:
                return f"view://{normalized}"
        except Exception:
            return raw
    return raw


def _normalize_uuid(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    compact = str(value).replace("-", "").strip()
    if len(compact) != 32 or not all(c in "0123456789abcdefABCDEF" for c in compact):
        return None
    compact = compact.lower()
    return (
        f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-"
        f"{compact[16:20]}-{compact[20:]}"
    )


def _format_stage_value(stage: str) -> str:
    mapping = {
        "intent": "Intent",
        "context": "Context",
        "spec": "Specification",
        "plan": "Plan",
        "tasks": "Tasks",
        "implementation": "Implementation",
        "feedback": "Feedback",
    }
    return mapping.get(stage, stage)


def _make_idse_id(project: str, session_id: str, stage: str) -> str:
    return f"{project}::{session_id}::{stage}"


def _derive_version(session_id: str) -> Optional[str]:
    # Lightweight heuristic: use trailing vN / vN.N token when present.
    parts = session_id.replace("_", "-").split("-")
    for token in reversed(parts):
        if token.startswith("v") and len(token) > 1:
            return token
    return None


def _drop_idse_id(properties: Dict[str, Any], prop_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    if "idse_id" not in prop_map:
        return properties
    name = prop_map.get("idse_id", {}).get("name", "IDSE_ID")
    if name in properties:
        return {k: v for k, v in properties.items() if k != name}
    return properties


def _is_archived_page(page: Dict[str, Any]) -> bool:
    return bool(page.get("archived")) or bool(page.get("in_trash"))


def _select_best_active_page_id(results: List[Dict[str, Any]]) -> Optional[str]:
    if not results:
        return None
    active = [page for page in results if not _is_archived_page(page)]
    candidates = active or results
    candidates = sorted(
        candidates,
        key=lambda p: p.get("last_edited_time") or "",
        reverse=True,
    )
    for page in candidates:
        page_id = _extract_page_id(page)
        if page_id:
            return page_id
    return None


def _debug_payload(tool_name: str, payload: Dict[str, Any]) -> None:
    import json

    sanitized = payload
    if "pages" in payload:
        sanitized = {
            **payload,
            "pages": [
                {
                    **page,
                    "content": f"<{len(page.get('content', ''))} chars>"
                    if isinstance(page.get("content"), str)
                    else page.get("content"),
                }
                for page in payload["pages"]
            ],
        }
    if "children" in payload and isinstance(payload["children"], list):
        sanitized = {
            **payload,
            "children": f"<{len(payload['children'])} blocks>",
        }

    print(f"DEBUG MCP {tool_name} payload:")
    print(json.dumps(sanitized, indent=2))


def _debug_result(tool_name: str, result: Any) -> None:
    import json

    if isinstance(result, (dict, list)):
        print(f"DEBUG MCP {tool_name} result:")
        print(json.dumps(result, indent=2))
    else:
        print(f"DEBUG MCP {tool_name} result: {result}")
