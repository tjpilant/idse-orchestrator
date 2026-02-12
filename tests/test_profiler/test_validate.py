from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from idse_orchestrator.profiler.error_codes import ProfilerErrorCode
from idse_orchestrator.profiler.models import AgentSpecProfilerDoc
from idse_orchestrator.profiler.validate import validate_profiler_doc


def _valid_payload() -> dict:
    return {
        "mission_contract": {
            "objective_function": {
                "input_description": "Support ticket details and metadata",
                "output_description": "A categorized and prioritized ticket action plan",
                "transformation_summary": "Transform incoming support tickets into prioritized remediation plans",
            },
            "success_metric": "Resolve 90% of ticket triage decisions within 15 minutes",
            "explicit_exclusions": ["Do not execute production changes"],
            "core_tasks": [
                {
                    "task": "Classify ticket",
                    "method": "Map ticket content to a predefined category taxonomy",
                }
            ],
            "authority_boundary": {
                "may": ["Tag and prioritize tickets"],
                "may_not": ["Deploy code changes"],
            },
            "constraints": ["Use only approved ticket fields"],
            "failure_conditions": ["Category confidence below threshold"],
            "output_contract": {
                "format_type": "narrative",
                "required_sections": ["classification", "priority", "next-steps"],
                "required_metadata": ["confidence_score"],
                "validation_rules": ["Priority must be one of P1-P4"],
            },
        },
        "persona_overlay": {
            "industry_context": "SaaS support",
            "tone": "Direct",
            "detail_level": "Medium",
            "reference_preferences": [],
            "communication_rules": [],
        },
    }


def test_validate_profiler_doc_accepts_valid_input() -> None:
    doc = AgentSpecProfilerDoc.model_validate(_valid_payload())
    assert validate_profiler_doc(doc) is None


def test_validate_profiler_doc_rejects_generic_objective() -> None:
    payload = _valid_payload()
    payload["mission_contract"]["objective_function"]["transformation_summary"] = "Be helpful with anything"
    doc = AgentSpecProfilerDoc.model_validate(payload)

    rejection = validate_profiler_doc(doc)
    assert rejection is not None
    codes = {error.code for error in rejection.errors}
    assert ProfilerErrorCode.GENERIC_OBJECTIVE_FUNCTION in codes


def test_validate_profiler_doc_rejects_multi_objective() -> None:
    payload = _valid_payload()
    payload["mission_contract"]["objective_function"]["transformation_summary"] = (
        "Transform tickets and summarize trends"
    )
    doc = AgentSpecProfilerDoc.model_validate(payload)

    rejection = validate_profiler_doc(doc)
    assert rejection is not None
    codes = {error.code for error in rejection.errors}
    assert ProfilerErrorCode.MULTI_OBJECTIVE_AGENT in codes


def test_validate_profiler_doc_rejects_non_measurable_metric() -> None:
    payload = _valid_payload()
    payload["mission_contract"]["success_metric"] = "Improve outcomes"
    doc = AgentSpecProfilerDoc.model_validate(payload)

    rejection = validate_profiler_doc(doc)
    assert rejection is not None
    codes = {error.code for error in rejection.errors}
    assert ProfilerErrorCode.NON_MEASURABLE_SUCCESS_METRIC in codes


def test_validate_profiler_doc_rejects_missing_constraints_exclusions_failures() -> None:
    payload = _valid_payload()
    payload["mission_contract"]["explicit_exclusions"] = []
    payload["mission_contract"]["constraints"] = []
    payload["mission_contract"]["failure_conditions"] = []

    with pytest.raises(PydanticValidationError):
        AgentSpecProfilerDoc.model_validate(payload)
