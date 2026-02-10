"""
Validation Engine

Validates IDSE pipeline artifacts for constitutional compliance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import re

from .constitution_rules import REQUIRED_SECTIONS


class ValidationEngine:
    """Validates IDSE artifacts against constitutional rules."""

    IMPLEMENTATION_PLACEHOLDERS = [
        "{{ project_name }}",
        "{{ session_id }}",
        "{{ stack }}",
        "{{ timestamp }}",
        "[Describe the architecture of what was implemented]",
        "[Summary of implementation work]",
        "[Test results, coverage, linting]",
        "[Any changes from the original plan, with justification]",
        "ComponentName",
        "NewComponentName",
        "PrimitiveA",
        "[List files that don't map to tracked components]",
    ]

    def validate_project(
        self,
        project_name: Optional[str] = None,
        backend_override: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Validate an IDSE project's pipeline artifacts.

        Args:
            project_name: Optional project name (auto-detects if None)

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "checks": List[str],
                "errors": List[str],
                "warnings": List[str]
            }
        """
        from .project_workspace import ProjectWorkspace
        from .session_graph import SessionGraph
        from .stage_state_model import StageStateModel
        from .artifact_config import ArtifactConfig
        from .artifact_database import ArtifactDatabase
        from .design_store_sqlite import DesignStoreSQLite

        manager = ProjectWorkspace()
        if project_name:
            project_path = manager.projects_root / project_name
            if not project_path.exists():
                return {
                    "valid": False,
                    "checks": [],
                    "errors": [f"Project '{project_name}' not found at {project_path}"],
                    "warnings": [],
                }
        else:
            project_path = manager.get_current_project()
            if not project_path:
                return {
                    "valid": False,
                    "checks": [],
                    "errors": ["No IDSE project found. Run 'idse init' first or use --project."],
                    "warnings": [],
                }

        session_id = session_id or SessionGraph(project_path).get_current_session()
        session_path = project_path / "sessions" / session_id
        project_name = project_path.name

        config = ArtifactConfig(backend_override=backend_override)
        backend = config.get_storage_backend()
        use_db = backend == "sqlite"
        db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False) if use_db else None

        checks: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        artifacts = ["intent.md", "context.md", "spec.md", "plan.md", "tasks.md", "implementation.md", "feedback.md"]
        artifact_stage_map = {
            "intent.md": "intent",
            "context.md": "context",
            "spec.md": "spec",
            "plan.md": "plan",
            "tasks.md": "tasks",
            "implementation.md": "implementation",
            "feedback.md": "feedback",
        }

        for artifact in artifacts:
            if use_db and db:
                stage = artifact_stage_map[artifact]
                try:
                    db.load_artifact(project_name, session_id, stage)
                    checks.append(f"{artifact} exists")
                except FileNotFoundError:
                    errors.append(f"{artifact} is missing")
            else:
                artifact_path = self._get_artifact_path(session_path, artifact)
                if artifact_path.exists():
                    checks.append(f"{artifact} exists")
                else:
                    errors.append(f"{artifact} is missing")

        for artifact in artifacts:
            content = None
            if use_db and db:
                stage = artifact_stage_map[artifact]
                try:
                    content = db.load_artifact(project_name, session_id, stage).content
                except FileNotFoundError:
                    content = None
            else:
                artifact_path = self._get_artifact_path(session_path, artifact)
                if artifact_path.exists():
                    content = artifact_path.read_text()

            if content is not None:
                scan_text = self._strip_code(content)
                if "[REQUIRES INPUT]" in scan_text:
                    errors.append(f"{artifact} contains [REQUIRES INPUT] markers")
                else:
                    checks.append(f"{artifact} has no [REQUIRES INPUT] markers")

        # Additional enforcement for implementation artifacts:
        # block unresolved scaffolds and require a structured impact section.
        implementation_content = None
        if use_db and db:
            try:
                implementation_content = db.load_artifact(project_name, session_id, "implementation").content
            except FileNotFoundError:
                implementation_content = None
        else:
            impl_path = self._get_artifact_path(session_path, "implementation.md")
            if impl_path.exists():
                implementation_content = impl_path.read_text()

        if implementation_content is not None:
            if "## Component Impact Report" not in implementation_content:
                errors.append("implementation.md missing '## Component Impact Report' section")
            else:
                checks.append("implementation.md has section: Component Impact Report")

            for marker in self.IMPLEMENTATION_PLACEHOLDERS:
                if marker in implementation_content:
                    errors.append(f"implementation.md contains placeholder content: {marker}")

            component_bullet = re.search(r"^\s*-\s*\*\*[^*]+\*\*", implementation_content, re.MULTILINE)
            if not component_bullet:
                errors.append("implementation.md has no component entries in Component Impact Report")
            else:
                checks.append("implementation.md has component entries")

        for artifact, required_sections in REQUIRED_SECTIONS.items():
            content = None
            if use_db and db:
                stage = artifact_stage_map.get(artifact)
                if stage:
                    try:
                        content = db.load_artifact(project_name, session_id, stage).content
                    except FileNotFoundError:
                        content = None
            else:
                artifact_path = self._get_artifact_path(session_path, artifact)
                if artifact_path.exists():
                    content = artifact_path.read_text()

            if content is not None:
                for section in required_sections:
                    pattern = rf"##?\s+.*{re.escape(section)}"
                    if re.search(pattern, content, re.IGNORECASE):
                        checks.append(f"{artifact} has section: {section}")
                    else:
                        warnings.append(f"{artifact} missing recommended section: {section}")

        results = {
            "valid": len(errors) == 0,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

        try:
            if use_db:
                tracker = StageStateModel(
                    store=DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False),
                    project_name=project_name,
                    session_id=session_id,
                )
            else:
                tracker = StageStateModel(project_path)
            tracker.set_validation_status("passing" if results["valid"] else "failing")
        except Exception as exc:
            warnings.append(f"Failed to persist validation status: {exc}")

        return results

    def _get_artifact_path(self, session_path: Path, artifact_name: str) -> Path:
        artifact_map = {
            "intent.md": session_path / "intents" / "intent.md",
            "context.md": session_path / "contexts" / "context.md",
            "spec.md": session_path / "specs" / "spec.md",
            "plan.md": session_path / "plans" / "plan.md",
            "tasks.md": session_path / "tasks" / "tasks.md",
            "implementation.md": session_path / "implementation" / "README.md",
            "feedback.md": session_path / "feedback" / "feedback.md",
        }

        return artifact_map.get(artifact_name, session_path / artifact_name)

    def _strip_code(self, content: str) -> str:
        """Remove fenced code blocks and inline code spans before scanning."""
        # Remove fenced code blocks
        content = re.sub(r"```[\\s\\S]*?```", "", content)
        # Remove inline code spans
        content = re.sub(r"`[^`]*`", "", content)
        return content
