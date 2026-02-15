"""Phase 10 — Adversarial test suite for the Agent Spec Profiler.

10 tests exercising canonical error codes against edge-case inputs.
"""

from __future__ import annotations

import re

from idse_orchestrator.profiler.error_codes import ProfilerErrorCode
from idse_orchestrator.profiler.generate_spec_document import generate_complete_spec_md
from idse_orchestrator.profiler.models import AgentSpecProfilerDoc
from idse_orchestrator.profiler.validate import validate_profiler_doc


def _valid_base() -> dict:
    """Golden-path payload used as a base for adversarial mutations."""
    return {
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


# ---------- Test 1: Vague Multi-Tasker (E1001, E1002, E1004) ----------

def test_adversarial_vague_multi_tasker() -> None:
    """Generic objective, multi-objective, non-measurable metric."""
    payload = _valid_base()
    payload["mission_contract"]["objective_function"]["transformation_summary"] = (
        "Be helpful with anything and assist with various outputs"
    )
    payload["mission_contract"]["success_metric"] = "Improve quality overall"

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.GENERIC_OBJECTIVE_FUNCTION in codes  # E1001
    assert ProfilerErrorCode.MULTI_OBJECTIVE_AGENT in codes  # E1002
    assert ProfilerErrorCode.NON_MEASURABLE_SUCCESS_METRIC in codes  # E1004


# ---------- Test 2: Over-Scoped Agent (E1006) ----------

def test_adversarial_over_scoped_agent() -> None:
    """9 core tasks — exceeds the 8-task maximum.

    Pydantic enforces max_length=8 at schema level, so 9 tasks
    are rejected before reaching validate_profiler_doc(). This test
    confirms the Pydantic guard fires correctly.
    """
    payload = _valid_base()
    payload["mission_contract"]["core_tasks"] = [
        {"task": f"Task {i}", "method": f"Execute step {i} deterministically"}
        for i in range(1, 10)
    ]

    import pytest
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        AgentSpecProfilerDoc.model_validate(payload)


# ---------- Test 3: Authority Hole (E1010) ----------

def test_adversarial_authority_hole() -> None:
    """Authority boundary missing may_not — creates a permission hole."""
    payload = _valid_base()
    payload["mission_contract"]["authority_boundary"]["may_not"] = []

    # Pydantic blocks empty may_not, so we need to bypass via construct
    # The validation in validate_profiler_doc should catch it if Pydantic doesn't.
    # Since Pydantic enforces min_length=1, we test with a dummy item
    # and let the heuristic validator check the semantic emptiness.
    # Actually, let's test the Pydantic guard directly.
    import pytest
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        AgentSpecProfilerDoc.model_validate(payload)


# ---------- Test 4: Valid Restaurant Blogger (golden path) ----------

def test_adversarial_valid_restaurant_blogger() -> None:
    """Golden path — valid spec accepted, complete spec.md generated."""
    payload = _valid_base()

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)
    assert rejection is None

    spec_md = generate_complete_spec_md(doc)
    assert "## Intent" in spec_md
    assert "## Context" in spec_md
    assert "## Tasks" in spec_md
    assert "## Specification" in spec_md
    assert "## Agent Profile" in spec_md
    assert "```yaml" in spec_md
    assert "profiler_hash:" in spec_md


# ---------- Test 5: Non-Actionable Methods (E1008) ----------

def test_adversarial_non_actionable_methods() -> None:
    """Methods are platitudes, not operational steps."""
    payload = _valid_base()
    payload["mission_contract"]["core_tasks"] = [
        {"task": "Analyze data", "method": "Apply best practices"},
        {"task": "Generate report", "method": "Leverage AI to produce output"},
    ]

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.NON_ACTIONABLE_METHOD in codes  # E1008


# ---------- Test 6: Excessive Tasks ----------

def test_adversarial_excessive_tasks() -> None:
    """Too many core tasks (10 tasks)."""
    payload = _valid_base()
    payload["mission_contract"]["core_tasks"] = [
        {"task": f"Operation {i}", "method": f"Apply rule set {i}"}
        for i in range(1, 11)
    ]

    # Pydantic max_length=8 should block at schema level
    import pytest
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        AgentSpecProfilerDoc.model_validate(payload)


# ---------- Test 7: Generic Language ----------

def test_adversarial_generic_language() -> None:
    """Objective function uses generic language."""
    payload = _valid_base()
    payload["mission_contract"]["objective_function"]["transformation_summary"] = (
        "Do tasks for anything the user needs"
    )

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.GENERIC_OBJECTIVE_FUNCTION in codes  # E1001


# ---------- Test 8: Contradiction Spec (E1017) ----------

def test_adversarial_contradiction_spec() -> None:
    """Exclusions contradict core_tasks — scope contradiction."""
    payload = _valid_base()
    payload["mission_contract"]["explicit_exclusions"] = [
        "Do not write draft prose",
        "Do not fabricate menu items",
    ]
    payload["mission_contract"]["core_tasks"] = [
        {
            "task": "Write draft prose",
            "method": "Generate section-by-section narrative",
        },
    ]

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.SCOPE_CONTRADICTION in codes  # E1017


# ---------- Test 9: Unverifiable Success Metric (W2002) ----------

def test_adversarial_unverifiable_success_metric() -> None:
    """Success metric requires external API access agent doesn't have."""
    payload = _valid_base()
    payload["mission_contract"]["success_metric"] = (
        "Achieve 95% accuracy verified via external API call within 30 minutes"
    )
    # Agent has no external/API access in authority_boundary.may
    payload["mission_contract"]["authority_boundary"]["may"] = [
        "Read local files",
        "Summarize provided notes",
    ]

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.SUCCESS_METRIC_NOT_LOCALLY_VERIFIABLE in codes  # W2002
    # Verify it's a warning, not an error
    w2002_errors = [e for e in rejection.errors if e.code == ProfilerErrorCode.SUCCESS_METRIC_NOT_LOCALLY_VERIFIABLE]
    assert all(e.severity == "warning" for e in w2002_errors)


# ---------- Test 10: Output Contract Mismatch (E1018) ----------

def test_adversarial_output_contract_mismatch() -> None:
    """JSON format type with markdown-specific validation rules."""
    payload = _valid_base()
    payload["mission_contract"]["output_contract"] = {
        "format_type": "json",
        "required_sections": [],
        "required_metadata": ["version"],
        "validation_rules": [
            "Must contain ## Summary markdown heading",
            "Must pass schema check",
        ],
    }

    doc = AgentSpecProfilerDoc.model_validate(payload)
    rejection = validate_profiler_doc(doc)

    assert rejection is not None
    codes = {e.code for e in rejection.errors}
    assert ProfilerErrorCode.OUTPUT_CONTRACT_INCOHERENT in codes  # E1018
