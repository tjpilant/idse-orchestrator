from __future__ import annotations

from enum import Enum


class ProfilerErrorCode(str, Enum):
    MISSING_REQUIRED_FIELD = "missing_required_field"
    GENERIC_OBJECTIVE_FUNCTION = "generic_objective_function"
    MULTI_OBJECTIVE_AGENT = "multi_objective_agent"
    MISSING_SUCCESS_METRIC = "missing_success_metric"
    NON_MEASURABLE_SUCCESS_METRIC = "non_measurable_success_metric"
    MISSING_EXPLICIT_EXCLUSIONS = "missing_explicit_exclusions"
    TOO_MANY_CORE_TASKS = "too_many_core_tasks"
    MISSING_TASK = "missing_task"
    MISSING_METHOD = "missing_method"
    MISSING_AUTHORITY_BOUNDARY = "missing_authority_boundary"
    MISSING_MAY_NOT = "missing_may_not"
    MISSING_CONSTRAINTS = "missing_constraints"
    MISSING_FAILURE_CONDITIONS = "missing_failure_conditions"
    MISSING_OUTPUT_CONTRACT = "missing_output_contract"
    INVALID_FORMAT_TYPE = "invalid_format_type"
    MISSING_REQUIRED_SECTIONS = "missing_required_sections"
    MISSING_VALIDATION_RULES = "missing_validation_rules"
    PERSONA_LEAK_INTO_MISSION = "persona_leak_into_mission"
