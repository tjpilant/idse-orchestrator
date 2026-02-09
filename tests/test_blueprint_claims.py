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
    assert "- [invariant] SQLite is the authoritative storage backend for project artifacts." in content


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
