from __future__ import annotations

import re
from typing import List, Optional

from .error_codes import ProfilerErrorCode
from .models import AgentSpecProfilerDoc, ProfilerError, ProfilerRejection


GENERIC_OBJECTIVE_PHRASES = {
    "be helpful",
    "assist with anything",
    "help with anything",
    "various outputs",
    "anything",
    "do tasks",
}

MISSION_LEAK_PHRASES = {
    "friendly",
    "empathetic",
    "casual tone",
    "professional tone",
    "persona",
}

MEASURABLE_HINTS = (
    "%",
    "percent",
    "per ",
    "within ",
    "under ",
    "less than",
    "more than",
    "at least",
    "at most",
    "days",
    "hours",
    "minutes",
    "seconds",
)


def _has_number(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _is_measurable_metric(metric: str) -> bool:
    lowered = metric.lower()
    return _has_number(metric) or any(token in lowered for token in MEASURABLE_HINTS)


def _contains_generic_language(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in GENERIC_OBJECTIVE_PHRASES)


def _looks_multi_objective(summary: str) -> bool:
    lowered = summary.lower()
    if " and " in lowered or " or " in lowered:
        return True
    # Heuristic: two or more comma-separated clauses often indicate multiple objectives.
    return lowered.count(",") >= 2


def _persona_leaks_into_mission(summary: str) -> bool:
    lowered = summary.lower()
    return any(token in lowered for token in MISSION_LEAK_PHRASES)


def _add_error(
    errors: List[ProfilerError],
    *,
    field: str,
    code: ProfilerErrorCode,
    message: str,
) -> None:
    errors.append(ProfilerError(field=field, code=code, message=message))


def validate_profiler_doc(doc: AgentSpecProfilerDoc) -> Optional[ProfilerRejection]:
    errors: List[ProfilerError] = []
    next_questions: List[str] = []

    mission = doc.mission_contract
    objective = mission.objective_function

    if _contains_generic_language(objective.transformation_summary):
        _add_error(
            errors,
            field="mission_contract.objective_function.transformation_summary",
            code=ProfilerErrorCode.GENERIC_OBJECTIVE_FUNCTION,
            message="Transformation summary is too generic.",
        )
        next_questions.append(
            "What single transformation do you perform from input to output in one precise sentence?"
        )

    if _looks_multi_objective(objective.transformation_summary):
        _add_error(
            errors,
            field="mission_contract.objective_function.transformation_summary",
            code=ProfilerErrorCode.MULTI_OBJECTIVE_AGENT,
            message="Transformation summary appears to contain multiple objectives.",
        )
        next_questions.append(
            "Which single objective is primary, and what should be explicitly out of scope?"
        )

    if not mission.success_metric.strip():
        _add_error(
            errors,
            field="mission_contract.success_metric",
            code=ProfilerErrorCode.MISSING_SUCCESS_METRIC,
            message="Success metric is required.",
        )
        next_questions.append("How will success be measured numerically or with a clear proxy?")
    elif not _is_measurable_metric(mission.success_metric):
        _add_error(
            errors,
            field="mission_contract.success_metric",
            code=ProfilerErrorCode.NON_MEASURABLE_SUCCESS_METRIC,
            message="Success metric must be measurable.",
        )
        next_questions.append("Can you rewrite success with a number, threshold, or time bound?")

    if not mission.explicit_exclusions:
        _add_error(
            errors,
            field="mission_contract.explicit_exclusions",
            code=ProfilerErrorCode.MISSING_EXPLICIT_EXCLUSIONS,
            message="At least one explicit exclusion is required.",
        )

    if not mission.constraints:
        _add_error(
            errors,
            field="mission_contract.constraints",
            code=ProfilerErrorCode.MISSING_CONSTRAINTS,
            message="At least one constraint is required.",
        )

    if not mission.failure_conditions:
        _add_error(
            errors,
            field="mission_contract.failure_conditions",
            code=ProfilerErrorCode.MISSING_FAILURE_CONDITIONS,
            message="At least one failure condition is required.",
        )

    if len(mission.core_tasks) > 8:
        _add_error(
            errors,
            field="mission_contract.core_tasks",
            code=ProfilerErrorCode.TOO_MANY_CORE_TASKS,
            message="No more than 8 core tasks are allowed.",
        )

    for i, task in enumerate(mission.core_tasks):
        if not task.task.strip():
            _add_error(
                errors,
                field=f"mission_contract.core_tasks[{i}].task",
                code=ProfilerErrorCode.MISSING_TASK,
                message="Task label is required.",
            )
        if not task.method.strip():
            _add_error(
                errors,
                field=f"mission_contract.core_tasks[{i}].method",
                code=ProfilerErrorCode.MISSING_METHOD,
                message="Task method is required.",
            )

    if not mission.authority_boundary.may:
        _add_error(
            errors,
            field="mission_contract.authority_boundary.may",
            code=ProfilerErrorCode.MISSING_AUTHORITY_BOUNDARY,
            message="At least one allowed action is required.",
        )

    if not mission.authority_boundary.may_not:
        _add_error(
            errors,
            field="mission_contract.authority_boundary.may_not",
            code=ProfilerErrorCode.MISSING_MAY_NOT,
            message="At least one prohibited action is required.",
        )

    output = mission.output_contract
    if output.format_type in {"narrative", "hybrid"} and not output.required_sections:
        _add_error(
            errors,
            field="mission_contract.output_contract.required_sections",
            code=ProfilerErrorCode.MISSING_REQUIRED_SECTIONS,
            message="Narrative and hybrid outputs require required_sections.",
        )

    if not output.validation_rules:
        _add_error(
            errors,
            field="mission_contract.output_contract.validation_rules",
            code=ProfilerErrorCode.MISSING_VALIDATION_RULES,
            message="At least one validation rule is required.",
        )

    if _persona_leaks_into_mission(objective.transformation_summary):
        _add_error(
            errors,
            field="mission_contract.objective_function.transformation_summary",
            code=ProfilerErrorCode.PERSONA_LEAK_INTO_MISSION,
            message="Mission summary should describe transformation, not persona style.",
        )
        next_questions.append(
            "Can you move style/tone language into persona_overlay and keep mission purely functional?"
        )

    if not errors:
        return None

    deduped_questions = list(dict.fromkeys(next_questions))
    return ProfilerRejection(errors=errors, next_questions=deduped_questions)
