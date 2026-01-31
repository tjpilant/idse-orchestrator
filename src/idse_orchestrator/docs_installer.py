from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple

DOC_FILES = [
    "01-idse-philosophy.md",
    "02-idse-constitution.md",
    "03-idse-pipeline.md",
    "04-idse-agents.md",
    "04-idse-spec-plan-tasks.md",
    "05-idse-prompting-guide.md",
    "06-idse-implementation-patterns.md",
    "07-sdd-to-idse.md",
    "08-getting-started.md",
    "09-metadata-sop.md",
]

TEMPLATE_FILES = [
    "context-template.md",
    "feedback-template.md",
    "intent-template.md",
    "plan-template.md",
    "spec-template.md",
    "tasks-template.md",
    "test-plan-template.md",
]


def _first_existing_path(candidates: List[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def install_docs(workspace: Path, force: bool = False) -> Tuple[int, int]:
    """
    Copy bundled IDSE docs and templates into the target workspace.

    Returns (docs_copied, templates_copied).
    """
    workspace = workspace.resolve()
    target_docs = workspace / ".idse" / "docs"
    target_templates = workspace / ".idse" / "kb" / "templates"

    # Locate packaged resources; fallback to repo-level docs if running editable
    pkg_root = Path(__file__).resolve().parent
    repo_root = pkg_root.parent.parent.parent  # back to repo root when editable

    doc_source = _first_existing_path(
        [
            pkg_root / "resources" / "docs",
            repo_root / "docs",
        ]
    )
    template_source = _first_existing_path(
        [
            pkg_root / "resources" / "templates",
            repo_root / "docs" / "kb" / "templates",
        ]
    )

    if doc_source is None:
        raise RuntimeError("Could not find bundled IDSE docs to install.")
    if template_source is None:
        raise RuntimeError("Could not find bundled template files to install.")

    target_docs.mkdir(parents=True, exist_ok=True)
    target_templates.mkdir(parents=True, exist_ok=True)

    docs_copied = _copy_files(doc_source, target_docs, DOC_FILES, force)
    templates_copied = _copy_files(template_source, target_templates, TEMPLATE_FILES, force)
    return docs_copied, templates_copied


def _copy_files(source_dir: Path, dest_dir: Path, filenames: List[str], force: bool) -> int:
    copied = 0
    for name in filenames:
        src = source_dir / name
        dest = dest_dir / name

        if not src.exists():
            continue
        if dest.exists() and not force:
            continue

        shutil.copy2(src, dest)
        copied += 1
    return copied
