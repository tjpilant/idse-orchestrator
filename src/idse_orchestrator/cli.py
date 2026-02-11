"""
IDSE Orchestrator CLI

Command-line interface for managing IDSE projects in client workspaces.

Commands:
- init: Initialize a new IDSE project with pipeline structure
- validate: Check artifacts for constitutional compliance
- status: Display current project and session status
"""

import click
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys

from . import __version__


@click.group()
@click.version_option(version=__version__, prog_name="idse")
@click.option(
    "--backend",
    type=click.Choice(["sqlite", "filesystem", "notion"], case_sensitive=False),
    help="Override artifact backend for this command.",
)
@click.pass_context
def main(ctx, backend: Optional[str]):
    """
    IDSE Developer Orchestrator

    Manage Intent-Driven Systems Engineering projects in your workspace.
    This CLI coordinates IDE agents and manages pipeline artifacts locally.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    if backend:
        ctx.obj["backend_override"] = backend.lower()


@main.command()
@click.argument("project_name")
@click.option("--stack", default="python", help="Technology stack (python, node, go, etc.)")
@click.option("--guided/--no-guided", default=False, help="Run interactive questionnaire")
@click.option(
    "--agentic",
    type=click.Choice(["agency-swarm", "crew-ai", "autogen"], case_sensitive=False),
    help="Agent framework to integrate (agency-swarm, crew-ai, autogen)",
)
@click.option(
    "--backend",
    type=click.Choice(["sqlite", "filesystem"], case_sensitive=False),
    help="Override artifact backend (filesystem is legacy opt-in).",
)
@click.option("--create-agent-files/--no-create-agent-files", default=True, help="Create agent instruction files (CLAUDE.md, AGENTS.md, .cursorrules)")
@click.pass_context
def init(ctx, project_name: str, stack: str, guided: bool, agentic: Optional[str], backend: Optional[str], create_agent_files: bool):
    """
    Initialize a new IDSE project with blueprint session.

    Creates blueprint session (__blueprint__) for project-level meta-planning.
    Optionally integrates with agent frameworks (Agency Swarm, Crew AI, AutoGen).
    For feature sessions, use 'idse session create'.

    Examples:
        idse init customer-portal --stack python
        idse init my-agency --agentic agency-swarm --guided
    """
    from .project_workspace import ProjectWorkspace

    click.echo(f"🚀 Initializing IDSE project: {project_name}")
    click.echo(f"   Stack: {stack}")

    try:
        if backend:
            from .artifact_config import ArtifactConfig

            config = ArtifactConfig()
            config.config["storage_backend"] = backend.lower()
            config.save()

        manager = ProjectWorkspace()
        project_path = manager.init_project(
            project_name,
            stack,
            create_agent_files=create_agent_files,
            backend=backend,
        )

        # Run guided setup if requested
        if guided:
            from .blueprint_wizard import BlueprintWizard

            wizard = BlueprintWizard()
            artifacts = wizard.run(project_name, stack)

            session_path = project_path / "sessions" / "__blueprint__"

            artifact_map = {
                "intent_md": session_path / "intents" / "intent.md",
                "context_md": session_path / "contexts" / "context.md",
                "spec_md": session_path / "specs" / "spec.md",
                "plan_md": session_path / "plans" / "plan.md",
                "tasks_md": session_path / "tasks" / "tasks.md",
                "feedback_md": session_path / "feedback" / "feedback.md",
                "implementation_readme_md": session_path / "implementation" / "README.md"
            }

            for artifact_name, file_path in artifact_map.items():
                if artifact_name in artifacts:
                    file_path.write_text(artifacts[artifact_name])

            click.echo("\n✅ Blueprint populated with your answers!")

        click.echo("📘 Blueprint session initialized")
        click.echo(f"📁 Location: {project_path}")
        click.echo("📝 Pipeline artifacts created")
        click.echo("📊 Session state initialized")

        if create_agent_files:
            click.echo(f"🤖 Agent instruction files created")

        # Install agentic framework if specified
        if agentic:
            from .framework_installer import install_agentic_framework

            framework_choice = agentic.lower()
            try:
                install_agentic_framework(project_path, framework_choice, stack)
            except Exception as framework_error:
                click.echo(f"⚠️  Warning: Framework installation failed: {framework_error}", err=True)
                click.echo("   Project created successfully, but framework resources not installed.")

        click.echo("")
        click.echo(f"Next steps:")
        click.echo(f"  1. Edit blueprint documents in .idse/projects/{project_name}/sessions/__blueprint__/")
        click.echo(f"  2. Run 'idse validate' to check compliance")
        click.echo(f"  3. Run 'idse status' to view pipeline progress")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def validate(ctx, project: Optional[str]):
    """
    Validate pipeline artifacts for constitutional compliance.

    Checks:
    - All required sections present in artifacts
    - No [REQUIRES INPUT] markers remaining
    - Stage sequencing (Article III compliance)
    - Template compliance (Article IV)

    Example:
        idse validate
        idse validate --project customer-portal
    """
    from .validation_engine import ValidationEngine

    click.echo("🔍 Validating IDSE pipeline artifacts...")

    try:
        validator = ValidationEngine()
        results = validator.validate_project(project, backend_override=ctx.obj.get("backend_override"))

        if results["valid"]:
            click.echo("✅ Validation passed!")
            for check in results["checks"]:
                click.echo(f"   ✓ {check}")
        else:
            click.echo("❌ Validation failed:", err=True)
            for error in results["errors"]:
                click.echo(f"   ✗ {error}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--session", "session_id", help="Session ID (defaults to CURRENT_SESSION)")
@click.option("--all-sessions", is_flag=True, help="Export all sessions for the project")
@click.option("--stages", help="Comma-separated stage list (intent,context,...)")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to .idseconfig.json (defaults to ~/.idseconfig.json)",
)
@click.pass_context
def export(ctx, project: Optional[str], session_id: Optional[str], all_sessions: bool, stages: Optional[str], config_path: Optional[Path]):
    """
    Generate markdown file views from SQLite.

    Example:
        idse export
        idse export --session __blueprint__
        idse export --all-sessions
        idse export --stages intent,context,plan
    """
    from .artifact_config import ArtifactConfig
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace
    from .session_graph import SessionGraph

    config = ArtifactConfig(config_path, backend_override=ctx.obj.get("backend_override"))
    backend = config.get_storage_backend()
    if backend != "sqlite":
        click.echo("❌ Error: export requires sqlite storage backend (set storage_backend=sqlite).", err=True)
        sys.exit(1)

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)

    project_name = project_path.name

    if all_sessions and session_id:
        click.echo("❌ Error: --all-sessions cannot be used with --session.", err=True)
        sys.exit(1)

    stage_list = None
    if stages:
        stage_list = [s.strip() for s in stages.split(",") if s.strip()]

    generator = FileViewGenerator(idse_root=manager.idse_root)

    if all_sessions:
        results = generator.generate_project(project_name, stages=stage_list)
        total = sum(len(paths) for paths in results.values())
        try:
            from .artifact_database import ArtifactDatabase

            current = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False).get_current_session(project_name)
            if current:
                generator.generate_session_state(project_name, current)
                generator.generate_agent_registry(project_name)
            generator.generate_blueprint_meta(project_name)
        except Exception:
            pass
        click.echo(f"✅ Exported {total} artifacts for {len(results)} sessions in {project_name}")
        return

    session_id = session_id or SessionGraph(project_path).get_current_session()
    written = generator.generate_session(project_name, session_id, stages=stage_list)
    try:
        generator.generate_session_state(project_name, session_id)
        generator.generate_agent_registry(project_name)
        generator.generate_blueprint_meta(project_name)
    except Exception:
        pass
    click.echo(f"✅ Exported {len(written)} artifacts for {project_name}/{session_id}")


@main.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--sessions", help="Comma-separated session IDs to migrate")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to .idseconfig.json (defaults to ~/.idseconfig.json)",
)
@click.pass_context
def migrate(ctx, project: Optional[str], sessions: Optional[str], config_path: Optional[Path]):
    """
    Migrate file-based project artifacts into SQLite.

    Example:
        idse migrate
        idse migrate --project my-project
        idse migrate --sessions __blueprint__,session-123
    """
    from .artifact_config import ArtifactConfig
    from .migration import FileToDatabaseMigrator

    config = ArtifactConfig(config_path, backend_override=ctx.obj.get("backend_override"))
    backend = config.get_storage_backend()
    if backend != "sqlite":
        click.echo("❌ Error: migrate requires sqlite storage backend (set storage_backend=sqlite).", err=True)
        sys.exit(1)

    session_list = None
    if sessions:
        session_list = [s.strip() for s in sessions.split(",") if s.strip()]

    migrator = FileToDatabaseMigrator(idse_root=None)
    results = migrator.migrate_project(project_name=project, sessions=session_list)

    total = sum(len(stages) for stages in results.values())
    click.echo(f"✅ Migrated {total} artifacts across {len(results)} sessions")


@main.command()
@click.argument(
    "query_name",
    type=click.Choice(
        ["sessions", "artifacts", "stage-status", "unsynced", "specs-in-progress"], case_sensitive=False
    ),
)
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--session", "session_id", help="Session ID filter for artifacts")
@click.option("--stage", help="Stage filter for artifacts")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to .idseconfig.json (defaults to ~/.idseconfig.json)",
)
@click.pass_context
def query(ctx, query_name: str, project: Optional[str], session_id: Optional[str], stage: Optional[str], config_path: Optional[Path]):
    """
    Run fixed queries against the SQLite backend.

    Example:
        idse query sessions
        idse query artifacts --session __blueprint__
        idse query specs-in-progress
        idse query unsynced
    """
    from .artifact_config import ArtifactConfig
    from .artifact_database import ArtifactDatabase
    from .project_workspace import ProjectWorkspace

    config = ArtifactConfig(config_path, backend_override=ctx.obj.get("backend_override"))
    if config.get_storage_backend() != "sqlite":
        click.echo("❌ Error: query requires sqlite storage backend (set storage_backend=sqlite).", err=True)
        sys.exit(1)

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
    project_name = project_path.name

    db = ArtifactDatabase(idse_root=manager.idse_root)
    query_name = query_name.lower()

    if query_name == "sessions":
        sessions = db.list_sessions(project_name)
        click.echo(f"Sessions ({len(sessions)}):")
        for sid in sessions:
            click.echo(f" - {sid}")
        return

    if query_name == "artifacts":
        records = db.list_artifacts(project_name, session_id=session_id, stage=stage)
        click.echo(f"Artifacts ({len(records)}):")
        for record in records:
            click.echo(f" - {record.session_id}/{record.stage} ({record.updated_at})")
        return

    if query_name == "stage-status":
        from .session_graph import SessionGraph

        current_session = SessionGraph(project_path).get_current_session()
        try:
            state = db.load_session_state(project_name, current_session)
        except FileNotFoundError:
            click.echo("No session state recorded.")
            return
        click.echo(f"Project: {state.get('project_name')}")
        click.echo(f"Session: {state.get('session_id', current_session)}")
        click.echo("Stages:")
        for stage_name, status in state.get("stages", {}).items():
            click.echo(f" - {stage_name}: {status}")
        return

    if query_name == "unsynced":
        from .session_graph import SessionGraph

        current_session = SessionGraph(project_path).get_current_session()
        try:
            state = db.load_session_state(project_name, current_session)
        except FileNotFoundError:
            click.echo("No session state recorded.")
            return
        last_sync = state.get("last_sync") or "Never"
        click.echo(f"Last Sync: {last_sync}")
        return

    if query_name == "specs-in-progress":
        records = db.find_artifacts_with_marker(project_name, "spec", "[REQUIRES INPUT]")
        if not records:
            click.echo("No spec artifacts marked in progress.")
            return
        click.echo("Specs in progress:")
        for record in records:
            click.echo(f" - {record.session_id}/spec")


@main.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to .idseconfig.json (defaults to ~/.idseconfig.json)",
)
@click.pass_context
def sync(ctx, config_path: Optional[Path]):
    """Sync pipeline artifacts via configured DesignStore backends."""
    ctx.obj["config_path"] = config_path


@sync.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--session", "session_override", help="Session ID (uses CURRENT_SESSION if not specified)")
@click.option("--yes", is_flag=True, help="Skip overwrite confirmation")
@click.option("--debug", is_flag=True, help="Print MCP payloads")
@click.option("--force-create", is_flag=True, help="Always create new pages (no upsert)")
@click.pass_context
def push(ctx, project: Optional[str], session_override: Optional[str], yes: bool, debug: bool, force_create: bool):
    """
    Write pipeline artifacts through the DesignStore.

    Persists artifacts via the configured storage backend and
    updates the sync timestamp.

    Example:
        idse sync push
        idse sync push --project customer-portal
    """
    from .project_workspace import ProjectWorkspace
    from .artifact_config import ArtifactConfig
    from .design_store import DesignStoreFilesystem
    from .stage_state_model import StageStateModel
    from .session_graph import SessionGraph
    from .artifact_database import ArtifactDatabase, hash_content
    from .design_store_sqlite import DesignStoreSQLite

    try:
        manager = ProjectWorkspace()
        if project:
            project_path = manager.projects_root / project
        else:
            project_path = manager.get_current_project()
            if not project_path:
                click.echo("❌ Error: No IDSE project found", err=True)
                sys.exit(1)

        project_name = project_path.name
        session_id = session_override or SessionGraph(project_path).get_current_session()
        session_path = project_path / "sessions" / session_id

        artifacts = {}
        config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))
        storage_backend = config.get_storage_backend()
        sync_backend = config.get_sync_backend()
        use_db = storage_backend == "sqlite"
        db = None
        if use_db:
            db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
        stage_paths = {
            "intent": session_path / "intents" / "intent.md",
            "context": session_path / "contexts" / "context.md",
            "spec": session_path / "specs" / "spec.md",
            "plan": session_path / "plans" / "plan.md",
            "tasks": session_path / "tasks" / "tasks.md",
            "implementation": session_path / "implementation" / "README.md",
            "feedback": session_path / "feedback" / "feedback.md",
        }
        for stage, path in stage_paths.items():
            if use_db:
                try:
                    record = db.load_artifact(project_name, session_id, stage)
                    artifacts[stage] = record.content
                    continue
                except FileNotFoundError:
                    pass
            if path.exists():
                artifacts[stage] = path.read_text()

        remote_store = config.get_design_store(manager.idse_root, purpose="sync")
        if debug and hasattr(remote_store, "set_debug"):
            remote_store.set_debug(True)
        if force_create and hasattr(remote_store, "set_force_create"):
            remote_store.set_force_create(True)
        if use_db:
            tracker = StageStateModel(
                store=DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False),
                project_name=project_name,
                session_id=session_id,
            )
        else:
            tracker = StageStateModel(project_path)

        if not yes and not click.confirm(
            f"Overwrite remote artifacts for {project_name}/{session_id}?"
        ):
            click.echo("ℹ️  Sync push cancelled.")
            return

        click.echo(f"📤 Syncing artifacts for {project_name}/{session_id}...")
        click.echo(f"   Storage: {storage_backend}")
        click.echo(f"   Sync Target: {sync_backend}")
        pushed = []
        skipped = []
        failed = []
        for stage, content in artifacts.items():
            try:
                if use_db and sync_backend == "notion":
                    remote_store.save_artifact(project_name, session_id, stage, content)
                    if getattr(remote_store, "last_write_skipped", False):
                        skipped.append(stage)
                    else:
                        pushed.append(stage)
                    continue

                local_hash = hash_content(content)
                try:
                    remote_content = remote_store.load_artifact(project_name, session_id, stage)
                    remote_hash = hash_content(remote_content)
                    if remote_hash == local_hash:
                        skipped.append(stage)
                        continue
                except FileNotFoundError:
                    pass
                remote_store.save_artifact(project_name, session_id, stage, content)
                pushed.append(stage)
            except Exception as exc:
                failed.append((stage, str(exc)))
        tracker.mark_synced()

        click.echo(f"✅ Synced {len(pushed)} stages")
        click.echo(f"   Stages: {', '.join(pushed)}")
        if skipped:
            click.echo(f"   Skipped (unchanged): {', '.join(skipped)}")
        if failed:
            click.echo(f"   Failed: {', '.join(stage for stage, _ in failed)}")
            for stage, message in failed:
                click.echo(f"     - {stage}: {message}")
        click.echo(f"   Timestamp: {tracker.get_status().get('last_sync')}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--session", "session_override", help="Session ID (uses CURRENT_SESSION if not specified)")
@click.option("--yes", is_flag=True, help="Skip overwrite confirmation")
@click.pass_context
def pull(ctx, project: Optional[str], session_override: Optional[str], yes: bool):
    """
    Read pipeline artifacts from the DesignStore.

    Retrieves artifacts via the configured storage backend.

    Example:
        idse sync pull
        idse sync pull --session __blueprint__
    """
    from .project_workspace import ProjectWorkspace
    from .artifact_config import ArtifactConfig
    from .design_store import DesignStoreFilesystem
    from .stage_state_model import StageStateModel
    from .session_graph import SessionGraph
    from .artifact_database import ArtifactDatabase, hash_content
    from .design_store_sqlite import DesignStoreSQLite
    from .file_view_generator import FileViewGenerator

    try:
        manager = ProjectWorkspace()
        if project:
            project_path = manager.projects_root / project
        else:
            project_path = manager.get_current_project()
            if not project_path:
                click.echo("❌ Error: No IDSE project found", err=True)
                sys.exit(1)

        project_name = project_path.name
        session_id = session_override or SessionGraph(project_path).get_current_session()

        config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))
        storage_backend = config.get_storage_backend()
        sync_backend = config.get_sync_backend()
        use_db = storage_backend == "sqlite"
        db = None
        if use_db:
            db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
        local_store = DesignStoreFilesystem(manager.idse_root)
        remote_store = config.get_design_store(manager.idse_root, purpose="sync")
        if use_db:
            tracker = StageStateModel(
                store=DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False),
                project_name=project_name,
                session_id=session_id,
            )
        else:
            tracker = StageStateModel(project_path)

        if not yes and not click.confirm(
            f"Overwrite local artifacts for {project_name}/{session_id}?"
        ):
            click.echo("ℹ️  Sync pull cancelled.")
            return

        click.echo(f"📥 Pulling artifacts for {project_name}/{session_id}...")
        click.echo(f"   Storage: {storage_backend}")
        click.echo(f"   Sync Source: {sync_backend}")
        artifacts = {}
        failed = []
        for stage in DesignStoreFilesystem.STAGE_PATHS.keys():
            try:
                artifacts[stage] = remote_store.load_artifact(project_name, session_id, stage)
            except FileNotFoundError:
                continue
            except Exception as exc:
                failed.append((stage, str(exc)))
                continue
        changed_stages = []
        for stage, content in artifacts.items():
            try:
                if use_db:
                    try:
                        local_record = db.load_artifact(project_name, session_id, stage)
                        if local_record.content_hash == hash_content(content):
                            continue
                    except FileNotFoundError:
                        pass
                    db.save_artifact(project_name, session_id, stage, content)
                    changed_stages.append(stage)
                else:
                    local_store.save_artifact(project_name, session_id, stage, content)
            except Exception as exc:
                failed.append((stage, str(exc)))
        tracker.mark_synced()

        if use_db and changed_stages:
            generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
            generator.generate_session(project_name, session_id, stages=changed_stages)
            generator.generate_session_state(project_name, session_id)
            generator.generate_agent_registry(project_name)
            generator.generate_blueprint_meta(project_name)

        click.echo(f"✅ Retrieved {len(artifacts)} stage artifacts")
        for stage in artifacts:
            click.echo(f"   ✓ {stage}")
        if failed:
            click.echo(f"   Failed: {', '.join(stage for stage, _ in failed)}")
            for stage, message in failed:
                click.echo(f"     - {stage}: {message}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.pass_context
def setup(ctx):
    """Configure storage/sync backends."""
    from .artifact_config import ArtifactConfig

    config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))

    # Storage remains SQLite by default and should not be changed in normal workflows.
    config.config.setdefault("storage_backend", "sqlite")

    backend = click.prompt(
        "Sync backend", type=click.Choice(["filesystem", "notion", "sqlite"]), default="filesystem"
    )
    config.config["sync_backend"] = backend

    if backend == "filesystem":
        base_path = click.prompt(
            "Base path for filesystem backend",
            default="",
            show_default=False,
        )
        if base_path:
            config.config["base_path"] = base_path

    if backend == "sqlite":
        db_path = click.prompt(
            "SQLite db path",
            default=str(Path.cwd() / ".idse" / "idse.db"),
        )
        config.config["sqlite"] = {"db_path": db_path}

    if backend == "notion":
        database_id = click.prompt("Notion database ID")
        credentials_dir = click.prompt(
            "Credentials directory",
            default=str(Path.cwd() / "mnt" / "mcp_credentials"),
        )
        config.config["notion"] = {
            "database_id": database_id,
            "credentials_dir": credentials_dir,
        }

    config.save()
    click.echo(f"✅ Saved config to {config.config_path}")


@sync.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def status(ctx, project: Optional[str]):
    """Show sync backend and last sync timestamp."""
    from .artifact_config import ArtifactConfig
    from .project_workspace import ProjectWorkspace
    from .stage_state_model import StageStateModel

    config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))
    backend = config.get_sync_backend()
    storage_backend = config.get_storage_backend()

    manager = ProjectWorkspace()
    project_path = manager.projects_root / project if project else manager.get_current_project()
    if not project_path:
        click.echo("❌ Error: No IDSE project found", err=True)
        sys.exit(1)

    tracker = StageStateModel(project_path)
    state = tracker.get_status()
    click.echo("🔗 Sync Status")
    click.echo(f"Storage Backend: {storage_backend}")
    click.echo(f"Sync Backend: {backend}")
    click.echo(f"Last Sync: {state.get('last_sync', 'Never')}")


@sync.command()
@click.pass_context
def test(ctx):
    """Validate sync backend connectivity and schema."""
    from .artifact_config import ArtifactConfig
    from .project_workspace import ProjectWorkspace

    config_path = ctx.obj.get("config_path")
    config = ArtifactConfig(config_path, backend_override=ctx.obj.get("backend_override"))
    backend = config.get_sync_backend()

    click.echo("🧪 Sync Backend Test")
    click.echo(f"Backend: {backend}")
    click.echo(f"Config: {config.config_path}")

    if backend == "filesystem":
        manager = ProjectWorkspace()
        idse_root = manager.idse_root
        if not idse_root.exists():
            click.echo("❌ Filesystem backend not found: .idse missing", err=True)
            sys.exit(1)
        click.echo(f"✅ Filesystem backend available at {idse_root}")
        return

    try:
        store = config.get_design_store(purpose="sync")
        validate = getattr(store, "validate_backend", None)
        if not callable(validate):
            click.echo("⚠️  Backend does not provide validation.")
            return
        if backend == "notion":
            notion_cfg = config.config.get("notion", {})
            tool_names = notion_cfg.get("tool_names")
            if tool_names:
                click.echo(f"Tool Names: {tool_names}")
        result = validate()
        if result.get("checks"):
            for check in result["checks"]:
                click.echo(f"   ✓ {check}")
        if result.get("warnings"):
            for warning in result["warnings"]:
                click.echo(f"   ! {warning}")
        click.echo("✅ Backend validation complete")
    except Exception as e:
        click.echo(f"❌ Backend validation failed: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.option("--schema", "show_schema", is_flag=True, help="Show tool input schemas")
@click.pass_context
def tools(ctx, show_schema: bool):
    """List MCP tools available for the configured backend."""
    from .artifact_config import ArtifactConfig

    config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))
    backend = config.get_sync_backend()

    click.echo("🧰 Sync Backend Tools")
    click.echo(f"Backend: {backend}")

    if backend == "filesystem":
        click.echo("Filesystem backend has no MCP tools.")
        return

    store = config.get_design_store(purpose="sync")
    if not hasattr(store, "list_tools"):
        click.echo("Backend does not expose MCP tools.")
        return

    tools = store.list_tools()
    tool_list = getattr(tools, "tools", []) if tools else []
    if not tool_list:
        click.echo("No tools returned.")
        return

    for tool in tool_list:
        click.echo(f" - {tool.name}")
        if show_schema and getattr(tool, "inputSchema", None):
            import json

            click.echo(json.dumps(tool.inputSchema, indent=2))


@sync.command()
@click.pass_context
def describe(ctx):
    """Describe the backend by dumping raw MCP query response."""
    from .artifact_config import ArtifactConfig

    config = ArtifactConfig(ctx.obj.get("config_path"), backend_override=ctx.obj.get("backend_override"))
    backend = config.get_sync_backend()

    click.echo("🧾 Backend Description")
    click.echo(f"Backend: {backend}")

    if backend == "filesystem":
        click.echo("Filesystem backend has no remote metadata.")
        return

    store = config.get_design_store(purpose="sync")
    describe = getattr(store, "describe_backend", None)
    if not callable(describe):
        click.echo("Backend does not support describe.")
        return

    data = describe()
    import json

    click.echo(json.dumps(data, indent=2))


@main.group()
def artifact():
    """Manage pipeline artifacts in the SQLite store."""
    pass


@artifact.command("write")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--session", "session_id", help="Session ID (defaults to CURRENT_SESSION)")
@click.option("--stage", required=True, help="Stage name (intent, context, spec, plan, tasks, implementation, feedback)")
@click.option("--file", "file_path", type=click.Path(dir_okay=False, path_type=Path), help="Read content from file")
@click.pass_context
def artifact_write(ctx, project: Optional[str], session_id: Optional[str], stage: str, file_path: Optional[Path]):
    """
    Write an artifact into SQLite and regenerate its file view.

    Example:
        idse --backend sqlite artifact write --stage feedback < feedback.md
        idse --backend sqlite artifact write --session my-session --stage plan --file plans/plan.md
    """
    from .artifact_config import ArtifactConfig
    from .design_store import DesignStoreFilesystem
    from .project_workspace import ProjectWorkspace
    from .session_graph import SessionGraph

    config = ArtifactConfig(
        ctx.obj.get("config_path"),
        backend_override=ctx.obj.get("backend_override"),
    )
    if config.get_storage_backend() != "sqlite":
        click.echo("❌ Error: artifact write requires sqlite backend.", err=True)
        sys.exit(1)

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)

    project_name = project_path.name
    session_id = session_id or SessionGraph(project_path).get_current_session()

    if stage not in DesignStoreFilesystem.STAGE_PATHS:
        click.echo(f"❌ Error: Unknown stage '{stage}'", err=True)
        sys.exit(1)

    if file_path:
        content = file_path.read_text()
    else:
        content = click.get_text_stream("stdin").read()
        if not content:
            click.echo("❌ Error: No content provided on stdin.", err=True)
            sys.exit(1)

    store = config.get_design_store(manager.idse_root)
    store.save_artifact(project_name, session_id, stage, content)
    click.echo(f"✅ Wrote {stage} for {project_name}/{session_id}")


@main.group()
def agents():
    """Manage IDE agent registry and tool hooks."""
    pass


@agents.command("install-hooks")
@click.option("--force", is_flag=True, help="Overwrite existing hooks")
@click.pass_context
def install_hooks(ctx, force: bool):
    """
    Install Claude Code hooks for Agent Mode enforcement.

    Copies hook scripts to .claude/hooks/ and updates .claude/settings.local.json
    to enforce 'planning' vs 'implementation' mode restrictions.

    Example:
        idse agents install-hooks
    """
    import shutil
    import json
    from pathlib import Path
    
    # 1. Locate resource
    pkg_root = Path(__file__).resolve().parent
    hook_src = pkg_root / "resources" / "hooks" / "enforce-agent-mode.sh"
    
    if not hook_src.exists():
        click.echo("❌ Error: Bundled hook script not found.", err=True)
        sys.exit(1)

    # 2. Determine target
    # Assume we are in the project root or look for .claude dir
    project_root = Path.cwd()
    claude_dir = project_root / ".claude"
    hooks_dir = claude_dir / "hooks"
    
    if not claude_dir.exists():
        click.echo(f"⚠️  No .claude directory found at {project_root}. Creating it...")
        claude_dir.mkdir(parents=True, exist_ok=True)
    
    hooks_dir.mkdir(exist_ok=True)
    target_script = hooks_dir / "enforce-agent-mode.sh"

    # 3. Copy hook script
    if target_script.exists() and not force:
        click.echo(f"ℹ️  Hook script already exists at {target_script}. Use --force to overwrite.")
    else:
        shutil.copy2(hook_src, target_script)
        target_script.chmod(0o755)  # Make executable
        click.echo(f"✅ Installed hook script: {target_script}")

    # 4. Update settings.local.json
    settings_file = claude_dir / "settings.local.json"
    settings = {}
    
    if settings_file.exists():
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            click.echo(f"⚠️  Warning: Could not parse {settings_file}. Starting with empty settings.")

    # Ensure structure exists
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PreToolUse" not in settings["hooks"]:
        settings["hooks"]["PreToolUse"] = []

    # Define the hook configurations
    hook_configs = [
        {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
                {
                    "type": "command",
                    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/enforce-agent-mode.sh"
                }
            ]
        },
        {
            "matcher": "Bash",
            "hooks": [
                {
                    "type": "command",
                    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/enforce-agent-mode.sh"
                }
            ]
        }
    ]

    # Merge hooks (avoid duplicates)
    existing_hooks = settings["hooks"]["PreToolUse"]
    updated = False
    
    for new_hook in hook_configs:
        is_duplicate = False
        for i, exist in enumerate(existing_hooks):
            # Simple deduplication based on matcher
            if exist.get("matcher") == new_hook["matcher"]:
                # Check if command matches
                cmds = exist.get("hooks", [])
                if any(h.get("command", "").endswith("enforce-agent-mode.sh") for h in cmds):
                     is_duplicate = True
                     break
        
        if not is_duplicate:
            existing_hooks.append(new_hook)
            updated = True

    if updated:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        click.echo(f"✅ Updated {settings_file} with pre-tool hooks.")
    else:
        click.echo(f"ℹ️  Settings already configured.")



@agents.command("list")
def agents_list():
    """List registered IDE agents."""
    from .agent_registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.list_agents()
    if not agents:
        click.echo("No agents registered.")
        return

    click.echo("🤖 Agent Registry")
    for agent in agents:
        agent_id = agent.get("id", "unknown")
        role = agent.get("role", "unknown")
        mode = agent.get("mode", "unknown")
        stages = ", ".join(agent.get("stages", []))
        click.echo(f" - {agent_id} | role: {role} | mode: {mode} | stages: {stages}")


@agents.command("set-mode")
@click.argument("agent_id")
@click.argument("mode", type=click.Choice(["planning", "implementation"], case_sensitive=False))
def agents_set_mode(agent_id: str, mode: str):
    """Set agent mode (planning or implementation)."""
    from .agent_registry import AgentRegistry

    registry = AgentRegistry()
    try:
        updated = registry.set_agent_mode(agent_id, mode.lower())
    except KeyError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"✅ Updated {updated.get('id')} mode → {updated.get('mode')}")


@agents.command("set-role")
@click.argument("agent_id")
@click.argument("role")
def agents_set_role(agent_id: str, role: str):
    """Set agent role label."""
    from .agent_registry import AgentRegistry

    registry = AgentRegistry()
    try:
        updated = registry.set_agent_role(agent_id, role)
    except KeyError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"✅ Updated {updated.get('id')} role → {updated.get('role')}")


@main.group()
def docs():
    """Manage local IDSE reference docs and templates."""
    pass


@main.group()
def blueprint():
    """Manage Blueprint promotion and governance controls."""
    pass


@blueprint.command("promote")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--claim", "claim_text", required=True, help="Atomic claim to evaluate for promotion")
@click.option(
    "--classification",
    required=True,
    type=click.Choice(
        ["invariant", "boundary", "ownership_rule", "non_negotiable_constraint"],
        case_sensitive=False,
    ),
    help="Constitutional class for the claim",
)
@click.option(
    "--source",
    "source_refs",
    multiple=True,
    required=True,
    help="Artifact reference in session:stage format (repeatable)",
)
@click.option("--min-days", default=7, show_default=True, help="Minimum temporal stability window")
@click.option("--dry-run", is_flag=True, help="Evaluate without persisting promotion decision")
@click.pass_context
def blueprint_promote(
    ctx,
    project: Optional[str],
    claim_text: str,
    classification: str,
    source_refs: tuple[str, ...],
    min_days: int,
    dry_run: bool,
):
    """Evaluate and promote converged intent into blueprint scope."""
    from .artifact_database import ArtifactDatabase
    from .blueprint_promotion import BlueprintPromotionGate
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    parsed_sources: list[tuple[str, str]] = []
    for ref in source_refs:
        if ":" not in ref:
            click.echo(f"❌ Error: Invalid --source '{ref}'. Expected session:stage.", err=True)
            sys.exit(1)
        session_id, stage = ref.split(":", 1)
        parsed_sources.append((session_id.strip(), stage.strip()))

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    gate = BlueprintPromotionGate(db)
    decision = gate.evaluate_and_record(
        project,
        claim_text=claim_text,
        classification=classification.lower(),
        source_refs=parsed_sources,
        min_convergence_days=min_days,
        dry_run=dry_run,
    )

    click.echo(f"Blueprint Promotion Decision: {decision.status}")
    if decision.failed_tests:
        click.echo(f"Failed Tests: {', '.join(decision.failed_tests)}")
    click.echo(f"Evidence Hash: {decision.evidence_hash}")
    click.echo(
        "Evidence: "
        f"sessions={len(decision.evidence.get('source_sessions', []))}, "
        f"stages={len(decision.evidence.get('source_stages', []))}, "
        f"feedback={len(decision.evidence.get('feedback_artifacts', []))}"
    )

    if not dry_run:
        generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
        if decision.status == "ALLOW":
            generator.apply_allowed_promotions_to_blueprint(project)
        generator.generate_blueprint_meta(project)
        click.echo("✅ Blueprint artifacts regenerated")


@blueprint.command("declare")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--claim", "claim_text", required=True, help="Founding claim text to declare")
@click.option(
    "--classification",
    required=True,
    type=click.Choice(
        ["invariant", "boundary", "ownership_rule", "non_negotiable_constraint"],
        case_sensitive=False,
    ),
    help="Constitutional class for the claim",
)
@click.option(
    "--source",
    "sources",
    multiple=True,
    required=True,
    help="Artifact reference in session:stage format (repeatable)",
)
@click.option("--actor", default="architect", show_default=True, help="Actor performing declaration")
def blueprint_declare(
    project: Optional[str],
    claim_text: str,
    classification: str,
    sources: tuple[str, ...],
    actor: str,
):
    """Declare a founding blueprint claim without convergence-gate requirements."""
    from .artifact_database import ArtifactDatabase
    from .blueprint_promotion import BlueprintPromotionGate
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    parsed_sources: list[tuple[str, str]] = []
    for source in sources:
        if ":" not in source:
            click.echo(f"❌ Error: Invalid --source '{source}'. Expected session:stage.", err=True)
            sys.exit(1)
        session_id, stage = source.split(":", 1)
        parsed_sources.append((session_id.strip(), stage.strip()))

    source_sessions = {session_id for session_id, _ in parsed_sources}
    if len(source_sessions) != 1:
        click.echo("❌ Error: All --source values must share the same session.", err=True)
        sys.exit(1)
    source_session = parsed_sources[0][0]

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    for session_id, stage in parsed_sources:
        if db.get_artifact_id(project, session_id, stage) is None:
            click.echo(
                f"❌ Error: source artifact not found for {project}/{session_id}:{stage}.",
                err=True,
            )
            sys.exit(1)

    gate = BlueprintPromotionGate(db)
    try:
        result = gate.declare_claim(
            project,
            claim_text=claim_text,
            classification=classification.lower(),
            source_session=source_session,
            source_stages=[stage for _, stage in parsed_sources],
            actor=actor,
        )
    except ValueError as exc:
        click.echo(f"❌ Error: {exc}", err=True)
        sys.exit(1)

    generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
    generator.apply_allowed_promotions_to_blueprint(project)
    generator.generate_blueprint_meta(project)
    click.echo(
        f"✅ Declared claim {result['claim_id']} [{classification.lower()}|{result['origin']}]"
    )


@blueprint.command("reinforce")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--claim-id", required=True, type=int, help="Claim ID to reinforce")
@click.option(
    "--source",
    required=True,
    help="Artifact reference in session:stage format",
)
@click.option("--actor", default="system", show_default=True, help="Actor recording reinforcement")
def blueprint_reinforce(
    project: Optional[str],
    claim_id: int,
    source: str,
    actor: str,
):
    """Record reinforcement evidence for an active claim without changing claim status."""
    from .artifact_database import ArtifactDatabase
    from .blueprint_promotion import BlueprintPromotionGate
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    if ":" not in source:
        click.echo(f"❌ Error: Invalid --source '{source}'. Expected session:stage.", err=True)
        sys.exit(1)
    session_id, stage = source.split(":", 1)
    session_id = session_id.strip()
    stage = stage.strip()

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    if db.get_artifact_id(project, session_id, stage) is None:
        click.echo(
            f"❌ Error: source artifact not found for {project}/{session_id}:{stage}.",
            err=True,
        )
        sys.exit(1)

    gate = BlueprintPromotionGate(db)
    try:
        result = gate.reinforce_claim(
            project,
            claim_id=claim_id,
            reinforcing_session=session_id,
            reinforcing_stage=stage,
            actor=actor,
        )
    except ValueError as exc:
        click.echo(f"❌ Error: {exc}", err=True)
        sys.exit(1)

    FileViewGenerator(idse_root=manager.idse_root, allow_create=False).generate_blueprint_meta(project)
    click.echo(f"✅ Reinforced claim {result['claim_id']}")


@blueprint.command("extract-candidates")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option(
    "--stage",
    "stages",
    multiple=True,
    help="Limit extraction to stage(s). Repeatable (intent,context,spec,plan,tasks,implementation,feedback). Defaults to intent/context/spec/implementation/feedback.",
)
@click.option("--min-sources", default=2, show_default=True, help="Minimum source references per candidate")
@click.option("--min-sessions", default=2, show_default=True, help="Minimum unique sessions per candidate")
@click.option("--min-stages", default=2, show_default=True, help="Minimum unique stages per candidate")
@click.option("--limit", default=20, show_default=True, help="Maximum candidates to return")
@click.option("--evaluate", is_flag=True, help="Also run promotion gate (dry-run) for each extracted candidate")
@click.option("--min-days", default=7, show_default=True, help="Minimum temporal stability window for evaluation")
@click.option("--json", "json_output", is_flag=True, help="Output candidates as JSON")
def blueprint_extract_candidates(
    project: Optional[str],
    stages: tuple[str, ...],
    min_sources: int,
    min_sessions: int,
    min_stages: int,
    limit: int,
    evaluate: bool,
    min_days: int,
    json_output: bool,
):
    """Extract cross-session blueprint promotion candidates from SQLite artifacts."""
    import json

    from .artifact_database import ArtifactDatabase
    from .blueprint_promotion import BlueprintPromotionGate
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    gate = BlueprintPromotionGate(db)
    candidates = gate.extract_candidates(
        project,
        stages=stages,
        min_sources=min_sources,
        min_sessions=min_sessions,
        min_stages=min_stages,
        limit=limit,
    )

    if not candidates:
        click.echo("No candidates found for current thresholds.")
        return

    if json_output:
        payload = []
        for idx, candidate in enumerate(candidates, start=1):
            item = {
                "index": idx,
                "claim_text": candidate.claim_text,
                "suggested_classification": candidate.suggested_classification,
                "support_count": candidate.support_count,
                "session_count": candidate.session_count,
                "stage_count": candidate.stage_count,
                "source_refs": [f"{session}:{stage}" for session, stage in candidate.source_refs],
            }
            if evaluate:
                decision = gate.evaluate_promotion(
                    project,
                    claim_text=candidate.claim_text,
                    classification=candidate.suggested_classification,
                    source_refs=candidate.source_refs,
                    min_convergence_days=min_days,
                )
                item["evaluation"] = {
                    "status": decision.status,
                    "failed_tests": decision.failed_tests,
                    "evidence_hash": decision.evidence_hash,
                }
            payload.append(item)
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"Extracted {len(candidates)} candidate(s):")
    for idx, candidate in enumerate(candidates, start=1):
        click.echo(f"{idx}. {candidate.claim_text}")
        click.echo(
            f"   Suggested: {candidate.suggested_classification} | "
            f"support={candidate.support_count} sessions={candidate.session_count} stages={candidate.stage_count}"
        )
        click.echo(
            "   Sources: " + ", ".join(f"{session}:{stage}" for session, stage in candidate.source_refs)
        )
        if evaluate:
            decision = gate.evaluate_promotion(
                project,
                claim_text=candidate.claim_text,
                classification=candidate.suggested_classification,
                source_refs=candidate.source_refs,
                min_convergence_days=min_days,
            )
            summary = f"{decision.status} ({decision.evidence_hash[:12]})"
            if decision.failed_tests:
                summary += f" failed={','.join(decision.failed_tests)}"
            click.echo(f"   Gate: {summary}")


@blueprint.command("verify")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--accept", is_flag=True, help="Accept current blueprint file as authoritative hash.")
def blueprint_verify(project: Optional[str], accept: bool):
    """Verify blueprint.md integrity against stored authoritative hash."""
    from .artifact_database import ArtifactDatabase, hash_content
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
    warning_msg = generator.verify_blueprint_integrity(project)
    if warning_msg is None:
        click.echo("✅ Blueprint integrity OK")
        return

    click.echo(f"⚠️  {warning_msg}")
    if not accept:
        sys.exit(1)

    scope = generator.ensure_blueprint_scope(project)
    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    expected_hash = db.get_blueprint_hash(project) or ""
    actual_hash = hash_content(scope.read_text())
    db.record_integrity_event(project, expected_hash, actual_hash, "accept")
    db.save_blueprint_hash(project, actual_hash)
    click.echo("✅ Accepted current blueprint content and updated authoritative hash")


@blueprint.command("claims")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--status", help="Optional status filter (active, superseded, invalidated)")
@click.option("--all", "show_all", is_flag=True, help="Show all claims (same as omitting --status).")
def blueprint_claims(project: Optional[str], status: Optional[str], show_all: bool):
    """List blueprint claims and lifecycle status."""
    from .artifact_database import ArtifactDatabase
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    if status and status not in {"active", "superseded", "invalidated"}:
        click.echo("❌ Error: --status must be one of active|superseded|invalidated", err=True)
        sys.exit(1)
    filter_status = None if show_all else status

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    claims = db.get_blueprint_claims(project, status=filter_status)
    if not claims:
        click.echo("No blueprint claims found.")
        return
    for claim in claims:
        click.echo(
            f"{claim['claim_id']}: [{claim['classification']}] {claim['status']} | "
            f"{claim['claim_text']} | created={claim['created_at']}"
        )


@blueprint.command("demote")
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--claim-id", required=True, type=int, help="Claim ID to demote")
@click.option("--reason", required=True, help="Evidence-based reason for demotion")
@click.option(
    "--status",
    "new_status",
    default="invalidated",
    show_default=True,
    type=click.Choice(["superseded", "invalidated"], case_sensitive=False),
    help="Lifecycle status to apply",
)
@click.option("--superseding-claim-id", type=int, help="Required when --status superseded")
@click.option("--actor", default="operator", show_default=True, help="Actor performing demotion")
def blueprint_demote(
    project: Optional[str],
    claim_id: int,
    reason: str,
    new_status: str,
    superseding_claim_id: Optional[int],
    actor: str,
):
    """Demote a blueprint claim via lifecycle gate checks."""
    from .artifact_database import ArtifactDatabase
    from .blueprint_promotion import BlueprintPromotionGate
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            click.echo("❌ Error: No IDSE project found", err=True)
            sys.exit(1)
        project = project_path.name

    db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
    gate = BlueprintPromotionGate(db)
    try:
        result = gate.demote_claim(
            project,
            claim_id=claim_id,
            reason=reason,
            new_status=new_status.lower(),
            actor=actor,
            superseding_claim_id=superseding_claim_id,
        )
    except ValueError as exc:
        click.echo(f"❌ Error: {exc}", err=True)
        sys.exit(1)

    generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
    generator.apply_allowed_promotions_to_blueprint(project)
    generator.generate_blueprint_meta(project)

    click.echo(
        f"✅ Demoted claim {result['claim_id']} ({result['old_status']} -> {result['new_status']})"
    )

@docs.command("install")
@click.option("--force", is_flag=True, help="Overwrite existing docs/templates")
@click.pass_context
def docs_install(ctx, force: bool):
    """
    Install bundled IDSE reference docs and templates into .idse/.

    Copies:
    - docs/*.md (philosophy, constitution, pipeline, agents, etc.)
    - kb/templates/*.md (intent, context, spec, plan, tasks, feedback, test plan)
    """
    from pathlib import Path
    from .docs_installer import install_docs

    workspace = Path.cwd()
    click.echo(f"📚 Installing IDSE reference docs into {workspace}/.idse/")
    try:
        docs_copied, templates_copied = install_docs(workspace, force=force)
        click.echo(f"   Docs copied: {docs_copied}")
        click.echo(f"   Templates copied: {templates_copied}")
        if not force:
            click.echo("   (existing files were kept; use --force to overwrite)")
        click.echo("✅ Done")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.group()
def compile():
    """Compile IDSE artifacts into machine-executable specs."""
    pass


@compile.command("agent-spec")
@click.option("--project", help="Project name")
@click.option("--session", "session_id", required=True, help="Feature session ID")
@click.option("--blueprint", default="__blueprint__", help="Blueprint session for defaults")
@click.option("--out", type=click.Path(), help="Output directory")
@click.option("--dry-run", is_flag=True, help="Validate and print without writing")
@click.pass_context
def compile_agent_spec_cmd(
    ctx,
    project: Optional[str],
    session_id: str,
    blueprint: str,
    out: Optional[str],
    dry_run: bool,
):
    """Compile AgentProfileSpec from spec.md."""
    from .compiler import compile_agent_spec

    try:
        output = compile_agent_spec(
            project=project,
            session_id=session_id,
            blueprint_id=blueprint,
            out_dir=Path(out) if out else None,
            dry_run=dry_run,
            backend=ctx.obj.get("backend_override"),
        )
        if dry_run:
            click.echo(output)
        else:
            click.echo(f"✅ Agent spec written: {output}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)



@main.group()
def session():
    """Manage feature sessions"""
    pass


def _sync_session_metadata_to_sqlite(project_name: str, metadata, *, idse_root: Path) -> None:
    """Persist session metadata changes into SQLite source of truth."""
    from .artifact_database import ArtifactDatabase
    from .file_view_generator import FileViewGenerator

    db = ArtifactDatabase(idse_root=idse_root, allow_create=False)
    db.ensure_session(
        project_name,
        metadata.session_id,
        name=metadata.name,
        session_type=metadata.session_type,
        description=metadata.description,
        is_blueprint=metadata.is_blueprint,
        parent_session=metadata.parent_session,
        owner=metadata.owner,
        status=metadata.status,
    )
    db.save_session_extras(
        project_name,
        metadata.session_id,
        collaborators=[c.to_dict() for c in metadata.collaborators],
        tags=metadata.tags,
    )
    FileViewGenerator(idse_root=idse_root, allow_create=False).generate_blueprint_meta(project_name)


def _resolve_project_path(project: Optional[str]) -> tuple["ProjectWorkspace", Path, str]:
    from .project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
    else:
        project_path = manager.get_current_project()
        if not project_path:
            raise FileNotFoundError("Not in an IDSE project directory")
        project = project_path.name

    if not project_path.exists():
        raise FileNotFoundError(f"Project '{project}' not found")

    return manager, project_path, project


@session.command("create")
@click.argument("session_name", required=False)
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def create_session(ctx, session_name: str, project: str):
    """Create new feature session within project"""
    from .project_workspace import ProjectWorkspace
    from .pipeline_artifacts import PipelineArtifacts
    from .artifact_config import ArtifactConfig

    manager = ProjectWorkspace()

    if not project:
        current_proj = manager.get_current_project()
        if current_proj:
            project = current_proj.name
        else:
            click.echo("❌ Error: Not in an IDSE project directory", err=True)
            click.echo("Specify project with --project or run from project directory")
            sys.exit(1)

    project_path = manager.projects_root / project

    if not project_path.exists():
        click.echo(f"❌ Error: Project '{project}' not found", err=True)
        click.echo(f"Run 'idse init {project}' first")
        sys.exit(1)

    if not session_name:
        session_id = f"session-{int(datetime.now().timestamp())}"
    else:
        session_id = session_name

    session_path = project_path / "sessions" / session_id

    if session_path.exists():
        click.echo(f"❌ Error: Session '{session_id}' already exists", err=True)
        sys.exit(1)

    dirs_to_create = [
        session_path / "intents",
        session_path / "contexts",
        session_path / "specs",
        session_path / "plans",
        session_path / "tasks",
        session_path / "implementation",
        session_path / "feedback",
        session_path / "metadata"
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    loader = PipelineArtifacts()
    artifacts = loader.load_all_templates(project_name=project, stack="python")

    artifact_map = {
        "intent.md": session_path / "intents" / "intent.md",
        "context.md": session_path / "contexts" / "context.md",
        "spec.md": session_path / "specs" / "spec.md",
        "plan.md": session_path / "plans" / "plan.md",
        "tasks.md": session_path / "tasks" / "tasks.md",
        "feedback.md": session_path / "feedback" / "feedback.md",
        "implementation_readme.md": session_path / "implementation" / "README.md"
    }

    for template_name, file_path in artifact_map.items():
        if template_name in artifacts:
            file_path.write_text(artifacts[template_name])

    owner_file = session_path / "metadata" / ".owner"
    owner_file.write_text(f"Created: {datetime.now().isoformat()}\n")

    from .session_metadata import SessionMetadata

    metadata = SessionMetadata(
        session_id=session_id,
        name=session_id,
        session_type="feature",
        description=None,
        is_blueprint=False,
        parent_session="__blueprint__",
        related_sessions=[],
        owner="system",
        collaborators=[],
        tags=[],
        status="draft",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    metadata.save(session_path)

    from .stage_state_model import StageStateModel

    state_tracker = StageStateModel(project_path, session_id=session_id)
    state_tracker.init_state(project, session_id, is_blueprint=False)

    config = ArtifactConfig(
        ctx.obj.get("config_path") if ctx.obj else None,
        backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
    )
    if config.get_storage_backend() == "sqlite":
        from .artifact_database import ArtifactDatabase
        from .design_store import DesignStoreFilesystem
        from .file_view_generator import FileViewGenerator

        db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
        db.ensure_project(project, stack="python")
        db.ensure_session(
            project,
            session_id,
            name=metadata.name,
            session_type=metadata.session_type,
            description=metadata.description,
            is_blueprint=metadata.is_blueprint,
            parent_session=metadata.parent_session,
            owner=metadata.owner,
            status=metadata.status,
        )
        db.save_session_extras(
            project,
            session_id,
            collaborators=[c.to_dict() for c in metadata.collaborators],
            tags=metadata.tags,
        )

        stage_paths = {
            stage: session_path / folder / filename
            for stage, (folder, filename) in DesignStoreFilesystem.STAGE_PATHS.items()
        }
        for stage, path in stage_paths.items():
            if path.exists():
                db.save_artifact(project, session_id, stage, path.read_text())

        db.save_session_state(project, session_id, state_tracker.get_status(project))
        db.set_current_session(project, session_id)
        generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=True)
        generator.generate_session(project, session_id)
        generator.generate_session_state(project, session_id)
        generator.generate_blueprint_meta(project)

    from .session_graph import SessionGraph

    SessionGraph(project_path).set_current_session(session_id)

    click.echo(f"✅ Feature session created: {session_id}")
    click.echo(f"📁 Location: {session_path}")
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    if config.get_storage_backend() != "sqlite":
        try:
            from .session_graph import SessionGraph

            SessionGraph(project_path).rebuild_blueprint_meta(project_path)
            click.echo("📘 Blueprint meta.md refreshed.")
        except Exception as meta_err:
            click.echo(f"⚠️  Warning: Failed to refresh blueprint meta: {meta_err}", err=True)


@session.command("switch")
@click.argument("session_id")
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def switch_session(ctx, session_id: str, project: str):
    """Switch the active session pointer (CURRENT_SESSION)."""
    from .project_workspace import ProjectWorkspace
    from .artifact_config import ArtifactConfig

    manager = ProjectWorkspace()

    if not project:
        current_proj = manager.get_current_project()
        if current_proj:
            project = current_proj.name
        else:
            click.echo("❌ Error: Not in an IDSE project directory", err=True)
            click.echo("Specify project with --project or run from project directory")
            sys.exit(1)

    project_path = manager.projects_root / project
    session_path = project_path / "sessions" / session_id

    if not session_path.exists():
        click.echo(f"❌ Error: Session '{session_id}' not found in project '{project}'", err=True)
        sys.exit(1)

    from .session_graph import SessionGraph

    config = ArtifactConfig(
        backend_override=ctx.obj.get("backend_override") if ctx.obj else None
    )
    if config.get_storage_backend() == "sqlite":
        from .file_view_generator import FileViewGenerator

        generator = FileViewGenerator(idse_root=manager.idse_root, allow_create=False)
        generator.generate_blueprint_meta(project)

    SessionGraph(project_path).set_current_session(session_id)
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    if config.get_storage_backend() != "sqlite":
        try:
            from .session_graph import SessionGraph

            SessionGraph(project_path).rebuild_blueprint_meta(project_path)
            click.echo("📘 Blueprint meta.md refreshed.")
        except Exception as meta_err:
            click.echo(f"⚠️  Warning: Failed to refresh blueprint meta: {meta_err}", err=True)


@session.command("set-owner")
@click.argument("session_id")
@click.option("--owner", required=True, help="Owner name")
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def set_owner(ctx, session_id: str, owner: str, project: Optional[str]):
    """Set session owner in metadata and SQLite."""
    from .artifact_config import ArtifactConfig
    from .session_metadata import SessionMetadata

    try:
        manager, project_path, project_name = _resolve_project_path(project)
        session_path = project_path / "sessions" / session_id
        if not session_path.exists():
            click.echo(f"❌ Error: Session '{session_id}' not found in project '{project_name}'", err=True)
            sys.exit(1)

        metadata = SessionMetadata.load(session_path)
        metadata.update(session_path, owner=owner)

        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )
        if config.get_storage_backend() == "sqlite":
            _sync_session_metadata_to_sqlite(project_name, metadata, idse_root=manager.idse_root)

        click.echo(f"✅ Owner updated for {project_name}/{session_id}: {owner}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@session.command("add-collaborator")
@click.argument("session_id")
@click.option("--name", required=True, help="Collaborator name")
@click.option(
    "--role",
    type=click.Choice(["owner", "contributor", "reviewer", "viewer"], case_sensitive=False),
    default="contributor",
    show_default=True,
    help="Collaborator role",
)
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def add_collaborator(ctx, session_id: str, name: str, role: str, project: Optional[str]):
    """Add collaborator to a session in metadata and SQLite."""
    from .artifact_config import ArtifactConfig
    from .session_metadata import SessionMetadata

    try:
        manager, project_path, project_name = _resolve_project_path(project)
        session_path = project_path / "sessions" / session_id
        if not session_path.exists():
            click.echo(f"❌ Error: Session '{session_id}' not found in project '{project_name}'", err=True)
            sys.exit(1)

        metadata = SessionMetadata.load(session_path)
        metadata.add_collaborator(session_path, name=name, role=role.lower())

        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )
        if config.get_storage_backend() == "sqlite":
            _sync_session_metadata_to_sqlite(project_name, metadata, idse_root=manager.idse_root)

        click.echo(f"✅ Collaborator added for {project_name}/{session_id}: {name} ({role.lower()})")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@session.command("remove-collaborator")
@click.argument("session_id")
@click.option("--name", required=True, help="Collaborator name")
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def remove_collaborator(ctx, session_id: str, name: str, project: Optional[str]):
    """Remove collaborator from a session in metadata and SQLite."""
    from .artifact_config import ArtifactConfig
    from .session_metadata import SessionMetadata

    try:
        manager, project_path, project_name = _resolve_project_path(project)
        session_path = project_path / "sessions" / session_id
        if not session_path.exists():
            click.echo(f"❌ Error: Session '{session_id}' not found in project '{project_name}'", err=True)
            sys.exit(1)

        metadata = SessionMetadata.load(session_path)
        metadata.remove_collaborator(session_path, name=name)

        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )
        if config.get_storage_backend() == "sqlite":
            _sync_session_metadata_to_sqlite(project_name, metadata, idse_root=manager.idse_root)

        click.echo(f"✅ Collaborator removed for {project_name}/{session_id}: {name}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@session.command("set-status")
@click.argument("session_id")
@click.option(
    "--status",
    "session_status",
    required=True,
    type=click.Choice(["draft", "in_progress", "review", "complete", "archived"], case_sensitive=False),
    help="Session status",
)
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def set_status(ctx, session_id: str, session_status: str, project: Optional[str]):
    """Set session status in metadata and SQLite."""
    from .artifact_config import ArtifactConfig
    from .session_metadata import SessionMetadata
    from .stage_state_model import StageStateModel
    from .design_store_sqlite import DesignStoreSQLite
    from .validation_engine import ValidationEngine

    try:
        manager, project_path, project_name = _resolve_project_path(project)
        session_path = project_path / "sessions" / session_id
        if not session_path.exists():
            click.echo(f"❌ Error: Session '{session_id}' not found in project '{project_name}'", err=True)
            sys.exit(1)

        normalized_status = session_status.lower()
        metadata = SessionMetadata.load(session_path)
        metadata.update(session_path, status=normalized_status)

        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )
        if config.get_storage_backend() == "sqlite":
            _sync_session_metadata_to_sqlite(project_name, metadata, idse_root=manager.idse_root)
            tracker = StageStateModel(
                project_path=project_path,
                store=DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False),
                project_name=project_name,
                session_id=session_id,
            )
            try:
                tracker.get_status(project_name)
            except FileNotFoundError:
                tracker.init_state(project_name, session_id, is_blueprint=metadata.is_blueprint)
        else:
            tracker = StageStateModel(project_path=project_path, session_id=session_id)
            try:
                tracker.get_status(project_name)
            except FileNotFoundError:
                tracker.init_state(project_name, session_id, is_blueprint=metadata.is_blueprint)

        if normalized_status == "complete":
            validator = ValidationEngine()
            validation_results = validator.validate_project(
                project_name=project_name,
                backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
                session_id=session_id,
            )
            if not validation_results["valid"]:
                click.echo(
                    f"❌ Cannot mark {project_name}/{session_id} complete: validation failed",
                    err=True,
                )
                for error in validation_results["errors"]:
                    click.echo(f"   ✗ {error}", err=True)
                sys.exit(1)
            for stage in tracker.STAGE_NAMES:
                tracker.update_stage(stage, "completed")
            tracker.set_validation_status("passing")

        click.echo(f"✅ Status updated for {project_name}/{session_id}: {normalized_status}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@session.command("set-stage")
@click.argument("session_id")
@click.option(
    "--stage",
    "stage_name",
    required=True,
    type=click.Choice(["intent", "context", "spec", "plan", "tasks", "implementation", "feedback"], case_sensitive=False),
    help="Pipeline stage name",
)
@click.option(
    "--status",
    "stage_status",
    required=True,
    type=click.Choice(["pending", "in_progress", "completed"], case_sensitive=False),
    help="Stage status",
)
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def set_stage(ctx, session_id: str, stage_name: str, stage_status: str, project: Optional[str]):
    """Set a single stage status in session state."""
    from .artifact_config import ArtifactConfig
    from .session_metadata import SessionMetadata
    from .stage_state_model import StageStateModel
    from .design_store_sqlite import DesignStoreSQLite

    try:
        manager, project_path, project_name = _resolve_project_path(project)
        session_path = project_path / "sessions" / session_id
        if not session_path.exists():
            click.echo(f"❌ Error: Session '{session_id}' not found in project '{project_name}'", err=True)
            sys.exit(1)

        try:
            metadata = SessionMetadata.load(session_path)
            is_blueprint = metadata.is_blueprint
        except FileNotFoundError:
            is_blueprint = session_id == "__blueprint__"

        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )

        if config.get_storage_backend() == "sqlite":
            tracker = StageStateModel(
                project_path=project_path,
                store=DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False),
                project_name=project_name,
                session_id=session_id,
            )
        else:
            tracker = StageStateModel(project_path=project_path, session_id=session_id)

        try:
            tracker.get_status(project_name)
        except FileNotFoundError:
            tracker.init_state(project_name, session_id, is_blueprint=is_blueprint)

        tracker.update_stage(stage_name.lower(), stage_status.lower())
        click.echo(
            f"✅ Stage updated for {project_name}/{session_id}: {stage_name.lower()} -> {stage_status.lower()}"
        )
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--plan", type=click.Choice(["feature"], case_sensitive=False), required=True, help="Plan type (currently only 'feature' supported)")
@click.argument("feature_name")
@click.option("--project", help="Project name (auto-detects from current directory if not specified)")
@click.option("--blueprint", default="__blueprint__", help="Parent blueprint session ID (default: __blueprint__)")
@click.option("--owner", help="Session owner (human or AI agent)")
@click.option("--description", help="One-line summary of the feature")
@click.pass_context
def spawn(ctx, plan: str, feature_name: str, project: Optional[str], blueprint: str, owner: Optional[str], description: Optional[str]):
    """
    Spawn a new feature session with full scaffolding and lineage tracking.

    This command creates a complete IDSE feature session with:
    - Full 7-stage pipeline directory structure
    - Pre-populated templates
    - Rich metadata (session.json) with lineage
    - Auto-update of blueprint meta.md

    Examples:
        idse spawn --plan feature sync-bridge --owner gpt5 --description "Notion-VSCode sync"
        idse spawn --plan feature auth-service --blueprint __blueprint__
    """
    from .project_workspace import ProjectWorkspace

    click.echo(f"🚀 Spawning feature session: {feature_name}")

    try:
        manager = ProjectWorkspace()

        # Auto-detect project if not specified
        if not project:
            current_project = manager.get_current_project()
            if current_project:
                project_path = current_project
                project = current_project.name
            else:
                click.echo("❌ Error: Could not auto-detect project", err=True)
                click.echo("   Run from within an IDSE project directory, or use --project", err=True)
                sys.exit(1)
        else:
            project_path = manager.projects_root / project

        if not project_path.exists():
            click.echo(f"❌ Error: Project '{project}' not found at {project_path}", err=True)
            click.echo(f"   Run 'idse init {project}' first", err=True)
            sys.exit(1)

        # Verify blueprint exists
        blueprint_path = project_path / "sessions" / blueprint
        if not blueprint_path.exists():
            click.echo(f"❌ Error: Blueprint session '{blueprint}' does not exist", err=True)
            click.echo(f"   Available sessions: {', '.join([s.name for s in (project_path / 'sessions').iterdir() if s.is_dir()])}", err=True)
            sys.exit(1)

        click.echo(f"   Project: {project}")
        click.echo(f"   Parent: {blueprint}")
        if owner:
            click.echo(f"   Owner: {owner}")
        if description:
            click.echo(f"   Description: {description}")

        # Create feature session using SessionGraph
        from .session_graph import SessionGraph

        session_path = SessionGraph(project_path).create_feature_session(
            session_id=feature_name,
            parent_session=blueprint,
            description=description,
            owner=owner
        )

        # Update blueprint meta.md
        from .session_graph import SessionGraph

        SessionGraph(project_path).update_blueprint_meta(project_path, session_path)

        click.echo("")
        click.echo(f"✅ Feature session '{feature_name}' spawned successfully!")
        click.echo(f"📁 Location: {session_path}")
        click.echo(f"📘 Blueprint meta.md updated with new session")
        click.echo(f"📊 Session state initialized")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  1. cd {session_path}")
        click.echo(f"  2. Edit intents/intent.md to define feature objective")
        click.echo(f"  3. Run 'idse validate' to check constitutional compliance")
        click.echo(f"  4. View blueprint status: cat {project_path}/sessions/{blueprint}/metadata/meta.md")

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--project", help="Project name to generate files for")
@click.option("--stack", default="python", help="Technology stack (python, node, go, etc.)")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.pass_context
def generate_agent_files(ctx, project: Optional[str], stack: str, force: bool):
    """
    Generate agent instruction files (CLAUDE.md, AGENTS.md, .cursorrules) for an existing project.

    This is useful if you initialized a project before this feature was added,
    or if you want to regenerate the files.

    Example:
        idse generate-agent-files --project studiompd --stack python
        idse generate-agent-files --project studiompd --force
    """
    from .project_workspace import ProjectWorkspace

    if not project:
        click.echo("❌ Error: --project is required", err=True)
        sys.exit(1)

    click.echo(f"🤖 Generating agent instruction files for: {project}")

    try:
        manager = ProjectWorkspace()

        # Check if project exists
        project_path = manager.projects_root / project
        if not project_path.exists():
            click.echo(f"❌ Error: Project '{project}' not found at {project_path}", err=True)
            sys.exit(1)

        # Check if files already exist and handle force flag
        workspace_root = manager.workspace_root
        existing_files = []
        for filename in ["CLAUDE.md", "AGENTS.md", ".cursorrules"]:
            if (workspace_root / filename).exists():
                existing_files.append(filename)

        if existing_files and not force:
            click.echo(f"⚠️  Warning: The following files already exist:")
            for f in existing_files:
                click.echo(f"   - {f}")
            click.echo("")
            click.echo("Use --force to overwrite them, or delete them manually first.")
            sys.exit(1)

        # Temporarily override to allow overwriting
        if force:
            # Delete existing files
            for filename in ["CLAUDE.md", "AGENTS.md", ".cursorrules"]:
                filepath = workspace_root / filename
                if filepath.exists():
                    filepath.unlink()
                    click.echo(f"  🗑️  Removed existing {filename}")

        # Generate files
        manager._create_agent_instructions(project, stack)

        click.echo("")
        click.echo(f"✅ Agent instruction files created successfully!")
        click.echo(f"   Files: CLAUDE.md, AGENTS.md, .cursorrules")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--project", help="Project name (auto-detects from current directory if not specified)")
@click.option("--type", "session_type", type=click.Choice(["blueprint", "feature", "exploratory"], case_sensitive=False), help="Filter by session type")
@click.option("--status", "session_status", type=click.Choice(["draft", "in_progress", "review", "complete", "archived"], case_sensitive=False), help="Filter by status")
@click.option("--tag", help="Filter by tag")
@click.option("--include-legacy", is_flag=True, help="Include legacy sessions without metadata")
@click.pass_context
def sessions(ctx, project: Optional[str], session_type: Optional[str], session_status: Optional[str], tag: Optional[str], include_legacy: bool):
    """
    List all sessions in a project with optional filters.

    Shows session ID, type, status, owner, and creation date.

    Examples:
        idse sessions
        idse sessions --type feature
        idse sessions --status in_progress
        idse sessions --tag critical
    """
    from .project_workspace import ProjectWorkspace
    from .session_manager import SessionManager

    try:
        manager = ProjectWorkspace()

        # Auto-detect project if not specified
        if not project:
            current_project = manager.get_current_project()
            if current_project:
                project_path = current_project
                project = current_project.name
            else:
                click.echo("❌ Error: Could not auto-detect project", err=True)
                click.echo("   Run from within an IDSE project directory, or use --project", err=True)
                sys.exit(1)
        else:
            project_path = manager.projects_root / project

        if not project_path.exists():
            click.echo(f"❌ Error: Project '{project}' not found", err=True)
            sys.exit(1)

        session_mgr = SessionManager(project_path)
        sessions_list = session_mgr.list_sessions(
            session_type=session_type,
            status=session_status,
            tag=tag,
            include_legacy=include_legacy
        )

        if not sessions_list:
            click.echo(f"No sessions found in project '{project}'")
            if session_type or session_status or tag:
                click.echo("Try removing filters to see all sessions")
            return

        click.echo(f"\n📂 Sessions in project '{project}':")
        click.echo(f"   Found {len(sessions_list)} session(s)\n")

        for session in sessions_list:
            # Icon based on type
            icon = "📘" if session.is_blueprint else "📄"

            click.echo(f"{icon} {session.session_id}")
            click.echo(f"   Type: {session.session_type}")
            click.echo(f"   Status: {session.status}")
            click.echo(f"   Owner: {session.owner}")
            click.echo(f"   Created: {session.created_at[:10] if session.created_at != 'unknown' else 'unknown'}")

            if session.description:
                click.echo(f"   Description: {session.description}")

            if session.tags:
                click.echo(f"   Tags: {', '.join(session.tags)}")

            if session.parent_session:
                click.echo(f"   Parent: {session.parent_session}")

            click.echo()

        # Show statistics
        stats = session_mgr.get_statistics()
        click.echo("Statistics:")
        click.echo(f"  Total: {stats['total_sessions']}")
        click.echo(f"  Blueprint: {stats['blueprint_count']}")
        click.echo(f"  Feature: {stats['feature_count']}")
        if stats['orphaned_count'] > 0:
            click.echo(f"  ⚠️  Orphaned: {stats['orphaned_count']}")
        if stats['legacy_count'] > 0:
            click.echo(f"  Legacy (no metadata): {stats['legacy_count']}")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command("session-info")
@click.argument("session_id")
@click.option("--project", help="Project name (auto-detects from current directory if not specified)")
@click.option("--lineage", is_flag=True, help="Show parent and child sessions")
@click.pass_context
def session_info(ctx, session_id: str, project: Optional[str], lineage: bool):
    """
    Show detailed information about a specific session.

    Displays:
    - Session metadata (type, status, owner, description)
    - Creation and update timestamps
    - Collaborators and tags
    - Lineage (parent and child sessions) if --lineage flag is set

    Examples:
        idse session-info sync-bridge
        idse session-info __blueprint__ --lineage
    """
    from .project_workspace import ProjectWorkspace
    from .session_manager import SessionManager

    try:
        manager = ProjectWorkspace()

        # Auto-detect project if not specified
        if not project:
            current_project = manager.get_current_project()
            if current_project:
                project_path = current_project
                project = current_project.name
            else:
                click.echo("❌ Error: Could not auto-detect project", err=True)
                click.echo("   Run from within an IDSE project directory, or use --project", err=True)
                sys.exit(1)
        else:
            project_path = manager.projects_root / project

        if not project_path.exists():
            click.echo(f"❌ Error: Project '{project}' not found", err=True)
            sys.exit(1)

        session_mgr = SessionManager(project_path)

        if lineage:
            info = session_mgr.get_session_lineage(session_id)
            session = info['session']

            click.echo(f"\n📘 Session: {session.session_id}")
            click.echo(f"   Type: {session.session_type}")
            click.echo(f"   Status: {session.status}")
            click.echo(f"   Owner: {session.owner}")

            if session.description:
                click.echo(f"   Description: {session.description}")

            click.echo("\n🔗 Lineage:")

            if info['parent']:
                click.echo(f"   Parent: {info['parent'].session_id} ({info['parent'].session_type})")
            else:
                click.echo(f"   Parent: {session.parent_session or 'None (root session)'}")

            if info['children']:
                click.echo(f"   Children ({len(info['children'])}):")
                for child in info['children']:
                    click.echo(f"     - {child.session_id} ({child.session_type}, {child.status})")
            else:
                click.echo("   Children: None")

            if info['related']:
                click.echo(f"   Related ({len(info['related'])}):")
                for related in info['related']:
                    click.echo(f"     - {related.session_id}")

        else:
            session = session_mgr.get_session(session_id)

            click.echo(f"\n📘 Session: {session.session_id}")
            click.echo(f"   Name: {session.name}")
            click.echo(f"   Type: {session.session_type}")
            click.echo(f"   Status: {session.status}")
            click.echo(f"   Blueprint: {'Yes' if session.is_blueprint else 'No'}")
            click.echo(f"   Owner: {session.owner}")

            if session.description:
                click.echo(f"   Description: {session.description}")

            if session.parent_session:
                click.echo(f"   Parent: {session.parent_session}")

            if session.tags:
                click.echo(f"   Tags: {', '.join(session.tags)}")

            if session.collaborators:
                click.echo(f"   Collaborators ({len(session.collaborators)}):")
                for collab in session.collaborators:
                    click.echo(f"     - {collab.name} ({collab.role})")

            click.echo(f"\n⏰ Timestamps:")
            click.echo(f"   Created: {session.created_at}")
            click.echo(f"   Updated: {session.updated_at}")

            click.echo(f"\n💡 Tip: Use --lineage to see parent/child relationships")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def status(ctx, project: Optional[str]):
    """
    Display current project and session status.

    Shows:
    - Current project and session
    - Stage completion status (pending/in_progress/complete)
    - Last sync timestamp
    - Validation status

    Example:
        idse status
    """
    from .stage_state_model import StageStateModel
    from .ide_agent_routing import IDEAgentRouting
    from .artifact_config import ArtifactConfig
    from .artifact_database import ArtifactDatabase
    from .design_store_sqlite import DesignStoreSQLite
    from .file_view_generator import FileViewGenerator
    from .project_workspace import ProjectWorkspace

    try:
        manager = ProjectWorkspace()
        config = ArtifactConfig(
            ctx.obj.get("config_path") if ctx.obj else None,
            backend_override=ctx.obj.get("backend_override") if ctx.obj else None,
        )
        backend = config.get_storage_backend()
        if backend == "sqlite":
            try:
                ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
            except FileNotFoundError as exc:
                legacy = (manager.idse_root / "projects").exists()
                if legacy:
                    click.echo("❌ Error: Legacy project detected. Run 'idse migrate' to convert to SQLite.", err=True)
                else:
                    click.echo(str(exc), err=True)
                sys.exit(1)
            project_path = manager.projects_root / project if project else manager.get_current_project()
            if not project_path:
                raise FileNotFoundError("No IDSE project found. Run 'idse init' first.")
            project_name = project_path.name
            db = ArtifactDatabase(idse_root=manager.idse_root, allow_create=False)
            current_session = db.get_current_session(project_name)
            if not current_session:
                raise FileNotFoundError(
                    "Database missing current session. Run 'idse init' or 'idse migrate'."
                )
            store = DesignStoreSQLite(idse_root=manager.idse_root, allow_create=False)
            tracker = StageStateModel(
                project_path=project_path,
                store=store,
                project_name=project_name,
                session_id=current_session,
            )
            try:
                state = tracker.get_status(project_name)
            except FileNotFoundError:
                tracker.init_state(
                    project_name,
                    current_session,
                    is_blueprint=current_session == "__blueprint__",
                )
                state = tracker.get_status(project_name)
            # Keep file views in sync for IDE agents.
            tracker.refresh_state_file()
            FileViewGenerator(idse_root=manager.idse_root, allow_create=False).generate_agent_registry(project_name)
        else:
            tracker = StageStateModel(store=None, project_name=project)
            state = tracker.get_status(project)
        router = IDEAgentRouting()

        click.echo("📊 IDSE Project Status")
        click.echo("")
        click.echo(f"Project: {state['project_name']}")
        click.echo(f"Session: {state['session_id']}")
        click.echo(f"Last Sync: {state.get('last_sync', 'Never')}")
        click.echo("")
        click.echo("Pipeline Stages:")

        for stage, status in state["stages"].items():
            icon = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⏳"
            agent = router.get_agent_for_stage(stage)
            agent_id = agent.get("id") if agent else None
            agent_mode = agent.get("mode") if agent else None
            if agent_id and agent_mode:
                agent_hint = f"  → {agent_id} ({agent_mode})"
            elif agent_id:
                agent_hint = f"  → {agent_id}"
            else:
                agent_hint = ""
            click.echo(f"  {icon} {stage.ljust(15)}: {status.ljust(12)}{agent_hint}")

        click.echo("")
        validation_status = state.get("validation_status", "unknown")
        if validation_status == "passing":
            click.echo("✅ Validation: Passing")
        else:
            click.echo(f"⚠️  Validation: {validation_status}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
