from __future__ import annotations

from pathlib import Path
from typing import Optional

from .loader import SessionLoader, resolve_project_root
from .parser import parse_agent_profile
from .merger import merge_profiles
from .emitter import emit_profile, render_profile


def compile_agent_spec(
    project: Optional[str],
    session_id: str,
    blueprint_id: str = "__blueprint__",
    out_dir: Optional[Path] = None,
    dry_run: bool = False,
    backend: Optional[str] = None,
):
    project_root = resolve_project_root(project)
    loader = SessionLoader(
        project_root,
        project_name=project or project_root.name,
        backend=backend,
    )

    blueprint_md = loader.load_spec(blueprint_id)
    feature_md = loader.load_spec(session_id)

    blueprint_profile = parse_agent_profile(blueprint_md)
    feature_profile = parse_agent_profile(feature_md)

    merged = merge_profiles(blueprint_profile, feature_profile)

    # Attach explicit provenance for the compiled feature profile.
    merged["source_session"] = session_id
    merged["source_blueprint"] = blueprint_id

    if dry_run:
        return render_profile(merged)

    output_dir = out_dir or (project_root / "build" / "agents")
    return emit_profile(merged, output_dir, session_id, blueprint_id)
