"""Install agent framework resources into IDSE projects."""

from pathlib import Path
import shutil
import json
from typing import Optional


def find_git_root(start_path: Path) -> Optional[Path]:
    """
    Find the git repository root by walking up the directory tree.

    Args:
        start_path: Path to start searching from

    Returns:
        Path to git root (.git parent directory), or None if not in a git repo
    """
    current = start_path.resolve()

    # Walk up the directory tree
    while current != current.parent:  # Stop at filesystem root
        if (current / ".git").exists():
            return current
        current = current.parent

    # Check filesystem root
    if (current / ".git").exists():
        return current

    return None


def install_agentic_framework(project_path: Path, framework: str, stack: str) -> None:
    """Install agent framework resources based on selection."""
    normalized = framework.lower()

    if normalized == "agency-swarm":
        install_agency_swarm(project_path, stack)
    elif normalized == "crew-ai":
        raise NotImplementedError("Crew AI support coming soon")
    elif normalized == "autogen":
        raise NotImplementedError("AutoGen support coming soon")
    else:
        raise ValueError(f"Unknown framework: {framework}")


def install_agency_swarm(project_path: Path, stack: str) -> None:
    """Install Agency Swarm framework resources."""

    print("\n🤖 Installing Agency Swarm framework resources...")

    # Resolve repository root (four levels up from this file)
    repo_root = Path(__file__).parent.parent.parent.parent
    constitution_src = repo_root / ".idse" / "governance" / "AGENCY_SWARM_CONSTITUTION.md"

    # Project-scoped governance directory
    governance_dir = project_path / ".idse" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    constitution_dst = governance_dir / "AGENCY_SWARM_CONSTITUTION.md"

    if constitution_src.exists():
        shutil.copy(constitution_src, constitution_dst)
        print("  ✓ Copied AGENCY_SWARM_CONSTITUTION.md")
    else:
        print(f"  ⚠ Warning: Source constitution not found at {constitution_src}")

    # Workflow file packaged with resources (submodule or copied fallback)
    workflow_src = (
        Path(__file__).parent
        / "resources"
        / "frameworks"
        / "agency-swarm"
        / ".cursor"
        / "rules"
        / "workflow.mdc"
    )
    fallback_workflow_src = repo_root / ".cursor" / "rules" / "workflow.mdc"

    # Copy workflow into USER'S working directory repo root for IDE usage
    # Find the git root by walking up from current working directory
    user_cwd = Path.cwd()
    user_repo_root = find_git_root(user_cwd)

    if user_repo_root:
        workflow_dst = user_repo_root / ".cursor" / "rules" / "workflow.mdc"
    else:
        # Fallback: use current working directory if not in a git repo
        workflow_dst = user_cwd / ".cursor" / "rules" / "workflow.mdc"

    workflow_dst.parent.mkdir(parents=True, exist_ok=True)

    if workflow_src.exists():
        shutil.copy(workflow_src, workflow_dst)
        print(f"  ✓ Copied .cursor/rules/workflow.mdc to {workflow_dst}")
    elif fallback_workflow_src.exists():
        shutil.copy(fallback_workflow_src, workflow_dst)
        print(f"  ✓ Copied .cursor/rules/workflow.mdc (fallback) to {workflow_dst}")
    else:
        print(f"  ⚠ Warning: Workflow not found at {workflow_src}")
        print(f"     Fallback also missing at {fallback_workflow_src}")
        print("     Run: git submodule update --init --recursive to fetch template")

    # Source directory: agency-starter-template submodule
    submodule_root = (
        Path(__file__).parent
        / "resources"
        / "frameworks"
        / "agency-swarm"
    )

    # Copy .claude/agents/ directory (sub-agents for Agency Builder orchestration)
    claude_agents_src = submodule_root / ".claude" / "agents"
    claude_agents_dst = user_repo_root / ".claude" / "agents" if user_repo_root else user_cwd / ".claude" / "agents"

    if claude_agents_src.exists():
        claude_agents_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(claude_agents_src, claude_agents_dst, dirs_exist_ok=True)
        agent_count = len(list(claude_agents_src.glob("*.md")))
        print(f"  ✓ Copied {agent_count} sub-agent definitions to .claude/agents/")
    else:
        print(f"  ⚠ Warning: .claude/agents/ not found in submodule at {claude_agents_src}")

    # Copy .claude/README.md
    claude_readme_src = submodule_root / ".claude" / "README.md"
    claude_readme_dst = user_repo_root / ".claude" / "README.md" if user_repo_root else user_cwd / ".claude" / "README.md"

    if claude_readme_src.exists():
        claude_readme_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(claude_readme_src, claude_readme_dst)
        print(f"  ✓ Copied .claude/README.md")

    # Copy .cursor/commands/ directory (helper commands)
    cursor_commands_src = submodule_root / ".cursor" / "commands"
    cursor_commands_dst = user_repo_root / ".cursor" / "commands" if user_repo_root else user_cwd / ".cursor" / "commands"

    if cursor_commands_src.exists():
        cursor_commands_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(cursor_commands_src, cursor_commands_dst, dirs_exist_ok=True)
        command_count = len(list(cursor_commands_src.glob("*.md")))
        print(f"  ✓ Copied {command_count} helper commands to .cursor/commands/")

    # Framework metadata within project
    metadata = {
        "framework": "agency-swarm",
        "framework_version": "1.0.0",
        "installer_url": "https://github.com/VRSEN/agency-swarm",
        "constitution": ".idse/governance/AGENCY_SWARM_CONSTITUTION.md",
        "workflow": ".cursor/rules/workflow.mdc",
        "stack": stack,
    }

    metadata_dir = project_path / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    framework_file = metadata_dir / "framework.json"
    framework_file.write_text(json.dumps(metadata, indent=2))
    print("  ✓ Created metadata/framework.json")

    print("\n✅ Agency Swarm framework resources installed")
    print("")
    print("📘 Constitution: .idse/governance/AGENCY_SWARM_CONSTITUTION.md")
    print("🔧 Workflow: .cursor/rules/workflow.mdc")
    print("🤖 Sub-agents: .claude/agents/ (6 specialized orchestration agents)")
    print("⚡ Commands: .cursor/commands/ (5 helper utilities)")
    print("📋 Metadata: metadata/framework.json")
    print("")
    print("Next steps:")
    print("  1. Install Agency Swarm: pip install agency-swarm")
    print("  2. Follow .cursor/rules/workflow.mdc for agent creation")
    print("  3. Use .claude/agents/ for orchestrated agency building")
    print("  4. Use IDSE pipeline (blueprint) for project-level planning")
    print("")
