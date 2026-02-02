"""
Session Graph

Handles session creation, lineage, and blueprint metadata.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional


class SessionGraph:
    def __init__(self, project_path: Path):
        self.project_path = project_path

    def get_current_session(self) -> str:
        current_session_file = self.project_path / "CURRENT_SESSION"
        if not current_session_file.exists():
            raise FileNotFoundError(f"No CURRENT_SESSION file in {self.project_path}")
        return current_session_file.read_text().strip()

    def set_current_session(self, session_id: str) -> None:
        current_session_file = self.project_path / "CURRENT_SESSION"
        current_session_file.write_text(session_id)

    def create_blueprint_meta(self, project_path: Path, project_name: str) -> None:
        blueprint_path = project_path / "sessions" / "__blueprint__"
        meta_file = blueprint_path / "metadata" / "meta.md"

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
        session_id: str,
        parent_session: str = "__blueprint__",
        description: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> Path:
        session_path = self.project_path / "sessions" / session_id

        if session_path.exists():
            raise ValueError(f"Session '{session_id}' already exists at {session_path}")

        # Verify parent exists
        parent_path = self.project_path / "sessions" / parent_session
        if not parent_path.exists():
            raise ValueError(f"Parent session '{parent_session}' does not exist")

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

        from .pipeline_artifacts import PipelineArtifacts

        loader = PipelineArtifacts()
        artifacts = loader.load_all_templates(project_name=self.project_path.name, stack="python")

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

        owner_file = session_path / "metadata" / ".owner"
        owner_file.write_text(f"Created: {datetime.now().isoformat()}\n")
        if owner:
            with owner_file.open("a") as f:
                f.write(f"Owner: {owner}\n")

        from .session_metadata import SessionMetadata

        metadata = SessionMetadata(
            session_id=session_id,
            name=session_id,
            session_type="feature",
            description=description,
            is_blueprint=False,
            parent_session=parent_session,
            related_sessions=[],
            owner=owner or "system",
            collaborators=[],
            tags=[],
            status="draft",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        metadata.save(session_path)

        from .stage_state_model import StageStateModel

        state_tracker = StageStateModel(self.project_path)
        state_tracker.init_state(self.project_path.name, session_id, is_blueprint=False)

        return session_path

    def update_blueprint_meta(self, project_path: Path, new_session_path: Path) -> None:
        from .session_metadata import SessionMetadata

        blueprint_meta = project_path / "sessions" / "__blueprint__" / "metadata" / "meta.md"

        if not blueprint_meta.exists():
            self.create_blueprint_meta(project_path, project_path.name)

        session_metadata = SessionMetadata.load(new_session_path)

        new_session_entry = f"- `{session_metadata.session_id}` - {session_metadata.description or 'Feature session'}\n"
        new_row = (
            f"| {session_metadata.session_id} | {session_metadata.session_type} |"
            f" {session_metadata.status} | {session_metadata.owner} |"
            f" {session_metadata.created_at[:10]} | 0% |\n"
        )

        content = blueprint_meta.read_text()

        updated = content.replace(
            "(To be added as sessions are created)",
            new_session_entry + "(To be added as sessions are created)",
        )

        updated = updated.replace(
            "---\n*Last updated:",
            f"{new_row}\n---\n*Last updated: {datetime.now().isoformat()}\n*Previous update:",
        )

        blueprint_meta.write_text(updated)

    def rebuild_blueprint_meta(self, project_path: Path) -> None:
        from .session_metadata import SessionMetadata

        blueprint_path = project_path / "sessions" / "__blueprint__"
        meta_file = blueprint_path / "metadata" / "meta.md"
        sessions_dir = project_path / "sessions"

        sessions = []
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            try:
                meta = SessionMetadata.load(session_dir)
                sessions.append(meta)
            except FileNotFoundError:
                continue

        sessions.sort(key=lambda m: (0 if m.session_id == "__blueprint__" else 1, m.created_at), reverse=False)

        registry_lines = []
        matrix_rows = []
        for meta in sessions:
            if meta.session_id == "__blueprint__":
                registry_lines.append("- `__blueprint__` (THIS SESSION) - Project governance and roadmap")
            else:
                registry_lines.append(f"- `{meta.session_id}` - {meta.description or 'Feature session'}")
            matrix_rows.append(
                f"| {meta.session_id} | {meta.session_type} | {meta.status} | {meta.owner} | {meta.created_at[:10]} | 0% |"
            )

        registry_section = "\n".join(registry_lines) if registry_lines else "(To be added as sessions are created)"
        matrix_section = "\n".join([
            "| Session ID | Type | Status | Owner | Created | Progress |",
            "|------------|------|--------|-------|---------|----------|",
        ] + matrix_rows)

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
