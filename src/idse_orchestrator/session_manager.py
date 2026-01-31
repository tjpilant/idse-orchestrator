"""
Session Manager

Provides session discovery, search, and lineage tracking capabilities.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from .session_metadata import SessionMetadata


class SessionManager:
    """
    Manages session discovery, search, and navigation.

    Provides methods to:
    - List all sessions in a project
    - Filter sessions by type, status, or tags
    - Search sessions by name/description
    - Navigate session lineage (parent/children)
    """

    def __init__(self, project_path: Path):
        """
        Initialize SessionManager.

        Args:
            project_path: Path to project directory
        """
        self.project_path = project_path
        self.sessions_dir = project_path / "sessions"

        if not self.sessions_dir.exists():
            raise FileNotFoundError(
                f"Sessions directory not found: {self.sessions_dir}\n"
                f"This may not be a valid IDSE project."
            )

    def list_sessions(
        self,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        include_legacy: bool = False
    ) -> List[SessionMetadata]:
        """
        List all sessions with optional filters.

        Args:
            session_type: Filter by type (blueprint, feature, exploratory)
            status: Filter by status (draft, in_progress, review, complete, archived)
            tag: Filter by tag
            include_legacy: Include sessions without session.json

        Returns:
            List of SessionMetadata objects, sorted by creation date (newest first)
        """
        sessions = []

        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                metadata = SessionMetadata.load(session_dir)

                # Apply filters
                if session_type and metadata.session_type != session_type:
                    continue
                if status and metadata.status != status:
                    continue
                if tag and tag not in metadata.tags:
                    continue

                sessions.append(metadata)

            except FileNotFoundError:
                # session.json doesn't exist (legacy session)
                if include_legacy:
                    # Create minimal metadata for legacy session
                    legacy_metadata = self._create_legacy_metadata(session_dir)
                    if legacy_metadata:
                        sessions.append(legacy_metadata)
                continue

        # Sort by creation date (newest first)
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def search_sessions(self, query: str) -> List[SessionMetadata]:
        """
        Search sessions by name or description.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching SessionMetadata objects
        """
        sessions = self.list_sessions()
        results = []

        query_lower = query.lower()
        for session in sessions:
            # Search in session_id, name, and description
            if (
                query_lower in session.session_id.lower()
                or query_lower in session.name.lower()
                or (session.description and query_lower in session.description.lower())
            ):
                results.append(session)

        return results

    def get_session(self, session_id: str) -> SessionMetadata:
        """
        Get metadata for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            SessionMetadata object

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_path = self.sessions_dir / session_id

        if not session_path.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found")

        return SessionMetadata.load(session_path)

    def get_session_lineage(self, session_id: str) -> Dict[str, Any]:
        """
        Get parent and child sessions for lineage tracking.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with 'session', 'parent', and 'children' keys
        """
        session_path = self.sessions_dir / session_id
        metadata = SessionMetadata.load(session_path)

        # Find parent
        parent = None
        if metadata.parent_session:
            try:
                parent_path = self.sessions_dir / metadata.parent_session
                parent = SessionMetadata.load(parent_path)
            except FileNotFoundError:
                # Parent session doesn't exist (orphaned)
                pass

        # Find children
        children = []
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir() or session_dir.name == session_id:
                continue

            try:
                child_metadata = SessionMetadata.load(session_dir)
                if child_metadata.parent_session == session_id:
                    children.append(child_metadata)
            except FileNotFoundError:
                continue

        # Find related sessions
        related = []
        for related_id in metadata.related_sessions:
            try:
                related_path = self.sessions_dir / related_id
                related_metadata = SessionMetadata.load(related_path)
                related.append(related_metadata)
            except FileNotFoundError:
                continue

        return {
            "session": metadata,
            "parent": parent,
            "children": children,
            "related": related
        }

    def get_blueprint_session(self) -> Optional[SessionMetadata]:
        """
        Get the blueprint session for this project.

        Returns:
            SessionMetadata for blueprint, or None if not found
        """
        sessions = self.list_sessions(session_type="blueprint")
        if sessions:
            return sessions[0]  # Should only be one blueprint per project
        return None

    def get_feature_sessions(self) -> List[SessionMetadata]:
        """
        Get all feature sessions in the project.

        Returns:
            List of feature SessionMetadata objects
        """
        return self.list_sessions(session_type="feature")

    def get_orphaned_sessions(self) -> List[SessionMetadata]:
        """
        Find sessions whose parent_session doesn't exist.

        Returns:
            List of orphaned SessionMetadata objects
        """
        orphaned = []
        all_sessions = self.list_sessions()

        for session in all_sessions:
            if session.parent_session:
                parent_path = self.sessions_dir / session.parent_session
                if not parent_path.exists():
                    orphaned.append(session)

        return orphaned

    def _create_legacy_metadata(self, session_dir: Path) -> Optional[SessionMetadata]:
        """
        Create minimal metadata for legacy sessions without session.json.

        Args:
            session_dir: Path to legacy session directory

        Returns:
            SessionMetadata object or None if invalid
        """
        # Check if .owner file exists
        owner_file = session_dir / "metadata" / ".owner"
        if not owner_file.exists():
            return None

        # Parse .owner file
        owner_content = owner_file.read_text()
        created_at = None
        owner = "unknown"

        for line in owner_content.split("\n"):
            if line.startswith("Created:"):
                created_at = line.split(":", 1)[1].strip()
            elif line.startswith("Client ID:"):
                owner = line.split(":", 1)[1].strip()

        # Determine if blueprint based on session name
        is_blueprint = session_dir.name == "__blueprint__"

        return SessionMetadata(
            session_id=session_dir.name,
            name=session_dir.name,
            session_type="blueprint" if is_blueprint else "feature",
            description="Legacy session (no metadata)",
            is_blueprint=is_blueprint,
            parent_session=None if is_blueprint else "__blueprint__",
            related_sessions=[],
            owner=owner,
            collaborators=[],
            tags=["legacy"],
            status="unknown",
            created_at=created_at or "unknown",
            updated_at=created_at or "unknown"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get project session statistics.

        Returns:
            Dictionary with session counts and statistics
        """
        all_sessions = self.list_sessions(include_legacy=True)

        stats = {
            "total_sessions": len(all_sessions),
            "by_type": {},
            "by_status": {},
            "blueprint_count": 0,
            "feature_count": 0,
            "orphaned_count": len(self.get_orphaned_sessions()),
            "legacy_count": len([s for s in all_sessions if "legacy" in s.tags])
        }

        for session in all_sessions:
            # Count by type
            stats["by_type"][session.session_type] = stats["by_type"].get(session.session_type, 0) + 1

            # Count by status
            stats["by_status"][session.status] = stats["by_status"].get(session.status, 0) + 1

            # Special counts
            if session.is_blueprint:
                stats["blueprint_count"] += 1
            elif session.session_type == "feature":
                stats["feature_count"] += 1

        return stats

    def __repr__(self) -> str:
        """String representation."""
        return f"SessionManager(project='{self.project_path.name}', sessions_dir='{self.sessions_dir}')"
