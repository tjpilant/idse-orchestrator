from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.blueprint_promotion import BlueprintPromotionGate


def _seed_sources(db: ArtifactDatabase, project: str) -> None:
    db.save_artifact(project, "s1", "intent", "SQLite is default storage backend for all new projects.")
    db.save_artifact(project, "s2", "spec", "New projects must use SQLite as the mandatory storage backend.")


def test_promotion_gate_denies_insufficient_session_diversity(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    db.save_artifact(project, "s1", "intent", "SQLite is default storage backend for all new projects.")
    db.save_artifact(project, "s1", "feedback", "No contradiction found.")
    gate = BlueprintPromotionGate(db)

    decision = gate.evaluate_promotion(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        source_refs=[("s1", "intent")],
        min_convergence_days=0,
    )
    assert decision.status == "DENY"
    assert "INSUFFICIENT_SESSION_DIVERSITY" in decision.failed_tests
    assert "INSUFFICIENT_STAGE_DIVERSITY" in decision.failed_tests


def test_promotion_gate_denies_without_feedback(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    _seed_sources(db, project)
    gate = BlueprintPromotionGate(db)

    decision = gate.evaluate_promotion(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        source_refs=[("s1", "intent"), ("s2", "spec")],
        min_convergence_days=0,
    )
    assert decision.status == "DENY"
    assert "NO_FEEDBACK_EVIDENCE" in decision.failed_tests


def test_promotion_gate_denies_on_feedback_contradiction(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    _seed_sources(db, project)
    db.save_artifact(project, "s1", "feedback", "[CONTRADICTION] This proposal was rejected.")
    db.save_artifact(project, "s2", "feedback", "No contradiction found.")
    gate = BlueprintPromotionGate(db)

    decision = gate.evaluate_promotion(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        source_refs=[("s1", "intent"), ("s2", "spec")],
        min_convergence_days=0,
    )
    assert decision.status == "DENY"
    assert "CONTRADICTED_BY_FEEDBACK" in decision.failed_tests


def test_promotion_gate_allows_and_records(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    _seed_sources(db, project)
    db.save_artifact(project, "s1", "feedback", "Implementation feedback confirmed this constraint.")
    db.save_artifact(project, "s2", "feedback", "Lessons learned reinforced the same invariant.")
    gate = BlueprintPromotionGate(db)

    decision = gate.evaluate_and_record(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        source_refs=[("s1", "intent"), ("s2", "spec")],
        min_convergence_days=0,
        dry_run=False,
    )
    assert decision.status == "ALLOW"
    assert decision.failed_tests == []

    rows = db.list_blueprint_promotions(project, status="ALLOW")
    assert len(rows) == 1
    assert rows[0]["claim_text"] == "SQLite is default storage backend."
    assert rows[0]["classification"] == "invariant"


def test_promotion_gate_ignores_contradiction_word_in_explanatory_text(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    _seed_sources(db, project)
    db.save_artifact(
        project,
        "s1",
        "feedback",
        "Added structured contradiction/reinforcement signals for machine readability.",
    )
    db.save_artifact(project, "s2", "feedback", "Constraint reinforced during implementation.")
    gate = BlueprintPromotionGate(db)

    decision = gate.evaluate_promotion(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        source_refs=[("s1", "intent"), ("s2", "spec")],
        min_convergence_days=0,
    )
    assert decision.status == "ALLOW"
    assert decision.failed_tests == []


def test_extract_candidates_finds_cross_session_claims(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    db.save_artifact(
        project,
        "s1",
        "spec",
        "- SQLite is the default storage backend for project artifacts.\n"
        "- Notion is a sync target.",
    )
    db.save_artifact(
        project,
        "s2",
        "feedback",
        "- SQLite is default storage backend for all project artifacts.\n"
        "- Keep Notion as projection only.",
    )
    gate = BlueprintPromotionGate(db)

    candidates = gate.extract_candidates(
        project,
        min_sources=2,
        min_sessions=2,
        min_stages=2,
        limit=10,
    )

    assert candidates
    assert any(
        item.claim_text == "SQLite is the authoritative storage backend for project artifacts."
        for item in candidates
    )
    top = candidates[0]
    assert top.session_count >= 2
    assert top.support_count >= 2


def test_extract_candidates_uses_canonical_claim_mapping(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    db.save_artifact(
        project,
        "s1",
        "spec",
        "Refactor IDSE orchestration to use SQLite as the authoritative store for projects and artifacts.",
    )
    db.save_artifact(
        project,
        "s2",
        "feedback",
        "Requested explicit split where SQLite is core storage and Notion/filesystem are sync targets only.",
    )
    gate = BlueprintPromotionGate(db)

    candidates = gate.extract_candidates(
        project,
        min_sources=2,
        min_sessions=2,
        min_stages=2,
        limit=10,
    )

    assert candidates
    assert any(
        item.claim_text == "SQLite is the authoritative storage backend for project artifacts."
        for item in candidates
    )


def test_extract_candidates_maps_purpose_from_intent_context(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    project = "demo"
    db.save_artifact(
        project,
        "s1",
        "intent",
        "The IDSE Orchestrator exists to be the design-time Documentation OS for Intent-Driven Systems Engineering.",
    )
    db.save_artifact(
        project,
        "s2",
        "context",
        "IDSE Orchestrator provides design-time cognition as a Documentation OS for teams.",
    )
    gate = BlueprintPromotionGate(db)

    candidates = gate.extract_candidates(
        project,
        min_sources=2,
        min_sessions=2,
        min_stages=2,
        limit=10,
    )

    assert any(
        item.claim_text
        == "IDSE Orchestrator is the design-time Documentation OS for project intent and delivery."
        for item in candidates
    )
