from __future__ import annotations

from pathlib import Path

import yaml

from idse_orchestrator.compiler import compile_agent_spec
from idse_orchestrator.profiler.cli import run_profiler_intake
from idse_orchestrator.profiler.generate_spec_document import generate_complete_spec_md
from idse_orchestrator.profiler.models import ProfilerAcceptance


def _write_spec(path: Path, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Specification\n\n## Agent Profile\n\n```yaml\n"
        + yaml.safe_dump(profile, sort_keys=False)
        + "```\n"
    )


def test_profiler_to_compiler_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    payload = {
        "mission_contract": {
            "objective_function": {
                "input_description": "Issue details",
                "output_description": "Remediation plan",
                "transformation_summary": "Transform issue details into remediation plans",
            },
            "success_metric": "95% acceptance rate within 30 minutes",
            "explicit_exclusions": ["Do not execute production actions"],
            "core_tasks": [
                {
                    "task": "Classify issue",
                    "method": "Map issue to known taxonomy",
                }
            ],
            "authority_boundary": {
                "may": ["Tag and prioritize issues"],
                "may_not": ["Deploy changes"],
            },
            "constraints": ["Use only provided issue fields"],
            "failure_conditions": ["Insufficient issue details"],
            "output_contract": {
                "format_type": "json",
                "required_sections": [],
                "required_metadata": ["ticket_id"],
                "validation_rules": ["Action plan contains priority"],
            },
        },
        "persona_overlay": {
            "industry_context": "IT Operations",
            "tone": "Direct",
            "detail_level": "High",
            "reference_preferences": ["Internal runbooks"],
            "communication_rules": ["No speculative claims"],
        },
    }

    outcome = run_profiler_intake(payload)
    assert isinstance(outcome, ProfilerAcceptance)

    project = "demo"
    project_root = tmp_path / ".idse" / "projects" / project
    blueprint_spec = project_root / "sessions" / "__blueprint__" / "specs" / "spec.md"
    feature_spec = project_root / "sessions" / "feature-a" / "specs" / "spec.md"

    _write_spec(blueprint_spec, {"id": "base", "name": "Base"})

    feature_profile = {
        **outcome.mapped_agent_profile_spec,
        "id": "feature-a",
        "name": "Feature A",
    }
    _write_spec(feature_spec, feature_profile)

    rendered = compile_agent_spec(
        project=project,
        session_id="feature-a",
        blueprint_id="__blueprint__",
        backend="filesystem",
        dry_run=True,
    )
    data = yaml.safe_load(rendered)

    assert data["id"] == "feature-a"
    assert data["name"] == "Feature A"
    assert data["description"] == "Transform issue details into remediation plans"


def test_profiler_doc_generator_to_compiler_end_to_end(tmp_path: Path, monkeypatch) -> None:
    """Phase 7: profiler intake → generate_complete_spec_md → compile_agent_spec."""
    monkeypatch.chdir(tmp_path)

    payload = {
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
                    "method": "Generate section-by-section narrative with factual checks",
                },
            ],
            "authority_boundary": {
                "may": ["Summarize provided notes", "Suggest headline variants"],
                "may_not": ["Invent quotes from owners"],
            },
            "constraints": ["Cite all factual claims from provided inputs"],
            "failure_conditions": ["Missing required sections"],
            "output_contract": {
                "format_type": "narrative",
                "required_sections": ["headline", "lede", "menu-highlights", "closing"],
                "required_metadata": ["target_keyword"],
                "validation_rules": ["Word count in target range"],
            },
        },
        "persona_overlay": {
            "industry_context": "Hospitality content marketing",
            "tone": "Warm and descriptive",
            "detail_level": "High",
            "reference_preferences": [],
            "communication_rules": [],
        },
    }

    # Phase 1-2: Intake + Validation
    outcome = run_profiler_intake(payload)
    assert isinstance(outcome, ProfilerAcceptance)

    # Phase 3: Document Generation — produces a complete spec.md
    spec_md = generate_complete_spec_md(outcome.doc)
    assert "## Agent Profile" in spec_md
    assert "## Intent" in spec_md

    # Write generated spec.md as the feature session, add id/name for compiler
    project = "demo"
    project_root = tmp_path / ".idse" / "projects" / project
    blueprint_spec = project_root / "sessions" / "__blueprint__" / "specs" / "spec.md"
    feature_spec = project_root / "sessions" / "blog-writer" / "specs" / "spec.md"

    _write_spec(blueprint_spec, {"id": "base", "name": "Base"})

    # The generated spec.md from the profiler has an Agent Profile block.
    # We need to inject id and name into the YAML block for the compiler.
    # Simulate what a real user would do: write the generated spec.md with id/name added.
    from idse_orchestrator.compiler.parser import parse_agent_profile

    profile_data = parse_agent_profile(spec_md)
    profile_data["id"] = "blog-writer"
    profile_data["name"] = "Restaurant Blog Writer"
    _write_spec(feature_spec, profile_data)

    # Compile the generated spec.md through the full compiler pipeline
    rendered = compile_agent_spec(
        project=project,
        session_id="blog-writer",
        blueprint_id="__blueprint__",
        backend="filesystem",
        dry_run=True,
    )
    data = yaml.safe_load(rendered)

    assert data["id"] == "blog-writer"
    assert data["name"] == "Restaurant Blog Writer"
    assert "Transform raw restaurant notes" in data["description"]
    assert data["source_session"] == "blog-writer"
    assert data["source_blueprint"] == "__blueprint__"
