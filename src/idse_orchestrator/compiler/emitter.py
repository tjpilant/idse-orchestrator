from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import yaml

from .models import AgentProfileSpec
from .errors import ValidationError


def emit_profile(
    merged: Dict,
    out_dir: Path,
    session_id: str,
    blueprint_id: str,
) -> Path:
    """Validate and write AgentProfileSpec YAML to disk."""
    try:
        model = AgentProfileSpec(**merged)
    except Exception as exc:
        raise ValidationError(str(exc)) from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{session_id}.profile.yaml"

    header = (
        f"# Generated: {datetime.now().isoformat()}\n"
        f"# Source session: {session_id}\n"
        f"# Source blueprint: {blueprint_id}\n"
    )

    payload = model.model_dump()
    yaml_text = yaml.safe_dump(payload, sort_keys=False)

    output_path.write_text(header + yaml_text)
    return output_path


def render_profile(merged: Dict) -> str:
    """Validate and return YAML as a string (for dry-run)."""
    try:
        model = AgentProfileSpec(**merged)
    except Exception as exc:
        raise ValidationError(str(exc)) from exc

    return yaml.safe_dump(model.model_dump(), sort_keys=False)
