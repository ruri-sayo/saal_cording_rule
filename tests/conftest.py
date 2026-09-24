"""Shared pytest fixtures and helpers for the SAALCO test suite.

Responsibilities:
- Copy `tests/fixtures/<name>` project trees into a git-initialized `tmp_path`.
- Finalize fixture documents (`approved_hash: COMPUTE` placeholders) using the real
  `saalco.documents.content_hash` so fixtures never hardcode a hash by hand.
- Provide helpers to synthesize an Evidence manifest and a coverage-contexts JSON without
  running the real gates/coverage pipeline, so unit/integration tests stay fast and offline.

Non-responsibilities:
- Does not run pytest/coverage subprocesses itself; see tests/e2e for real subprocess runs.

External dependencies: git (subprocess), invoked only inside `tmp_path` trees. Tests must
never touch the real repository's git config; every helper here operates on a path the
caller passes in, defaulting to nothing outside `tmp_path`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from saalco.documents import content_hash, parse_document

FIXTURES_DIR = Path(__file__).parent / "fixtures"

#: `tests/fixtures/**` holds simulated *user* SAALCO projects (their own `verifies`-marked
#: tests are fixture data, not part of this test suite) — pytest must never collect them as
#: its own tests. saalco.markers.scan_tests independently skips this same tree so a real
#: `saalco check` run against this repository never counts fixture markers as its own.
collect_ignore_glob = ["fixtures/*"]

#: Env layered onto every git invocation in these helpers: never read the user's global/
#: system git config, so fixture repos are fully deterministic regardless of the host.
GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "SAALCO Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "SAALCO Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        env={**os.environ, **GIT_ENV},
        text=True,
        capture_output=True,
        check=True,
    )


def finalize_documents(root: Path) -> None:
    """Replace `approved_hash: COMPUTE` placeholders with the real content hash.

    Side Effects:
        Rewrites every `docs/features/**/*.md` whose header carries the placeholder.
    """
    for path in sorted((root / "docs" / "features").glob("F-*/*.md")):
        doc = parse_document(path)
        if doc.header.get("approved_hash") == "COMPUTE":
            doc.header["approved_hash"] = content_hash(doc)
            path.write_text(
                "---\n"
                + "".join(f"{k}: {v}\n" for k, v in doc.header.items())
                + "---\n"
                + doc.body,
                encoding="utf-8",
            )


def init_git(root: Path, *, commit: bool = True) -> None:
    """Initialize a throwaway git repo in `root` with a deterministic local identity.

    Side Effects:
        Runs `git init`/`config`/`add`/`commit` in `root` only; never reads or writes the
        real repository's `.git/config` (GIT_CONFIG_NOSYSTEM/GIT_CONFIG_GLOBAL are set to
        skip host-level config entirely).
    """
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "SAALCO Test")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "commit.gpgsign", "false")
    if commit:
        commit_all(root, "fixture: initial commit")


def commit_all(root: Path, message: str) -> str:
    """`git add -A && git commit` in `root`, returning the new commit hash.

    Side Effects:
        Stages and commits every change under `root`.
    """
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message, "--allow-empty")
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def copy_fixture(name: str, tmp_path: Path, *, git: bool = True) -> Path:
    """Copy `tests/fixtures/<name>` into `tmp_path`, finalize hashes, and git-init it.

    Args:
        name: fixture directory name under `tests/fixtures/`.
        tmp_path: pytest's per-test temp directory (used as the copy destination directly).
        git: when True (default), run `git init` and commit the initial tree.

    Returns:
        `tmp_path`, now containing the fixture project (and its own git repo, if `git`).

    Side Effects:
        Copies files, optionally runs git.
    """
    source = FIXTURES_DIR / name
    for entry in source.iterdir():
        destination = tmp_path / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination)
        else:
            shutil.copy2(entry, destination)
    finalize_documents(tmp_path)
    gitignore = tmp_path / ".gitignore"
    if not gitignore.exists():
        # Mirror a real `saalco init` project: .saal/ (raw artifacts/packages) is never
        # tracked, so write_coverage_json's untracked output doesn't pollute git diffs that
        # current_manifest/_commit_is_current expect to be evidence-bookkeeping-only.
        gitignore.write_text(".saal/\n")
    if git:
        init_git(tmp_path)
    return tmp_path


def write_manifest(
    root: Path,
    *,
    tests: list[dict[str, object]] | None = None,
    coverage: dict[str, object] | None = None,
    gates: list[dict[str, object]] | None = None,
    overall: str = "PASS",
    target: str | None = None,
    run_id: str = "20240101T000000",
) -> dict[str, object]:
    """Write and commit a synthetic Evidence manifest current for HEAD.

    Bypasses the real gate/coverage pipeline (`evidence.create`) entirely: writes
    `evidence/<target>/<run_id>/manifest.json` directly against the current HEAD, then
    commits it. Because the only change between the pre-manifest HEAD and the new HEAD is
    under `evidence/`, `saalco.evidence.current_manifest` picks it up as current (contract 3).

    Args:
        root: a git-initialized project root (see `copy_fixture`).
        tests: manifest `tests[]` entries; defaults to none.
        coverage: manifest `coverage` block; defaults to an all-NOT_EVALUATED block.
        gates: manifest `gates[]` entries; defaults to none.
        overall: top-level `overall` field.
        target: commit the manifest targets; defaults to current HEAD.
        run_id: manifest `run_id`.

    Returns:
        The manifest dict that was written.

    Side Effects:
        Writes `evidence/<target>/<run_id>/manifest.json` and commits it (git add -A; commit).
    """
    target = target or _git(root, "rev-parse", "HEAD").stdout.strip()
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "saal_rules_version": "1.0",
        "saalco_version": "1.0.0",
        "target_commit": target,
        "run_id": run_id,
        "executed_at": "2024-01-01T00:00:00+00:00",
        "environment": {"os": "test", "python": "3.11", "arch": "test"},
        "lockfile": {"path": None, "sha256": None},
        "gates": gates or [],
        "tests": tests or [],
        "coverage": coverage
        or {
            "total": None,
            "diff": None,
            "diff_base_commit": None,
            "status": "NOT_EVALUATED",
            "json_path": None,
        },
        "artifacts": [],
        "overall": overall,
    }
    destination = root / "evidence" / target / run_id
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    commit_all(root, f"evidence: {run_id}")
    return manifest


def write_coverage_json(
    root: Path, target: str, run_id: str, files: dict[str, dict[str, list[str]]]
) -> str:
    """Write a coverage.py-shaped JSON with per-line test contexts.

    Args:
        root: project root.
        target: commit hash the artifacts directory is keyed by.
        run_id: run id the artifacts directory is keyed by.
        files: `{repo_relative_path: {line_number_str: [context, ...]}}`.

    Returns:
        The repo-relative `json_path` suitable for `coverage.json_path` in a manifest.

    Side Effects:
        Writes `.saal/artifacts/<target>/<run_id>/coverage.json` (untracked; not committed).
    """
    raw = root / ".saal" / "artifacts" / target / run_id
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / "coverage.json"
    data = {
        "files": {
            name: {"contexts": contexts, "executed_lines": [], "missing_lines": []}
            for name, contexts in files.items()
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path.relative_to(root).as_posix()


@pytest.fixture
def saal_project(tmp_path):
    """Factory fixture: `saal_project("valid_project")` copies + git-inits a fixture."""

    def _make(name: str, *, git: bool = True) -> Path:
        return copy_fixture(name, tmp_path, git=git)

    return _make


@pytest.fixture
def write_manifest_fn():
    """Factory fixture exposing `write_manifest` as a callable for tests."""
    return write_manifest


@pytest.fixture
def write_coverage_fn():
    """Factory fixture exposing `write_coverage_json` as a callable for tests."""
    return write_coverage_json


@pytest.fixture
def finalize_fn():
    """Factory fixture exposing `finalize_documents` as a callable for tests."""
    return finalize_documents


@pytest.fixture
def commit_all_fn():
    """Factory fixture exposing `commit_all` as a callable for tests."""
    return commit_all


@pytest.fixture
def head_commit():
    """Factory fixture: `head_commit(root)` returns `git rev-parse HEAD` for `root`."""

    def _head(root: Path) -> str:
        return _git(root, "rev-parse", "HEAD").stdout.strip()

    return _head
