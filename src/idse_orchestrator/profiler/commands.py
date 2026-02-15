from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .cli import (
    collect_profiler_answers_interactive,
    load_profiler_answers_from_json,
    run_profiler_intake,
    save_profiler_answers_to_json,
)
from .generate_spec_document import generate_complete_spec_md
from .models import ProfilerRejection
from .schema import export_profiler_json_schema


@click.group()
def profiler() -> None:
    """Profiler intake and schema tools."""


@profiler.command("intake")
@click.option("--from-json", "from_json", type=click.Path(exists=True, path_type=Path), help="Load intake answers from JSON and skip prompts.")
@click.option("--save-answers", type=click.Path(path_type=Path), help="Save collected answers to JSON before validation.")
@click.option("--out", type=click.Path(path_type=Path), help="Write accepted mapped profile JSON to path.")
@click.option("--spec-out", type=click.Path(path_type=Path), help="Write generated spec.md to path.")
def profiler_intake_cmd(
    from_json: Optional[Path],
    save_answers: Optional[Path],
    out: Optional[Path],
    spec_out: Optional[Path],
) -> None:
    """Run Agent Spec Profiler intake (intake -> validation -> generation)."""
    try:
        if from_json:
            payload = load_profiler_answers_from_json(from_json)
        else:
            payload = collect_profiler_answers_interactive()
            if save_answers:
                save_profiler_answers_to_json(save_answers, payload)
                click.echo(f"✅ Saved profiler answers: {save_answers}")

        result = run_profiler_intake(payload)

        if isinstance(result, ProfilerRejection):
            click.echo("❌ Profiler rejected input", err=True)
            click.echo(
                json.dumps(
                    {
                        "errors": [error.model_dump() for error in result.errors],
                        "next_questions": result.next_questions,
                    },
                    indent=2,
                ),
                err=True,
            )
            raise click.ClickException("Profiler validation failed")

        mapped = result.mapped_agent_profile_spec

        if spec_out:
            spec_md = generate_complete_spec_md(result.doc)
            spec_out.parent.mkdir(parents=True, exist_ok=True)
            spec_out.write_text(spec_md)
            click.echo(f"✅ Wrote generated spec.md: {spec_out}")

        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(mapped, indent=2, sort_keys=True) + "\n")
            click.echo(f"✅ Wrote mapped profile JSON: {out}")

        if not out and not spec_out:
            click.echo(json.dumps(mapped, indent=2, sort_keys=True))
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@profiler.command("export-schema")
@click.option("--out", type=click.Path(path_type=Path), required=True, help="Output schema file path.")
def profiler_export_schema_cmd(out: Path) -> None:
    """Export AgentSpecProfilerDoc JSON Schema."""
    schema = export_profiler_json_schema()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    click.echo(f"✅ Wrote profiler schema: {out}")
