from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated

from .error_codes import ProfilerErrorCode


Text3 = Annotated[str, StringConstraints(min_length=3)]
Text5 = Annotated[str, StringConstraints(min_length=5)]
Text2 = Annotated[str, StringConstraints(min_length=2)]


class ObjectiveFunction(BaseModel):
    input_description: Text3
    output_description: Text3
    transformation_summary: Text5


class CoreTask(BaseModel):
    task: Text2
    method: Text2


class AuthorityBoundary(BaseModel):
    may: List[str] = Field(min_length=1)
    may_not: List[str] = Field(min_length=1)


class OutputContract(BaseModel):
    format_type: Literal["narrative", "json", "hybrid"]
    required_sections: List[str] = Field(default_factory=list)
    required_metadata: List[str] = Field(default_factory=list)
    validation_rules: List[str] = Field(min_length=1)


class MissionContract(BaseModel):
    objective_function: ObjectiveFunction
    success_metric: Text3
    explicit_exclusions: List[str] = Field(min_length=1)
    core_tasks: List[CoreTask] = Field(min_length=1, max_length=8)
    authority_boundary: AuthorityBoundary
    constraints: List[str] = Field(min_length=1)
    failure_conditions: List[str] = Field(min_length=1)
    output_contract: OutputContract


class PersonaOverlay(BaseModel):
    industry_context: Optional[str] = None
    tone: Optional[str] = None
    detail_level: Optional[str] = None
    reference_preferences: List[str] = Field(default_factory=list)
    communication_rules: List[str] = Field(default_factory=list)


class AgentSpecProfilerDoc(BaseModel):
    mission_contract: MissionContract
    persona_overlay: PersonaOverlay = Field(default_factory=PersonaOverlay)
    schema_version: str = "1.0"


class ProfilerError(BaseModel):
    field: str
    code: ProfilerErrorCode
    message: str
    severity: str = "error"


class ProfilerRejection(BaseModel):
    errors: List[ProfilerError] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)


class ProfilerAcceptance(BaseModel):
    doc: AgentSpecProfilerDoc
    mapped_agent_profile_spec: Dict[str, Any]
