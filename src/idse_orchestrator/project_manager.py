"""
Project Manager

Handles IDSE project initialization, directory creation, and metadata management.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import shutil


class ProjectManager:
    """Manages IDSE project lifecycle operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize ProjectManager.

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
        client_id: Optional[str] = None,
        create_agent_files: bool = True,
        is_blueprint: bool = True
    ) -> Path:
        """
        Initialize a new IDSE project with full directory structure.

        Args:
            project_name: Name of the project
            stack: Technology stack (python, node, go, etc.)
            client_id: Optional client ID from Agency Core
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
        from .template_loader import TemplateLoader

        loader = TemplateLoader()
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
        if client_id:
            with owner_file.open("a") as f:
                f.write(f"Client ID: {client_id}\n")

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
            owner=client_id or "system",
            collaborators=[],
            tags=[],
            status="draft",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        metadata.save(session_path)

        # Create CURRENT_SESSION pointer
        current_session_file = project_path / "CURRENT_SESSION"
        current_session_file.write_text(session_id)

        # Initialize session_state.json
        from .state_tracker import StateTracker

        tracker = StateTracker(project_path)
        tracker.init_state(project_name, session_id, is_blueprint=is_blueprint)

        # Create blueprint meta.md if this is a blueprint session
        if is_blueprint:
            self.create_blueprint_meta(project_path, project_name)

        # Create agent instruction files if requested
        if create_agent_files:
            self._create_agent_instructions(project_name, stack)

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
                if projects:
                    # Return first project (could be smarter with git or cwd context)
                    return projects[0]
            current = current.parent

        return None

    def get_current_session(self, project_path: Path) -> str:
        """
        Get current session ID from CURRENT_SESSION file.

        Args:
            project_path: Path to project directory

        Returns:
            Session ID string
        """
        current_session_file = project_path / "CURRENT_SESSION"
        if not current_session_file.exists():
            raise FileNotFoundError(f"No CURRENT_SESSION file in {project_path}")

        return current_session_file.read_text().strip()

    def get_project_uuid(self, project_name: str) -> Optional[str]:
        """Get cached project UUID from project metadata."""
        project_path = self.projects_root / project_name
        metadata_file = project_path / "metadata" / "project.json"

        if not metadata_file.exists():
            return None

        try:
            metadata = json.loads(metadata_file.read_text())
            return metadata.get("project_uuid")
        except (json.JSONDecodeError, KeyError):
            return None

    def set_project_uuid(self, project_name: str, project_uuid: str) -> None:
        """Cache project UUID in project metadata."""
        project_path = self.projects_root / project_name
        metadata_dir = project_path / "metadata"
        metadata_file = metadata_dir / "project.json"

        metadata_dir.mkdir(parents=True, exist_ok=True)

        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text())
            except json.JSONDecodeError:
                metadata = {}
        else:
            metadata = {}

        metadata.update({
            "project_name": project_name,
            "project_uuid": project_uuid,
            "last_synced": datetime.now().isoformat()
        })

        if "created_at" not in metadata:
            metadata["created_at"] = datetime.now().isoformat()

        metadata_file.write_text(json.dumps(metadata, indent=2))

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
            "timestamp": datetime.now().isoformat()
        }

        # Files to create
        agent_files = {
            "CLAUDE.md": self.workspace_root / "CLAUDE.md",
            "AGENTS.md": self.workspace_root / "AGENTS.md",
            ".cursorrules": self.workspace_root / ".cursorrules"
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
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        gov_dst_dir = self.idse_root / "governance"
        gov_dst_dir.mkdir(parents=True, exist_ok=True)

        # Core IDSE governance packaged with the orchestrator
        for filename in ["IDSE_CONSTITUTION.md", "IDSE_PIPELINE.md"]:
            src = gov_src_dir / filename
            dst = gov_dst_dir / filename
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        # Agency Swarm constitution (sourced from repo-level .idse/governance if present)
        agency_src = repo_root / ".idse" / "governance" / "AGENCY_SWARM_CONSTITUTION.md"
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

    def create_blueprint_meta(self, project_path: Path, project_name: str) -> None:
        """
        Create meta.md in blueprint session to track all feature sessions.

        Args:
            project_path: Path to project directory
            project_name: Name of the project
        """
        blueprint_path = project_path / "sessions" / "__blueprint__"
        meta_file = blueprint_path / "metadata" / "meta.md"

        # Don't overwrite if already exists
        if meta_file.exists():
            return

        template = f"""# {project_name} - Blueprint Session Meta

## Session Registry

This document tracks all sessions spawned from this Blueprint.

### Active Sessions
- `__blueprint__` (THIS SESSION) - Project governance and roadmap

### Feature Sessions
(To be added as sessions are created)

## Session Status Matrix

| Session ID | Type | Status | Owner | Created | Progress |
|------------|------|--------|-------|---------|----------|
| __blueprint__ | blueprint | in_progress | system | {datetime.now().date()} | 20% |

## Lineage Graph

```
__blueprint__ (root)
├── (no feature sessions yet)
```

## Governance

This Blueprint defines:
- Project-level intent and vision
- Technical architecture constraints
- Feature roadmap and dependencies
- Session creation rules

All Feature Sessions inherit from this Blueprint's context and specs.

## Feedback Loop

Feedback from Feature Sessions flows upward to inform Blueprint updates.

---
*Last updated: {datetime.now().isoformat()}*
"""

        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(template)

    def create_feature_session(
        self,
        project_path: Path,
        session_id: str,
        parent_session: str = "__blueprint__",
        description: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> Path:
        """
        Create a new feature session inheriting from parent.

        Args:
            project_path: Path to project directory
            session_id: Unique session identifier
            parent_session: Parent session ID (defaults to __blueprint__)
            description: Optional session description
            client_id: Optional client ID

        Returns:
            Path to created session directory

        Raises:
            ValueError: If session already exists or parent doesn't exist
        """
        session_path = project_path / "sessions" / session_id

        if session_path.exists():
            raise ValueError(f"Session '{session_id}' already exists at {session_path}")

        # Verify parent exists
        parent_path = project_path / "sessions" / parent_session
        if not parent_path.exists():
            raise ValueError(f"Parent session '{parent_session}' does not exist")

        # Create session directory structure (same as init_project)
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
        from .template_loader import TemplateLoader

        loader = TemplateLoader()
        artifacts = loader.load_all_templates(project_name=project_path.name, stack="python")

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
        if client_id:
            with owner_file.open("a") as f:
                f.write(f"Client ID: {client_id}\n")

        # Create session.json metadata with lineage
        from .session_metadata import SessionMetadata

        metadata = SessionMetadata(
            session_id=session_id,
            name=session_id,
            session_type="feature",
            description=description,
            is_blueprint=False,
            parent_session=parent_session,
            related_sessions=[],
            owner=client_id or "system",
            collaborators=[],
            tags=[],
            status="draft",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        metadata.save(session_path)

        # Initialize state
        from .state_tracker import StateTracker

        state_tracker = StateTracker(project_path)
        state_tracker.init_state(project_path.name, session_id, is_blueprint=False)

        return session_path

    def update_blueprint_meta(self, project_path: Path, new_session_path: Path) -> None:
        """
        Add new session to blueprint's meta.md.

        Args:
            project_path: Path to project directory
            new_session_path: Path to newly created session
        """
        from .session_metadata import SessionMetadata

        blueprint_meta = project_path / "sessions" / "__blueprint__" / "metadata" / "meta.md"

        # Create meta.md if it doesn't exist
        if not blueprint_meta.exists():
            self.create_blueprint_meta(project_path, project_path.name)

        # Load session metadata
        session_metadata = SessionMetadata.load(new_session_path)

        # Prepare new entries
        new_session_entry = f"- `{session_metadata.session_id}` - {session_metadata.description or 'Feature session'}\n"

        new_row = f"| {session_metadata.session_id} | {session_metadata.session_type} | {session_metadata.status} | {session_metadata.owner} | {session_metadata.created_at[:10]} | 0% |\n"

        # Update meta.md
        content = blueprint_meta.read_text()

        # Add to Feature Sessions list
        updated = content.replace(
            "(To be added as sessions are created)",
            new_session_entry + "(To be added as sessions are created)"
        )

        # Add to status matrix (before the separator line)
        updated = updated.replace(
            "---\n*Last updated:",
            f"{new_row}\n---\n*Last updated: {datetime.now().isoformat()}\n*Previous update:"
        )

        blueprint_meta.write_text(updated)

    def rebuild_blueprint_meta(self, project_path: Path) -> None:
        """
        Rebuild the blueprint meta.md from all session metadata.

        Ensures the blueprint registry stays accurate even if sessions were added/removed manually.
        """
        from .session_metadata import SessionMetadata

        blueprint_path = project_path / "sessions" / "__blueprint__"
        meta_file = blueprint_path / "metadata" / "meta.md"
        sessions_dir = project_path / "sessions"

        # Gather session metadata
        sessions = []
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            try:
                meta = SessionMetadata.load(session_dir)
                sessions.append(meta)
            except FileNotFoundError:
                continue

        # Sort with blueprint first, then by created_at descending
        sessions.sort(key=lambda m: (0 if m.session_id == "__blueprint__" else 1, m.created_at), reverse=False)

        # Build registry list and status matrix rows
        registry_lines = []
        matrix_rows = []
        for meta in sessions:
            if meta.session_id == "__blueprint__":
                registry_lines.append(f"- `__blueprint__` (THIS SESSION) - Project governance and roadmap")
            else:
                registry_lines.append(f"- `{meta.session_id}` - {meta.description or 'Feature session'}")
            matrix_rows.append(
                f"| {meta.session_id} | {meta.session_type} | {meta.status} | {meta.owner} | {meta.created_at[:10]} | 0% |"
            )

        registry_section = "\n".join(registry_lines) if registry_lines else "(To be added as sessions are created)"
        matrix_section = "\n".join(["| Session ID | Type | Status | Owner | Created | Progress |", "|------------|------|--------|-------|---------|----------|"] + matrix_rows)

        content = f"""# {project_path.name} - Blueprint Session Meta

## Session Registry

This document tracks all sessions spawned from this Blueprint.

### Active Sessions
{registry_section}

## Session Status Matrix

{matrix_section}

## Lineage Graph

```
__blueprint__ (root)
```

## Governance

This Blueprint defines:
- Project-level intent and vision
- Technical architecture constraints
- Feature roadmap and dependencies
- Session creation rules

All Feature Sessions inherit from this Blueprint's context and specs.

## Feedback Loop

Feedback from Feature Sessions flows upward to inform Blueprint updates.

---
*Last updated: {datetime.now().isoformat()}*
"""
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(content)
