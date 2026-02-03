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

    def validate_project(self, project_name: Optional[str] = None) -> Dict:
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

        session_id = SessionGraph(project_path).get_current_session()
        session_path = project_path / "sessions" / session_id

        checks: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        artifacts = ["intent.md", "context.md", "spec.md", "plan.md", "tasks.md", "feedback.md"]

        for artifact in artifacts:
            artifact_path = self._get_artifact_path(session_path, artifact)
            if artifact_path.exists():
                checks.append(f"{artifact} exists")
            else:
                errors.append(f"{artifact} is missing")

        for artifact in artifacts:
            artifact_path = self._get_artifact_path(session_path, artifact)
            if artifact_path.exists():
                content = artifact_path.read_text()
                scan_text = self._strip_code(content)
                if "[REQUIRES INPUT]" in scan_text:
                    errors.append(f"{artifact} contains [REQUIRES INPUT] markers")
                else:
                    checks.append(f"{artifact} has no [REQUIRES INPUT] markers")

        for artifact, required_sections in REQUIRED_SECTIONS.items():
            artifact_path = self._get_artifact_path(session_path, artifact)
            if artifact_path.exists():
                content = artifact_path.read_text()
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

        tracker = StageStateModel(project_path)
        tracker.set_validation_status("passing" if results["valid"] else "failing")

        return results

    def _get_artifact_path(self, session_path: Path, artifact_name: str) -> Path:
        artifact_map = {
            "intent.md": session_path / "intents" / "intent.md",
            "context.md": session_path / "contexts" / "context.md",
            "spec.md": session_path / "specs" / "spec.md",
            "plan.md": session_path / "plans" / "plan.md",
            "tasks.md": session_path / "tasks" / "tasks.md",
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
