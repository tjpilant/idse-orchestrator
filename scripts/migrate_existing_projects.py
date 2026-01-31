#!/usr/bin/env python3
"""
Migration Script: Add metadata to existing IDSE projects

This script backfills session.json and meta.md for projects created
before the multi-layer pipeline architecture was implemented.

Usage:
    python scripts/migrate_existing_projects.py
    python scripts/migrate_existing_projects.py --project my-project
    python scripts/migrate_existing_projects.py --dry-run
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from idse_orchestrator.session_metadata import SessionMetadata
from idse_orchestrator.project_manager import ProjectManager


def migrate_session(session_path: Path, project_name: str, is_blueprint: bool = False) -> bool:
    """
    Migrate a single session to the new metadata format.

    Args:
        session_path: Path to session directory
        project_name: Name of the project
        is_blueprint: Whether this is a blueprint session

    Returns:
        True if migration was successful
    """
    print(f"  Migrating session: {session_path.name}")

    # Check if session.json already exists
    metadata_file = session_path / "metadata" / "session.json"
    if metadata_file.exists():
        print(f"    ✓ session.json already exists, skipping")
        return True

    # Parse .owner file if it exists
    owner_file = session_path / "metadata" / ".owner"
    created_at = datetime.now().isoformat()
    owner = "system"

    if owner_file.exists():
        owner_content = owner_file.read_text()
        for line in owner_content.split("\n"):
            if line.startswith("Created:"):
                created_at = line.split(":", 1)[1].strip()
            elif line.startswith("Client ID:"):
                owner = line.split(":", 1)[1].strip()

    # Determine session type
    session_id = session_path.name
    if is_blueprint or session_id == "__blueprint__":
        session_type = "blueprint"
        is_blueprint = True
        parent_session = None
    else:
        session_type = "feature"
        is_blueprint = False
        parent_session = "__blueprint__"

    # Create metadata
    metadata = SessionMetadata(
        session_id=session_id,
        name=project_name if is_blueprint else session_id,
        session_type=session_type,
        description=f"Migrated from legacy session",
        is_blueprint=is_blueprint,
        parent_session=parent_session,
        related_sessions=[],
        owner=owner,
        collaborators=[],
        tags=["legacy", "migrated"],
        status="in_progress",  # Assume existing sessions are in progress
        created_at=created_at,
        updated_at=datetime.now().isoformat()
    )

    # Save metadata
    try:
        metadata.save(session_path)
        print(f"    ✓ Created session.json")
        return True
    except Exception as e:
        print(f"    ✗ Failed to create session.json: {e}")
        return False


def migrate_project(project_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate a single project to the new metadata format.

    Args:
        project_path: Path to project directory
        dry_run: If True, don't make any changes

    Returns:
        True if migration was successful
    """
    project_name = project_path.name
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating project: {project_name}")

    sessions_dir = project_path / "sessions"
    if not sessions_dir.exists():
        print(f"  ✗ No sessions directory found")
        return False

    # Find all sessions
    sessions = [s for s in sessions_dir.iterdir() if s.is_dir()]
    if not sessions:
        print(f"  ✗ No sessions found")
        return False

    print(f"  Found {len(sessions)} session(s)")

    # Migrate each session
    success_count = 0
    for session_path in sessions:
        is_blueprint = session_path.name == "__blueprint__"

        if not dry_run:
            if migrate_session(session_path, project_name, is_blueprint):
                success_count += 1
        else:
            print(f"  [DRY RUN] Would migrate: {session_path.name}")
            success_count += 1

    # Create blueprint meta.md if this is a blueprint session
    blueprint_path = sessions_dir / "__blueprint__"
    if blueprint_path.exists():
        meta_file = blueprint_path / "metadata" / "meta.md"

        if not meta_file.exists() and not dry_run:
            print(f"  Creating blueprint meta.md...")
            manager = ProjectManager()
            manager.create_blueprint_meta(project_path, project_name)

            # Update meta.md with existing feature sessions
            feature_sessions = [s for s in sessions if s.name != "__blueprint__"]
            if feature_sessions:
                print(f"  Adding {len(feature_sessions)} feature session(s) to meta.md...")
                for feature_session in feature_sessions:
                    manager.update_blueprint_meta(project_path, feature_session)

            print(f"    ✓ Created and populated meta.md")
        elif meta_file.exists():
            print(f"    ✓ meta.md already exists")
        else:
            print(f"  [DRY RUN] Would create blueprint meta.md")

    # Update session_state.json to include is_blueprint flag
    state_file = project_path / "session_state.json"
    if state_file.exists() and not dry_run:
        try:
            with open(state_file, "r") as f:
                state = json.load(f)

            # Add is_blueprint if missing
            if "is_blueprint" not in state:
                state["is_blueprint"] = state.get("session_id") == "__blueprint__"

                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2)

                print(f"  ✓ Updated session_state.json with is_blueprint flag")
        except Exception as e:
            print(f"  ⚠ Failed to update session_state.json: {e}")

    print(f"\n  ✅ Successfully migrated {success_count}/{len(sessions)} session(s)")
    return success_count == len(sessions)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing IDSE projects to new metadata format"
    )
    parser.add_argument(
        "--project",
        help="Specific project to migrate (migrates all if not specified)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    # Find .idse directory
    manager = ProjectManager()
    projects_root = manager.projects_root

    if not projects_root.exists():
        print(f"❌ No .idse/projects directory found at {projects_root}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)

    # Get projects to migrate
    if args.project:
        project_path = projects_root / args.project
        if not project_path.exists():
            print(f"❌ Project '{args.project}' not found at {project_path}")
            sys.exit(1)
        projects = [project_path]
    else:
        projects = [p for p in projects_root.iterdir() if p.is_dir()]

    if not projects:
        print(f"❌ No projects found in {projects_root}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"IDSE Project Migration")
    print(f"{'='*60}")
    print(f"Projects root: {projects_root}")
    print(f"Projects to migrate: {len(projects)}")
    if args.dry_run:
        print(f"Mode: DRY RUN (no changes will be made)")
    print(f"{'='*60}")

    # Migrate projects
    success_count = 0
    for project_path in projects:
        if migrate_project(project_path, args.dry_run):
            success_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Migration Complete")
    print(f"{'='*60}")
    print(f"Successfully migrated: {success_count}/{len(projects)} project(s)")

    if args.dry_run:
        print(f"\n💡 This was a dry run. Run without --dry-run to apply changes.")
    else:
        print(f"\n✅ All projects migrated successfully!")
        print(f"\nNext steps:")
        print(f"  1. Run 'idse sessions' to verify migration")
        print(f"  2. Check blueprint meta.md files for accuracy")
        print(f"  3. Test spawning new feature sessions")


if __name__ == "__main__":
    main()
