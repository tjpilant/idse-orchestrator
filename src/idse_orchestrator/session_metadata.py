"""
Session Metadata

Handles rich session metadata including lineage, collaborators, and status tracking.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import json


@dataclass
class Collaborator:
    """Represents a collaborator on a session."""

    name: str
    role: str  # owner, contributor, reviewer, viewer
    joined_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "joined_at": self.joined_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collaborator":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            role=data["role"],
            joined_at=data["joined_at"]
        )


@dataclass
class SessionMetadata:
    """
    Comprehensive session metadata.

    This class manages all metadata for an IDSE session, including:
    - Session identification and type
    - Lineage tracking (parent/child relationships)
    - Collaborators and permissions
    - Tags and status
    - Timestamps
    """

    session_id: str
    name: str
    session_type: str  # "blueprint", "feature", "exploratory"
    description: Optional[str]
    is_blueprint: bool
    parent_session: Optional[str]  # e.g., "__blueprint__"
    related_sessions: List[str]
    owner: str
    collaborators: List[Collaborator]
    tags: List[str]
    status: str  # draft, in_progress, review, complete, archived
    created_at: str
    updated_at: str

    def __post_init__(self):
        """Validate session metadata after initialization."""
        valid_types = ["blueprint", "feature", "exploratory"]
        if self.session_type not in valid_types:
            raise ValueError(
                f"Invalid session_type: {self.session_type}. Must be one of {valid_types}"
            )

        valid_statuses = ["draft", "in_progress", "review", "complete", "archived"]
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {self.status}. Must be one of {valid_statuses}"
            )

        valid_roles = ["owner", "contributor", "reviewer", "viewer"]
        for collab in self.collaborators:
            if collab.role not in valid_roles:
                raise ValueError(
                    f"Invalid collaborator role: {collab.role}. Must be one of {valid_roles}"
                )

    @classmethod
    def load(cls, session_path: Path) -> "SessionMetadata":
        """
        Load session.json from metadata directory.

        Args:
            session_path: Path to session directory

        Returns:
            SessionMetadata instance

        Raises:
            FileNotFoundError: If session.json doesn't exist
            json.JSONDecodeError: If session.json is malformed
        """
        metadata_file = session_path / "metadata" / "session.json"

        if not metadata_file.exists():
            raise FileNotFoundError(
                f"Session metadata not found: {metadata_file}\n"
                f"This may be a legacy session. Run migration to upgrade."
            )

        with open(metadata_file, "r") as f:
            data = json.load(f)

        # Convert collaborators from dict to Collaborator objects
        collaborators = []
        for c in data.get("collaborators", []):
            if isinstance(c, dict):
                collaborators.append(Collaborator.from_dict(c))
            elif isinstance(c, str):
                # Handle legacy string collaborators (e.g., ["Claude"])
                collaborators.append(Collaborator(
                    name=c,
                    role="contributor",
                    joined_at=data.get("created_at", datetime.now().isoformat())
                ))
            # else: skip invalid entries

        return cls(
            session_id=data["session_id"],
            name=data["name"],
            session_type=data["session_type"],
            description=data.get("description"),
            is_blueprint=data["is_blueprint"],
            parent_session=data.get("parent_session"),
            related_sessions=data.get("related_sessions", []),
            owner=data["owner"],
            collaborators=collaborators,
            tags=data.get("tags", []),
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

    def save(self, session_path: Path) -> None:
        """
        Save to metadata/session.json.

        Args:
            session_path: Path to session directory
        """
        metadata_dir = session_path / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = metadata_dir / "session.json"

        # Convert to dictionary
        data = {
            "session_id": self.session_id,
            "name": self.name,
            "session_type": self.session_type,
            "description": self.description,
            "is_blueprint": self.is_blueprint,
            "parent_session": self.parent_session,
            "related_sessions": self.related_sessions,
            "owner": self.owner,
            "collaborators": [c.to_dict() for c in self.collaborators],
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

        with open(metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def update(self, session_path: Path, **kwargs) -> None:
        """
        Update metadata fields and save.

        Args:
            session_path: Path to session directory
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Always update timestamp
        self.updated_at = datetime.now().isoformat()

        self.save(session_path)

    def add_collaborator(
        self,
        session_path: Path,
        name: str,
        role: str = "contributor"
    ) -> None:
        """
        Add a collaborator to the session.

        Args:
            session_path: Path to session directory
            name: Collaborator name
            role: Collaborator role (owner, contributor, reviewer, viewer)
        """
        # Check if collaborator already exists
        if any(c.name == name for c in self.collaborators):
            raise ValueError(f"Collaborator {name} already exists")

        collaborator = Collaborator(
            name=name,
            role=role,
            joined_at=datetime.now().isoformat()
        )

        self.collaborators.append(collaborator)
        self.update(session_path, collaborators=self.collaborators)

    def remove_collaborator(self, session_path: Path, name: str) -> None:
        """
        Remove a collaborator from the session.

        Args:
            session_path: Path to session directory
            name: Collaborator name
        """
        self.collaborators = [c for c in self.collaborators if c.name != name]
        self.update(session_path, collaborators=self.collaborators)

    def add_tag(self, session_path: Path, tag: str) -> None:
        """
        Add a tag to the session.

        Args:
            session_path: Path to session directory
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.update(session_path, tags=self.tags)

    def remove_tag(self, session_path: Path, tag: str) -> None:
        """
        Remove a tag from the session.

        Args:
            session_path: Path to session directory
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.update(session_path, tags=self.tags)

    def add_related_session(self, session_path: Path, related_session_id: str) -> None:
        """
        Link a related session.

        Args:
            session_path: Path to session directory
            related_session_id: ID of related session
        """
        if related_session_id not in self.related_sessions:
            self.related_sessions.append(related_session_id)
            self.update(session_path, related_sessions=self.related_sessions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "session_type": self.session_type,
            "description": self.description,
            "is_blueprint": self.is_blueprint,
            "parent_session": self.parent_session,
            "related_sessions": self.related_sessions,
            "owner": self.owner,
            "collaborators": [c.to_dict() for c in self.collaborators],
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionMetadata(session_id='{self.session_id}', "
            f"type='{self.session_type}', status='{self.status}', "
            f"is_blueprint={self.is_blueprint})"
        )
