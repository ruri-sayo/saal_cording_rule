from __future__ import annotations

import subprocess
from pathlib import Path

from .documents import parse_document
from .errors import SaalcoError


def discover(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "docs" / "project.md").is_file():
            return candidate
    raise SaalcoError(f"ERROR {here}: not inside a SAALCO project. Run `saalco init`.")


def config(root: Path) -> dict[str, str]:
    doc = parse_document(root / "docs" / "project.md")
    version = doc.header.get("saal_rules_version")
    if version != "1.0":
        raise SaalcoError(
            f"ERROR docs/project.md: unsupported saal_rules_version {version!r}; expected '1.0'."
        )
    return doc.header


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if check and proc.returncode:
        raise SaalcoError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()
