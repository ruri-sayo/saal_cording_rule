from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestMarker:
    nodeid: str
    category: str
    marker: str
    referenced_id: str | None
    spec: str | None = None


def _marker(call: ast.AST) -> tuple[str, str | None, str | None] | None:
    node = call.func if isinstance(call, ast.Call) else call
    if not isinstance(node, ast.Attribute) or node.attr not in {"verifies", "impl_aware"}:
        return None
    marker = node.attr
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


def scan_tests(root: Path) -> list[TestMarker]:
    result: list[TestMarker] = []
    tests = root / "tests"
    if not tests.exists():
        return result
    for path in sorted(tests.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        category = next((x for x in ("unit", "integration", "e2e") if x in path.parts), "unknown")
        module_marks: list[tuple[str, str | None, str | None]] = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
            ):
                values: list[ast.AST] = (
                    list(node.value.elts)
                    if isinstance(node.value, (ast.List, ast.Tuple))
                    else [node.value]
                )
                module_marks.extend(value for value in (_marker(v) for v in values) if value)
        for walked in ast.walk(tree):
            if isinstance(
                walked, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and walked.name.startswith("test"):
                marks = [value for value in (_marker(d) for d in walked.decorator_list) if value]
                marks = marks or module_marks or [("impl_aware", None, None)]
                rel = path.relative_to(root).as_posix()
                for marker, ident, spec in marks:
                    result.append(
                        TestMarker(f"{rel}::{walked.name}", category, marker, ident, spec)
                    )
    return result
