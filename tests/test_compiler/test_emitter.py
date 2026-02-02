from pathlib import Path
import yaml

from idse_orchestrator.compiler.emitter import emit_profile


def test_emit_profile(tmp_path: Path):
    merged = {"id": "agent-1", "name": "Agent One"}
    out_dir = tmp_path / "out"
    output = emit_profile(merged, out_dir, session_id="s1", blueprint_id="__blueprint__")

    assert output.exists()
    text = output.read_text()
    assert "Source session: s1" in text

    data = yaml.safe_load(text.split("\n", 3)[-1])
    assert data["id"] == "agent-1"
