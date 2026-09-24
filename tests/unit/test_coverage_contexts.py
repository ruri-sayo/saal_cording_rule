"""Unit tests for saalco.coverage_contexts: test-context suffix stripping and lookup.

pytestmark impl_aware: exercises the exact coverage.py context suffix format.
"""

import json
from pathlib import Path

import pytest

from saalco.coverage_contexts import load

pytestmark = pytest.mark.impl_aware


def _manifest(json_path: str | None) -> dict:
    return {"coverage": {"json_path": json_path}}


def test_strips_run_setup_teardown_and_param_suffixes(tmp_path: Path):
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/a.py": {
                        "contexts": {
                            "1": ["tests/unit/test_a.py::test_x|run"],
                            "2": ["tests/unit/test_a.py::test_y[case1]|setup"],
                            "3": ["tests/unit/test_a.py::test_z[case2]|teardown"],
                        }
                    }
                }
            }
        )
    )
    result = load(tmp_path, _manifest("coverage.json"))
    assert result == {
        "src/a.py": {
            "tests/unit/test_a.py::test_x",
            "tests/unit/test_a.py::test_y",
            "tests/unit/test_a.py::test_z",
        }
    }


def test_empty_context_string_ignored(tmp_path: Path):
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(json.dumps({"files": {"src/a.py": {"contexts": {"1": [""]}}}}))
    result = load(tmp_path, _manifest("coverage.json"))
    assert result == {}


def test_missing_json_path_returns_none(tmp_path: Path):
    assert load(tmp_path, _manifest(None)) is None


def test_missing_file_on_disk_returns_none(tmp_path: Path):
    assert load(tmp_path, _manifest("does-not-exist.json")) is None


def test_malformed_json_returns_none(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("not json")
    assert load(tmp_path, _manifest("bad.json")) is None


def test_absolute_path_resolved_relative_to_root(tmp_path: Path):
    coverage_path = tmp_path / "coverage.json"
    absolute = (tmp_path / "src" / "a.py").resolve()
    coverage_path.write_text(
        json.dumps(
            {"files": {str(absolute): {"contexts": {"1": ["tests/unit/test_a.py::test_x|run"]}}}}
        )
    )
    result = load(tmp_path, _manifest("coverage.json"))
    assert result == {"src/a.py": {"tests/unit/test_a.py::test_x"}}
