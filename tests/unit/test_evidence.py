"""Unit tests for saalco.evidence: diff coverage line mapping, JUnit nodeid mapping,
parametrize aggregation, and current_manifest selection.

pytestmark impl_aware: exercises internal helpers (`_changed_lines`, `_junit_nodeid`,
`_parse_junit`) and the current_manifest bookkeeping-only-diff contract directly.
"""

from pathlib import Path

import pytest

from saalco.evidence import _changed_lines, _junit_nodeid, _parse_junit, current_manifest

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
