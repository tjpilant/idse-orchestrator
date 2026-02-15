from __future__ import annotations

from enum import Enum


# Numeric ID mapping for telemetry and cross-platform tracking.
ERROR_CODE_IDS: dict[str, int] = {
    "missing_required_field": 1000,
    "generic_objective_function": 1001,
    "multi_objective_agent": 1002,
    "missing_success_metric": 1003,
    "non_measurable_success_metric": 1004,
    "missing_explicit_exclusions": 1005,
    "too_many_core_tasks": 1006,
    "missing_task": 1007,
    "non_actionable_method": 1008,
    "missing_authority_boundary": 1009,
    "missing_may_not": 1010,
    "missing_constraints": 1011,
    "missing_failure_conditions": 1012,
    "missing_output_contract": 1013,
    "invalid_format_type": 1014,
    "missing_required_sections": 1015,
    "missing_validation_rules": 1016,
    "scope_contradiction": 1017,
    "output_contract_incoherent": 1018,
    "persona_leak_into_mission": 2001,
    "success_metric_not_locally_verifiable": 2002,
}


class ProfilerErrorCode(str, Enum):
    MISSING_REQUIRED_FIELD = "missing_required_field"
    GENERIC_OBJECTIVE_FUNCTION = "generic_objective_function"
    MULTI_OBJECTIVE_AGENT = "multi_objective_agent"
    MISSING_SUCCESS_METRIC = "missing_success_metric"
    NON_MEASURABLE_SUCCESS_METRIC = "non_measurable_success_metric"
    MISSING_EXPLICIT_EXCLUSIONS = "missing_explicit_exclusions"
    TOO_MANY_CORE_TASKS = "too_many_core_tasks"
    MISSING_TASK = "missing_task"
    NON_ACTIONABLE_METHOD = "non_actionable_method"
    MISSING_AUTHORITY_BOUNDARY = "missing_authority_boundary"
    MISSING_MAY_NOT = "missing_may_not"
    MISSING_CONSTRAINTS = "missing_constraints"
    MISSING_FAILURE_CONDITIONS = "missing_failure_conditions"
    MISSING_OUTPUT_CONTRACT = "missing_output_contract"
    INVALID_FORMAT_TYPE = "invalid_format_type"
    MISSING_REQUIRED_SECTIONS = "missing_required_sections"
    MISSING_VALIDATION_RULES = "missing_validation_rules"
    SCOPE_CONTRADICTION = "scope_contradiction"
    OUTPUT_CONTRACT_INCOHERENT = "output_contract_incoherent"
    PERSONA_LEAK_INTO_MISSION = "persona_leak_into_mission"
    SUCCESS_METRIC_NOT_LOCALLY_VERIFIABLE = "success_metric_not_locally_verifiable"
