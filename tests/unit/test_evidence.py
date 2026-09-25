"""Unit tests for saalco.evidence: diff coverage line mapping, JUnit nodeid mapping,
parametrize aggregation, current_manifest selection, and the F-003 uv.lock precondition /
`--locked` injection (REQ-0006, DD-0006).

pytestmark impl_aware: exercises internal helpers (`_changed_lines`, `_junit_nodeid`,
`_parse_junit`, `_check_lockfile`, `_inject_locked`) and the current_manifest
bookkeeping-only-diff contract directly.
"""

import subprocess
from pathlib import Path

import pytest

from saalco.errors import EnvironmentError as SaalcoEnvironmentError
from saalco.errors import SaalcoError
from saalco.evidence import (
    _changed_lines,
    _check_lockfile,
    _inject_locked,
    _junit_nodeid,
    _parse_junit,
    current_manifest,
)

pytestmark = pytest.mark.impl_aware


def test_changed_lines_pure_deletion_ignored():
    diff = "+++ b/src/a.py\n@@ -5,3 +5,0 @@\n-old line\n-old line\n-old line\n"
    assert _changed_lines(diff) == {}


def test_changed_lines_addition_recorded():
    diff = "+++ b/src/a.py\n@@ -1,0 +2,3 @@\n+new1\n+new2\n+new3\n"
    assert _changed_lines(diff) == {"src/a.py": {2, 3, 4}}


def test_changed_lines_single_line_hunk_defaults_count_one():
    diff = "+++ b/src/a.py\n@@ -1 +1 @@\n-old\n+new\n"
    assert _changed_lines(diff) == {"src/a.py": {1}}


def test_changed_lines_multiple_files():
    diff = "+++ b/src/a.py\n@@ -1,0 +1,1 @@\n+x\n+++ b/src/b.py\n@@ -1,0 +5,2 @@\n+y\n+z\n"
    result = _changed_lines(diff)
    assert result == {"src/a.py": {1}, "src/b.py": {5, 6}}


def test_junit_nodeid_function_with_file():
    nodeid = _junit_nodeid(Path("/root"), "tests.unit.test_a", "test_x", "tests/unit/test_a.py")
    assert nodeid == "tests/unit/test_a.py::test_x"


def test_junit_nodeid_class_qualified_with_file():
    nodeid = _junit_nodeid(
        Path("/root"), "tests.unit.test_a.TestFoo", "test_x", "tests/unit/test_a.py"
    )
    assert nodeid == "tests/unit/test_a.py::TestFoo::test_x"


def test_junit_nodeid_strips_parametrize_suffix():
    nodeid = _junit_nodeid(
        Path("/root"), "tests.unit.test_a", "test_x[case1]", "tests/unit/test_a.py"
    )
    assert nodeid == "tests/unit/test_a.py::test_x"


def test_junit_nodeid_without_file_resolves_via_filesystem(tmp_path: Path):
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_a.py").write_text("")
    nodeid = _junit_nodeid(tmp_path, "tests.unit.test_a.TestFoo", "test_x", None)
    assert nodeid == "tests/unit/test_a.py::TestFoo::test_x"


def test_junit_nodeid_no_plausible_file_returns_none(tmp_path: Path):
    assert _junit_nodeid(tmp_path, "nope.nothing", "test_x", None) is None


def _junit_xml(cases: list[str]) -> str:
    return '<testsuite name="root">' + "".join(cases) + "</testsuite>"


def test_parse_junit_aggregates_parametrize_all_pass(tmp_path: Path):
    path = tmp_path / "junit.xml"
    path.write_text(
        _junit_xml(
            [
                '<testcase classname="tests.unit.test_a" name="test_x[1]" file="tests/unit/test_a.py"/>',
                '<testcase classname="tests.unit.test_a" name="test_x[2]" file="tests/unit/test_a.py"/>',
            ]
        )
    )
    results = _parse_junit(tmp_path, path)
    assert results == {"tests/unit/test_a.py::test_x": "PASS"}


def test_parse_junit_aggregates_parametrize_any_failure_fails_all(tmp_path: Path):
    path = tmp_path / "junit.xml"
    path.write_text(
        _junit_xml(
            [
                '<testcase classname="tests.unit.test_a" name="test_x[1]" file="tests/unit/test_a.py"/>',
                (
                    '<testcase classname="tests.unit.test_a" name="test_x[2]" '
                    'file="tests/unit/test_a.py"><failure>boom</failure></testcase>'
                ),
            ]
        )
    )
    results = _parse_junit(tmp_path, path)
    assert results == {"tests/unit/test_a.py::test_x": "FAIL"}


def test_parse_junit_skipped_only_absent_from_results(tmp_path: Path):
    path = tmp_path / "junit.xml"
    path.write_text(
        _junit_xml(
            [
                (
                    '<testcase classname="tests.unit.test_a" name="test_x" '
                    'file="tests/unit/test_a.py"><skipped/></testcase>'
                ),
            ]
        )
    )
    assert _parse_junit(tmp_path, path) == {}


def test_parse_junit_malformed_file_returns_empty(tmp_path: Path):
    path = tmp_path / "junit.xml"
    path.write_text("not xml")
    assert _parse_junit(tmp_path, path) == {}


def test_current_manifest_none_without_evidence(saal_project):
    root = saal_project("valid_project")
    assert current_manifest(root) is None


def test_current_manifest_found_for_bookkeeping_only_diff(saal_project, write_manifest_fn):
    root = saal_project("valid_project")
    written = write_manifest_fn(root, overall="PASS")
    found = current_manifest(root)
    assert found is not None
    assert found["run_id"] == written["run_id"]
    assert found["target_commit"] == written["target_commit"]


def test_current_manifest_ties_broken_by_latest_run_id(
    saal_project, write_manifest_fn, head_commit
):
    root = saal_project("valid_project")
    head = head_commit(root)
    write_manifest_fn(root, target=head, run_id="20240101T000000")
    write_manifest_fn(root, target=head, run_id="20240101T999999")
    found = current_manifest(root)
    assert found["run_id"] == "20240101T999999"


def test_create_runs_pytest_with_ctrace_coverage_core(saal_project, monkeypatch):
    """Regression: sys.monitoring drops all but the first test context per line (§13-14)."""
    from conftest import commit_all, write_uv_lock

    from saalco import evidence

    root = saal_project("valid_project")
    project = root / "docs/project.md"
    project.write_text(
        project.read_text().replace("test.unit:\n", "test.unit: python -m pytest tests/unit\n")
    )
    # `language: python` -> saalco.evidence.create now requires a committed, current uv.lock
    # (F-003, REQ-0006) before it will run at all.
    write_uv_lock(root)
    commit_all(root, "configure unit tests")
    seen: list[dict[str, str] | None] = []

    def fake_run(root_, command, log, environment=None):
        seen.append(environment)
        log.write_text("", encoding="utf-8")
        return 0, "PASS", "t0", "t1"

    monkeypatch.setattr(evidence, "_run", fake_run)
    evidence.create(root)
    test_envs = [env for env in seen if env and "COVERAGE_FILE" in env]
    assert test_envs, "no pytest suite was run"
    assert all(env.get("COVERAGE_CORE") == "ctrace" for env in test_envs)


# ---------------------------------------------------------------------------
# _inject_locked (DD-0006 "--locked の付与")
# ---------------------------------------------------------------------------


def test_inject_locked_adds_flag_after_run():
    assert _inject_locked("uv run pytest tests/unit") == "uv run --locked pytest tests/unit"


def test_inject_locked_leaves_already_locked_command_unchanged():
    assert (
        _inject_locked("uv run --locked pytest tests/unit") == "uv run --locked pytest tests/unit"
    )


def test_inject_locked_leaves_frozen_command_unchanged():
    assert (
        _inject_locked("uv run --frozen pytest tests/unit") == "uv run --frozen pytest tests/unit"
    )


def test_inject_locked_leaves_non_uv_run_command_unchanged():
    assert _inject_locked("python -m pytest tests/unit") == "python -m pytest tests/unit"
    assert _inject_locked("ruff check .") == "ruff check ."


def test_inject_locked_unparsable_command_returned_unchanged():
    unparsable = "uv run 'unterminated"
    assert _inject_locked(unparsable) == unparsable


# ---------------------------------------------------------------------------
# _check_lockfile (REQ-0006, DD-0006 precondition)
# ---------------------------------------------------------------------------


def test_check_lockfile_missing_raises_exit_2(saal_project):
    root = saal_project("valid_project")
    with pytest.raises(SaalcoError) as excinfo:
        _check_lockfile(root)
    assert excinfo.value.exit_code == 2
    assert "not found" in str(excinfo.value)


def test_check_lockfile_untracked_raises_exit_2(saal_project, write_uv_lock_fn):
    root = saal_project("valid_project")
    write_uv_lock_fn(root)  # writes uv.lock on disk but does not stage/commit it
    with pytest.raises(SaalcoError) as excinfo:
        _check_lockfile(root)
    assert excinfo.value.exit_code == 2
    assert "not tracked" in str(excinfo.value)


def test_check_lockfile_outdated_raises_exit_2(saal_project, write_uv_lock_fn, commit_all_fn):
    root = saal_project("valid_project")
    write_uv_lock_fn(root)
    commit_all_fn(root, "lock")
    pyproject = root / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("0.1.0", "0.2.0"))
    commit_all_fn(root, "bump version without relocking")
    with pytest.raises(SaalcoError) as excinfo:
        _check_lockfile(root)
    assert excinfo.value.exit_code == 2
    assert "out of date" in str(excinfo.value)


def test_check_lockfile_current_does_not_raise(saal_project, write_uv_lock_fn, commit_all_fn):
    root = saal_project("valid_project")
    write_uv_lock_fn(root)
    commit_all_fn(root, "lock")
    _check_lockfile(root)  # must not raise


def test_check_lockfile_uv_missing_raises_exit_3(
    saal_project, write_uv_lock_fn, commit_all_fn, monkeypatch
):
    root = saal_project("valid_project")
    write_uv_lock_fn(root)
    commit_all_fn(root, "lock")

    from saalco import evidence

    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if list(args)[:1] == ["uv"]:
            raise OSError("uv: command not found")
        return real_run(args, *a, **kw)

    monkeypatch.setattr(evidence.subprocess, "run", fake_run)
    with pytest.raises(SaalcoEnvironmentError) as excinfo:
        _check_lockfile(root)
    assert excinfo.value.exit_code == 3


def test_check_lockfile_check_unexpected_exit_code_raises_exit_3(
    saal_project, write_uv_lock_fn, commit_all_fn, monkeypatch
):
    root = saal_project("valid_project")
    write_uv_lock_fn(root)
    commit_all_fn(root, "lock")

    from saalco import evidence

    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if list(args)[:2] == ["uv", "lock"]:
            return subprocess.CompletedProcess(args, 7, "weird failure\n", "")
        return real_run(args, *a, **kw)

    monkeypatch.setattr(evidence.subprocess, "run", fake_run)
    with pytest.raises(SaalcoEnvironmentError) as excinfo:
        _check_lockfile(root)
    assert excinfo.value.exit_code == 3
    assert "weird failure" in str(excinfo.value)


def test_check_lockfile_skipped_for_language_other(saal_project, commit_all_fn, monkeypatch):
    """REQ-0006 §8: `language: other` projects never go through the precondition at all."""
    from saalco import evidence

    root = saal_project("valid_project")
    project = root / "docs/project.md"
    project.write_text(project.read_text().replace("language: python", "language: other"))
    commit_all_fn(root, "switch to language: other")

    calls: list[Path] = []
    monkeypatch.setattr(evidence, "_check_lockfile", lambda root_: calls.append(root_))
    evidence.create(root)  # no uv.lock anywhere; must not raise
    assert calls == []


# ---------------------------------------------------------------------------
# coverage export uses `--locked` (DD-0006)
# ---------------------------------------------------------------------------


def test_create_coverage_export_uses_locked_for_python(
    saal_project, write_uv_lock_fn, commit_all_fn, monkeypatch
):
    from saalco import evidence

    root = saal_project("valid_project")
    write_uv_lock_fn(root)
    commit_all_fn(root, "lock")

    monkeypatch.setattr(
        evidence,
        "_run",
        lambda root_, command, log, environment=None: (0, "PASS", "t0", "t1"),
    )
    seen_commands: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if isinstance(args, list) and args[:2] == ["uv", "run"]:
            seen_commands.append(args)
            return subprocess.CompletedProcess(args, 1, "", "no coverage tool")
        return real_run(args, *a, **kw)

    monkeypatch.setattr(evidence.subprocess, "run", fake_run)
    evidence.create(root)
    assert seen_commands, "coverage export was not invoked"
    assert seen_commands[0][:3] == ["uv", "run", "--locked"]
