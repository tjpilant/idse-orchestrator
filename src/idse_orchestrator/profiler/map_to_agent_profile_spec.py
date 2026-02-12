from __future__ import annotations

from typing import Any, Dict

from .models import AgentSpecProfilerDoc


def to_agent_profile_spec(doc: AgentSpecProfilerDoc) -> Dict[str, Any]:
    mc = doc.mission_contract
    po = doc.persona_overlay

    return {
        "name": None,
        "description": mc.objective_function.transformation_summary,
        "objective_function": {
            "input_description": mc.objective_function.input_description,
            "output_description": mc.objective_function.output_description,
            "transformation_summary": mc.objective_function.transformation_summary,
        },
        "success_criteria": mc.success_metric,
        "out_of_scope": mc.explicit_exclusions,
        "capabilities": [{"task": t.task, "method": t.method} for t in mc.core_tasks],
        "action_permissions": {
            "may": mc.authority_boundary.may,
            "may_not": mc.authority_boundary.may_not,
        },
        "constraints": mc.constraints,
        "failure_modes": mc.failure_conditions,
        "output_contract": {
            "format_type": mc.output_contract.format_type,
            "required_sections": mc.output_contract.required_sections,
            "required_metadata": mc.output_contract.required_metadata,
            "validation_rules": mc.output_contract.validation_rules,
        },
        "persona": {
            "industry_context": po.industry_context,
            "tone": po.tone,
            "detail_level": po.detail_level,
            "reference_preferences": po.reference_preferences,
            "communication_rules": po.communication_rules,
        },
    }
