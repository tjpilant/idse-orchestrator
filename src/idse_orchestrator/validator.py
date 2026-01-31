"""
Validator

Validates IDSE pipeline artifacts for constitutional compliance.
"""

from pathlib import Path
from typing import Dict, List, Optional
import re


class Validator:
    """Validates IDSE artifacts against constitutional rules."""

    REQUIRED_SECTIONS = {
        "intent.md": ["Purpose / Goal", "Problem / Opportunity", "Vision", "Stakeholders", "Success Criteria"],
        "context.md": ["Environment Overview", "Technical Context", "Organizational Context"],
        "spec.md": ["Purpose", "System Overview", "Functional Requirements"],
        "plan.md": ["Architectural Overview", "Core Components", "Data Flow"],
        "tasks.md": ["Phase"],
    }

    def __init__(self):
        """Initialize Validator."""
        pass

    def validate_project(self, project_name: Optional[str] = None) -> Dict:
        """
        Validate an IDSE project's pipeline artifacts.

        Args:
            project_name: Optional project name (auto-detects if None)

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "checks": List[str],  # Passed checks
                "errors": List[str],  # Failed checks
                "warnings": List[str]  # Non-blocking issues
            }
        """
        from .project_manager import ProjectManager

        manager = ProjectManager()
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

        # Get current session
        session_id = manager.get_current_session(project_path)
        session_path = project_path / "sessions" / session_id

        checks = []
        errors = []
        warnings = []

        # Check 1: All artifact files exist
        artifacts = ["intent.md", "context.md", "spec.md", "plan.md", "tasks.md", "feedback.md"]

        for artifact in artifacts:
            artifact_path = self._get_artifact_path(session_path, artifact)

            if artifact_path.exists():
                checks.append(f"{artifact} exists")
            else:
                errors.append(f"{artifact} is missing")

        # Check 2: No [REQUIRES INPUT] markers
        for artifact in artifacts:
            artifact_path = self._get_artifact_path(session_path, artifact)

            if artifact_path.exists():
                content = artifact_path.read_text()

                if "[REQUIRES INPUT]" in content:
                    errors.append(f"{artifact} contains [REQUIRES INPUT] markers")
                else:
                    checks.append(f"{artifact} has no [REQUIRES INPUT] markers")

        # Check 3: Required sections present
        for artifact, required_sections in self.REQUIRED_SECTIONS.items():
            artifact_path = self._get_artifact_path(session_path, artifact)

            if artifact_path.exists():
                content = artifact_path.read_text()

                for section in required_sections:
                    # Simple regex to find section headers
                    pattern = rf"##?\s+.*{re.escape(section)}"

                    if re.search(pattern, content, re.IGNORECASE):
                        checks.append(f"{artifact} has section: {section}")
                    else:
                        warnings.append(f"{artifact} missing recommended section: {section}")

        # Check 4: Stage sequencing (Article III)
        # TODO: Implement stage ordering validation

        # Check 5: Template compliance (Article IV)
        # TODO: Check artifacts follow template structure

        return {
            "valid": len(errors) == 0,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    def _get_artifact_path(self, session_path: Path, artifact_name: str) -> Path:
        """
        Get path to artifact file.

        Args:
            session_path: Path to session directory
            artifact_name: Name of artifact (e.g., "intent.md")

        Returns:
            Path to artifact file
        """
        artifact_map = {
            "intent.md": session_path / "intents" / "intent.md",
            "context.md": session_path / "contexts" / "context.md",
            "spec.md": session_path / "specs" / "spec.md",
            "plan.md": session_path / "plans" / "plan.md",
            "tasks.md": session_path / "tasks" / "tasks.md",
            "feedback.md": session_path / "feedback" / "feedback.md",
        }

        return artifact_map.get(artifact_name, session_path / artifact_name)
