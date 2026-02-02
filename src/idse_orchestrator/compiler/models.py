from __future__ import annotations

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class AgentProfileSpec(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    goals: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    memory_policy: Optional[Dict[str, Any]] = None
    runtime_hints: Optional[Dict[str, Any]] = None
    version: str = "1.0"
    source_session: Optional[str] = None
    source_blueprint: Optional[str] = None
