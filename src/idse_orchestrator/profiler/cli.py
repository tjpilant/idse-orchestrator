from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from pydantic import ValidationError as PydanticValidationError

from .map_to_agent_profile_spec import to_agent_profile_spec
from .models import AgentSpecProfilerDoc, CoreTask, ProfilerAcceptance, ProfilerRejection
from .validate import validate_profiler_doc


def _parse_csv_list(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_required_text(question: str) -> str:
    return click.prompt(question, type=str).strip()


def _prompt_optional_text(question: str) -> Optional[str]:
    value = click.prompt(question, default="", show_default=False).strip()
    return value or None


def _prompt_list(question: str, *, required: bool) -> List[str]:
    while True:
        raw = click.prompt(question, default="", show_default=False)
        values = _parse_csv_list(raw)
        if values or not required:
            return values
        click.echo("At least one value is required.")


def collect_profiler_answers_interactive() -> Dict[str, Any]:
    # 1-4
    input_description = _prompt_required_text("1/20 Input description")
    output_description = _prompt_required_text("2/20 Output description")
    transformation_summary = _prompt_required_text("3/20 Transformation summary (one sentence)")
    success_metric = _prompt_required_text("4/20 Success metric (measurable)")

    # 5-7
    explicit_exclusions = _prompt_list("5/20 Explicit exclusions (comma-separated)", required=True)
    task_names = _prompt_list("6/20 Core tasks (comma-separated, max 8)", required=True)
    if len(task_names) > 8:
        task_names = task_names[:8]

    core_tasks: List[CoreTask] = []
    for index, task in enumerate(task_names, start=1):
        method = _prompt_required_text(f"7/20 Method for task {index} '{task}'")
        core_tasks.append(CoreTask(task=task, method=method))

    # 8-15
    may = _prompt_list("8/20 Authority boundary: may (comma-separated)", required=True)
    may_not = _prompt_list("9/20 Authority boundary: may_not (comma-separated)", required=True)
    constraints = _prompt_list("10/20 Constraints (comma-separated)", required=True)
    failure_conditions = _prompt_list("11/20 Failure conditions (comma-separated)", required=True)

    while True:
        format_type = click.prompt(
            "12/20 Output format type",
            type=click.Choice(["narrative", "json", "hybrid"], case_sensitive=False),
        ).lower()
        if format_type in {"narrative", "json", "hybrid"}:
            break

    required_sections: List[str] = []
    if format_type in {"narrative", "hybrid"}:
        required_sections = _prompt_list("13/20 Required sections (comma-separated)", required=True)
    else:
        click.echo("13/20 Required sections skipped for json output")

    required_metadata = _prompt_list("14/20 Required metadata (comma-separated, optional)", required=False)
    validation_rules = _prompt_list("15/20 Validation rules (comma-separated)", required=True)

    # 16-20
    industry_context = _prompt_optional_text("16/20 Industry context (optional)")
    tone = _prompt_optional_text("17/20 Tone (optional)")
    detail_level = _prompt_optional_text("18/20 Detail level (optional)")
    reference_preferences = _prompt_list("19/20 Reference preferences (comma-separated, optional)", required=False)
    communication_rules = _prompt_list("20/20 Communication rules (comma-separated, optional)", required=False)

    return {
        "mission_contract": {
            "objective_function": {
                "input_description": input_description,
                "output_description": output_description,
                "transformation_summary": transformation_summary,
            },
            "success_metric": success_metric,
            "explicit_exclusions": explicit_exclusions,
            "core_tasks": [task.model_dump() for task in core_tasks],
            "authority_boundary": {
                "may": may,
                "may_not": may_not,
            },
            "constraints": constraints,
            "failure_conditions": failure_conditions,
            "output_contract": {
                "format_type": format_type,
                "required_sections": required_sections,
                "required_metadata": required_metadata,
                "validation_rules": validation_rules,
            },
        },
        "persona_overlay": {
            "industry_context": industry_context,
            "tone": tone,
            "detail_level": detail_level,
            "reference_preferences": reference_preferences,
            "communication_rules": communication_rules,
        },
    }


def run_profiler_intake(payload: Dict[str, Any]) -> ProfilerAcceptance | ProfilerRejection:
    try:
        doc = AgentSpecProfilerDoc.model_validate(payload)
    except PydanticValidationError as exc:
        return ProfilerRejection(
            errors=[],
            next_questions=[f"Fix schema validation errors: {exc.errors()}"],
        )

    rejection = validate_profiler_doc(doc)
    if rejection:
        return rejection

    mapped = to_agent_profile_spec(doc)
    return ProfilerAcceptance(doc=doc, mapped_agent_profile_spec=mapped)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
