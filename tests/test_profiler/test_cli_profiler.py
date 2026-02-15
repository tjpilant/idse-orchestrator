from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from idse_orchestrator.cli import main


def test_profiler_intake_valid_answers_emit_mapped_json(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        out_path = Path("mapped.json")
        answers = "\n".join(
            [
                "Ticket text",
                "Action plan",
                "Transform tickets into action plans",
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

        result = runner.invoke(main, ["profiler", "intake", "--out", str(out_path)], input=answers)

        assert result.exit_code == 0
        payload = json.loads(out_path.read_text())
        assert payload["success_criteria"] == "95% of plans accepted within 30 minutes"
        assert payload["capabilities"][0]["task"] == "Classify ticket"


def test_profiler_intake_invalid_answers_show_rejection(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        answers = "\n".join(
            [
                "Ticket text",
                "Action plan",
                "Be helpful with anything",
                "Make users happy",
                "No production changes",
                "Classify ticket",
                "Taxonomy classification",
                "Tag tickets",
                "Deploy code",
                "Use internal data only",
                "Missing ticket fields",
                "json",
                "",
                "ticket_id",
                "Must include actions",
                "",
                "",
                "",
                "",
                "",
            ]
        ) + "\n"

        result = runner.invoke(main, ["profiler", "intake"], input=answers)

        assert result.exit_code != 0
        assert "Profiler rejected input" in result.output
        assert "generic_objective_function" in result.output


def test_profiler_export_schema_writes_file(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        out = Path("schema.json")
        result = runner.invoke(main, ["profiler", "export-schema", "--out", str(out)])

        assert result.exit_code == 0
        schema = json.loads(out.read_text())
        assert schema["title"] == "AgentSpecProfilerDoc"
        assert "mission_contract" in schema["properties"]


def test_profiler_intake_generates_spec_md(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        spec_path = Path("spec.md")
        answers = "\n".join(
            [
                "Ticket text",
                "Action plan",
                "Transform tickets into action plans",
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

        result = runner.invoke(
            main, ["profiler", "intake", "--spec-out", str(spec_path)], input=answers
        )

        assert result.exit_code == 0, result.output
        spec_md = spec_path.read_text()
        assert "## Intent" in spec_md
        assert "## Context" in spec_md
        assert "## Tasks" in spec_md
        assert "## Specification" in spec_md
        assert "## Agent Profile" in spec_md
        assert "```yaml" in spec_md
