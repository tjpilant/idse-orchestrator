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
    idse_id: str
    content: str
    content_hash: str
    semantic_fingerprint: str
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

    def get_session_metadata(self, project: str, session_id: str) -> Optional[Dict[str, Any]]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_id, name, session_type, description, is_blueprint, parent_session,
                       owner, status, created_at, updated_at
                FROM sessions
                WHERE project_id = ? AND session_id = ?;
                """,
                (project_id, session_id),
            ).fetchone()
        return dict(row) if row else None

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> ArtifactRecord:
        project_id = self.ensure_project(project)
        session_row_id = self.ensure_session(project, session_id)
        now = _now()
        content_hash = _hash_content(content)
        semantic_fingerprint = _semantic_fingerprint(content)
        idse_id = _make_idse_id(project, session_id, stage)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    project_id,
                    session_id,
                    stage,
                    idse_id,
                    content,
                    content_hash,
                    semantic_fingerprint,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, stage)
                DO UPDATE SET
                    idse_id = excluded.idse_id,
                    content = excluded.content,
                    content_hash = excluded.content_hash,
                    semantic_fingerprint = excluded.semantic_fingerprint,
                    updated_at = excluded.updated_at;
                """,
                (
                    project_id,
                    session_row_id,
                    stage,
                    idse_id,
                    content,
                    content_hash,
                    semantic_fingerprint,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
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
            idse_id=row["idse_id"],
            content=row["content"],
            content_hash=row["content_hash"],
            semantic_fingerprint=row["semantic_fingerprint"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def load_artifact(self, project: str, session_id: str, stage: str) -> ArtifactRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
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
            idse_id=row["idse_id"],
            content=row["content"],
            content_hash=row["content_hash"],
            semantic_fingerprint=row["semantic_fingerprint"],
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
            SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
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
                idse_id=row["idse_id"],
                content=row["content"],
                content_hash=row["content_hash"],
                semantic_fingerprint=row["semantic_fingerprint"],
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
                SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
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
                idse_id=row["idse_id"],
                content=row["content"],
                content_hash=row["content_hash"],
                semantic_fingerprint=row["semantic_fingerprint"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def find_by_idse_id(self, idse_id: str) -> Optional[ArtifactRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
                       a.created_at, a.updated_at
                FROM artifacts a
                JOIN sessions s ON a.session_id = s.id
                JOIN projects p ON a.project_id = p.id
                WHERE a.idse_id = ?;
                """,
                (idse_id,),
            ).fetchone()
        if not row:
            return None
        return ArtifactRecord(
            project=row["project"],
            session_id=row["session_id"],
            stage=row["stage"],
            idse_id=row["idse_id"],
            content=row["content"],
            content_hash=row["content_hash"],
            semantic_fingerprint=row["semantic_fingerprint"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_artifact_id(self, project: str, session_id: str, stage: str) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT a.id
                FROM artifacts a
                JOIN sessions s ON a.session_id = s.id
                JOIN projects p ON a.project_id = p.id
                WHERE p.name = ? AND s.session_id = ? AND a.stage = ?;
                """,
                (project, session_id, stage),
            ).fetchone()
        if not row:
            return None
        return int(row["id"])

    def save_dependency(
        self,
        artifact_id: int,
        depends_on_artifact_id: int,
        dependency_type: str = "upstream",
    ) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifact_dependencies (
                    artifact_id, depends_on_artifact_id, dependency_type, created_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(artifact_id, depends_on_artifact_id)
                DO UPDATE SET dependency_type = excluded.dependency_type;
                """,
                (artifact_id, depends_on_artifact_id, dependency_type, now),
            )

    def replace_dependencies(
        self,
        artifact_id: int,
        depends_on_artifact_ids: Iterable[int],
        dependency_type: str = "upstream",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM artifact_dependencies WHERE artifact_id = ?;",
                (artifact_id,),
            )
            for depends_on_artifact_id in depends_on_artifact_ids:
                conn.execute(
                    """
                    INSERT INTO artifact_dependencies (
                        artifact_id, depends_on_artifact_id, dependency_type, created_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(artifact_id, depends_on_artifact_id)
                    DO UPDATE SET dependency_type = excluded.dependency_type;
                    """,
                    (artifact_id, depends_on_artifact_id, dependency_type, _now()),
                )

    def get_dependencies(self, artifact_id: int, direction: str = "upstream") -> list[ArtifactRecord]:
        if direction not in {"upstream", "downstream"}:
            raise ValueError("direction must be 'upstream' or 'downstream'")

        with self._connect() as conn:
            if direction == "upstream":
                rows = conn.execute(
                    """
                    SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
                           a.created_at, a.updated_at
                    FROM artifact_dependencies d
                    JOIN artifacts a ON d.depends_on_artifact_id = a.id
                    JOIN sessions s ON a.session_id = s.id
                    JOIN projects p ON a.project_id = p.id
                    WHERE d.artifact_id = ?
                    ORDER BY a.id;
                    """,
                    (artifact_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT p.name AS project, s.session_id, a.stage, a.idse_id, a.content, a.content_hash, a.semantic_fingerprint,
                           a.created_at, a.updated_at
                    FROM artifact_dependencies d
                    JOIN artifacts a ON d.artifact_id = a.id
                    JOIN sessions s ON a.session_id = s.id
                    JOIN projects p ON a.project_id = p.id
                    WHERE d.depends_on_artifact_id = ?
                    ORDER BY a.id;
                    """,
                    (artifact_id,),
                ).fetchall()
        return [
            ArtifactRecord(
                project=row["project"],
                session_id=row["session_id"],
                stage=row["stage"],
                idse_id=row["idse_id"],
                content=row["content"],
                content_hash=row["content_hash"],
                semantic_fingerprint=row["semantic_fingerprint"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def save_artifact_edge(
        self,
        from_artifact_id: int,
        to_artifact_id: int,
        edge_type: str = "derives",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO artifact_edges (
                    from_artifact_id, to_artifact_id, edge_type, created_at
                ) VALUES (?, ?, ?, ?);
                """,
                (from_artifact_id, to_artifact_id, edge_type, _now()),
            )

    def list_artifact_edges(self, artifact_id: int, direction: str = "outbound") -> list[Dict[str, Any]]:
        if direction not in {"outbound", "inbound"}:
            raise ValueError("direction must be 'outbound' or 'inbound'")
        with self._connect() as conn:
            if direction == "outbound":
                rows = conn.execute(
                    """
                    SELECT from_artifact_id, to_artifact_id, edge_type, created_at
                    FROM artifact_edges
                    WHERE from_artifact_id = ?;
                    """,
                    (artifact_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT from_artifact_id, to_artifact_id, edge_type, created_at
                    FROM artifact_edges
                    WHERE to_artifact_id = ?;
                    """,
                    (artifact_id,),
                ).fetchall()
        return [dict(row) for row in rows]

    def save_feedback_signal(
        self,
        artifact_id: int,
        *,
        contradiction_flag: bool = False,
        reinforcement_flag: bool = False,
        notes: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_signals (
                    artifact_id, contradiction_flag, reinforcement_flag, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id)
                DO UPDATE SET
                    contradiction_flag = excluded.contradiction_flag,
                    reinforcement_flag = excluded.reinforcement_flag,
                    notes = excluded.notes,
                    created_at = excluded.created_at;
                """,
                (
                    artifact_id,
                    1 if contradiction_flag else 0,
                    1 if reinforcement_flag else 0,
                    notes,
                    _now(),
                ),
            )

    def list_feedback_signals(self, project: str, session_ids: Optional[Iterable[str]] = None) -> list[Dict[str, Any]]:
        query = [
            """
            SELECT fs.artifact_id, fs.contradiction_flag, fs.reinforcement_flag, fs.notes, fs.created_at,
                   s.session_id, a.idse_id
            FROM feedback_signals fs
            JOIN artifacts a ON fs.artifact_id = a.id
            JOIN sessions s ON a.session_id = s.id
            JOIN projects p ON a.project_id = p.id
            WHERE p.name = ?
            """
        ]
        params: list[Any] = [project]
        if session_ids:
            session_list = list(session_ids)
            placeholders = ",".join(["?"] * len(session_list))
            query.append(f"AND s.session_id IN ({placeholders})")
            params.extend(session_list)
        query.append("ORDER BY fs.created_at DESC;")
        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
        return [dict(row) for row in rows]

    def save_promotion_candidate(
        self,
        project: str,
        *,
        claim_text: str,
        classification: str,
        evidence_hash: str,
        failed_tests: Iterable[str],
        evidence: Dict[str, Any],
        source_artifact_ids: Iterable[int],
    ) -> int:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO promotion_candidates (
                    project_id, claim_text, classification, evidence_hash,
                    failed_tests_json, evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    claim_text,
                    classification,
                    evidence_hash,
                    json.dumps(list(failed_tests)),
                    json.dumps(evidence),
                    _now(),
                ),
            )
            candidate_id = int(conn.execute("SELECT last_insert_rowid() AS id;").fetchone()["id"])
            for artifact_id in source_artifact_ids:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO promotion_candidate_sources (candidate_id, artifact_id)
                    VALUES (?, ?);
                    """,
                    (candidate_id, artifact_id),
                )
        return candidate_id

    def save_promotion_record(
        self,
        project: str,
        *,
        candidate_id: int,
        status: str,
        promoted_claim: Optional[str] = None,
        evidence_hash: Optional[str] = None,
    ) -> int:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO promotion_records (
                    project_id, candidate_id, status, promoted_claim, evidence_hash, created_at, promoted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    candidate_id,
                    status,
                    promoted_claim,
                    evidence_hash,
                    _now(),
                    _now() if status == "ALLOW" else None,
                ),
            )
            return int(conn.execute("SELECT last_insert_rowid() AS id;").fetchone()["id"])

    def save_sync_metadata(
        self,
        artifact_id: int,
        backend: str,
        *,
        last_push_hash: Optional[str] = None,
        last_pull_hash: Optional[str] = None,
        remote_id: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT last_push_hash, last_pull_hash, remote_id
                FROM sync_metadata
                WHERE artifact_id = ? AND backend = ?;
                """,
                (artifact_id, backend),
            ).fetchone()
            push_hash = last_push_hash if last_push_hash is not None else (existing["last_push_hash"] if existing else None)
            pull_hash = last_pull_hash if last_pull_hash is not None else (existing["last_pull_hash"] if existing else None)
            rem = remote_id if remote_id is not None else (existing["remote_id"] if existing else None)
            conn.execute(
                """
                INSERT INTO sync_metadata (
                    artifact_id, backend, last_push_hash, last_push_at, last_pull_hash, last_pull_at, remote_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id, backend)
                DO UPDATE SET
                    last_push_hash = excluded.last_push_hash,
                    last_push_at = excluded.last_push_at,
                    last_pull_hash = excluded.last_pull_hash,
                    last_pull_at = excluded.last_pull_at,
                    remote_id = excluded.remote_id;
                """,
                (
                    artifact_id,
                    backend,
                    push_hash,
                    now if last_push_hash is not None else None,
                    pull_hash,
                    now if last_pull_hash is not None else None,
                    rem,
                ),
            )

    def get_sync_metadata(self, artifact_id: int, backend: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT artifact_id, backend, last_push_hash, last_push_at, last_pull_hash, last_pull_at, remote_id
                FROM sync_metadata
                WHERE artifact_id = ? AND backend = ?;
                """,
                (artifact_id, backend),
            ).fetchone()
        if not row:
            return {}
        return dict(row)

    def find_artifact_id_by_remote_id(self, backend: str, remote_id: str) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT artifact_id
                FROM sync_metadata
                WHERE backend = ? AND remote_id = ?;
                """,
                (backend, remote_id),
            ).fetchone()
        if not row:
            return None
        return int(row["artifact_id"])

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

    def save_blueprint_promotion(
        self,
        project: str,
        *,
        claim_text: str,
        classification: str,
        status: str,
        evidence_hash: str,
        failed_tests: Iterable[str],
        evidence: Dict[str, Any],
        source_artifact_ids: Iterable[int],
        promoted_at: Optional[str] = None,
    ) -> int:
        candidate_id = self.save_promotion_candidate(
            project,
            claim_text=claim_text,
            classification=classification,
            evidence_hash=evidence_hash,
            failed_tests=failed_tests,
            evidence=evidence,
            source_artifact_ids=source_artifact_ids,
        )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE promotion_candidates
                SET created_at = ?
                WHERE id = ?;
                """,
                (promoted_at or _now(), candidate_id),
            )
        return self.save_promotion_record(
            project,
            candidate_id=candidate_id,
            status=status,
            promoted_claim=claim_text if status == "ALLOW" else None,
            evidence_hash=evidence_hash,
        )

    def list_blueprint_promotions(self, project: str, status: Optional[str] = None) -> list[Dict[str, Any]]:
        project_id = self.ensure_project(project)
        query = """
            SELECT pr.id, pc.claim_text, pc.classification, pr.status, pr.evidence_hash,
                   pc.failed_tests_json, pc.evidence_json, pr.created_at, pr.promoted_at
            FROM promotion_records pr
            JOIN promotion_candidates pc ON pr.candidate_id = pc.id
            WHERE pr.project_id = ?
        """
        params: list[Any] = [project_id]
        if status:
            query += " AND pr.status = ?"
            params.append(status)
        query += " ORDER BY pr.created_at DESC;"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            results: list[Dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["failed_tests"] = json.loads(item.pop("failed_tests_json") or "[]")
                item["evidence"] = json.loads(item.pop("evidence_json") or "{}")
                src_rows = conn.execute(
                    """
                    SELECT p.name AS project, s.session_id, a.stage, a.idse_id
                    FROM promotion_candidate_sources pcs
                    JOIN artifacts a ON pcs.artifact_id = a.id
                    JOIN sessions s ON a.session_id = s.id
                    JOIN projects p ON a.project_id = p.id
                    WHERE pcs.candidate_id = (
                        SELECT candidate_id FROM promotion_records WHERE id = ?
                    )
                    ORDER BY s.session_id, a.stage;
                    """,
                    (row["id"],),
                ).fetchall()
                item["sources"] = [dict(src) for src in src_rows]
                results.append(item)
        return results

    def save_blueprint_hash(self, project: str, file_hash: str) -> None:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO blueprint_integrity (project_id, file_hash, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id)
                DO UPDATE SET file_hash = excluded.file_hash, updated_at = excluded.updated_at;
                """,
                (project_id, file_hash, _now()),
            )

    def get_blueprint_hash(self, project: str) -> Optional[str]:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT file_hash
                FROM blueprint_integrity
                WHERE project_id = ?;
                """,
                (project_id,),
            ).fetchone()
        if not row:
            return None
        return str(row["file_hash"])

    def record_integrity_event(
        self,
        project: str,
        expected_hash: str,
        actual_hash: str,
        action: str = "warn",
    ) -> None:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO integrity_events (
                    project_id, expected_hash, actual_hash, action, created_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (project_id, expected_hash, actual_hash, action, _now()),
            )

    def save_blueprint_claim(
        self,
        project: str,
        *,
        claim_text: str,
        classification: str,
        promotion_record_id: Optional[int],
        origin: str = "converged",
        status: str = "active",
        supersedes_claim_id: Optional[int] = None,
    ) -> int:
        project_id = self.ensure_project(project)
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO blueprint_claims (
                    project_id, claim_text, classification, status, supersedes_claim_id,
                    promotion_record_id, origin, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, claim_text)
                DO UPDATE SET
                    classification = excluded.classification,
                    status = excluded.status,
                    supersedes_claim_id = excluded.supersedes_claim_id,
                    promotion_record_id = excluded.promotion_record_id,
                    origin = excluded.origin,
                    updated_at = excluded.updated_at;
                """,
                (
                    project_id,
                    claim_text,
                    classification,
                    status,
                    supersedes_claim_id,
                    promotion_record_id,
                    origin,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT claim_id
                FROM blueprint_claims
                WHERE project_id = ? AND claim_text = ?;
                """,
                (project_id, claim_text),
            ).fetchone()
        return int(row["claim_id"])

    def get_blueprint_claims(self, project: str, status: Optional[str] = None) -> list[Dict[str, Any]]:
        project_id = self.ensure_project(project)
        query = """
            SELECT claim_id, project_id, claim_text, classification, status, supersedes_claim_id,
                   promotion_record_id, origin, created_at, updated_at
            FROM blueprint_claims
            WHERE project_id = ?
        """
        params: list[Any] = [project_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at;"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_claim_status(
        self,
        claim_id: int,
        status: str,
        supersedes_claim_id: Optional[int] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE blueprint_claims
                SET status = ?, supersedes_claim_id = ?, updated_at = ?
                WHERE claim_id = ?;
                """,
                (status, supersedes_claim_id, _now(), claim_id),
            )

    def record_lifecycle_event(
        self,
        claim_id: int,
        project: str,
        old_status: str,
        new_status: str,
        reason: str,
        actor: str = "system",
        superseding_claim_id: Optional[int] = None,
    ) -> None:
        project_id = self.ensure_project(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO claim_lifecycle_events (
                    claim_id, project_id, old_status, new_status, reason, actor, superseding_claim_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    claim_id,
                    project_id,
                    old_status,
                    new_status,
                    reason,
                    actor,
                    superseding_claim_id,
                    _now(),
                ),
            )

    def get_lifecycle_events(self, project: str, claim_id: Optional[int] = None) -> list[Dict[str, Any]]:
        project_id = self.ensure_project(project)
        query = """
            SELECT e.id, e.claim_id, e.project_id, c.claim_text, e.old_status, e.new_status,
                   e.reason, e.actor, e.superseding_claim_id, e.created_at
            FROM claim_lifecycle_events e
            JOIN blueprint_claims c ON e.claim_id = c.claim_id
            WHERE e.project_id = ?
        """
        params: list[Any] = [project_id]
        if claim_id is not None:
            query += " AND e.claim_id = ?"
            params.append(claim_id)
        query += " ORDER BY e.created_at DESC;"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def _now() -> str:
    return datetime.now().isoformat()


def hash_content(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _hash_content(content: str) -> str:
    return hash_content(content)


def _semantic_fingerprint(content: str) -> str:
    normalized = " ".join(content.lower().split())
    return sha256(normalized.encode("utf-8")).hexdigest()


def _make_idse_id(project: str, session_id: str, stage: str) -> str:
    return f"{project}::{session_id}::{stage}"


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
    cursor = conn.execute("PRAGMA table_info(artifacts);")
    artifact_columns = {row[1] for row in cursor.fetchall()}
    if "idse_id" not in artifact_columns:
        conn.execute("ALTER TABLE artifacts ADD COLUMN idse_id TEXT;")
        conn.execute(
            """
            UPDATE artifacts
            SET idse_id = (
                SELECT p.name || '::' || s.session_id || '::' || artifacts.stage
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE s.id = artifacts.session_id
            )
            WHERE idse_id IS NULL;
            """
        )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_idse_id ON artifacts(idse_id);")
    if "semantic_fingerprint" not in artifact_columns:
        conn.execute("ALTER TABLE artifacts ADD COLUMN semantic_fingerprint TEXT;")
        conn.execute(
            """
            UPDATE artifacts
            SET semantic_fingerprint = content_hash
            WHERE semantic_fingerprint IS NULL;
            """
        )
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='blueprint_claims';
        """
    )
    if cursor.fetchone():
        cursor = conn.execute("PRAGMA table_info(blueprint_claims);")
        claim_columns = {row[1]: row for row in cursor.fetchall()}
        if "origin" not in claim_columns:
            conn.execute(
                "ALTER TABLE blueprint_claims ADD COLUMN origin TEXT NOT NULL DEFAULT 'converged';"
            )
        conn.execute(
            """
            UPDATE blueprint_claims
            SET origin = 'converged'
            WHERE origin IS NULL OR TRIM(origin) = '';
            """
        )
        promotion_record_col = claim_columns.get("promotion_record_id")
        if promotion_record_col and int(promotion_record_col[3]) == 1:
            _migrate_blueprint_claims_nullable_promotion_record(conn)


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
            idse_id TEXT UNIQUE,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            semantic_fingerprint TEXT,
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
        """
        CREATE TABLE IF NOT EXISTS artifact_dependencies (
            id INTEGER PRIMARY KEY,
            artifact_id INTEGER NOT NULL,
            depends_on_artifact_id INTEGER NOT NULL,
            dependency_type TEXT NOT NULL DEFAULT 'upstream',
            created_at TEXT NOT NULL,
            UNIQUE(artifact_id, depends_on_artifact_id),
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
            FOREIGN KEY(depends_on_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS artifact_edges (
            id INTEGER PRIMARY KEY,
            from_artifact_id INTEGER NOT NULL,
            to_artifact_id INTEGER NOT NULL,
            edge_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(from_artifact_id, to_artifact_id, edge_type),
            FOREIGN KEY(from_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
            FOREIGN KEY(to_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id INTEGER PRIMARY KEY,
            artifact_id INTEGER NOT NULL,
            backend TEXT NOT NULL,
            last_push_hash TEXT,
            last_push_at TEXT,
            last_pull_hash TEXT,
            last_pull_at TEXT,
            remote_id TEXT,
            UNIQUE(artifact_id, backend),
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS feedback_signals (
            artifact_id INTEGER PRIMARY KEY,
            contradiction_flag INTEGER NOT NULL DEFAULT 0,
            reinforcement_flag INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS promotion_candidates (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            claim_text TEXT NOT NULL,
            classification TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            failed_tests_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS promotion_candidate_sources (
            id INTEGER PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            UNIQUE(candidate_id, artifact_id),
            FOREIGN KEY(candidate_id) REFERENCES promotion_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS promotion_records (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            promoted_claim TEXT,
            evidence_hash TEXT,
            created_at TEXT NOT NULL,
            promoted_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(candidate_id) REFERENCES promotion_candidates(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blueprint_integrity (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL UNIQUE,
            file_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS integrity_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            expected_hash TEXT NOT NULL,
            actual_hash TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blueprint_claims (
            claim_id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            claim_text TEXT NOT NULL,
            classification TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            supersedes_claim_id INTEGER,
            promotion_record_id INTEGER,
            origin TEXT NOT NULL DEFAULT 'converged',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, claim_text),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(supersedes_claim_id) REFERENCES blueprint_claims(claim_id),
            FOREIGN KEY(promotion_record_id) REFERENCES promotion_records(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS claim_lifecycle_events (
            id INTEGER PRIMARY KEY,
            claim_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            old_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            reason TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT 'system',
            superseding_claim_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(claim_id) REFERENCES blueprint_claims(claim_id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(superseding_claim_id) REFERENCES blueprint_claims(claim_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blueprint_promotions (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            claim_text TEXT NOT NULL,
            classification TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            failed_tests_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            promoted_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blueprint_promotion_sources (
            id INTEGER PRIMARY KEY,
            promotion_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            UNIQUE(promotion_id, artifact_id),
            FOREIGN KEY(promotion_id) REFERENCES blueprint_promotions(id) ON DELETE CASCADE,
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
        );
        """,
    ]


def _migrate_blueprint_claims_nullable_promotion_record(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.execute("ALTER TABLE blueprint_claims RENAME TO blueprint_claims_legacy;")
    conn.execute(
        """
        CREATE TABLE blueprint_claims (
            claim_id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            claim_text TEXT NOT NULL,
            classification TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            supersedes_claim_id INTEGER,
            promotion_record_id INTEGER,
            origin TEXT NOT NULL DEFAULT 'converged',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, claim_text),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(supersedes_claim_id) REFERENCES blueprint_claims(claim_id),
            FOREIGN KEY(promotion_record_id) REFERENCES promotion_records(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        INSERT INTO blueprint_claims (
            claim_id, project_id, claim_text, classification, status, supersedes_claim_id,
            promotion_record_id, origin, created_at, updated_at
        )
        SELECT
            claim_id, project_id, claim_text, classification, status, supersedes_claim_id,
            promotion_record_id, COALESCE(NULLIF(origin, ''), 'converged'), created_at, updated_at
        FROM blueprint_claims_legacy;
        """
    )
    conn.execute("DROP TABLE blueprint_claims_legacy;")
    conn.execute("PRAGMA foreign_keys = ON;")
