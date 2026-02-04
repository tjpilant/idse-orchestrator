from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import StdioServerParameters

from .design_store_mcp import MCPDesignStoreAdapter


class NotionDesignStore(MCPDesignStoreAdapter):
    """Notion-backed DesignStore using the Notion MCP server."""

    DEFAULT_TOOL_NAMES = {
        "query_database": "notion-query-database",
        "fetch_page": "notion-fetch",
        "create_page": "notion-create-page",
        "update_page": "notion-update-page",
        "append_children": "append_block_children",
        "update_data_source": "notion-update-data-source",
    }

    DEFAULT_PROPERTIES = {
        "title": {"name": "Title", "type": "title"},
        "idse_id": {"name": "IDSE_ID", "type": "rich_text"},
        "project": {"name": "Project", "type": "rich_text"},
        "session": {"name": "Session", "type": "rich_text"},
        "stage": {"name": "Stage", "type": "select"},
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
        self.database_view_id = database_view_id
        self.database_view_url = database_view_url
        self.parent_data_source_url = parent_data_source_url
        self.data_source_id = data_source_id
        self.debug = False
        self.use_idse_id = True
        self._idse_schema_checked = False
        self.tool_names = {**self.DEFAULT_TOOL_NAMES, **(tool_names or {})}
        self.properties = self._normalize_properties(
            {**self.DEFAULT_PROPERTIES, **(properties or {})}
        )

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

    def load_artifact(self, project: str, session_id: str, stage: str) -> str:
        page = self._query_artifact_page(project, session_id, stage)
        if not page:
            raise FileNotFoundError(
                f"Artifact not found: {project}/{session_id}/{stage}"
            )
        if self._content_type() == "page_body":
            fetch = self._call_tool(
                self.tool_names["fetch_page"], {"page_id": page["id"]}
            )
            return _extract_page_body(fetch)
        return self._extract_property_text(page, "content")

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> None:
        self._ensure_idse_id_property()
        page = self._query_artifact_page(project, session_id, stage)
        title_prop = self.properties.get("title")
        title_value = f"{stage.title()} – {project} – {session_id}"
        properties = {
            self.properties["project"]["name"]: self._property_value("project", project),
            self.properties["session"]["name"]: self._property_value("session", session_id),
            self.properties["stage"]["name"]: self._property_value(
                "stage", _format_stage_value(stage)
            ),
        }
        if self.use_idse_id:
            properties[self.properties["idse_id"]["name"]] = self._property_value(
                "idse_id", _make_idse_id(project, session_id, stage)
            )
        if title_prop:
            properties[title_prop["name"]] = self._property_value("title", title_value)
        if self._content_type() != "page_body":
            properties[self.properties["content"]["name"]] = self._property_value(
                "content", content
            )
        content_payload = content if self._content_type() == "page_body" else None
        
        # Flatten properties for both create and update (Notion MCP expects SQLite values)
        flat_properties = _flatten_property_values(properties)

        if page:
            # Update existing page
            if self.tool_names.get("update_page"):
                payload_props = {
                    "data": {
                        "page_id": page["id"],
                        "command": "update_properties",
                        "properties": flat_properties,
                    }
                }
                if self.debug:
                    _debug_payload(self.tool_names["update_page"], payload_props)
                try:
                    result = self._call_tool(self.tool_names["update_page"], payload_props)
                except Exception as exc:
                    if "Property \"IDSE_ID\" not found" in str(exc):
                        self.use_idse_id = False
                        flat_props_no_id = _drop_idse_id(flat_properties, self.properties)
                        payload_props["data"]["properties"] = flat_props_no_id
                        result = self._call_tool(self.tool_names["update_page"], payload_props)
                    else:
                        raise
                if self.debug:
                    _debug_result(self.tool_names["update_page"], result)

                if content_payload is not None:
                    payload_content = {
                        "data": {
                            "page_id": page["id"],
                            "command": "replace_content",
                            "new_str": content_payload,
                        }
                    }
                    if self.debug:
                        _debug_payload(self.tool_names["update_page"], payload_content)
                    result = self._call_tool(self.tool_names["update_page"], payload_content)
                    if self.debug:
                        _debug_result(self.tool_names["update_page"], result)
            return

        create_tool = self.tool_names["create_page"]
        if create_tool == "create_database_item":
            payload = {
                "database_id": self.database_id,
                "properties": properties,
            }
            if self.debug:
                _debug_payload(create_tool, payload)
            try:
                new_page = self._call_tool(create_tool, payload)
            except Exception as exc:
                if "Property \"IDSE_ID\" not found" in str(exc):
                    self.use_idse_id = False
                    payload["properties"] = _drop_idse_id(properties, self.properties)
                    new_page = self._call_tool(create_tool, payload)
                else:
                    raise
            if self.debug:
                _debug_result(create_tool, new_page)
            if content_payload is not None and self.tool_names.get("append_children"):
                page_id = _extract_page_id(new_page)
                if page_id:
                    append_payload = {
                        "block_id": page_id,
                        "children": _render_page_body(content_payload),
                    }
                    if self.debug:
                        _debug_payload(self.tool_names["append_children"], append_payload)
                    result = self._call_tool(self.tool_names["append_children"], append_payload)
                    if self.debug:
                        _debug_result(self.tool_names["append_children"], result)
            return

        if create_tool == "notion-create-pages":
            payload = {
                "pages": [
                    {
                        "properties": flat_properties,
                        "content": content_payload or "",
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
            except Exception as exc:
                if "Property \"IDSE_ID\" not found" in str(exc):
                    self.use_idse_id = False
                    payload["pages"][0]["properties"] = _drop_idse_id(
                        payload["pages"][0]["properties"], self.properties
                    )
                    result = self._call_tool(create_tool, payload)
                else:
                    raise
            if self.debug:
                _debug_result(create_tool, result)
            return

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
        }
        if content_payload is not None:
            payload["content"] = content_payload
        if self.debug:
            _debug_payload(create_tool, payload)
        result = self._call_tool(create_tool, payload)
        if self.debug:
            _debug_result(create_tool, result)

    def list_sessions(self, project: str) -> List[str]:
        results = self._query_database(
            filters=[self._property_filter("project", project)]
        )
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

            for key in ("project", "session", "stage", "content"):
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

    def _query_artifact_page(
        self, project: str, session_id: str, stage: str
    ) -> Optional[Dict[str, Any]]:
        self._ensure_idse_id_property()
        filters = [
            self._property_filter(
                "idse_id", _make_idse_id(project, session_id, stage)
            )
        ]
        try:
            results = self._query_database(filters)
        except Exception as exc:
            if "IDSE_ID" in str(exc):
                self.use_idse_id = False
                results = []
            else:
                raise
        if results:
            return results[0]
        fallback_filters = [
            self._property_filter("project", project),
            self._property_filter("session", session_id),
            self._property_filter("stage", stage),
        ]
        fallback_results = self._query_database(fallback_filters)
        return fallback_results[0] if fallback_results else None

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

    def _ensure_idse_id_property(self) -> None:
        if not self.use_idse_id or self._idse_schema_checked:
            return
        tool = self.tool_names.get("update_data_source")
        if not tool:
            return
        data_source_id = self.data_source_id or self.database_id
        if not data_source_id:
            return
        payload = {
            "data_source_id": data_source_id,
            "properties": {
                self.properties["idse_id"]["name"]: {"rich_text": {}}
            },
        }
        if self.debug:
            _debug_payload(tool, payload)
        try:
            result = self._call_tool(tool, payload)
            if self.debug:
                _debug_result(tool, result)
        except Exception:
            self.use_idse_id = False
        self._idse_schema_checked = True

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
        if ptype in ("title", "rich_text"):
            items = value.get(ptype, [])
            return "".join([item.get("plain_text", "") for item in items])
        return ""

    def _content_type(self) -> str:
        return self.properties["content"]["type"]

    @staticmethod
    def _normalize_properties(properties: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        normalized: Dict[str, Dict[str, str]] = {}
        for key, prop in properties.items():
            ptype = prop.get("type", "").lower()
            if ptype == "text":
                ptype = "rich_text"
            normalized[key] = {**prop, "type": ptype}
        return normalized


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
        flattened[name] = value
    return flattened


def _extract_page_id(result: Any) -> Optional[str]:
    if isinstance(result, dict):
        return result.get("id") or result.get("page_id")
    if isinstance(result, str):
        return result
    return None


def _format_stage_value(stage: str) -> str:
    mapping = {
        "intent": "Intent",
        "context": "Context",
        "spec": "Specification",
        "plan": "Plan",
        "tasks": "Tasks",
        "implementation": "Test Plan",
        "feedback": "Feedback",
    }
    return mapping.get(stage, stage)


def _make_idse_id(project: str, session_id: str, stage: str) -> str:
    return f"{project}::{session_id}::{stage}"


def _drop_idse_id(properties: Dict[str, Any], prop_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    name = prop_map.get("idse_id", {}).get("name", "IDSE_ID")
    if name in properties:
        return {k: v for k, v in properties.items() if k != name}
    return properties


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
