"""End-to-end test: the full spec §19 SAALCO lifecycle via real `python -m saalco` subprocesses.

init -> new (REQ/AD/DD/UT/ST) -> sample implementation + spec-derived tests in the SAMPLE
project -> approve -> commit -> check -> evidence -> commit evidence -> check --verification
(exit 0) -> trace (verified).

Runs `[sys.executable, "-m", "saalco", ...]` (never the uv-tool-installed `saalco`, which may
be stale) so the subprocess uses this checkout's code. `saalco.evidence.create` always shells
out to a bare `uv run coverage json ...`; offline, that only succeeds if `uv run` can resolve
a `coverage` executable without a network round trip. This module probes that exact command
first and skips (not fails) when it cannot, per the shared brief's environmental-skip carve-out.

pytestmark impl_aware: drives the CLI and asserts on its real subprocess output/exit codes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.impl_aware

TIMEOUT = 60


def _env(root: Path) -> dict[str, str]:
    """Environment for subprocess calls: offline uv, isolated git identity, fixed PYTHONPATH.

    Prepends this checkout's own venv `bin/` to PATH so a bare `uv run coverage ...` (no
    pyproject dependencies in the sample project) resolves to the `coverage` already
    installed for saalco's own dev environment, instead of trying to sync a fresh venv from
    the network.
    """
    venv_bin = str(Path(sys.executable).parent)
    values = dict(os.environ)
    values["PATH"] = f"{venv_bin}{os.pathsep}{values.get('PATH', '')}"
    values["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    values["UV_OFFLINE"] = "1"
    values["GIT_CONFIG_NOSYSTEM"] = "1"
    values["GIT_CONFIG_GLOBAL"] = os.devnull
    values["SAALCO_ALLOW_NONTTY_APPROVE"] = "1"
    return values


def _saalco(root: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "saalco", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )


def _git(root: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )


def _replace(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text().replace(old, new))


@pytest.fixture
def e2e_root(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    env = _env(tmp_path)
    return tmp_path, env


def test_full_spec_19_lifecycle(e2e_root):
    root, env = e2e_root

    probe = subprocess.run(
        ["uv", "run", "coverage", "--version"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(
            "environment: `uv run coverage` cannot be resolved offline in a fresh temp "
            f"project (needed by saalco.evidence.create's hardcoded coverage export): "
            f"{probe.stderr.strip()[:500]}"
        )

    # --- init ---------------------------------------------------------
    result = _saalco(
        root,
        "init",
        "--name",
        "e2e",
        "--type",
        "system",
        "--language",
        "python",
        "--non-interactive",
        env=env,
    )
    assert result.returncode == 0, result.stderr

    project_md = root / "docs/project.md"
    text = project_md.read_text()
    for key in ("gate.01.format", "gate.02.lint", "gate.03.typecheck", "gate.06.static_analysis"):
        text = (
            text.replace(f"{key}: uv run ruff format --check .", f"{key}:")
            .replace(f"{key}: uv run ruff check .", f"{key}:")
            .replace(f"{key}: uv run mypy src", f"{key}:")
        )
    for category in ("unit", "integration", "e2e"):
        text = text.replace(
            f"test.{category}: uv run pytest tests/{category}",
            f"test.{category}: {sys.executable} -m pytest tests/{category}",
        )
    project_md.write_text(text)

    # Let the sample project's own tests import its own src/ modules directly (a normal
    # pytest "pythonpath" ini option, not a saalco concept).
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace("markers = [", 'pythonpath = ["src"]\nmarkers = [')
    )

    # `uv run coverage json` (invoked by saalco.evidence.create) syncs a throwaway venv for
    # this ad-hoc pyproject.toml, writing .venv/ and uv.lock; those must never be tracked, or
    # they'd show up as a non-bookkeeping diff and break current_manifest's "current" check.
    gitignore = root / ".gitignore"
    gitignore.write_text(gitignore.read_text() + ".venv/\nuv.lock\n")

    # --- new: feature (Tier M, so AD / IT documents are Tier-mandated).
    result = _saalco(root, "new", "feature", "Widget", "--tier", "M", "--slug", "widget", env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "F-001"

    for kind in ("req", "ad", "dd", "ut", "st"):
        result = _saalco(root, "new", kind, f"Widget {kind}", "--feature", "F-001", env=env)
        assert result.returncode == 0, result.stderr

    feature_dir = root / "docs/features/F-001_widget"
    _replace(feature_dir / "20-architecture.md", "covers: \n", "covers: REQ-0001\n")
    _replace(feature_dir / "30-detailed-design.md", "covers: \n", "covers: AD-0001\n")
    _replace(feature_dir / "40-unit-test-spec.md", "covers: \n", "covers: DD-0001\n")
    _replace(feature_dir / "60-system-e2e-spec.md", "covers: \n", "covers: REQ-0001\n")

    # --- sample implementation + spec-derived tests (SAMPLE project; `verifies` is fine
    #     here since this is not saalco's own suite) ----------------------------------
    (root / "src" / "widget.py").write_text(
        '"""Widget module for the e2e sample project."""\n\n\ndef area(w: int, h: int) -> int:\n'
        '    """Return the rectangle area."""\n    return w * h\n'
    )
    (root / "tests/unit/test_widget.py").write_text(
        "import pytest\n\nfrom widget import area\n\n\n"
        "@pytest.mark.verifies('DD-0001')\n"
        "def test_area():\n    assert area(2, 3) == 6\n"
    )
    (root / "tests/integration/test_widget_ad.py").write_text(
        "import pytest\n\n\n@pytest.mark.verifies('AD-0001')\ndef test_architecture_holds():\n    assert True\n"
    )
    (root / "tests/e2e/test_widget_req.py").write_text(
        "import pytest\n\n\n@pytest.mark.verifies('REQ-0001')\ndef test_widget_end_to_end():\n    assert True\n"
    )

    # --- approve --------------------------------------------------------
    _git(root, "config", "user.name", "E2E Human", env=env)
    _git(root, "config", "user.email", "e2e@example.invalid", env=env)
    _git(root, "config", "commit.gpgsign", "false", env=env)
    to_approve = [
        str(feature_dir / name)
        for name in (
            "00-meta.md",
            "10-requirements.md",
            "20-architecture.md",
            "30-detailed-design.md",
            "40-unit-test-spec.md",
            "60-system-e2e-spec.md",
        )
    ]
    result = _saalco(root, "approve", *to_approve, env=env)
    assert result.returncode == 0, result.stderr

    # --- commit -----------------------------------------------------------
    _git(root, "add", "-A", env=env)
    result = _git(root, "commit", "-q", "-m", "e2e: widget feature", env=env)
    assert result.returncode == 0, result.stderr

    # --- check (static) -----------------------------------------------
    result = _saalco(root, "check", env=env)
    assert result.returncode == 0, result.stdout + result.stderr

    # --- evidence -------------------------------------------------------
    result = _saalco(root, "evidence", env=env)
    assert "Overall: PASS" in result.stdout, result.stdout + "\n" + result.stderr
    assert result.returncode == 0, result.stdout + result.stderr

    # --- commit evidence --------------------------------------------------
    _git(root, "add", "-A", env=env)
    result = _git(root, "commit", "-q", "-m", "e2e: evidence", env=env)
    assert result.returncode == 0, result.stderr

    # --- check --verification -------------------------------------------
    result = _saalco(root, "check", "--verification", env=env)
    assert result.returncode == 0, result.stdout + result.stderr

    # --- trace: REQ-0001 verified ----------------------------------------
    result = _saalco(root, "trace", "--json", env=env)
    assert result.returncode == 0, result.stderr
    assert '"req_id": "REQ-0001"' in result.stdout
    assert '"verify_status": "verified"' in result.stdout
    rtm = (root / "docs/trace/rtm.csv").read_text()
    assert "REQ-0001" in rtm and "verified" in rtm


# NOTE: the coverage_failure fixture's "check --verification FAIL without a DEV, WARNING with
# a matching open DEV (rule 7.3)" scenario is covered by
# tests/integration/test_cli.py::test_check_verification_coverage_fail_without_dev and
# ::test_check_verification_coverage_fail_downgraded_by_matching_open_dev — those exercise the
# same in-process checks.run() path deterministically and offline, without needing a second
# subprocess-based repetition here.
