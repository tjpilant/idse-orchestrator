from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, Optional


DEFAULT_DB_NAME = "idse.db"


@dataclass(frozen=True)
class ArtifactRecord:
    project: str
    session_id: str
    stage: str
    content: str
    content_hash: str
    created_at: str
    updated_at: str


class ArtifactDatabase:
    """SQLite-backed source of truth for IDSE artifacts and metadata."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        idse_root: Optional[Path] = None,
        allow_create: bool = True,
    ):
        if db_path is None:
            if idse_root is None:
                from .project_workspace import ProjectWorkspace

                manager = ProjectWorkspace()
                idse_root = manager.idse_root
            db_path = idse_root / DEFAULT_DB_NAME

        self.db_path = Path(db_path)
        if not self.db_path.exists() and not allow_create:
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. Run 'idse init' or 'idse migrate'."
            )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for statement in _schema_statements():
                conn.execute(statement)
            _ensure_columns(conn)

    def ensure_project(self, project: str, stack: Optional[str] = None, owner: Optional[str] = None) -> int:
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, stack, owner, current_session_id FROM projects WHERE name = ?;",
                (project,),
            ).fetchone()
            if row:
                update_fields = []
                params: list[Any] = []
                if stack is not None and stack != row["stack"]:
                    update_fields.append("stack = ?")
                    params.append(stack)
                if owner is not None and owner != row["owner"]:
                    update_fields.append("owner = ?")
                    params.append(owner)
                if update_fields:
                    update_fields.append("updated_at = ?")
                    params.append(now)
                    params.append(project)
                    conn.execute(
                        f"UPDATE projects SET {', '.join(update_fields)} WHERE name = ?;",
                        params,
                    )
                return int(row["id"])

            conn.execute(
                """
                INSERT INTO projects (name, stack, owner, created_at, updated_at, current_session_id)
                VALUES (?, ?, ?, ?, ?, NULL);
                """,
                (project, stack, owner or "system", now, now),
            )
            return int(conn.execute("SELECT id FROM projects WHERE name = ?;", (project,)).fetchone()["id"])

    def ensure_session(
        self,
        project: str,
        session_id: str,
        *,
        name: Optional[str] = None,
        session_type: Optional[str] = None,
        description: Optional[str] = None,
        is_blueprint: Optional[bool] = None,
        parent_session: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        project_id = self.ensure_project(project)
        now = _now()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE project_id = ? AND session_id = ?;",
                (project_id, session_id),
            ).fetchone()
            if row:
                updates = []
                params: list[Any] = []
                for column, value in [
                    ("name", name),
                    ("session_type", session_type),
                    ("description", description),
                    ("is_blueprint", (1 if is_blueprint else 0) if is_blueprint is not None else None),
                    ("parent_session", parent_session),
                    ("status", status),
                    ("owner", owner),
                ]:
                    if value is not None:
                        updates.append(f"{column} = ?")
                        params.append(value)
                if updates:
                    updates.append("updated_at = ?")
                    params.append(now)
                    params.extend([project_id, session_id])
                    conn.execute(
                        f"UPDATE sessions SET {', '.join(updates)} WHERE project_id = ? AND session_id = ?;",
                        params,
                    )
                return int(row["id"])

            insert_is_blueprint = is_blueprint if is_blueprint is not None else (session_id == "__blueprint__")
            insert_session_type = session_type if session_type is not None else ("blueprint" if insert_is_blueprint else "feature")
            insert_status = status if status is not None else "draft"
            insert_name = name if name is not None else session_id
            insert_owner = owner if owner is not None else "system"

            conn.execute(
                """
                INSERT INTO sessions (
                    project_id,
                    session_id,
                    name,
                    session_type,
                    description,
                    is_blueprint,
                    parent_session,
                    owner,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    session_id,
                    insert_name,
                    insert_session_type,
                    description,
                    1 if insert_is_blueprint else 0,
                    parent_session,
                    insert_owner,
                    insert_status,
                    now,
                    now,
                ),
            )
            return int(
                conn.execute(
                    "SELECT id FROM sessions WHERE project_id = ? AND session_id = ?;",
                    (project_id, session_id),
                ).fetchone()["id"]
            )

    def list_sessions(self, project: str) -> list[str]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id FROM sessions WHERE project_id = ? ORDER BY created_at;",
                (project_id,),
            ).fetchall()
        return [row["session_id"] for row in rows]

    def list_session_metadata(self, project: str) -> list[Dict[str, Any]]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, name, session_type, description, is_blueprint, parent_session,
                       owner, status, created_at, updated_at
                FROM sessions
                WHERE project_id = ?
                ORDER BY created_at;
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> ArtifactRecord:
        project_id = self.ensure_project(project)
        session_row_id = self.ensure_session(project, session_id)
        now = _now()
        content_hash = _hash_content(content)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    project_id,
                    session_id,
                    stage,
                    content,
                    content_hash,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, stage)
                DO UPDATE SET
                    content = excluded.content,
                    content_hash = excluded.content_hash,
                    updated_at = excluded.updated_at;
                """,
                (project_id, session_row_id, stage, content, content_hash, now, now),
            )
            row = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.content, a.content_hash,
                       a.created_at, a.updated_at
                FROM artifacts a
                JOIN sessions s ON a.session_id = s.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.name = ? AND s.session_id = ? AND a.stage = ?;
                """,
                (project, session_id, stage),
            ).fetchone()

        return ArtifactRecord(
            project=row["project"],
            session_id=row["session_id"],
            stage=row["stage"],
            content=row["content"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def load_artifact(self, project: str, session_id: str, stage: str) -> ArtifactRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.content, a.content_hash,
                       a.created_at, a.updated_at
                FROM artifacts a
                JOIN sessions s ON a.session_id = s.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.name = ? AND s.session_id = ? AND a.stage = ?;
                """,
                (project, session_id, stage),
            ).fetchone()

        if not row:
            raise FileNotFoundError(
                f"Artifact not found for project={project} session={session_id} stage={stage}"
            )

        return ArtifactRecord(
            project=row["project"],
            session_id=row["session_id"],
            stage=row["stage"],
            content=row["content"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def save_state(self, project: str, state: Dict[str, Any]) -> None:
        project_id = self.ensure_project(project)
        now = _now()
        payload = json.dumps(state)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_state (project_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id)
                DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at;
                """,
                (project_id, payload, now),
            )

    def load_state(self, project: str) -> Dict[str, Any]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM project_state WHERE project_id = ?;",
                (project_id,),
            ).fetchone()

        if not row:
            raise FileNotFoundError(f"State not found for project: {project}")

        return json.loads(row["state_json"])

    def set_current_session(self, project: str, session_id: str) -> None:
        project_id = self.ensure_project(project)
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE projects SET current_session_id = ?, updated_at = ? WHERE id = ?;",
                (session_id, now, project_id),
            )
            conn.execute(
                """
                INSERT INTO project_state (project_id, state_json, updated_at, current_session_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id)
                DO UPDATE SET current_session_id = excluded.current_session_id, updated_at = excluded.updated_at;
                """,
                (project_id, json.dumps({}), now, session_id),
            )

    def get_current_session(self, project: str) -> Optional[str]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT current_session_id FROM project_state WHERE project_id = ?;",
                (project_id,),
            ).fetchone()
            if row and row["current_session_id"]:
                return row["current_session_id"]
            row = conn.execute(
                "SELECT current_session_id FROM projects WHERE id = ?;",
                (project_id,),
            ).fetchone()
        if not row:
            return None
        return row["current_session_id"]

    def save_session_state(self, project: str, session_id: str, state: Dict[str, Any]) -> None:
        session_row_id = self.ensure_session(project, session_id)
        now = _now()
        payload = json.dumps(state)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_state (session_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id)
                DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at;
                """,
                (session_row_id, payload, now),
            )

    def load_session_state(self, project: str, session_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ss.state_json
                FROM session_state ss
                JOIN sessions s ON ss.session_id = s.id
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ? AND s.session_id = ?;
                """,
                (project, session_id),
            ).fetchone()

        if not row:
            raise FileNotFoundError(
                f"State not found for project={project} session={session_id}"
            )

        return json.loads(row["state_json"])

    def list_artifacts(
        self,
        project: str,
        session_id: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> list[ArtifactRecord]:
        query = [
            """
            SELECT p.name AS project, s.session_id, a.stage, a.content, a.content_hash,
                   a.created_at, a.updated_at
            FROM artifacts a
            JOIN sessions s ON a.session_id = s.id
            JOIN projects p ON a.project_id = p.id
            WHERE p.name = ?
            """
        ]
        params: list[Any] = [project]

        if session_id:
            query.append("AND s.session_id = ?")
            params.append(session_id)
        if stage:
            query.append("AND a.stage = ?")
            params.append(stage)

        query.append("ORDER BY s.session_id, a.stage;")

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()

        return [
            ArtifactRecord(
                project=row["project"],
                session_id=row["session_id"],
                stage=row["stage"],
                content=row["content"],
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def find_artifacts_with_marker(
        self,
        project: str,
        stage: str,
        marker: str,
    ) -> list[ArtifactRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.content, a.content_hash,
                       a.created_at, a.updated_at
                FROM artifacts a
                JOIN sessions s ON a.session_id = s.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.name = ? AND a.stage = ? AND a.content LIKE ?;
                """,
                (project, stage, f"%{marker}%"),
            ).fetchall()

        return [
            ArtifactRecord(
                project=row["project"],
                session_id=row["session_id"],
                stage=row["stage"],
                content=row["content"],
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def save_agent_registry(self, project: str, registry: Dict[str, Any]) -> None:
        project_id = self.ensure_project(project)
        now = _now()
        agents = registry.get("agents", [])

        with self._connect() as conn:
            # Preserve explicit registry ordering by replacing rows for this project.
            conn.execute(
                "DELETE FROM agent_stages WHERE agent_id IN (SELECT id FROM agents WHERE project_id = ?);",
                (project_id,),
            )
            conn.execute("DELETE FROM agents WHERE project_id = ?;", (project_id,))
            for agent in agents:
                agent_id = agent.get("id")
                if not agent_id:
                    continue
                role = agent.get("role")
                mode = agent.get("mode")
                conn.execute(
                    """
                    INSERT INTO agents (project_id, agent_id, role, mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (project_id, agent_id, role, mode, now, now),
                )
                row = conn.execute(
                    "SELECT id FROM agents WHERE project_id = ? AND agent_id = ?;",
                    (project_id, agent_id),
                ).fetchone()
                if not row:
                    continue
                agent_row_id = int(row["id"])
                conn.execute("DELETE FROM agent_stages WHERE agent_id = ?;", (agent_row_id,))
                for stage in agent.get("stages", []):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO agent_stages (agent_id, stage)
                        VALUES (?, ?);
                        """,
                        (agent_row_id, stage),
                    )

    def load_agent_registry(self, project: str) -> Dict[str, Any]:
        project_id = self.ensure_project(project)
        registry = {"agents": []}
        with self._connect() as conn:
            agents = conn.execute(
                "SELECT id, agent_id, role, mode FROM agents WHERE project_id = ? ORDER BY id ASC;",
                (project_id,),
            ).fetchall()
            for agent in agents:
                stages = conn.execute(
                    "SELECT stage FROM agent_stages WHERE agent_id = ?;",
                    (agent["id"],),
                ).fetchall()
                registry["agents"].append(
                    {
                        "id": agent["agent_id"],
                        "role": agent["role"],
                        "mode": agent["mode"],
                        "stages": [s["stage"] for s in stages],
                    }
                )
        return registry

    def save_session_extras(
        self,
        project: str,
        session_id: str,
        *,
        collaborators: Optional[Iterable[Dict[str, Any]]] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> None:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE project_id = ? AND session_id = ?;",
                (project_id, session_id),
            ).fetchone()
            if not row:
                return
            session_row_id = int(row["id"])

            if collaborators is not None:
                conn.execute("DELETE FROM collaborators WHERE session_id = ?;", (session_row_id,))
                for collaborator in collaborators:
                    name = collaborator.get("name")
                    role = collaborator.get("role")
                    joined_at = collaborator.get("joined_at") or _now()
                    if not name or not role:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO collaborators (session_id, name, role, joined_at)
                        VALUES (?, ?, ?, ?);
                        """,
                        (session_row_id, name, role, joined_at),
                    )

            if tags is not None:
                conn.execute("DELETE FROM session_tags WHERE session_id = ?;", (session_row_id,))
                for tag in tags:
                    if not tag:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO session_tags (session_id, tag)
                        VALUES (?, ?);
                        """,
                        (session_row_id, tag),
                    )


def _now() -> str:
    return datetime.now().isoformat()


def hash_content(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _hash_content(content: str) -> str:
    return hash_content(content)


def _ensure_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.execute("PRAGMA table_info(projects);")
    columns = {row[1] for row in cursor.fetchall()}
    if "current_session_id" not in columns:
        conn.execute("ALTER TABLE projects ADD COLUMN current_session_id TEXT;")
    cursor = conn.execute("PRAGMA table_info(project_state);")
    state_columns = {row[1] for row in cursor.fetchall()}
    if "current_session_id" not in state_columns:
        conn.execute("ALTER TABLE project_state ADD COLUMN current_session_id TEXT;")
    cursor = conn.execute("PRAGMA table_info(sessions);")
    session_columns = {row[1] for row in cursor.fetchall()}
    if "owner" not in session_columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN owner TEXT;")


def _schema_statements() -> Iterable[str]:
    return [
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            stack TEXT,
            owner TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            current_session_id TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            name TEXT NOT NULL,
            session_type TEXT NOT NULL,
            description TEXT,
            is_blueprint INTEGER NOT NULL DEFAULT 0,
            parent_session TEXT,
            owner TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, session_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(session_id, stage),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS project_state (
            project_id INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            current_session_id TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS session_state (
            session_id INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT,
            mode TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, agent_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_stages (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            UNIQUE(agent_id, stage),
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collaborators (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(session_id, name),
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS session_tags (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            UNIQUE(session_id, tag),
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """,
    ]
