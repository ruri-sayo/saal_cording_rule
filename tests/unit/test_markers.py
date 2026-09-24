"""Unit tests for saalco.markers.scan_tests: AST-based marker resolution.

pytestmark impl_aware: exercises the marker precedence rules and nodeid format directly
against the AST scanner implementation.
"""

from pathlib import Path

import pytest

from saalco.markers import scan_tests

pytestmark = pytest.mark.impl_aware


def _scan(tmp_path: Path, rel: str, text: str):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return scan_tests(tmp_path)


def test_function_level_verifies_marker(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/unit/test_a.py",
        "import pytest\n\n@pytest.mark.verifies('DD-0001')\ndef test_one():\n    pass\n",
    )
    assert len(marks) == 1
    m = marks[0]
    assert m.nodeid == "tests/unit/test_a.py::test_one"
    assert m.category == "unit"
    assert m.marker == "verifies"
    assert m.referenced_id == "DD-0001"
    assert m.spec is None


def test_class_decorated_test_yields_class_qualified_nodeid(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/integration/test_b.py",
        "import pytest\n\n"
        "class TestThing:\n"
        "    @pytest.mark.verifies('AD-0001')\n"
        "    def test_method(self):\n"
        "        pass\n",
    )
    assert marks[0].nodeid == "tests/integration/test_b.py::TestThing::test_method"
    assert marks[0].category == "integration"


def test_module_level_pytestmark_applies_to_all_tests(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/unit/test_c.py",
        "import pytest\n\npytestmark = pytest.mark.impl_aware\n\n"
        "def test_x():\n    pass\n\ndef test_y():\n    pass\n",
    )
    assert {m.nodeid for m in marks} == {
        "tests/unit/test_c.py::test_x",
        "tests/unit/test_c.py::test_y",
    }
    assert all(m.marker == "impl_aware" and m.referenced_id is None for m in marks)


def test_mark_alias_form_is_recognized(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/unit/test_d.py",
        "from pytest import mark\n\n@mark.verifies('DD-0002')\ndef test_alias():\n    pass\n",
    )
    assert marks[0].marker == "verifies"
    assert marks[0].referenced_id == "DD-0002"


def test_unmarked_test_defaults_to_impl_aware(tmp_path: Path):
    marks = _scan(tmp_path, "tests/unit/test_e.py", "def test_bare():\n    pass\n")
    assert len(marks) == 1
    assert marks[0].marker == "impl_aware"
    assert marks[0].referenced_id is None


def test_spec_keyword_is_captured(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/unit/test_f.py",
        "import pytest\n\n@pytest.mark.verifies('DD-0003', spec='UT-0007')\n"
        "def test_with_spec():\n    pass\n",
    )
    assert marks[0].referenced_id == "DD-0003"
    assert marks[0].spec == "UT-0007"


def test_function_marker_overrides_module_pytestmark(tmp_path: Path):
    marks = _scan(
        tmp_path,
        "tests/unit/test_g.py",
        "import pytest\n\npytestmark = pytest.mark.impl_aware\n\n"
        "@pytest.mark.verifies('DD-0004')\ndef test_override():\n    pass\n",
    )
    assert marks[0].marker == "verifies"
    assert marks[0].referenced_id == "DD-0004"


def test_e2e_category_from_path(tmp_path: Path):
    marks = _scan(tmp_path, "tests/e2e/test_h.py", "def test_flow():\n    pass\n")
    assert marks[0].category == "e2e"


def test_missing_tests_dir_returns_empty(tmp_path: Path):
    assert scan_tests(tmp_path) == []


def test_fixtures_directory_is_skipped(tmp_path: Path):
    """tests/fixtures/** holds simulated user projects; their markers must never count."""
    _scan(
        tmp_path,
        "tests/fixtures/valid_project/tests/e2e/test_req.py",
        "import pytest\n\n@pytest.mark.verifies('REQ-0001')\ndef test_thing_works():\n    pass\n",
    )
    real = _scan(
        tmp_path,
        "tests/unit/test_real.py",
        "import pytest\n\n@pytest.mark.verifies('DD-0001')\ndef test_real():\n    pass\n",
    )
    assert [m.nodeid for m in real] == ["tests/unit/test_real.py::test_real"]
