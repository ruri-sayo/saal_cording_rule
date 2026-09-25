# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""System / E2E test for F-003 (REQ-0006): missing, outdated, current uv.lock via the CLI.

Source documents (spec_ctx3/): 10-requirements.md (REQ-0006), 60-system-e2e-spec.md
(ST-0005), public-interface.md (`usage: saalco ...` --help text).

Drives the real CLI as a subprocess (`python -m saalco ...`), with `UV_OFFLINE=1` so no
network access is needed. Skips (does not fail) if `uv` cannot run offline in this
sandbox -- an environmental cause, not a test defect.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from saalco import documents


def _require_uv() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is not available on PATH in this environment")


def _env() -> dict[str, str]:
    return {**os.environ, "UV_OFFLINE": "1"}


def _run_saalco(root: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "saalco", *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=_env(),
        timeout=timeout,
        check=False,
    )


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )


def _snapshot(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(p.relative_to(path)) for p in path.rglob("*")}


def _uv_lock_offline(root: Path) -> None:
    result = subprocess.run(
        ["uv", "lock", "--offline"],
        cwd=root,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(
            f"`uv lock --offline` could not run in this environment: {result.stderr.strip()}"
        )


def _ensure_project_table(root: Path) -> None:
    """Give the generated pyproject.toml a `[project]` table with a `version` field.

    `saalco init`'s generated pyproject.toml does not declare `[project]` (it only carries
    the pytest marker registration), so there is no dependency-graph-affecting field to
    change for the "outdated lockfile" step. This adds a minimal, dependency-free
    `[project]` table so a later version bump can make `uv.lock` stale, per ST-0005's
    "pyproject.toml の version を変えて commit" step. This is test scaffolding only, not
    part of what ST-0005 verifies.
    """
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text()
    if re.search(r"(?m)^\[project\]", text):
        return
    header = '[project]\nname = "proj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n\n'
    pyproject.write_text(header + text)


def _minimize_gates(root: Path) -> None:
    """Keep evidence fast/deterministic: empty gates, keep test.unit as the only uv-run step."""
    doc = documents.parse_document(root / "docs" / "project.md")
    documents.set_header(
        doc,
        {
            "gate.01.format": "",
            "gate.02.lint": "",
            "gate.03.typecheck": "",
            "test.integration": "",
            "test.e2e": "",
        },
    )
    documents.atomic_write(doc)


def _bump_pyproject_version(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text()
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert match, "pyproject.toml has no version field to bump"
    old = match.group(1)
    parts = old.split(".")
    parts[-1] = str(int(parts[-1]) + 1) if parts[-1].isdigit() else "1"
    new = ".".join(parts)
    text = text[: match.start(1)] + new + text[match.end(1) :]
    pyproject.write_text(text)


@pytest.mark.verifies("REQ-0006", spec="ST-0005")
def test_evidence_with_missing_outdated_and_current_uv_lock_via_cli(tmp_path):
    _require_uv()
    root = tmp_path / "proj"
    root.mkdir()

    # 1. `saalco init` (language: python) -> guidance about the missing uv.lock.
    init_result = _run_saalco(
        root,
        "init",
        "--non-interactive",
        "--name",
        "proj",
        "--type",
        "system",
        "--language",
        "python",
    )
    assert init_result.returncode == 0
    assert not (root / "uv.lock").exists()
    assert "uv.lock" in init_result.stderr
    assert "uv lock" in init_result.stderr

    _run_git(root, "config", "user.email", "tester@example.com")
    _run_git(root, "config", "user.name", "Tester")

    _ensure_project_table(root)
    _minimize_gates(root)
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "init (no uv.lock yet)")

    before_evidence = _snapshot(root / "evidence")
    before_artifacts = _snapshot(root / ".saal" / "artifacts")

    # 2. `saalco evidence` stops at exit 2 and guides toward `uv lock`.
    evidence_result = _run_saalco(root, "evidence")
    assert evidence_result.returncode == 2
    assert "uv.lock" in evidence_result.stderr
    assert "uv lock" in evidence_result.stderr
    assert not (root / "uv.lock").exists()
    assert _snapshot(root / "evidence") == before_evidence
    assert _snapshot(root / ".saal" / "artifacts") == before_artifacts

    # 3. Run `uv lock` (offline) and commit uv.lock.
    _uv_lock_offline(root)
    assert (root / "uv.lock").exists()
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "add uv.lock")
    lock_after_first_lock = (root / "uv.lock").read_bytes()

    # 4. `saalco evidence` now creates Evidence.
    evidence_result = _run_saalco(root, "evidence")
    assert evidence_result.returncode in (0, 1)  # PASS or FAIL, but not a precondition stop
    assert any(p.name == "manifest.json" for p in (root / "evidence").rglob("manifest.json"))
    assert (root / "uv.lock").read_bytes() == lock_after_first_lock

    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "record first evidence")

    # 5. Change pyproject.toml (bump version) and commit -> uv.lock becomes outdated.
    _bump_pyproject_version(root)
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "bump pyproject version")

    # 6. `saalco evidence` stops at exit 2 again, uv.lock is unchanged.
    evidence_result = _run_saalco(root, "evidence")
    assert evidence_result.returncode == 2
    assert "uv.lock" in evidence_result.stderr
    assert "uv lock" in evidence_result.stderr
    assert (root / "uv.lock").read_bytes() == lock_after_first_lock

    # 7. Run `uv lock` again and commit.
    _uv_lock_offline(root)
    lock_after_second_lock = (root / "uv.lock").read_bytes()
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "re-lock uv.lock after pyproject bump")

    # 8. `saalco evidence` creates Evidence again.
    evidence_result = _run_saalco(root, "evidence")
    assert evidence_result.returncode in (0, 1)
    assert (root / "uv.lock").read_bytes() == lock_after_second_lock
