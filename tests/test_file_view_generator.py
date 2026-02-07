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

    generator = FileViewGenerator(idse_root=idse_root)
    meta_path = generator.generate_blueprint_meta(project)
    meta_content = meta_path.read_text()

    assert "## Delivery Summary" in meta_content
    assert "`sqlite-cms-refactor`" in meta_content
    assert "Added sqlite backend and migration flow." in meta_content


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
