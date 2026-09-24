"""Project discovery and configuration.

Responsibilities:
- Locate SAALCO project root by finding docs/project.md.
- Read and validate project configuration.
- Execute git commands with error handling.

Non-responsibilities:
- Document parsing (done by documents module).
- File operations beyond reading project.md.

External dependencies:
- git: for version control operations; missing binary -> ToolError.
- subprocess: to run git commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .documents import parse_document
from .errors import SaalcoError, ToolError


def discover(start: Path | None = None) -> Path:
    """Locate the SAALCO project root.

    Searches up from start directory for docs/project.md.

    Args:
        start: Starting directory; defaults to current working directory.

    Returns:
        Absolute path to project root.

    Raises:
        SaalcoError: If not inside a SAALCO project.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "docs" / "project.md").is_file():
            return candidate
    raise SaalcoError(f"ERROR {here}: not inside a SAALCO project. Run `saalco init`.")


#: Rule versions this SAALCO can operate. 1.1 only adds the language rule (Rule 11.5),
#: which SAALCO does not enforce, so both versions are checked identically.
SUPPORTED_RULES_VERSIONS = ("1.0", "1.1")


def config(root: Path) -> dict[str, str]:
    """Read and validate project configuration.

    Args:
        root: Project root directory.

    Returns:
        Dictionary of configuration key-value pairs from docs/project.md header.

    Raises:
        SaalcoError: If saal_rules_version is not one of SUPPORTED_RULES_VERSIONS.
    """
    doc = parse_document(root / "docs" / "project.md")
    version = doc.header.get("saal_rules_version")
    if version not in SUPPORTED_RULES_VERSIONS:
        expected = ", ".join(SUPPORTED_RULES_VERSIONS)
        raise SaalcoError(
            f"ERROR docs/project.md: unsupported saal_rules_version {version!r}; "
            f"expected one of {expected}."
        )
    return doc.header


def git(root: Path, *args: str, check: bool = True) -> str:
    """Execute a git command in the project directory.

    Args:
        root: Project root directory (working directory for git).
        *args: Arguments to pass to git command.
        check: If True, raise ToolError on non-zero exit; if False, return empty string.

    Returns:
        stdout output, stripped of trailing whitespace.

    Raises:
        ToolError: If check=True and git exits non-zero, or git binary is not found.
        SaalcoError: For other git failures (when check=True).

    Side Effects:
        Executes external git process.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("ERROR git: command not found. Install git.") from exc
    if check and proc.returncode:
        raise SaalcoError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()
