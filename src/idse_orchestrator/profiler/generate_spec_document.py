"""Generate complete IDSE spec.md from a validated AgentSpecProfilerDoc.

Each generator function produces human-readable prose styled like
HR job descriptions with analysis — not robotic templates.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

import yaml

from .map_to_agent_profile_spec import to_agent_profile_spec
from .models import AgentSpecProfilerDoc


def _compute_profiler_hash(doc: AgentSpecProfilerDoc) -> str:
    """SHA256 of the normalized ProfilerDoc for drift detection."""
    normalized = json.dumps(doc.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()


def generate_intent_section(doc: AgentSpecProfilerDoc) -> str:
    """Produce ## Intent with Goal, Problem/Opportunity, Stakeholders, Success Criteria."""
    mc = doc.mission_contract
    obj = mc.objective_function
    po = doc.persona_overlay

    stakeholders = po.industry_context or "agent consumers"
    exclusions_narrative = ", ".join(mc.explicit_exclusions)

    lines = [
        "## Intent",
        "",
        "### Goal",
        "",
        f"This agent transforms {obj.input_description.lower()} into "
        f"{obj.output_description.lower()}. "
        f"{obj.transformation_summary}.",
        "",
        "### Problem / Opportunity",
        "",
        f"Without this agent, the transformation from {obj.input_description.lower()} "
        f"to {obj.output_description.lower()} is manual, inconsistent, or absent. "
        f"The following areas are explicitly out of scope to keep the agent focused: "
        f"{exclusions_narrative}.",
        "",
        "### Stakeholders",
        "",
        f"Primary stakeholders operate in the **{stakeholders}** domain. "
        f"They expect reliable, deterministic output that meets the defined "
        f"success criteria without manual intervention.",
        "",
        "### Success Criteria",
        "",
        f"- {mc.success_metric}",
        "",
    ]
    return "\n".join(lines)


def generate_context_section(doc: AgentSpecProfilerDoc) -> str:
    """Produce ## Context with architectural constraints narrative."""
    mc = doc.mission_contract
    po = doc.persona_overlay

    may_items = "\n".join(f"  - {item}" for item in mc.authority_boundary.may)
    may_not_items = "\n".join(f"  - {item}" for item in mc.authority_boundary.may_not)
    constraint_items = "\n".join(f"- {c}" for c in mc.constraints)
    exclusion_items = "\n".join(f"- {e}" for e in mc.explicit_exclusions)

    lines = [
        "## Context",
        "",
        "### Authority Boundaries",
        "",
        "This agent operates within a clearly defined authority boundary. "
        "These boundaries exist to prevent scope creep and ensure the agent "
        "remains focused on its primary transformation.",
        "",
        "**Permitted actions:**",
        may_items,
        "",
        "**Prohibited actions:**",
        may_not_items,
        "",
        "### Operational Constraints",
        "",
        "The following constraints govern all agent behavior:",
        "",
        constraint_items,
        "",
        "### Explicit Exclusions",
        "",
        "These items are deliberately excluded from the agent's scope:",
        "",
        exclusion_items,
        "",
    ]

    if po.industry_context:
        lines.extend([
            "### Domain Context",
            "",
            f"This agent operates in the **{po.industry_context}** domain.",
            "",
        ])

    return "\n".join(lines)


def generate_tasks_section(doc: AgentSpecProfilerDoc) -> str:
    """Produce ## Tasks with core_tasks listed with methods."""
    mc = doc.mission_contract

    lines = [
        "## Tasks",
        "",
        "The following core tasks define the agent's operational responsibilities. "
        "Each task includes the specific method by which it should be performed.",
        "",
    ]

    for i, ct in enumerate(mc.core_tasks, start=1):
        lines.append(f"- **Task {i}** — {ct.task}")
        lines.append(f"  - Method: {ct.method}")
        lines.append("")

    return "\n".join(lines)


def generate_specification_section(doc: AgentSpecProfilerDoc) -> str:
    """Produce ## Specification with Overview, FR-N, NFR, AC-N, Assumptions."""
    mc = doc.mission_contract
    obj = mc.objective_function
    oc = mc.output_contract

    lines = [
        "## Specification",
        "",
        "### Overview",
        "",
        f"{obj.transformation_summary}. "
        f"The agent accepts {obj.input_description.lower()} as input and produces "
        f"{obj.output_description.lower()} as output. "
        f"All operations are deterministic and scoped to the defined authority boundary.",
        "",
        "### Functional Requirements",
        "",
    ]

    for i, ct in enumerate(mc.core_tasks, start=1):
        lines.append(f"- FR-{i}: Agent MUST {ct.task.lower()} using {ct.method.lower()}")

    lines.extend(["", "### Non-Functional Requirements", ""])

    for i, c in enumerate(mc.constraints, start=1):
        lines.append(f"- NFR-{i}: {c}")

    if oc.format_type:
        lines.append(
            f"- NFR-{len(mc.constraints) + 1}: Output format MUST be {oc.format_type}"
        )

    lines.extend(["", "### Acceptance Criteria", ""])

    ac_index = 1
    lines.append(f"- AC-{ac_index}: {mc.success_metric}")
    ac_index += 1

    for rule in oc.validation_rules:
        lines.append(f"- AC-{ac_index}: {rule}")
        ac_index += 1

    lines.extend([
        "",
        "### Assumptions / Constraints / Dependencies",
        "",
    ])

    for c in mc.constraints:
        lines.append(f"- Constraint: {c}")

    for e in mc.explicit_exclusions:
        lines.append(f"- Exclusion: {e}")

    lines.extend([
        "",
        "### Failure Conditions",
        "",
    ])

    for fc in mc.failure_conditions:
        lines.append(f"- {fc}")

    lines.append("")
    return "\n".join(lines)


def generate_agent_profile_yaml(doc: AgentSpecProfilerDoc) -> str:
    """Produce ## Agent Profile YAML block from deterministic mapping."""
    mapped = to_agent_profile_spec(doc)

    yaml_text = yaml.safe_dump(mapped, sort_keys=False, default_flow_style=False)
    profiler_hash = _compute_profiler_hash(doc)

    lines = [
        "## Agent Profile",
        "",
        "```yaml",
        f"# profiler_hash: {profiler_hash}",
        yaml_text.rstrip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def generate_complete_spec_md(doc: AgentSpecProfilerDoc) -> str:
    """Assemble all sections into a complete spec.md document."""
    sections = [
        "# Specification",
        "",
        generate_intent_section(doc),
        generate_context_section(doc),
        generate_tasks_section(doc),
        generate_specification_section(doc),
        generate_agent_profile_yaml(doc),
    ]
    return "\n".join(sections)
