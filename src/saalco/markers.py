"""AST-based scanner for pytest marker metadata on test functions.

Responsibilities:
    - Locate `tests/**/test_*.py` files and statically parse `@pytest.mark.verifies(...)`
      / `@pytest.mark.impl_aware` markers (spec §8.4) without importing or executing test code.
    - Resolve markers applied at function, class, and module (`pytestmark`) level, combining
      them per the documented precedence.
    - Produce nodeids in the RTM/manifest contract format (`path::name` or
      `path::Class::name`, no parametrize suffix; contract 1/6 in the shared brief).

Non-responsibilities:
    - Does not run pytest or resolve parametrize cases; the evidence pipeline (evidence.py)
      aggregates per-nodeid results across parametrized cases.
    - Does not validate that referenced IDs exist; checks.py cross-references those.

This module only reads files under `<root>/tests`; it performs no writes and no subprocess
or network I/O.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

#: Marker decorator names recognized on functions/classes/pytestmark, per spec §8.4.
_MARK_NAMES = {"verifies", "impl_aware"}


@dataclass
class TestMarker:
    """One (test, marker) pair as scanned from test source.

    Attributes:
        nodeid: `tests/.../test_x.py::test_name` or `tests/.../test_x.py::Class::test_name`,
            matching the evidence manifest `tests[].nodeid` format (contract 1).
        category: one of "unit", "integration", "e2e", "unknown" (derived from the path).
        marker: "verifies" or "impl_aware".
        referenced_id: the ID string passed as the marker's first positional argument, or
            None when the marker carries no reference (e.g. bare `impl_aware`).
        spec: optional `spec="UT-0003"`-style test-specification item, or None.
    """

    nodeid: str
    category: str
    marker: str
    referenced_id: str | None
    spec: str | None = None


def _attr_name(node: ast.expr) -> str | None:
    """Return the trailing attribute name of a `mark.x` / `pytest.mark.x` expression, if any."""
    return node.attr if isinstance(node, ast.Attribute) else None


def _marker(call: ast.expr) -> tuple[str, str | None, str | None] | None:
    """Extract (marker, referenced_id, spec) from a decorator/pytestmark expression.

    Accepts both `pytest.mark.verifies(...)` and the `from pytest import mark` form
    `mark.verifies(...)`, called or bare (e.g. `@pytest.mark.impl_aware`).

    Returns:
        None if `call` is not a recognized marker expression.
    """
    node = call.func if isinstance(call, ast.Call) else call
    attr = _attr_name(node)
    if attr not in _MARK_NAMES or not isinstance(node, ast.Attribute):
        return None
    # Accept `pytest.mark.X` and bare `mark.X` (module aliasing is not resolved further;
    # any `<name>.mark.X` or `mark.X` attribute chain is treated as a marker).
    base = node.value
    base_name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
    if base_name != "mark":
        return None
    marker = attr
    args = call.args if isinstance(call, ast.Call) else []
    ident = (
        args[0].value
        if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str)
        else None
    )
    spec = None
    if isinstance(call, ast.Call):
        for kw in call.keywords:
            if (
                kw.arg == "spec"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                spec = kw.value.value
    return marker, ident, spec


def _marks_from_decorators(
    decorators: list[ast.expr],
) -> list[tuple[str, str | None, str | None]]:
    """Collect all recognized markers from a decorator list, in source order."""
    return [value for value in (_marker(d) for d in decorators) if value]


def _marks_from_assign(
    node: ast.stmt, target_name: str
) -> list[tuple[str, str | None, str | None]]:
    """Collect markers from a module-level `<target_name> = mark.x(...)` / list/tuple assignment."""
    if not (
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == target_name for t in node.targets)
    ):
        return []
    values: list[ast.expr] = (
        list(node.value.elts) if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
    )
    return [value for value in (_marker(v) for v in values) if value]


def _is_test_function(
    node: ast.stmt,
) -> TypeGuard[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Check if an AST node is a test function (function/async function starting with 'test')."""
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
        "test"
    )


def scan_tests(root: Path) -> list[TestMarker]:
    """Scan `<root>/tests/**/test_*.py` for pytest marker metadata.

    Walks each module's top level only: module-level test functions, and methods of
    module-level test classes (nested helper functions/classes are not test entry points
    and are ignored, per spec §8.4's requirement to resolve function/class/module markers
    only for actual test items).

    Marker precedence when a test has decorators of its own: function-level markers win;
    otherwise class-level (for methods); otherwise module `pytestmark`; otherwise the test
    is treated as `impl_aware` with no reference (unmarked tests, per spec §8.4).

    Args:
        root: project root; files are read from `root / "tests"`. Anything under
            `tests/fixtures/` is sample data, not a test of this project, and is skipped so
            that fixture markers can never count toward verification.

    Returns:
        One `TestMarker` per (test, applicable marker) pair. A test decorated with several
        markers (e.g. both `verifies` calls) yields one entry per marker. Files that are
        missing, unreadable, or have a syntax error are skipped silently (best-effort scan
        used by non-blocking tooling; checks.py separately validates document-level
        consistency).

    Side Effects:
        Reads files under `root/tests`; performs no writes.
    """
    result: list[TestMarker] = []
    tests = root / "tests"
    if not tests.exists():
        return result
    for path in sorted(tests.rglob("test_*.py")):
        if "fixtures" in path.relative_to(tests).parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        category = next((x for x in ("unit", "integration", "e2e") if x in path.parts), "unknown")
        rel = path.relative_to(root).as_posix()
        module_marks: list[tuple[str, str | None, str | None]] = []
        for node in tree.body:
            module_marks.extend(_marks_from_assign(node, "pytestmark"))

        for node in tree.body:
            if _is_test_function(node):
                marks = (
                    _marks_from_decorators(node.decorator_list)
                    or module_marks
                    or [("impl_aware", None, None)]
                )
                for marker, ident, spec in marks:
                    result.append(TestMarker(f"{rel}::{node.name}", category, marker, ident, spec))
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                class_marks = _marks_from_decorators(node.decorator_list)
                for method in node.body:
                    if not _is_test_function(method):
                        continue
                    marks = (
                        _marks_from_decorators(method.decorator_list)
                        or class_marks
                        or module_marks
                        or [("impl_aware", None, None)]
                    )
                    for marker, ident, spec in marks:
                        result.append(
                            TestMarker(
                                f"{rel}::{node.name}::{method.name}", category, marker, ident, spec
                            )
                        )
    return result
