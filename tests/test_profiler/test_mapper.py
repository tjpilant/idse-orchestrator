from __future__ import annotations

from idse_orchestrator.profiler.map_to_agent_profile_spec import to_agent_profile_spec
from idse_orchestrator.profiler.models import AgentSpecProfilerDoc


def _payload() -> dict:
    return {
        "mission_contract": {
            "objective_function": {
                "input_description": "Issue report",
                "output_description": "Remediation checklist",
                "transformation_summary": "Transform issue reports into remediation checklists",
            },
            "success_metric": "95% of checklists accepted on first review",
            "explicit_exclusions": ["Do not execute remediations"],
            "core_tasks": [
                {
                    "task": "Extract issue facts",
                    "method": "Read report fields and normalize categories",
                },
                {
                    "task": "Generate remediation checklist",
                    "method": "Apply predefined runbook rules",
                },
            ],
            "authority_boundary": {
                "may": ["Suggest checklist actions"],
                "may_not": ["Run shell commands"],
            },
            "constraints": ["Use only ticket content"],
            "failure_conditions": ["Missing required fields"],
            "output_contract": {
                "format_type": "hybrid",
                "required_sections": ["summary", "checklist"],
                "required_metadata": ["ticket_id"],
                "validation_rules": ["Checklist has at least 3 steps"],
            },
        },
        "persona_overlay": {
            "industry_context": "Incident response",
            "tone": "Concise",
            "detail_level": "High",
            "reference_preferences": ["Internal runbooks"],
            "communication_rules": ["No speculative language"],
        },
    }


def test_to_agent_profile_spec_maps_full_contract() -> None:
    doc = AgentSpecProfilerDoc.model_validate(_payload())

    mapped = to_agent_profile_spec(doc)

    assert mapped["description"] == "Transform issue reports into remediation checklists"
    assert mapped["success_criteria"] == "95% of checklists accepted on first review"
    assert mapped["out_of_scope"] == ["Do not execute remediations"]
    assert mapped["capabilities"][0]["task"] == "Extract issue facts"
    assert mapped["action_permissions"]["may_not"] == ["Run shell commands"]
    assert mapped["output_contract"]["format_type"] == "hybrid"


def test_to_agent_profile_spec_maps_persona_overlay() -> None:
    doc = AgentSpecProfilerDoc.model_validate(_payload())

    mapped = to_agent_profile_spec(doc)

    assert mapped["persona"]["industry_context"] == "Incident response"
    assert mapped["persona"]["tone"] == "Concise"
    assert mapped["persona"]["reference_preferences"] == ["Internal runbooks"]
