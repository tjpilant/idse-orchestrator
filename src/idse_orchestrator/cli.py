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
@click.pass_context
def main(ctx):
    """
    IDSE Developer Orchestrator

    Manage Intent-Driven Systems Engineering projects in your workspace.
    This CLI coordinates IDE agents and manages pipeline artifacts locally.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@main.command()
@click.argument("project_name")
@click.option("--stack", default="python", help="Technology stack (python, node, go, etc.)")
@click.option("--guided/--no-guided", default=False, help="Run interactive questionnaire")
@click.option(
    "--agentic",
    type=click.Choice(["agency-swarm", "crew-ai", "autogen"], case_sensitive=False),
    help="Agent framework to integrate (agency-swarm, crew-ai, autogen)",
)
@click.option("--create-agent-files/--no-create-agent-files", default=True, help="Create agent instruction files (CLAUDE.md, AGENTS.md, .cursorrules)")
@click.pass_context
def init(ctx, project_name: str, stack: str, guided: bool, agentic: Optional[str], create_agent_files: bool):
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
        manager = ProjectWorkspace()
        project_path = manager.init_project(project_name, stack, create_agent_files=create_agent_files)

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
        results = validator.validate_project(project)

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


@main.group()
def docs():
    """Manage local IDSE reference docs and templates."""
    pass


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
def compile_agent_spec_cmd(project: Optional[str], session_id: str, blueprint: str, out: Optional[str], dry_run: bool):
    """Compile AgentProfileSpec from spec.md."""
    from .compiler import compile_agent_spec

    try:
        output = compile_agent_spec(
            project=project,
            session_id=session_id,
            blueprint_id=blueprint,
            out_dir=Path(out) if out else None,
            dry_run=dry_run,
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


@session.command("create")
@click.argument("session_name", required=False)
@click.option("--project", help="Project name (uses current if not specified)")
@click.pass_context
def create_session(ctx, session_name: str, project: str):
    """Create new feature session within project"""
    from .project_workspace import ProjectWorkspace
    from .pipeline_artifacts import PipelineArtifacts

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

    from .session_graph import SessionGraph
    
    SessionGraph(project_path).set_current_session(session_id)

    click.echo(f"✅ Feature session created: {session_id}")
    click.echo(f"📁 Location: {session_path}")
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    try:
        from .session_graph import SessionGraph

        SessionGraph(project_path).rebuild_blueprint_meta(project_path)
        click.echo("📘 Blueprint meta.md refreshed.")
    except Exception as meta_err:
        click.echo(f"⚠️  Warning: Failed to refresh blueprint meta: {meta_err}", err=True)


@session.command("switch")
@click.argument("session_id")
@click.option("--project", help="Project name (uses current if not specified)")
def switch_session(session_id: str, project: str):
    """Switch the active session pointer (CURRENT_SESSION)."""
    from .project_workspace import ProjectWorkspace

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
    
    SessionGraph(project_path).set_current_session(session_id)
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    try:
        from .session_graph import SessionGraph

        SessionGraph(project_path).rebuild_blueprint_meta(project_path)
        click.echo("📘 Blueprint meta.md refreshed.")
    except Exception as meta_err:
        click.echo(f"⚠️  Warning: Failed to refresh blueprint meta: {meta_err}", err=True)


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
    - Validation status

    Example:
        idse status
    """
    from .stage_state_model import StageStateModel

    try:
        tracker = StageStateModel()
        state = tracker.get_status(project)

        click.echo("📊 IDSE Project Status")
        click.echo("")
        click.echo(f"Project: {state['project_name']}")
        click.echo(f"Session: {state['session_id']}")
        click.echo("")
        click.echo("Pipeline Stages:")

        for stage, status in state["stages"].items():
            icon = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⏳"
            click.echo(f"  {icon} {stage.ljust(15)}: {status}")

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
