from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.file_view_generator import FileViewGenerator


def test_file_view_generator_session(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    session = "s1"
    db.save_artifact(project, session, "intent", "hello from db")

    generator = FileViewGenerator(idse_root=idse_root)
    written = generator.generate_session(project, session)

    intent_path = (
        idse_root / "projects" / project / "sessions" / session / "intents" / "intent.md"
    )
    assert intent_path in written
    assert intent_path.read_text() == "hello from db"


def test_file_view_generator_project(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    db.save_artifact(project, "s1", "intent", "s1 intent")
    db.save_artifact(project, "s2", "intent", "s2 intent")

    generator = FileViewGenerator(idse_root=idse_root)
    results = generator.generate_project(project, stages=["intent"])

    assert set(results.keys()) == {"s1", "s2"}
    path_s1 = idse_root / "projects" / project / "sessions" / "s1" / "intents" / "intent.md"
    path_s2 = idse_root / "projects" / project / "sessions" / "s2" / "intents" / "intent.md"
    assert path_s1.exists()
    assert path_s2.exists()


def test_generate_blueprint_meta_includes_delivery_summary(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "sqlite-cms-refactor",
        name="sqlite-cms-refactor",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="complete",
    )
    db.save_artifact(
        project,
        "sqlite-cms-refactor",
        "implementation",
        """# Implementation Readme

## Summary
- Added sqlite backend and migration flow.
- Added export and query support.
""",
    )
    db.save_session_state(
        project,
        "sqlite-cms-refactor",
        {
            "project_name": project,
            "session_id": "sqlite-cms-refactor",
            "is_blueprint": False,
            "stages": {
                "intent": "completed",
                "context": "completed",
                "spec": "completed",
                "plan": "completed",
                "tasks": "completed",
                "implementation": "completed",
                "feedback": "completed",
            },
            "last_sync": None,
            "validation_status": "passing",
            "created_at": "2026-02-07T00:00:00",
        },
    )

    generator = FileViewGenerator(idse_root=idse_root)
    meta_path = generator.generate_blueprint_meta(project)
    meta_content = meta_path.read_text()

    assert "## Delivery Summary" in meta_content
    assert "`sqlite-cms-refactor`" in meta_content
    assert "Added sqlite backend and migration flow." in meta_content
    assert "| sqlite-cms-refactor | feature | complete | system |" in meta_content
    assert "| 100% |" in meta_content


def test_generate_blueprint_meta_includes_feedback_rollup(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-a",
        name="feature-a",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="complete",
    )
    db.save_artifact(
        project,
        "feature-a",
        "intent",
        "This session has enough meaningful text to count as progress.",
    )
    db.save_artifact(
        project,
        "feature-a",
        "feedback",
        """# Feedback

### Lessons Learned
- Avoid rebuilding mapping logic in multiple places.
- Keep Notion projection fields outside core spine schema.
""",
    )

    generator = FileViewGenerator(idse_root=idse_root)
    meta_path = generator.generate_blueprint_meta(project)
    meta_content = meta_path.read_text()

    assert "## Feedback & Lessons Learned" in meta_content
    assert "`feature-a`" in meta_content
    assert "Avoid rebuilding mapping logic in multiple places." in meta_content


def test_generate_blueprint_meta_excludes_placeholder_sessions(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-placeholder",
        name="feature-placeholder",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="draft",
    )
    db.save_artifact(
        project,
        "feature-placeholder",
        "implementation",
        """# Implementation Readme
[REQUIRES INPUT]
""",
    )
    db.save_artifact(
        project,
        "feature-placeholder",
        "feedback",
        """# Feedback
[REQUIRES INPUT]
""",
    )

    generator = FileViewGenerator(idse_root=idse_root)
    meta_content = generator.generate_blueprint_meta(project).read_text()

    assert "`feature-placeholder`" not in meta_content.split("## Delivery Summary", 1)[1]
    assert "`feature-placeholder`" not in meta_content.split("## Feedback & Lessons Learned", 1)[1]


def test_blueprint_meta_truncates_long_bullets(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-long",
        name="feature-long",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="complete",
    )
    db.save_artifact(
        project,
        "feature-long",
        "intent",
        "This session has enough meaningful text to count as progress.",
    )
    long_item = "A" * 280
    db.save_artifact(
        project,
        "feature-long",
        "implementation",
        f"""# Implementation Readme

## Executive Summary
- {long_item}
""",
    )

    meta_content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    delivery_section = meta_content.split("## Delivery Summary", 1)[1].split("## Feedback & Lessons Learned", 1)[0]
    line = [x for x in delivery_section.splitlines() if "`feature-long`" in x][0]
    assert len(line) < 320
    assert "..." in line


def test_blueprint_meta_preserves_custom_narrative_block(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )

    meta_path = idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata" / "meta.md"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        """# demo - Blueprint Meta

## Meta Narrative

<!-- BEGIN CUSTOM NARRATIVE -->
Persistent detail line.
- Keep me
<!-- END CUSTOM NARRATIVE -->
"""
    )

    regenerated = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    assert "Persistent detail line." in regenerated
    assert "- Keep me" in regenerated


def test_blueprint_meta_rollup_reads_completion_notes(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"

    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-rich",
        name="feature-rich",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="complete",
    )
    db.save_artifact(project, "feature-rich", "intent", "Sufficiently meaningful intent text for reportability.")
    db.save_artifact(
        project,
        "feature-rich",
        "implementation",
        """# Implementation Readme

## Phase 4 Completion Record
- Added resilient retry handling in sync paths.
""",
    )
    db.save_artifact(
        project,
        "feature-rich",
        "feedback",
        """# Feedback

## Completion Notes
- Live validation surfaced payload shape mismatches.
""",
    )

    content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    assert "Added resilient retry handling in sync paths." in content
    assert "Live validation surfaced payload shape mismatches." in content


def test_blueprint_scope_file_is_created_and_not_overwritten(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )

    generator = FileViewGenerator(idse_root=idse_root)
    scope_path = generator.ensure_blueprint_scope(project)
    initial = scope_path.read_text()
    assert "## Core Invariants" in initial
    assert "Append-only via promotion gate." in initial

    scope_path.write_text("# custom blueprint scope\n")
    generator.generate_blueprint_meta(project)
    assert scope_path.read_text() == "# custom blueprint scope\n"


def test_blueprint_meta_includes_promotion_record_section(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    a = db.save_artifact(project, "s1", "intent", "intent detail content")
    b = db.save_artifact(project, "s2", "spec", "spec detail content")
    a_id = db.get_artifact_id(project, "s1", "intent")
    b_id = db.get_artifact_id(project, "s2", "spec")
    assert a_id is not None
    assert b_id is not None
    db.save_blueprint_promotion(
        project,
        claim_text="SQLite is default storage backend.",
        classification="invariant",
        status="ALLOW",
        evidence_hash="hash123",
        failed_tests=[],
        evidence={
            "source_sessions": ["s1", "s2"],
            "source_stages": ["intent", "spec"],
            "feedback_artifacts": [],
        },
        source_artifact_ids=[a_id, b_id],
        promoted_at="2026-02-08T00:00:00",
    )
    content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    assert "## Blueprint Promotion Record" in content
    assert "SQLite is default storage backend." in content


def test_blueprint_meta_lineage_graph_includes_children(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-a",
        name="feature-a",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-a-sub",
        name="feature-a-sub",
        session_type="feature",
        is_blueprint=False,
        parent_session="feature-a",
        status="draft",
    )

    content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    assert "__blueprint__ (root)" in content
    assert "feature-a" in content
    assert "feature-a-sub" in content


def test_blueprint_meta_active_sessions_excludes_complete(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.ensure_session(
        project,
        "feature-complete",
        name="feature-complete",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="complete",
    )
    db.ensure_session(
        project,
        "feature-progress",
        name="feature-progress",
        session_type="feature",
        is_blueprint=False,
        parent_session="__blueprint__",
        status="in_progress",
    )

    content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    active_section = content.split("### Active Sessions", 1)[1].split("## Session Status Matrix", 1)[0]
    assert "feature-progress" in active_section
    assert "feature-complete" not in active_section
    assert "| feature-complete | feature | complete |" in content


def test_blueprint_meta_dedupes_identical_promotion_records(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    db.save_artifact(project, "s1", "intent", "intent detail content")
    db.save_artifact(project, "s2", "spec", "spec detail content")
    a_id = db.get_artifact_id(project, "s1", "intent")
    b_id = db.get_artifact_id(project, "s2", "spec")
    assert a_id is not None
    assert b_id is not None

    for promoted_at in ["2026-02-08T00:00:00", "2026-02-08T01:00:00"]:
        db.save_blueprint_promotion(
            project,
            claim_text="SQLite is default storage backend.",
            classification="invariant",
            status="ALLOW",
            evidence_hash="hash-dedupe",
            failed_tests=[],
            evidence={
                "source_sessions": ["s1", "s2"],
                "source_stages": ["intent", "spec"],
                "feedback_artifacts": [],
            },
            source_artifact_ids=[a_id, b_id],
            promoted_at=promoted_at,
        )

    content = FileViewGenerator(idse_root=idse_root).generate_blueprint_meta(project).read_text()
    assert content.count("Promoted Claim: SQLite is default storage backend.") == 1


def test_apply_allowed_promotions_projects_claim_into_purpose_section(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(
        project,
        "__blueprint__",
        name="__blueprint__",
        session_type="blueprint",
        is_blueprint=True,
        status="draft",
    )
    a = db.save_artifact(project, "s1", "intent", "intent detail content")
    b = db.save_artifact(project, "s2", "context", "context detail content")
    a_id = db.get_artifact_id(project, "s1", "intent")
    b_id = db.get_artifact_id(project, "s2", "context")
    assert a_id is not None
    assert b_id is not None
    db.save_blueprint_promotion(
        project,
        claim_text="IDSE Orchestrator is the design-time Documentation OS for project intent and delivery.",
        classification="non_negotiable_constraint",
        status="ALLOW",
        evidence_hash="hash-purpose",
        failed_tests=[],
        evidence={
            "source_sessions": ["s1", "s2"],
            "source_stages": ["intent", "context"],
            "feedback_artifacts": [],
        },
        source_artifact_ids=[a_id, b_id],
        promoted_at="2026-02-08T00:00:00",
    )

    generator = FileViewGenerator(idse_root=idse_root)
    blueprint = generator.apply_allowed_promotions_to_blueprint(project).read_text()
    assert "## Purpose" in blueprint
    assert "- IDSE Orchestrator is the design-time Documentation OS for project intent and delivery." in blueprint
    assert (
        "- [non_negotiable_constraint] IDSE Orchestrator is the design-time Documentation OS for project intent and delivery."
        in blueprint
    )
