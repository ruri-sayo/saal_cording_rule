"""Commands for SAALCO operations.

Responsibilities:
- Initialize a SAALCO project with standard directory structure.
- Allocate and create feature documents.
- Add items to existing feature documents.
- Record human approvals with content hashing.

Non-responsibilities:
- Document content validation (done by checks module).
- Test execution or quality gate running.

External dependencies:
- git: for repository initialization and user name lookup.
- subprocess: to run git init and git config.
- Filesystem: creates/modifies .gitignore, docs/, .saal/, pyproject.toml.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import resources
from pathlib import Path

from .documents import atomic_write, content_hash, parse_document, set_header
from .errors import SaalcoError, ToolError
from .ids import allocate
from .project import config, git
from .templates import AGENTS, FILE_FOR_KIND, TIER_FILES, feature_document, project_document


def init_project(
    root: Path, name: str, project_type: str, language: str, specs: list[str]
) -> list[str]:
    """Initialize a SAALCO project with standard structure.

    Creates directories, template files, SAAL-DEV-RULES.md copy, .gitignore,
    and pyproject.toml (with guidance if file exists).

    Args:
        root: Project root directory (typically cwd).
        name: Project name.
        project_type: 'research' or 'system'.
        language: 'python' or 'other'.
        specs: List of specification file paths to copy to docs/input/.

    Returns:
        List of file paths that conflicted (already exist, not overwritten).

    Raises:
        SaalcoError: If invalid project_type/language, spec file not found, SAAL-DEV-RULES not available,
                     or git init fails.

    Side Effects:
        Creates directories, writes template files, modifies .gitignore,
        initializes git repo if needed, runs `git init` (external subprocess).
    """
    if project_type not in {"research", "system"} or language not in {"python", "other"}:
        raise SaalcoError("ERROR --type and --language have invalid values.")
    created, conflicts = [], []
    directories = [
        "docs/rules",
        "docs/input",
        "docs/architecture",
        "docs/features",
        "docs/trace",
        "evidence",
        "src",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        ".saal/artifacts",
    ]
    for directory in directories:
        (root / directory).mkdir(parents=True, exist_ok=True)
    files = {
        "AGENTS.md": AGENTS,
        "docs/project.md": project_document(name, project_type, language),
        "docs/ids.ledger": "",
    }
    for rel, text in files.items():
        path = root / rel
        if path.exists():
            conflicts.append(rel)
        else:
            path.write_text(text, encoding="utf-8")
            created.append(rel)
    rule_source = Path(__file__).resolve().parents[2] / "SAAL-DEV-RULES.md"
    if not rule_source.exists():
        rule_source = Path(
            str(resources.files("saalco").joinpath("templates/v1/SAAL-DEV-RULES.md"))
        )
    rule_dest = root / "docs/rules/SAAL-DEV-RULES.md"
    if rule_dest.exists():
        conflicts.append(str(rule_dest.relative_to(root)))
    elif rule_source.is_file():
        shutil.copyfile(rule_source, rule_dest)
        created.append(str(rule_dest.relative_to(root)))
    else:
        raise SaalcoError("ERROR bundled SAAL-DEV-RULES.md is unavailable.")
    for spec in specs:
        source = Path(spec).resolve()
        if not source.is_file():
            raise SaalcoError(f"ERROR {source}: specification file not found.")
        dest = root / "docs/input" / source.name
        if dest.exists():
            conflicts.append(str(dest.relative_to(root)))
        else:
            shutil.copyfile(source, dest)
            created.append(str(dest.relative_to(root)))
    gitignore = root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if ".saal/" not in content:
            gitignore.write_text(content.rstrip() + "\n.saal/\n", encoding="utf-8")
    else:
        gitignore.write_text(".saal/\n", encoding="utf-8")
        created.append(".gitignore")
    if not (root / ".git").exists():
        try:
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE)
        except FileNotFoundError as exc:
            raise ToolError("ERROR git: command not found. Install git.") from exc
        except subprocess.CalledProcessError as exc:
            raise ToolError(f"ERROR git init failed: {exc}") from exc
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[tool.pytest.ini_options]\nmarkers = [\n  "verifies(id, spec=None): specification-derived test",\n  "impl_aware(id=None): implementation-aware test",\n]\n',
            encoding="utf-8",
        )
        created.append("pyproject.toml")
    else:
        marker_snippet = """[tool.pytest.ini_options]
markers = [
  "verifies(id, spec=None): specification-derived test",
  "impl_aware(id=None): implementation-aware test",
]"""
        conflicts.append(f"pyproject.toml (add these markers if absent):\n\n{marker_snippet}")
    return conflicts


def new_feature(root: Path, title: str, tier: str, slug: str | None) -> str:
    """Create a new feature with associated documents.

    Args:
        root: Project root directory.
        title: Feature title (human-readable).
        tier: 'S', 'M', or 'L'.
        slug: URL-safe slug (optional; auto-generated from title if omitted or None).

    Returns:
        Allocated feature ID (e.g., 'F-001').

    Raises:
        SaalcoError: If tier is invalid, slug is auto-generated but empty (non-ASCII title),
                     or feature directory creation fails.

    Side Effects:
        Allocates ID, creates docs/features/F-NNN_slug/ directory,
        writes tier-specific template files.
    """
    if tier not in TIER_FILES:
        raise SaalcoError("ERROR --tier must be S, M, or L.")
    if slug is None:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise SaalcoError("ERROR title cannot produce an ASCII slug; pass --slug SLUG.")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise SaalcoError(
            f"ERROR slug '{slug}' does not match pattern ^[a-z0-9][a-z0-9-]*$. Pass --slug SLUG."
        )
    ident = allocate(root, "F", "-", title)
    folder = root / "docs/features" / f"{ident}_{slug}"
    folder.mkdir(parents=True)
    ptype = config(root)["type"]
    for name in TIER_FILES[tier]:
        path = folder / name
        if path.exists():
            raise SaalcoError(f"ERROR {path}: file already exists; refusing to overwrite.")
        path.write_text(feature_document(name, ident, tier, ptype), encoding="utf-8")
    return ident


def new_item(root: Path, kind: str, feature: str, title: str) -> tuple[str, str | None]:
    """Add an item to a feature document or create it.

    Args:
        root: Project root directory.
        kind: Item kind ('req', 'ad', 'dd', etc.; case-insensitive).
        feature: Feature ID prefix (e.g., 'F-001').
        title: Item title.

    Returns:
        Tuple of (allocated_id, warning). Warning is non-None if approval was invalidated.

    Raises:
        SaalcoError: If kind is unsupported or feature directory is not found/ambiguous.

    Side Effects:
        Allocates ID, creates or appends to document file,
        resets status to draft if document was approved.
    """
    kind = kind.upper()
    if kind not in FILE_FOR_KIND:
        raise SaalcoError(f"ERROR unsupported item kind {kind}.")
    matches = list((root / "docs/features").glob(f"{feature}_*"))
    if len(matches) != 1:
        raise SaalcoError(f"ERROR {feature}: feature not found or ambiguous.")
    ident = allocate(root, kind, feature, title)
    path = matches[0] / FILE_FOR_KIND[kind]
    if not path.exists():
        path.write_text(
            feature_document(
                path.name,
                feature,
                parse_document(matches[0] / "00-meta.md").header["tier"],
                config(root)["type"],
            ),
            encoding="utf-8",
        )
    doc = parse_document(path)
    warning = None
    if doc.header.get("status") == "approved":
        doc.header["status"] = "draft"
        for key in ("approved_by", "approved_at", "approved_hash"):
            doc.header.pop(key, None)
        warning = f"{path.relative_to(root)} approval invalidated; status reset to draft"
    if kind == "DEV":
        block = f"\n### {ident}: {title}\n\nrule:\nscope:\nstatus: open\nreason:\nresolution:\ndecided_by:\ndecided_at:\n"
    else:
        block = f"\n### {ident}: {title}\n\ncovers: {'-' if kind == 'REQ' else ''}\nverify: test\n"
    doc.body = doc.body.rstrip() + "\n" + block
    atomic_write(doc)
    return ident, warning


def approve(root: Path, paths: list[str]) -> None:
    """Record human approval of documents.

    Validates all paths before writing any files. Rejects non-.md files under docs/features/
    unless they are special documents. Requires TTY (unless SAALCO_ALLOW_NONTTY_APPROVE=1).

    Args:
        root: Project root directory.
        paths: Document file paths to approve (relative or absolute).

    Raises:
        SaalcoError: If TTY check fails, git config user.name unavailable,
                     path validation fails, or file I/O fails.

    Side Effects:
        Requires human operator (TTY). Computes content hash, updates header fields,
        writes updated document atomically.
    """
    if not sys.stdin.isatty() and os.environ.get("SAALCO_ALLOW_NONTTY_APPROVE") != "1":
        raise SaalcoError("ERROR approve requires a TTY and must be run by a human.")
    who = git(root, "config", "user.name", check=False)
    if not who:
        raise SaalcoError("ERROR git config user.name is required for approval.")

    # Validate all paths before writing
    for value in paths:
        path = (root / value).resolve() if not Path(value).is_absolute() else Path(value)
        if root not in path.parents:
            raise SaalcoError(f"ERROR {path}: path is outside the project.")
        # Check that path is .md file under docs/features/
        if not path.name.endswith(".md"):
            raise SaalcoError(
                f"ERROR {path}: only .md files may be approved. Pass paths like docs/features/F-001_name/30-detailed-design.md."
            )
        features_dir = root / "docs" / "features"
        try:
            path.relative_to(features_dir)
        except ValueError:
            raise SaalcoError(f"ERROR {path}: only files under docs/features/ may be approved.")

    # All paths valid; now approve
    for value in paths:
        path = (root / value).resolve() if not Path(value).is_absolute() else Path(value)
        doc = parse_document(path)
        set_header(
            doc,
            {
                "status": "approved",
                "approved_by": who,
                "approved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "version": str(int(doc.header.get("version", "0")) + 1),
            },
        )
        doc.header["approved_hash"] = content_hash(doc)
        atomic_write(doc)
