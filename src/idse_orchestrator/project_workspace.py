"""
Project Workspace

Handles IDSE project initialization and workspace-level resources.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import shutil


class ProjectWorkspace:
    """Manages IDSE project lifecycle operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize ProjectWorkspace.

        Args:
            workspace_root: Root directory for .idse/ folder. Defaults to current directory.
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.idse_root = self.workspace_root / ".idse"
        self.projects_root = self.idse_root / "projects"

    def init_project(
        self,
        project_name: str,
        stack: str,
        owner: Optional[str] = None,
        create_agent_files: bool = True,
        is_blueprint: bool = True,
    ) -> Path:
        """
        Initialize a new IDSE project with full directory structure.

        Args:
            project_name: Name of the project
            stack: Technology stack (python, node, go, etc.)
            owner: Optional owner identifier
            create_agent_files: If True, creates CLAUDE.md, AGENTS.md, .cursorrules in repo root
            is_blueprint: If True, creates a blueprint session; otherwise creates a feature session

        Returns:
            Path to created project directory

        Raises:
            ValueError: If project already exists
        """
        project_path = self.projects_root / project_name

        if project_path.exists():
            raise ValueError(f"Project '{project_name}' already exists at {project_path}")

        # Ensure governance/docs are present in workspace-level .idse
        self._ensure_governance_files()
        self._install_reference_docs()
        self._cleanup_nested_idse(project_path)

        # Create project structure
        session_id = "__blueprint__"
        session_path = project_path / "sessions" / session_id

        # Create all directories
        dirs_to_create = [
            session_path / "intents",
            session_path / "contexts",
            session_path / "specs",
            session_path / "plans",
            session_path / "tasks",
            session_path / "implementation",
            session_path / "feedback",
            session_path / "metadata",
        ]

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Load and populate templates
        from .pipeline_artifacts import PipelineArtifacts

        loader = PipelineArtifacts()
        artifacts = loader.load_all_templates(project_name=project_name, stack=stack)

        # Write artifacts
        artifact_map = {
            "intent.md": session_path / "intents" / "intent.md",
            "context.md": session_path / "contexts" / "context.md",
            "spec.md": session_path / "specs" / "spec.md",
            "plan.md": session_path / "plans" / "plan.md",
            "tasks.md": session_path / "tasks" / "tasks.md",
            "feedback.md": session_path / "feedback" / "feedback.md",
            "implementation_readme.md": session_path / "implementation" / "README.md",
        }

        for template_name, file_path in artifact_map.items():
            if template_name in artifacts:
                file_path.write_text(artifacts[template_name])

        # Create .owner metadata file (for backward compatibility)
        owner_file = session_path / "metadata" / ".owner"
        owner_file.write_text(f"Created: {datetime.now().isoformat()}\n")
        if owner:
            with owner_file.open("a") as f:
                f.write(f"Owner: {owner}\n")

        # Create session.json metadata
        from .session_metadata import SessionMetadata

        metadata = SessionMetadata(
            session_id=session_id,
            name=project_name if is_blueprint else session_id,
            session_type="blueprint" if is_blueprint else "feature",
            description=None,
            is_blueprint=is_blueprint,
            parent_session=None if is_blueprint else "__blueprint__",
            related_sessions=[],
            owner=owner or "system",
            collaborators=[],
            tags=[],
            status="draft",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        metadata.save(session_path)

        # Create CURRENT_SESSION pointer
        from .session_graph import SessionGraph

        SessionGraph(project_path).set_current_session(session_id)

        # Initialize session_state.json
        from .stage_state_model import StageStateModel

        tracker = StageStateModel(project_path, session_id=session_id)
        tracker.init_state(project_name, session_id, is_blueprint=is_blueprint)

        # Create blueprint meta.md if this is a blueprint session
        if is_blueprint:
            SessionGraph(project_path).create_blueprint_meta(project_path, project_name)

        # Create agent instruction files if requested
        if create_agent_files:
            self._create_agent_instructions(project_name, stack)

        # If sqlite backend configured, seed database and regenerate views
        try:
            from .artifact_config import ArtifactConfig

            config = ArtifactConfig()
            if config.get_backend() == "sqlite":
                from .artifact_database import ArtifactDatabase
                from .design_store import DesignStoreFilesystem
                from .file_view_generator import FileViewGenerator

                db = ArtifactDatabase(idse_root=self.idse_root)
                db.ensure_project(project_name, stack=stack, owner=owner)
                db.ensure_session(
                    project_name,
                    session_id,
                    name=metadata.name,
                    session_type=metadata.session_type,
                    description=metadata.description,
                    is_blueprint=metadata.is_blueprint,
                    parent_session=metadata.parent_session,
                    status=metadata.status,
                )
                db.save_session_extras(
                    project_name,
                    session_id,
                    collaborators=[c.to_dict() for c in metadata.collaborators],
                    tags=metadata.tags,
                )

                stage_paths = {
                    stage: session_path / folder / filename
                    for stage, (folder, filename) in DesignStoreFilesystem.STAGE_PATHS.items()
                }
                for stage, path in stage_paths.items():
                    if path.exists():
                        db.save_artifact(project_name, session_id, stage, path.read_text())

                tracker = StageStateModel(project_path)
                db.save_session_state(project_name, session_id, tracker.get_status(project_name))

                generator = FileViewGenerator(idse_root=self.idse_root)
                generator.generate_session(project_name, session_id)
        except Exception:
            # SQLite seeding is best-effort; filesystem remains authoritative unless configured.
            pass

        return project_path

    def _cleanup_nested_idse(self, project_path: Path) -> None:
        """
        Guardrail: ensure no nested .idse folder lives inside a project.

        Governance/docs belong at workspace .idse/, not under projects/<name>/.idse.
        If found, remove it to avoid duplicate governance copies.
        """
        nested = project_path / ".idse"
        if nested.exists():
            shutil.rmtree(nested, ignore_errors=True)

    def get_current_project(self) -> Optional[Path]:
        """
        Detect current project from workspace.

        Returns:
            Path to current project, or None if not in an IDSE project
        """
        # Look for .idse directory in current path hierarchy
        current = Path.cwd()

        while current != current.parent:
            idse_path = current / ".idse"
            if idse_path.exists():
                # Update workspace_root to match where .idse was found
                self.workspace_root = current
                self.idse_root = idse_path
                self.projects_root = idse_path / "projects"

                # Find which project we're in by checking subdirectories
                projects = [p for p in self.projects_root.iterdir() if p.is_dir()]
                if not projects:
                    return None

                if len(projects) == 1:
                    return projects[0]

                current_marker = self.projects_root / "CURRENT_PROJECT"
                if current_marker.exists():
                    name = current_marker.read_text().strip()
                    candidate = self.projects_root / name
                    if candidate.exists():
                        return candidate

                return projects[0]
            current = current.parent

        return None

    def _create_agent_instructions(self, project_name: str, stack: str) -> None:
        """
        Create agent instruction files in the workspace root.

        Args:
            project_name: Name of the project
            stack: Technology stack

        Creates:
            - CLAUDE.md: Instructions for Claude Code
            - AGENTS.md: Generic instructions for all AI agents
            - .cursorrules: Rules for Cursor IDE
        """
        from datetime import datetime

        # Get template directory
        template_dir = Path(__file__).parent / "templates" / "agent_instructions"

        # Substitution context
        context = {
            "project_name": project_name,
            "stack": stack,
            "timestamp": datetime.now().isoformat(),
        }

        # Files to create
        agent_files = {
            "CLAUDE.md": self.workspace_root / "CLAUDE.md",
            "AGENTS.md": self.workspace_root / "AGENTS.md",
            ".cursorrules": self.workspace_root / ".cursorrules",
        }

        for template_name, output_path in agent_files.items():
            template_path = template_dir / template_name

            if not template_path.exists():
                print(f"Warning: Template {template_name} not found, skipping")
                continue

            # Read template
            template_content = template_path.read_text()

            # Substitute variables
            content = template_content.format(**context)

            # Write to workspace root (don't overwrite if exists)
            if output_path.exists():
                print(f"  ℹ️  {template_name} already exists, skipping")
            else:
                output_path.write_text(content)
                print(f"  ✅ Created {template_name}")

    def _ensure_governance_files(self) -> None:
        """Copy governance files into workspace .idse if missing."""
        gov_src_dir = Path(__file__).parent / "governance"
        gov_dst_dir = self.idse_root / "governance"
        gov_dst_dir.mkdir(parents=True, exist_ok=True)

        # Core IDSE governance packaged with the orchestrator
        for filename in ["IDSE_CONSTITUTION.md", "IDSE_PIPELINE.md"]:
            src = gov_src_dir / filename
            dst = gov_dst_dir / filename
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        # Agency Swarm constitution (packaged with orchestrator if present)
        agency_src = gov_src_dir / "AGENCY_SWARM_CONSTITUTION.md"
        agency_dst = gov_dst_dir / "AGENCY_SWARM_CONSTITUTION.md"
        if agency_src.exists() and not agency_dst.exists():
            shutil.copy2(agency_src, agency_dst)

    def _install_reference_docs(self) -> None:
        """Install bundled docs/templates into workspace .idse if missing."""
        try:
            from .docs_installer import install_docs

            install_docs(self.workspace_root, force=False)
        except Exception as doc_err:
            print(f"Warning: Failed to install docs/templates: {doc_err}")
