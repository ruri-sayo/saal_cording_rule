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
from .errors import SaalcoError
from .ids import allocate
from .project import config, git
from .templates import AGENTS, FILE_FOR_KIND, TIER_FILES, feature_document, project_document


def init_project(
    root: Path, name: str, project_type: str, language: str, specs: list[str]
) -> list[str]:
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
        if ".saal/artifacts/" not in content:
            gitignore.write_text(content.rstrip() + "\n.saal/artifacts/\n", encoding="utf-8")
    else:
        gitignore.write_text(".saal/artifacts/\n", encoding="utf-8")
        created.append(".gitignore")
    if not (root / ".git").exists():
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE)
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[tool.pytest.ini_options]\nmarkers = [\n  "verifies(id, spec=None): specification-derived test",\n  "impl_aware(id=None): implementation-aware test",\n]\n',
            encoding="utf-8",
        )
        created.append("pyproject.toml")
    elif root != Path(__file__).resolve().parents[2]:
        conflicts.append("pyproject.toml (add pytest markers manually if absent)")
    return conflicts


def new_feature(root: Path, title: str, tier: str, slug: str | None) -> str:
    if tier not in TIER_FILES:
        raise SaalcoError("ERROR --tier must be S, M, or L.")
    if slug is None:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise SaalcoError("ERROR title cannot produce an ASCII slug; pass --slug.")
    ident = allocate(root, "F", "-", title)
    folder = root / "docs/features" / f"{ident}_{slug}"
    folder.mkdir(parents=True)
    ptype = config(root)["type"]
    for name in TIER_FILES[tier]:
        (folder / name).write_text(feature_document(name, ident, tier, ptype), encoding="utf-8")
    return ident


def new_item(root: Path, kind: str, feature: str, title: str) -> tuple[str, str | None]:
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
    if not sys.stdin.isatty() and os.environ.get("SAALCO_ALLOW_NONTTY_APPROVE") != "1":
        raise SaalcoError("ERROR approve requires a TTY and must be run by a human.")
    who = git(root, "config", "user.name", check=False)
    if not who:
        raise SaalcoError("ERROR git config user.name is required for approval.")
    for value in paths:
        path = (root / value).resolve() if not Path(value).is_absolute() else Path(value)
        if root not in path.parents:
            raise SaalcoError(f"ERROR {path}: path is outside the project.")
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
