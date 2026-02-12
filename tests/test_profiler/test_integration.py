from __future__ import annotations

from pathlib import Path

import yaml

from idse_orchestrator.compiler import compile_agent_spec
from idse_orchestrator.profiler.cli import run_profiler_intake
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
