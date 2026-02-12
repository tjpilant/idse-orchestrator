from __future__ import annotations

from typing import Any, Dict

from .models import AgentSpecProfilerDoc


def export_profiler_json_schema() -> Dict[str, Any]:
    return AgentSpecProfilerDoc.model_json_schema()
