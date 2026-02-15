from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from idse_orchestrator.cli import main


def _interactive_answers(transformation_summary: str) -> str:
    return "\n".join(
        [
            "Ticket text",
            "Action plan",
            transformation_summary,
            "95% of plans accepted within 30 minutes",
            "No production changes",
            "Classify ticket,Create plan",
            "Taxonomy classification",
            "Runbook mapping",
            "Tag tickets",
            "Deploy code",
            "Use internal data only",
            "Missing ticket fields",
            "hybrid",
            "summary,actions",
            "ticket_id",
            "Must include actions",
            "SaaS support",
            "Direct",
            "High",
            "Internal docs",
            "No speculation",
        ]
    ) + "\n"


def _valid_payload() -> dict:
    return {
        "mission_contract": {
            "objective_function": {
                "input_description": "Ticket text",
                "output_description": "Action plan",
                "transformation_summary": "Transform tickets into action plans",
            },
            "success_metric": "95% of plans accepted within 30 minutes",
            "explicit_exclusions": ["No production changes"],
            "core_tasks": [
                {"task": "Classify ticket", "method": "Taxonomy classification"},
                {"task": "Create plan", "method": "Runbook mapping"},
            ],
            "authority_boundary": {
                "may": ["Tag tickets"],
                "may_not": ["Deploy code"],
            },
            "constraints": ["Use internal data only"],
            "failure_conditions": ["Missing ticket fields"],
            "output_contract": {
                "format_type": "hybrid",
                "required_sections": ["summary", "actions"],
                "required_metadata": ["ticket_id"],
                "validation_rules": ["Must include actions"],
            },
        },
        "persona_overlay": {
            "industry_context": "SaaS support",
            "tone": "Direct",
            "detail_level": "High",
            "reference_preferences": ["Internal docs"],
            "communication_rules": ["No speculation"],
        },
    }


def test_profiler_intake_save_answers_creates_json(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        answers_path = Path("answers.json")

        result = runner.invoke(
            main,
            ["profiler", "intake", "--save-answers", str(answers_path)],
            input=_interactive_answers("Transform tickets into action plans"),
        )

        assert result.exit_code == 0, result.output
        assert answers_path.exists()

        payload = json.loads(answers_path.read_text(encoding="utf-8"))
        assert "mission_contract" in payload
        assert "persona_overlay" in payload
        assert payload["mission_contract"]["objective_function"]["input_description"] == "Ticket text"
        assert payload["mission_contract"]["output_contract"]["validation_rules"] == ["Must include actions"]


def test_profiler_intake_from_json_generates_spec_without_prompts(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        answers_path = Path("answers.json")
        spec_path = Path("agent.spec.md")
        answers_path.write_text(json.dumps(_valid_payload()), encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "profiler",
                "intake",
                "--from-json",
                str(answers_path),
                "--spec-out",
                str(spec_path),
            ],
        )

        assert result.exit_code == 0, result.output
        assert spec_path.exists()
        text = spec_path.read_text(encoding="utf-8")
        assert "## Intent" in text
        assert "## Agent Profile" in text


def test_profiler_intake_edit_retry_workflow(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        answers_path = Path("answers.json")
        spec_path = Path("agent.spec.md")

        first = runner.invoke(
            main,
            ["profiler", "intake", "--save-answers", str(answers_path)],
            input=_interactive_answers("Transform tickets and summarize trends"),
        )
        assert first.exit_code != 0
        assert answers_path.exists()
        assert "multi_objective_agent" in first.output

        edited = json.loads(answers_path.read_text(encoding="utf-8"))
        edited["mission_contract"]["objective_function"][
            "transformation_summary"
        ] = "Transform tickets into action plans"
        answers_path.write_text(json.dumps(edited), encoding="utf-8")

        second = runner.invoke(
            main,
            [
                "profiler",
                "intake",
                "--from-json",
                str(answers_path),
                "--spec-out",
                str(spec_path),
            ],
        )

        assert second.exit_code == 0, second.output
        assert spec_path.exists()
