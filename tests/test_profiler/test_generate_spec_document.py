"""Tests for the Profiler Document Generator (Phase 5.5)."""

from __future__ import annotations

import yaml

from idse_orchestrator.compiler.parser import parse_agent_profile
from idse_orchestrator.profiler.generate_spec_document import (
    generate_agent_profile_yaml,
    generate_complete_spec_md,
    generate_context_section,
    generate_intent_section,
    generate_specification_section,
    generate_tasks_section,
)
from idse_orchestrator.profiler.models import AgentSpecProfilerDoc


def _valid_doc() -> AgentSpecProfilerDoc:
    return AgentSpecProfilerDoc.model_validate(
        {
            "mission_contract": {
                "objective_function": {
                    "input_description": "Restaurant notes and menu details",
                    "output_description": "A polished long-form blog post draft",
                    "transformation_summary": "Transform raw restaurant notes into an SEO-ready narrative blog draft",
                },
                "success_metric": "Publishable draft produced within 45 minutes with at most 2 factual corrections",
                "explicit_exclusions": [
                    "Do not publish directly to CMS",
                    "Do not fabricate menu items",
                ],
                "core_tasks": [
                    {
                        "task": "Outline article structure",
                        "method": "Derive section plan from restaurant highlights and audience intent",
                    },
                    {
                        "task": "Write draft prose",
                        "method": "Generate section-by-section narrative with factual checks against source notes",
                    },
                ],
                "authority_boundary": {
                    "may": ["Summarize provided notes", "Suggest headline variants"],
                    "may_not": ["Invent quotes from owners", "Claim firsthand dining experience"],
                },
                "constraints": [
                    "Cite all factual claims from provided inputs",
                    "Keep article between 900 and 1300 words",
                ],
                "failure_conditions": [
                    "Missing required sections",
                    "Unsupported factual claims",
                ],
                "output_contract": {
                    "format_type": "narrative",
                    "required_sections": ["headline", "lede", "menu-highlights", "closing"],
                    "required_metadata": ["target_keyword"],
                    "validation_rules": [
                        "Word count in target range",
                        "All facts trace to source notes",
                    ],
                },
            },
            "persona_overlay": {
                "industry_context": "Hospitality content marketing",
                "tone": "Warm and descriptive",
                "detail_level": "High",
                "reference_preferences": ["Prefer first-party source notes"],
                "communication_rules": ["Avoid sensational claims"],
            },
        }
    )


def test_generate_intent_includes_required_subsections() -> None:
    doc = _valid_doc()
    intent = generate_intent_section(doc)

    assert "## Intent" in intent
    assert "### Goal" in intent
    assert "### Problem / Opportunity" in intent
    assert "### Stakeholders" in intent
    assert "### Success Criteria" in intent
    assert "45 minutes" in intent


def test_generate_context_includes_boundaries_and_constraints() -> None:
    doc = _valid_doc()
    context = generate_context_section(doc)

    assert "## Context" in context
    assert "### Authority Boundaries" in context
    assert "Summarize provided notes" in context
    assert "Invent quotes from owners" in context
    assert "### Operational Constraints" in context
    assert "### Explicit Exclusions" in context
    assert "Hospitality content marketing" in context


def test_generate_tasks_lists_all_tasks_with_methods() -> None:
    doc = _valid_doc()
    tasks = generate_tasks_section(doc)

    assert "## Tasks" in tasks
    assert "**Task 1**" in tasks
    assert "Outline article structure" in tasks
    assert "Method:" in tasks
    assert "Derive section plan" in tasks
    assert "**Task 2**" in tasks
    assert "Write draft prose" in tasks


def test_generate_specification_includes_numbered_fr_and_ac() -> None:
    doc = _valid_doc()
    spec = generate_specification_section(doc)

    assert "## Specification" in spec
    assert "### Overview" in spec
    assert "### Functional Requirements" in spec
    assert "FR-1:" in spec
    assert "FR-2:" in spec
    assert "### Non-Functional Requirements" in spec
    assert "NFR-1:" in spec
    assert "### Acceptance Criteria" in spec
    assert "AC-1:" in spec
    assert "AC-2:" in spec
    assert "### Failure Conditions" in spec


def test_generate_agent_profile_yaml_validates_against_schema() -> None:
    doc = _valid_doc()
    profile_section = generate_agent_profile_yaml(doc)

    assert "## Agent Profile" in profile_section
    assert "```yaml" in profile_section

    # Extract and parse the YAML
    data = parse_agent_profile(profile_section)
    assert data["description"] == "Transform raw restaurant notes into an SEO-ready narrative blog draft"
    assert data["constraints"] == [
        "Cite all factual claims from provided inputs",
        "Keep article between 900 and 1300 words",
    ]


def test_complete_spec_md_has_all_sections() -> None:
    doc = _valid_doc()
    spec_md = generate_complete_spec_md(doc)

    assert "# Specification" in spec_md
    assert "## Intent" in spec_md
    assert "## Context" in spec_md
    assert "## Tasks" in spec_md
    assert "## Specification" in spec_md
    assert "## Agent Profile" in spec_md


def test_complete_spec_md_parseable_by_compiler() -> None:
    doc = _valid_doc()
    spec_md = generate_complete_spec_md(doc)

    # The existing compiler parser should be able to extract the Agent Profile
    data = parse_agent_profile(spec_md)
    assert "description" in data
    assert "constraints" in data
    assert "capabilities" in data


def test_generated_prose_reads_like_hr_description() -> None:
    doc = _valid_doc()
    spec_md = generate_complete_spec_md(doc)

    # Verify prose quality: not just bullet lists, contains narrative sentences
    assert "This agent transforms" in spec_md
    assert "Primary stakeholders operate" in spec_md
    assert "These boundaries exist to prevent" in spec_md
    assert "The following core tasks define" in spec_md
