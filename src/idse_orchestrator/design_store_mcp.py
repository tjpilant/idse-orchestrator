from __future__ import annotations

import asyncio
import json
from abc import ABC
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .design_store import DesignStore


class MCPDesignStoreAdapter(DesignStore, ABC):
    """Base adapter for MCP-backed DesignStore implementations."""

    def __init__(self, server_params: StdioServerParameters):
        self._server_params = server_params

    def _run(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                return asyncio.run(coro)
            except* Exception as eg:
                raise RuntimeError(_flatten_exception_group(eg)) from eg
        if loop.is_running():
            raise RuntimeError(
                "MCPDesignStoreAdapter cannot run in an active event loop. "
                "Use async helpers or call from a sync context."
            )
        try:
            return loop.run_until_complete(coro)
        except* Exception as eg:
            raise RuntimeError(_flatten_exception_group(eg)) from eg

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return self._normalize_tool_result(result)

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        return self._run(self._call_tool_async(tool_name, arguments))

    async def _list_tools_async(self) -> Any:
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()

    def _list_tools(self) -> Any:
        return self._run(self._list_tools_async())

    def list_tools(self) -> Any:
        return self._list_tools()

    async def _with_session_async(self, func):
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await func(session)

    def _with_session(self, func):
        return self._run(self._with_session_async(func))

    async def _call_tool_in_session(self, session, tool_name: str, arguments: Dict[str, Any]) -> Any:
        result = await session.call_tool(tool_name, arguments=arguments)
        return self._normalize_tool_result(result)

    @staticmethod
    def _normalize_tool_result(result: Any) -> Any:
        if getattr(result, "isError", False):
            message = _extract_error_message(result)
            raise RuntimeError(message or "MCP tool error")
        content = getattr(result, "content", None)
        if not content:
            return None

        first = content[0]
        if isinstance(first, dict):
            if "json" in first:
                return first["json"]
            if "text" in first:
                return _maybe_json(first["text"])
            return first

        text = getattr(first, "text", None)
        if text is not None:
            return _maybe_json(text)

        return first


def _maybe_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw


def _extract_error_message(result: Any) -> str:
    content = getattr(result, "content", None) or []
    if not content:
        return ""
    first = content[0]
    if isinstance(first, dict):
        return first.get("text") or first.get("message", "")
    return getattr(first, "text", "") or ""


def _flatten_exception_group(eg: ExceptionGroup) -> str:
    messages = []
    for exc in eg.exceptions:
        if isinstance(exc, ExceptionGroup):
            messages.append(_flatten_exception_group(exc))
        else:
            messages.append(str(exc))
    return "; ".join([m for m in messages if m])
