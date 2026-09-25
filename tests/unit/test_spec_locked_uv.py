# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""Unit tests for F-003 (DD-0006): uv.lock precheck, --locked injection, init guidance.

Source documents (spec_ctx3/): 00-meta.md, 10-requirements.md (REQ-0006),
20-architecture.md (AD-0002), 30-detailed-design.md (DD-0006), 40-unit-test-spec.md
(UT-0006), public-interface.md.

External commands are replaced by a fake `uv` executable placed first on PATH, per
UT-0006 ("外部コマンドは置き換えて確認してよい"). Real `git` and `saalco` (in-process)
are used; nothing here touches src/ or existing tests/.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import saalco.cli
from saalco import documents


def _write_fake_uv(bin_dir: Path, lock_check_exit: int = 0) -> None:
    """Install a fake `uv` on PATH that fakes `lock --check` and `run [--locked|--frozen] ...`."""
    script = bin_dir / "uv"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [ "${1:-}" = "lock" ] && [ "${2:-}" = "--check" ]; then\n'
        '  echo "fake uv lock --check" >&2\n'
        f'  exit "${{UV_LOCK_CHECK_EXIT:-{lock_check_exit}}}"\n'
        "fi\n"
        'if [ "${1:-}" = "--version" ]; then\n'
        '  echo "uv 0.11.8 (fake)"\n'
        "  exit 0\n"
        "fi\n"
        'if [ "${1:-}" = "run" ]; then\n'
        "  shift\n"
        '  if [ "${1:-}" = "--locked" ] || [ "${1:-}" = "--frozen" ]; then\n'
        "    shift\n"
        "  fi\n"
        '  args="$*"\n'
        '  if [[ "$args" == *pytest* ]]; then\n'
        '    prev=""\n'
        '    for a in "$@"; do\n'
        '      case "$a" in\n'
        "        --junitxml=*)\n"
        '          path="${a#--junitxml=}"\n'
        '          mkdir -p "$(dirname "$path")"\n'
        "          cat > \"$path\" <<'XML'\n"
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<testsuites><testsuite name="pytest" tests="0" errors="0" failures="0" '
        'skipped="0"></testsuite></testsuites>\n'
        "XML\n"
        "          ;;\n"
        "      esac\n"
        '      prev="$a"\n'
        "    done\n"
        "    exit 0\n"
        "  fi\n"
        '  if [[ "$args" == *"coverage"*"json"* ]]; then\n'
        '    prev=""\n'
        '    for a in "$@"; do\n'
        '      if [ "$prev" = "-o" ]; then\n'
        '        mkdir -p "$(dirname "$a")"\n'
        '        echo \'{"files": {}}\' > "$a"\n'
        "      fi\n"
        '      prev="$a"\n'
        "    done\n"
        "    exit 0\n"
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _prepend_path(monkeypatch: pytest.MonkeyPatch, bin_dir: Path) -> None:
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")


def _init_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str = "python") -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    code = saalco.cli.main(
        [
            "init",
            "--non-interactive",
            "--name",
            "proj",
            "--type",
            "system",
            "--language",
            language,
        ]
    )
    assert code == 0
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "tester@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Tester"], check=True)
    return root


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True)


def _set_project_fields(root: Path, values: dict[str, str]) -> None:
    doc = documents.parse_document(root / "docs" / "project.md")
    documents.set_header(doc, values)
    documents.atomic_write(doc)


def _snapshot(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(p.relative_to(path)) for p in path.rglob("*")}


def _gate_command(manifest: dict, substring: str) -> str:
    matches = [g["command"] for g in manifest["gates"] if substring in g["command"]]
    assert len(matches) == 1, (
        f"expected exactly one gate command containing {substring!r}, got {matches}"
    )
    return matches[0]


def _assert_uv_run_flag(command: str, expected_flag: str) -> None:
    """Assert the command's first two tokens are `uv run`, followed immediately by
    `expected_flag`, and `--locked` appears exactly once iff `expected_flag == "--locked"`
    (i.e. no double-insertion of --locked into an already-locked/frozen command).

    The evidence runner may append further, unspecified flags (coverage/junit options) after
    the original command text (contract 1 only fixes the manifest schema, not per-gate
    argument appending), so this checks a stable prefix rather than exact equality.
    """
    tokens = command.split()
    assert tokens[0] == "uv"
    assert tokens[1] == "run"
    assert tokens[2] == expected_flag
    assert command.count("--locked") == (1 if expected_flag == "--locked" else 0)


# ---------------------------------------------------------------------------
# --locked injection (UT-0006 bullet 1)
# ---------------------------------------------------------------------------


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_locked_flag_injected_only_into_uv_run_commands(tmp_path, monkeypatch):
    """`uv run ...` gate/test commands gain `--locked`; others are left unchanged."""
    from saalco import evidence

    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=0)
    _prepend_path(monkeypatch, bin_dir)

    custom_gate_command = f'{sys.executable} -c "pass"'
    _set_project_fields(
        root,
        {
            # test.unit is left at the template default: "uv run pytest tests/unit"
            "test.integration": "uv run --locked pytest tests/integration",
            "test.e2e": "uv run --frozen pytest tests/e2e",
            "gate.07.custom": custom_gate_command,
        },
    )

    (root / "uv.lock").write_text("# fake lock\n")
    _commit_all(root, "configure gates and add lockfile")

    manifest_path, _overall = evidence.create(root)
    manifest = json.loads(Path(manifest_path).read_text())

    # Bare "uv run pytest tests/unit" gets --locked inserted right after "run".
    unit_command = _gate_command(manifest, "tests/unit")
    _assert_uv_run_flag(unit_command, "--locked")
    assert "pytest tests/unit" in unit_command

    # Already-locked / already-frozen commands are left untouched (no double-insertion).
    integration_command = _gate_command(manifest, "tests/integration")
    _assert_uv_run_flag(integration_command, "--locked")
    assert "pytest tests/integration" in integration_command

    e2e_command = _gate_command(manifest, "tests/e2e")
    _assert_uv_run_flag(e2e_command, "--frozen")
    assert "pytest tests/e2e" in e2e_command

    # A command that does not start with "uv run" is left untouched.
    assert _gate_command(manifest, custom_gate_command) == custom_gate_command

    # The default uv-run gates (ruff/mypy) get --locked too.
    format_command = _gate_command(manifest, "ruff format --check .")
    _assert_uv_run_flag(format_command, "--locked")
    assert "ruff format --check ." in format_command

    lint_command = _gate_command(manifest, "ruff check .")
    _assert_uv_run_flag(lint_command, "--locked")
    assert "ruff check ." in lint_command

    typecheck_command = _gate_command(manifest, "mypy src")
    _assert_uv_run_flag(typecheck_command, "--locked")
    assert "mypy src" in typecheck_command


# ---------------------------------------------------------------------------
# Precondition: uv.lock precheck (UT-0006 bullet 2)
# ---------------------------------------------------------------------------


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_stops_exit2_when_uv_lock_missing(tmp_path, monkeypatch, capsys):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=0)
    _prepend_path(monkeypatch, bin_dir)
    _commit_all(root, "no uv.lock")

    before_evidence = _snapshot(root / "evidence")
    before_artifacts = _snapshot(root / ".saal" / "artifacts")

    code = saalco.cli.main(["evidence"])
    captured = capsys.readouterr()

    assert code == 2
    assert "uv.lock" in captured.err
    assert "uv lock" in captured.err
    assert not (root / "uv.lock").exists()
    assert _snapshot(root / "evidence") == before_evidence
    assert _snapshot(root / ".saal" / "artifacts") == before_artifacts


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_stops_exit2_when_uv_lock_not_git_tracked(tmp_path, monkeypatch, capsys):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=0)
    _prepend_path(monkeypatch, bin_dir)

    gitignore = root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    gitignore.write_text(existing + "\nuv.lock\n")
    _commit_all(root, "ignore uv.lock")

    before_evidence = _snapshot(root / "evidence")
    before_artifacts = _snapshot(root / ".saal" / "artifacts")

    (root / "uv.lock").write_text("# untracked lock\n")

    code = saalco.cli.main(["evidence"])
    captured = capsys.readouterr()

    assert code == 2
    assert "uv.lock" in captured.err
    assert (root / "uv.lock").read_text() == "# untracked lock\n"
    assert _snapshot(root / "evidence") == before_evidence
    assert _snapshot(root / ".saal" / "artifacts") == before_artifacts


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_stops_exit2_when_lock_check_reports_outdated(tmp_path, monkeypatch, capsys):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=1)
    _prepend_path(monkeypatch, bin_dir)
    (root / "uv.lock").write_text("# lock\n")
    _commit_all(root, "add lock")

    before_evidence = _snapshot(root / "evidence")
    before_artifacts = _snapshot(root / ".saal" / "artifacts")

    code = saalco.cli.main(["evidence"])
    captured = capsys.readouterr()

    assert code == 2
    assert "uv.lock" in captured.err
    assert (root / "uv.lock").read_text() == "# lock\n"
    assert _snapshot(root / "evidence") == before_evidence
    assert _snapshot(root / ".saal" / "artifacts") == before_artifacts


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_stops_exit3_when_lock_check_fails_unexpectedly(tmp_path, monkeypatch):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=7)
    _prepend_path(monkeypatch, bin_dir)
    (root / "uv.lock").write_text("# lock\n")
    _commit_all(root, "add lock")

    code = saalco.cli.main(["evidence"])

    assert code == 3
    assert (root / "uv.lock").read_text() == "# lock\n"


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_stops_exit3_when_uv_not_found(tmp_path, monkeypatch):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    (root / "uv.lock").write_text("# lock\n")
    _commit_all(root, "add lock")

    git_path = shutil.which("git")
    assert git_path is not None, "git must be available to run this test"
    minimal_bin = tmp_path / "minimalbin"
    minimal_bin.mkdir()
    (minimal_bin / "git").symlink_to(git_path)
    monkeypatch.setenv("PATH", str(minimal_bin))

    code = saalco.cli.main(["evidence"])

    assert code == 3


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_no_precondition_error_when_lock_up_to_date(tmp_path, monkeypatch, capsys):
    root = _init_repo(tmp_path, monkeypatch, language="python")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=0)
    _prepend_path(monkeypatch, bin_dir)
    (root / "uv.lock").write_text("# lock\n")
    _commit_all(root, "add up-to-date lock")

    before_evidence = _snapshot(root / "evidence")

    code = saalco.cli.main(["evidence"])
    captured = capsys.readouterr()

    assert code not in (2, 3)
    assert "uv.lock: not found" not in captured.err
    assert _snapshot(root / "evidence") != before_evidence
    assert any(p.name == "manifest.json" for p in (root / "evidence").rglob("manifest.json"))


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_evidence_precondition_not_applied_for_language_other(tmp_path, monkeypatch, capsys):
    root = _init_repo(tmp_path, monkeypatch, language="other")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _write_fake_uv(bin_dir, lock_check_exit=0)
    _prepend_path(monkeypatch, bin_dir)
    _commit_all(root, "language other, no uv.lock")

    code = saalco.cli.main(["evidence"])
    captured = capsys.readouterr()

    assert "uv.lock" not in captured.err
    assert not (root / "uv.lock").exists()
    del code  # exit code is not constrained by the lockfile precondition for language: other


# ---------------------------------------------------------------------------
# init guidance (UT-0006 bullet 3)
# ---------------------------------------------------------------------------


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_init_warns_when_python_and_uv_lock_missing(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)

    code = saalco.cli.main(
        ["init", "--non-interactive", "--name", "proj", "--type", "system", "--language", "python"]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert not (root / "uv.lock").exists()
    assert "uv.lock" in captured.err
    assert "uv lock" in captured.err


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_init_silent_when_uv_lock_already_present(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "uv.lock").write_text("# preexisting\n")
    monkeypatch.chdir(root)

    code = saalco.cli.main(
        ["init", "--non-interactive", "--name", "proj", "--type", "system", "--language", "python"]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert "uv.lock" not in captured.err


@pytest.mark.verifies("DD-0006", spec="UT-0006")
def test_init_silent_for_language_other(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)

    code = saalco.cli.main(
        ["init", "--non-interactive", "--name", "proj", "--type", "system", "--language", "other"]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert "uv.lock" not in captured.err
