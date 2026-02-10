from pathlib import Path

import pytest

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.blueprint_promotion import BlueprintPromotionGate
from idse_orchestrator.file_view_generator import FileViewGenerator


def _seed_promotions(db: ArtifactDatabase, project: str) -> None:
    db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")
    db.save_artifact(project, "s1", "intent", "intent")
    db.save_artifact(project, "s2", "spec", "spec")
    a_id = db.get_artifact_id(project, "s1", "intent")
    b_id = db.get_artifact_id(project, "s2", "spec")
    assert a_id is not None
    assert b_id is not None
    db.save_blueprint_promotion(
        project,
        claim_text="SQLite is the authoritative storage backend for project artifacts.",
        classification="invariant",
        status="ALLOW",
        evidence_hash="hash1",
        failed_tests=[],
        evidence={"source_sessions": ["s1", "s2"], "source_stages": ["intent", "spec"], "feedback_artifacts": []},
        source_artifact_ids=[a_id, b_id],
        promoted_at="2026-02-08T00:00:00",
    )
    db.save_blueprint_promotion(
        project,
        claim_text="Notion is a sync target and not a source of truth.",
        classification="invariant",
        status="ALLOW",
        evidence_hash="hash2",
        failed_tests=[],
        evidence={"source_sessions": ["s1", "s2"], "source_stages": ["intent", "spec"], "feedback_artifacts": []},
        source_artifact_ids=[a_id, b_id],
        promoted_at="2026-02-08T01:00:00",
    )


def _promotion_record_id(db: ArtifactDatabase, project: str, claim_text: str = "seed claim") -> int:
    candidate_id = db.save_promotion_candidate(
        project,
        claim_text=claim_text,
        classification="invariant",
        evidence_hash=f"{claim_text}-hash",
        failed_tests=[],
        evidence={},
        source_artifact_ids=[],
    )
    return db.save_promotion_record(
        project,
        candidate_id=candidate_id,
        status="ALLOW",
        promoted_claim=claim_text,
        evidence_hash=f"{claim_text}-hash",
    )


def test_claim_lifecycle_tables_exist(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    with db._connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")}
    assert "blueprint_claims" in tables
    assert "claim_lifecycle_events" in tables


def test_save_and_get_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="SQLite is authoritative.",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "SQLite is authoritative."),
    )
    claims = db.get_blueprint_claims("demo")
    assert len(claims) == 1
    assert claims[0]["claim_id"] == claim_id


def test_filter_claims_by_status(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="SQLite is authoritative.",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "SQLite is authoritative."),
    )
    db.update_claim_status(claim_id, "invalidated")
    assert db.get_blueprint_claims("demo", status="active") == []
    assert len(db.get_blueprint_claims("demo", status="invalidated")) == 1


def test_update_claim_status_with_supersedes(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_a = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    claim_b = db.save_blueprint_claim(
        "demo",
        claim_text="B",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "B"),
    )
    db.update_claim_status(claim_a, "superseded", supersedes_claim_id=claim_b)
    rows = db.get_blueprint_claims("demo", status="superseded")
    assert rows[0]["supersedes_claim_id"] == claim_b


def test_auto_insert_claims_on_apply_promotions(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    generator = FileViewGenerator(idse_root=idse_root)
    generator.apply_allowed_promotions_to_blueprint(project)
    claims = db.get_blueprint_claims(project)
    assert len(claims) == 2


def test_auto_insert_claims_idempotent(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    generator = FileViewGenerator(idse_root=idse_root)
    generator.apply_allowed_promotions_to_blueprint(project)
    generator.apply_allowed_promotions_to_blueprint(project)
    assert len(db.get_blueprint_claims(project)) == 2


def test_demoted_claim_excluded_from_canonical_but_kept_in_ledger(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    generator = FileViewGenerator(idse_root=idse_root)
    blueprint_path = generator.apply_allowed_promotions_to_blueprint(project)
    claims = db.get_blueprint_claims(project)
    target = next(c for c in claims if "SQLite is the authoritative" in c["claim_text"])

    gate = BlueprintPromotionGate(db)
    gate.demote_claim(project, claim_id=target["claim_id"], reason="Obsolete constraint", new_status="invalidated")
    blueprint_path = generator.apply_allowed_promotions_to_blueprint(project)
    content = blueprint_path.read_text()

    core_section = content.split("## Core Invariants", 1)[1].split("## High-Level Architecture", 1)[0]
    assert "SQLite is the authoritative storage backend for project artifacts." not in core_section
    assert "- [invariant|converged] SQLite is the authoritative storage backend for project artifacts." in content


def test_demote_requires_reason(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    gate = BlueprintPromotionGate(db)
    with pytest.raises(ValueError, match="reason"):
        gate.demote_claim("demo", claim_id=claim_id, reason="   ")


def test_demote_rejects_non_active_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    db.update_claim_status(claim_id, "invalidated")
    gate = BlueprintPromotionGate(db)
    with pytest.raises(ValueError, match="only active claims"):
        gate.demote_claim("demo", claim_id=claim_id, reason="again")


def test_demote_rejects_invalid_status(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    gate = BlueprintPromotionGate(db)
    with pytest.raises(ValueError, match="Invalid demotion status"):
        gate.demote_claim("demo", claim_id=claim_id, reason="x", new_status="draft")


def test_superseded_requires_superseding_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    gate = BlueprintPromotionGate(db)
    with pytest.raises(ValueError, match="superseding_claim_id required"):
        gate.demote_claim("demo", claim_id=claim_id, reason="x", new_status="superseded")


def test_lifecycle_event_recorded_on_demotion(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    claim_id = db.save_blueprint_claim(
        "demo",
        claim_text="A",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, "demo", "A"),
    )
    gate = BlueprintPromotionGate(db)
    gate.demote_claim("demo", claim_id=claim_id, reason="Evidence", actor="tester")
    events = db.get_lifecycle_events("demo", claim_id=claim_id)
    assert len(events) == 1
    assert events[0]["reason"] == "Evidence"
    assert events[0]["actor"] == "tester"


def test_meta_shows_lifecycle_and_demotion_records(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    generator = FileViewGenerator(idse_root=idse_root)
    generator.apply_allowed_promotions_to_blueprint(project)
    claims = db.get_blueprint_claims(project)
    target = next(c for c in claims if "SQLite is the authoritative" in c["claim_text"])
    gate = BlueprintPromotionGate(db)
    gate.demote_claim(project, claim_id=target["claim_id"], reason="Evidence changed", actor="tester")
    generator.apply_allowed_promotions_to_blueprint(project)
    meta = generator.generate_blueprint_meta(project).read_text()

    assert "Lifecycle: invalidated" in meta
    assert "## Demotion Record" in meta
    assert "Reason: Evidence changed" in meta
    assert "Actor: tester" in meta


def test_declare_claim_creates_active_declared_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    db.save_artifact(project, "__blueprint__", "intent", "Founding intent.")

    result = gate.declare_claim(
        project,
        claim_text="SQLite is the authoritative storage backend.",
        classification="invariant",
        source_session="__blueprint__",
        source_stages=["intent"],
    )

    claims = db.get_blueprint_claims(project)
    assert result["status"] == "active"
    assert result["origin"] == "declared"
    assert len(claims) == 1
    assert claims[0]["origin"] == "declared"
    assert claims[0]["status"] == "active"


def test_declare_claim_rejects_non_blueprint_session(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)

    with pytest.raises(ValueError, match="__blueprint__"):
        gate.declare_claim(
            "demo",
            claim_text="A claim",
            classification="invariant",
            source_session="feature-1",
            source_stages=["intent"],
        )


def test_declare_claim_rejects_duplicate_active_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    db.save_artifact(project, "__blueprint__", "intent", "Founding intent.")

    gate.declare_claim(
        project,
        claim_text="A claim",
        classification="invariant",
        source_session="__blueprint__",
        source_stages=["intent"],
    )
    with pytest.raises(ValueError, match="Duplicate active claim"):
        gate.declare_claim(
            project,
            claim_text="A claim",
            classification="invariant",
            source_session="__blueprint__",
            source_stages=["intent"],
        )


def test_declare_claim_records_lifecycle_event(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    db.save_artifact(project, "__blueprint__", "intent", "Founding intent.")
    result = gate.declare_claim(
        project,
        claim_text="A claim",
        classification="invariant",
        source_session="__blueprint__",
        source_stages=["intent"],
        actor="architect",
    )

    events = db.get_lifecycle_events(project, claim_id=result["claim_id"])
    assert len(events) == 1
    assert events[0]["old_status"] == ""
    assert events[0]["new_status"] == "active"
    assert events[0]["reason"] == "Founding declaration from blueprint pipeline"
    assert events[0]["actor"] == "architect"


def test_declare_claim_has_no_promotion_record(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    db.save_artifact(project, "__blueprint__", "intent", "Founding intent.")

    result = gate.declare_claim(
        project,
        claim_text="A claim",
        classification="invariant",
        source_session="__blueprint__",
        source_stages=["intent"],
    )

    claim = db.get_blueprint_claims(project, status="active")[0]
    assert claim["claim_id"] == result["claim_id"]
    assert claim["promotion_record_id"] is None


def test_declare_claim_validates_classification(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    db.save_artifact(project, "__blueprint__", "intent", "Founding intent.")

    with pytest.raises(ValueError, match="classification"):
        gate.declare_claim(
            project,
            claim_text="A claim",
            classification="not-valid",
            source_session="__blueprint__",
            source_stages=["intent"],
        )


def test_reinforce_claim_records_event_without_status_change(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    claim_id = db.save_blueprint_claim(
        project,
        claim_text="A claim",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, project, "A claim"),
        origin="converged",
    )

    result = gate.reinforce_claim(
        project,
        claim_id=claim_id,
        reinforcing_session="session-1",
        reinforcing_stage="feedback",
        actor="system",
    )
    claim = db.get_blueprint_claims(project, status="active")[0]
    events = db.get_lifecycle_events(project, claim_id=claim_id)

    assert result["event"] == "reinforced"
    assert claim["status"] == "active"
    assert events[0]["old_status"] == "active"
    assert events[0]["new_status"] == "active"
    assert events[0]["reason"] == "Reinforced by session-1:feedback"


def test_reinforce_claim_rejects_nonexistent_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)

    with pytest.raises(ValueError, match="not found"):
        gate.reinforce_claim(
            "demo",
            claim_id=999,
            reinforcing_session="session-1",
            reinforcing_stage="feedback",
        )


def test_reinforce_claim_rejects_inactive_claim(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    gate = BlueprintPromotionGate(db)
    project = "demo"
    claim_id = db.save_blueprint_claim(
        project,
        claim_text="A claim",
        classification="invariant",
        promotion_record_id=_promotion_record_id(db, project, "A claim"),
        origin="converged",
    )
    db.update_claim_status(claim_id, "invalidated")

    with pytest.raises(ValueError, match="only active claims can be reinforced"):
        gate.reinforce_claim(
            project,
            claim_id=claim_id,
            reinforcing_session="session-1",
            reinforcing_stage="feedback",
        )


def test_blueprint_md_shows_declared_origin(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")
    db.save_blueprint_claim(
        project,
        claim_text="Declared claim text",
        classification="invariant",
        promotion_record_id=None,
        origin="declared",
    )
    content = FileViewGenerator(idse_root=idse_root).apply_allowed_promotions_to_blueprint(project).read_text()

    assert "[invariant|declared] Declared claim text" in content


def test_blueprint_md_shows_converged_origin(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    content = FileViewGenerator(idse_root=idse_root).apply_allowed_promotions_to_blueprint(project).read_text()

    assert "[invariant|converged] SQLite is the authoritative storage backend for project artifacts." in content


def test_meta_md_shows_origin_per_claim(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_promotions(db, project)
    db.save_blueprint_claim(
        project,
        claim_text="Declared claim text",
        classification="boundary",
        promotion_record_id=None,
        origin="declared",
    )
    generator = FileViewGenerator(idse_root=idse_root)
    generator.apply_allowed_promotions_to_blueprint(project)
    meta = generator.generate_blueprint_meta(project).read_text()

    assert "Origin: converged" in meta
    assert "Origin: declared" in meta
