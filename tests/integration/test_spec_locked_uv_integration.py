# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""Integration tests for F-003 (AD-0002): evidence runner and uv lockfile.

Source documents (spec_ctx3/): 20-architecture.md (AD-0002), 30-detailed-design.md
(DD-0006), 50-integration-test-spec.md (IT-0002).

Uses the real `uv` binary (offline) against a temporary, dependency-free project created
with `saalco init`, per IT-0002. Skips (does not fail) if `uv` cannot run offline in this
sandbox -- that is an environmental cause, not a test defect.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import saalco.cli
from saalco import documents


def _require_uv() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is not available on PATH in this environment")


def _init_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    monkeypatch.setenv("UV_OFFLINE", "1")
    code = saalco.cli.main(
        ["init", "--non-interactive", "--name", "proj", "--type", "system", "--language", "python"]
    )
    assert code == 0
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "tester@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Tester"], check=True)
    _ensure_project_table(root)
    return root


def _ensure_project_table(root: Path) -> None:
    """Give the generated pyproject.toml a `[project]` table with a `version` field.

    `saalco init`'s generated pyproject.toml does not declare `[project]` (it only carries
    the pytest marker registration), so there is no dependency-graph-affecting field to
    change for the "outdated lockfile" scenario. This adds a minimal, dependency-free
    `[project]` table so a later version bump can make `uv.lock` stale, per IT-0002 /
    DD-0006's "pyproject.toml を変更して uv.lock が古い状態" scenario. This is test
    scaffolding only, not part of what IT-0002 verifies.
    """
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text()
    if re.search(r"(?m)^\[project\]", text):
        return
    header = '[project]\nname = "proj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n\n'
    pyproject.write_text(header + text)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True)


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
            # left as-is: test.unit stays "uv run pytest tests/unit" (template default),
            # so --locked injection is observable.
        },
    )
    documents.atomic_write(doc)


def _uv_lock_offline(root: Path) -> None:
    result = subprocess.run(
        ["uv", "lock", "--offline"],
        cwd=root,
        capture_output=True,
        text=True,
        env={**os.environ, "UV_OFFLINE": "1"},
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(
            f"`uv lock --offline` could not run in this environment: {result.stderr.strip()}"
        )


def _snapshot(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(p.relative_to(path)) for p in path.rglob("*")}


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


@pytest.mark.verifies("AD-0002", spec="IT-0002")
def test_missing_uv_lock_stops_evidence_without_output(tmp_path, monkeypatch):
    _require_uv()
    root = _init_repo(tmp_path, monkeypatch)
    _minimize_gates(root)
    _commit_all(root, "no uv.lock")

    before_evidence = _snapshot(root / "evidence")
    before_artifacts = _snapshot(root / ".saal" / "artifacts")

    code = saalco.cli.main(["evidence"])

    assert code == 2
    assert not (root / "uv.lock").exists()
    assert _snapshot(root / "evidence") == before_evidence
    assert _snapshot(root / ".saal" / "artifacts") == before_artifacts


@pytest.mark.verifies("AD-0002", spec="IT-0002")
def test_untracked_uv_lock_stops_evidence(tmp_path, monkeypatch):
    _require_uv()
    root = _init_repo(tmp_path, monkeypatch)
    _minimize_gates(root)

    gitignore = root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    gitignore.write_text(existing + "\nuv.lock\n")
    _commit_all(root, "ignore uv.lock")

    _uv_lock_offline(root)
    assert (root / "uv.lock").exists()

    code = saalco.cli.main(["evidence"])

    assert code == 2


@pytest.mark.verifies("AD-0002", spec="IT-0002")
def test_outdated_uv_lock_stops_evidence_and_lock_is_unchanged(tmp_path, monkeypatch):
    _require_uv()
    root = _init_repo(tmp_path, monkeypatch)
    _minimize_gates(root)
    _commit_all(root, "configure gates")

    _uv_lock_offline(root)
    _commit_all(root, "add up-to-date uv.lock")

    lock_before = (root / "uv.lock").read_bytes()

    _bump_pyproject_version(root)
    _commit_all(root, "bump pyproject version (makes uv.lock stale)")

    code = saalco.cli.main(["evidence"])

    assert code == 2
    assert (root / "uv.lock").read_bytes() == lock_before


@pytest.mark.verifies("AD-0002", spec="IT-0002")
def test_up_to_date_uv_lock_allows_evidence_with_locked_commands(tmp_path, monkeypatch):
    _require_uv()
    root = _init_repo(tmp_path, monkeypatch)
    _minimize_gates(root)
    _commit_all(root, "configure gates")

    _uv_lock_offline(root)
    _commit_all(root, "add up-to-date uv.lock")

    lock_before = (root / "uv.lock").read_bytes()

    from saalco import evidence

    manifest_path, _overall = evidence.create(root)

    assert (root / "uv.lock").read_bytes() == lock_before

    manifest = json.loads(Path(manifest_path).read_text())
    unit_commands = [g["command"] for g in manifest["gates"] if "tests/unit" in g["command"]]
    assert len(unit_commands) == 1
    unit_command = unit_commands[0]
    # The evidence runner may append further flags (coverage/junit options) after the
    # configured command text, so check a stable prefix rather than exact equality.
    tokens = unit_command.split()
    assert tokens[0] == "uv"
    assert tokens[1] == "run"
    assert tokens[2] == "--locked"
    assert unit_command.count("--locked") == 1
    assert "pytest tests/unit" in unit_command
