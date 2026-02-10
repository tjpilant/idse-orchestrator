import os
from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.validation_engine import ValidationEngine

VALID_IMPLEMENTATION = """## Architecture
Implemented artifact validation enforcement.

## What Was Built
Added implementation guardrails.

## Validation Reports
pytest passing.

## Deviations from Plan
None.

## Component Impact Report
### Modified Components
- **ValidationEngine** (src/idse_orchestrator/validation_engine.py)
  - Parent Primitives: ValidationEngine
  - Type: Infrastructure
  - Changes: Added implementation placeholder checks
"""


def test_validation_engine_sqlite_backend(tmp_path: Path) -> None:
    cwd = Path.cwd()
    os.environ["IDSE_ARTIFACT_BACKEND"] = "sqlite"
    try:
        os.chdir(tmp_path)
        idse_root = tmp_path / ".idse"
        project = "demo"
        project_path = idse_root / "projects" / project
        session_id = "__blueprint__"
        session_path = project_path / "sessions" / session_id

        (session_path / "metadata").mkdir(parents=True, exist_ok=True)
        (project_path / "CURRENT_SESSION").write_text(session_id)

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(
            project,
            session_id,
            "intent",
            "## Problem / Opportunity\nTest\n## Stakeholders\nTest\n## Success Criteria\nTest\n",
        )
        db.save_artifact(project, session_id, "context", "## Constraints\nTest\n")
        db.save_artifact(project, session_id, "spec", "## Functional Requirements\nTest\n")
        db.save_artifact(project, session_id, "plan", "## Plan\nTest\n")
        db.save_artifact(project, session_id, "tasks", "## Phase\nTest\n")
        db.save_artifact(project, session_id, "implementation", VALID_IMPLEMENTATION)
        db.save_artifact(project, session_id, "feedback", "## Feedback\nTest\n")
        db.save_session_state(project, session_id, {"project_name": project, "session_id": session_id, "stages": {}})
        db.set_current_session(project, session_id)

        results = ValidationEngine().validate_project(project)
        assert results["valid"] is True
        assert any("intent.md exists" in check for check in results["checks"])
    finally:
        os.chdir(cwd)
        os.environ.pop("IDSE_ARTIFACT_BACKEND", None)


def test_validation_engine_rejects_placeholder_implementation(tmp_path: Path) -> None:
    cwd = Path.cwd()
    os.environ["IDSE_ARTIFACT_BACKEND"] = "sqlite"
    try:
        os.chdir(tmp_path)
        idse_root = tmp_path / ".idse"
        project = "demo"
        project_path = idse_root / "projects" / project
        session_id = "__blueprint__"
        session_path = project_path / "sessions" / session_id

        (session_path / "metadata").mkdir(parents=True, exist_ok=True)
        (project_path / "CURRENT_SESSION").write_text(session_id)

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, session_id, "intent", "## Problem / Opportunity\nx\n## Stakeholders\nx\n## Success Criteria\nx\n")
        db.save_artifact(project, session_id, "context", "## Constraints\nx\n")
        db.save_artifact(project, session_id, "spec", "## Functional Requirements\nx\n")
        db.save_artifact(project, session_id, "plan", "## Plan\nx\n")
        db.save_artifact(project, session_id, "tasks", "## Phase\nx\n")
        db.save_artifact(
            project,
            session_id,
            "implementation",
            "# Implementation: {{ project_name }}\n\n## Component Impact Report\n### Modified Components\n- **ComponentName** (source_module.py)\n  - Parent Primitives: PrimitiveA\n",
        )
        db.save_artifact(project, session_id, "feedback", "## Feedback\nx\n")
        db.save_session_state(project, session_id, {"project_name": project, "session_id": session_id, "stages": {}})
        db.set_current_session(project, session_id)

        results = ValidationEngine().validate_project(project)
        assert results["valid"] is False
        assert any("implementation.md contains placeholder content" in err for err in results["errors"])
    finally:
        os.chdir(cwd)
        os.environ.pop("IDSE_ARTIFACT_BACKEND", None)
