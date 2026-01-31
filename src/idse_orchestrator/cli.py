"""
IDSE Orchestrator CLI

Command-line interface for managing IDSE projects in client workspaces.

Commands:
- init: Initialize a new IDSE project with pipeline structure
- validate: Check artifacts for constitutional compliance
- sync push: Upload pipeline docs to Agency Core
- sync pull: Download latest artifacts from Agency Core
- status: Display current project and session status
"""

import click
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys
import requests

from . import __version__


@click.group()
@click.version_option(version=__version__, prog_name="idse")
@click.pass_context
def main(ctx):
    """
    IDSE Developer Orchestrator

    Manage Intent-Driven Systems Engineering projects in your workspace.
    This CLI coordinates IDE agents and syncs with the Agency Core backend.
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
@click.option("--client-id", help="Client ID from Agency Core")
@click.option("--create-agent-files/--no-create-agent-files", default=True, help="Create agent instruction files (CLAUDE.md, AGENTS.md, .cursorrules)")
@click.pass_context
def init(ctx, project_name: str, stack: str, guided: bool, agentic: Optional[str], client_id: Optional[str], create_agent_files: bool):
    """
    Initialize a new IDSE project with blueprint session.

    Creates blueprint session (__blueprint__) for project-level meta-planning.
    Optionally integrates with agent frameworks (Agency Swarm, Crew AI, AutoGen).
    For feature sessions, use 'idse session create'.

    Examples:
        idse init customer-portal --stack python
        idse init my-agency --agentic agency-swarm --guided
    """
    from .project_manager import ProjectManager

    click.echo(f"🚀 Initializing IDSE project: {project_name}")
    click.echo(f"   Stack: {stack}")

    try:
        manager = ProjectManager()
        project_path = manager.init_project(project_name, stack, client_id, create_agent_files)

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
        click.echo(f"  3. Run 'idse sync push' to upload to Agency Core")

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
    from .validator import Validator

    click.echo("🔍 Validating IDSE pipeline artifacts...")

    try:
        validator = Validator()
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
def sync():
    """Sync pipeline artifacts with Agency Core."""
    pass


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


@sync.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--agency-url", envvar="IDSE_AGENCY_URL", help="Agency Core URL")
@click.option("--session", "session_override", help="Session ID to sync (overrides CURRENT_SESSION)")
@click.pass_context
def push(ctx, project: Optional[str], agency_url: Optional[str], session_override: Optional[str]):
    """
    Upload local pipeline artifacts to Agency Core.

    Validates artifacts locally first, then uploads via MCP protocol.
    Updates sync timestamp and logs event locally.

    Example:
        idse sync push
        idse sync push --project customer-portal
    """
    from .mcp_client import MCPClient
    from .validator import Validator

    click.echo("📤 Syncing to Agency Core...")

    # Validate first
    click.echo("   Validating artifacts...")
    validator = Validator()
    results = validator.validate_project(project)

    if not results["valid"]:
        click.echo("❌ Validation failed. Fix errors before syncing:", err=True)
        for error in results["errors"]:
            click.echo(f"   ✗ {error}", err=True)
        sys.exit(1)

    try:
        client = MCPClient(agency_url)
        response = client.push_project(project, session_override=session_override)

        click.echo(f"✅ Synced successfully!")
        click.echo(f"   Project ID: {response.get('project_id')}")
        if response.get("synced_stages"):
            click.echo(f"   Stages: {', '.join(response['synced_stages'])}")
        if response.get("message"):
            click.echo(f"   Message: {response['message']}")
        click.echo(f"   Timestamp: {response.get('timestamp')}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.option("--project", help="Project name (uses current if not specified)")
@click.option("--agency-url", envvar="IDSE_AGENCY_URL", help="Agency Core URL")
@click.option("--session", "session_override", help="Session ID to pull (uses CURRENT_SESSION if not specified)")
@click.option("--force", is_flag=True, help="Overwrite local changes without prompting")
@click.pass_context
def pull(ctx, project: Optional[str], agency_url: Optional[str], session_override: Optional[str], force: bool):
    """
    Download latest pipeline artifacts from Agency Core.

    Pulls artifacts for the specified session (or CURRENT_SESSION if not specified).
    Compares remote timestamps with local, warns if local changes
    will be overwritten. Prompts for confirmation unless --force is used.

    Example:
        idse sync pull
        idse sync pull --session __blueprint__
        idse sync pull --force
    """
    from .mcp_client import MCPClient

    click.echo("📥 Pulling from Agency Core...")

    try:
        client = MCPClient(agency_url)
        response = client.pull_project(project, force=force, session_override=session_override)

        session_id = response.get("session_id", "unknown")
        click.echo(f"   Session: {session_id}")

        if response.get("conflicts") and not force:
            click.echo("⚠️  Warning: Local changes detected:")
            for conflict in response["conflicts"]:
                click.echo(f"   - {conflict}")

            if not click.confirm("Overwrite local changes?"):
                click.echo("Sync cancelled.")
                return

        # Proceed with pull
        client.apply_pull(response)

        artifact_count = len(response.get('artifacts', {}))
        click.echo("✅ Pull completed successfully!")
        click.echo(f"   Updated {artifact_count} artifacts for session '{session_id}'")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.group()
def blueprint():
    """Manage project blueprints"""
    pass


@blueprint.command("list")
@click.option("--agency-url", envvar="AGENCY_URL", default="http://127.0.0.1:8000")
def list_blueprints(agency_url: str):
    """List available blueprints from Agency Core"""
    from .mcp_client import MCPClient

    client = MCPClient(agency_url)
    target_url = client.agency_url

    try:
        response = requests.get(f"{target_url}/sync/blueprints", timeout=30)
        response.raise_for_status()
        data = response.json()

        click.echo("\n📘 Available Blueprints:\n")
        click.echo(f"{'Project Name':<30} {'Progress':<10}")
        click.echo("-" * 40)

        for bp in data.get("blueprints", []):
            name = bp["project_name"]
            progress = bp["progress_percent"]
            click.echo(f"{name:<30} {progress}%")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@blueprint.command("install")
@click.argument("source_project")
@click.argument("target_project")
@click.option("--agency-url", envvar="AGENCY_URL", default="http://127.0.0.1:8000")
def install_blueprint(source_project: str, target_project: str, agency_url: str):
    """Install blueprint from existing project"""
    from .mcp_client import MCPClient
    from .project_manager import ProjectManager

    click.echo(f"📥 Installing blueprint from {source_project}...")

    try:
        client = MCPClient(agency_url)
        target_url = client.agency_url

        resp = requests.get(f"{target_url}/sync/blueprints", timeout=30)
        resp.raise_for_status()
        blueprints = resp.json().get("blueprints", [])

        source = next((b for b in blueprints if b["project_name"] == source_project), None)
        if not source:
            raise ValueError(f"Blueprint '{source_project}' not found")

        artifacts = client.pull_blueprint(source["project_id"])

        manager = ProjectManager()
        project_path = manager.init_project(target_project, stack="python", client_id=None, create_agent_files=False)

        session_path = project_path / "sessions" / "__blueprint__"

        for artifact_name, content in artifacts.items():
            file_map = {
                "intent_md": session_path / "intents" / "intent.md",
                "context_md": session_path / "contexts" / "context.md",
                "spec_md": session_path / "specs" / "spec.md",
                "plan_md": session_path / "plans" / "plan.md",
                "tasks_md": session_path / "tasks" / "tasks.md",
                "feedback_md": session_path / "feedback" / "feedback.md",
                "implementation_md": session_path / "implementation" / "README.md",
                "implementation_readme_md": session_path / "implementation" / "README.md"
            }

            if artifact_name in file_map:
                file_map[artifact_name].write_text(content)

        click.echo(f"✅ Blueprint installed at: {project_path}")

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
    from .project_manager import ProjectManager
    from .template_loader import TemplateLoader

    manager = ProjectManager()

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

    loader = TemplateLoader()
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

    (project_path / "CURRENT_SESSION").write_text(session_id)

    click.echo(f"✅ Feature session created: {session_id}")
    click.echo(f"📁 Location: {session_path}")
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    try:
        manager.rebuild_blueprint_meta(project_path)
        click.echo("📘 Blueprint meta.md refreshed.")
    except Exception as meta_err:
        click.echo(f"⚠️  Warning: Failed to refresh blueprint meta: {meta_err}", err=True)


@session.command("switch")
@click.argument("session_id")
@click.option("--project", help="Project name (uses current if not specified)")
def switch_session(session_id: str, project: str):
    """Switch the active session pointer (CURRENT_SESSION)."""
    from .project_manager import ProjectManager

    manager = ProjectManager()

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

    (project_path / "CURRENT_SESSION").write_text(session_id)
    click.echo(f"📝 CURRENT_SESSION updated to: {session_id}")
    try:
        manager.rebuild_blueprint_meta(project_path)
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
    from .project_manager import ProjectManager

    click.echo(f"🚀 Spawning feature session: {feature_name}")

    try:
        manager = ProjectManager()

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

        # Create feature session using ProjectManager
        session_path = manager.create_feature_session(
            project_path=project_path,
            session_id=feature_name,
            parent_session=blueprint,
            description=description,
            client_id=owner
        )

        # Update blueprint meta.md
        manager.update_blueprint_meta(project_path, session_path)

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
    from .project_manager import ProjectManager

    if not project:
        click.echo("❌ Error: --project is required", err=True)
        sys.exit(1)

    click.echo(f"🤖 Generating agent instruction files for: {project}")

    try:
        manager = ProjectManager()

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
    from .project_manager import ProjectManager
    from .session_manager import SessionManager

    try:
        manager = ProjectManager()

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
    from .project_manager import ProjectManager
    from .session_manager import SessionManager

    try:
        manager = ProjectManager()

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
    from .state_tracker import StateTracker

    try:
        tracker = StateTracker()
        state = tracker.get_status(project)

        click.echo("📊 IDSE Project Status")
        click.echo("")
        click.echo(f"Project: {state['project_name']}")
        click.echo(f"Session: {state['session_id']}")
        click.echo(f"Last Sync: {state.get('last_sync', 'Never')}")
        click.echo("")
        click.echo("Pipeline Stages:")

        for stage, status in state["stages"].items():
            icon = "✅" if status == "complete" else "🔄" if status == "in_progress" else "⏳"
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
