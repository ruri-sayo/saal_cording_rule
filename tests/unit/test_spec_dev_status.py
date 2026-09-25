# Specification-derived tests (SAAL Rule 5.2): written only from approved
# documents and public interfaces, without reading the implementation.
"""Unit tests for DD-0005 (DEV status validation and closed-record checks).

Built only from docs/features/F-002 REQ-0005 / DD-0005 / UT-0005, spec §8.6 r4,
and saalco's public interface (signatures + docstrings; no bodies).

Strategy: rather than assert on exact error-message text (unspecified by the
public interface), each test compares `checks.run(...).errors` /
`.warnings` between two runs on the *same* project and the *same* DEV item id,
differing only in the one field under test (e.g. `status: open` vs.
`status: closed`, or `closed_at` present vs. absent). Any finding that
appears in one run and not the other is attributable exactly to that field,
regardless of the implementation's wording.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from saalco import checks, commands, documents, evidence


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_local_git_identity(root: Path) -> None:
    _run_git(root, "init")
    _run_git(root, "config", "user.email", "spec-dev-status-test@example.invalid")
    _run_git(root, "config", "user.name", "Spec Dev Status Test")


def _commit_all(root: Path, message: str) -> None:
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", message)


def _disable_network_gates(root: Path) -> None:
    """Point every gate/test command at something that needs no network access.

    `saalco init`'s default `docs/project.md` uses `uv run ruff ...` /
    `uv run mypy ...` gates, which would try to resolve/install packages for
    a brand-new throwaway project. We only need `saalco evidence` to produce
    a current Evidence manifest with a real (failing) `test.unit` run, so
    every other gate is cleared to empty (`NOT_CONFIGURED`, per spec §7.2)
    and `test.unit` is pointed at the interpreter running this test suite,
    bypassing `uv` entirely.
    """
    doc = documents.parse_document(root / "docs" / "project.md")
    documents.set_header(
        doc,
        {
            "gate.01.format": "",
            "gate.02.lint": "",
            "gate.03.typecheck": "",
            "gate.04.secret_scan": "",
            "gate.05.dependency_audit": "",
            "gate.06.static_analysis": "",
            "test.unit": f"{sys.executable} -m pytest tests/unit",
            "test.integration": "",
            "test.e2e": "",
        },
    )
    documents.atomic_write(doc)


def _build_light_project(tmp_path: Path) -> tuple[Path, str]:
    """A project needing only static checks (`saalco check`, no Evidence)."""
    root = tmp_path / "proj"
    root.mkdir()
    _init_local_git_identity(root)
    commands.init_project(
        root=root,
        name="dev-status-static-test",
        project_type="research",
        language="python",
        specs=[],
    )
    feature_id = commands.new_feature(root, "DEV status static test feature", "S", "devstatic")
    return root, feature_id


def _build_project_with_failing_verifies_test(tmp_path: Path) -> tuple[Path, str, str]:
    """A committed project whose only `verifies` test fails, for `saalco evidence`.

    This gives `saalco check --verification` a genuine rule-6.4 violation
    (`verifies` test not PASS, per spec §13 item 12 / DD-0001) to downgrade
    or not, exercising DD-0005's DEV-downgrade rule.
    """
    root = tmp_path / "proj"
    root.mkdir()
    _init_local_git_identity(root)
    commands.init_project(
        root=root,
        name="dev-status-evidence-test",
        project_type="research",
        language="python",
        specs=[],
    )
    _disable_network_gates(root)
    feature_id = commands.new_feature(root, "DEV status evidence test feature", "S", "devevidence")
    dd_id, _ = commands.new_item(root, "dd", feature_id, "Something that must be verified")

    unit_dir = root / "tests" / "unit"
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "test_intentional_failure.py").write_text(
        f'''"""Deliberately-failing Specification-derived test.

Gives `saalco evidence` a non-PASS `verifies` result for {dd_id}, so that
rule 6.4 ("verifies test not PASS") is violated under
`saalco check --verification`.
"""

import pytest


@pytest.mark.verifies("{dd_id}")
def test_intentionally_fails():
    assert False, "intentional failure, used only to produce a non-PASS result"
''',
        encoding="utf-8",
    )
    # Materialize `uv.lock` (used internally by `saalco evidence`'s
    # `uv run coverage json` step, per spec §14) *before* the initial
    # commit. Otherwise it is created as a side effect of the first
    # `evidence.create` call, landing outside the bookkeeping paths
    # (`evidence/`, `docs/trace/`, `docs/ids.ledger`) spec I-1 allows
    # between an Evidence's target commit and HEAD, which would make the
    # Evidence never "current".
    subprocess.run(["uv", "lock"], cwd=root, check=True, capture_output=True, text=True)
    _commit_all(root, "initial commit for DEV status evidence test project")
    return root, feature_id, dd_id


def _find_doc_with_item(root: Path, feature_id: str, item_id: str) -> Path:
    feature_dirs = list((root / "docs" / "features").glob(f"{feature_id}_*"))
    assert feature_dirs, f"no feature directory found for {feature_id}"
    for path in sorted(feature_dirs[0].glob("*.md")):
        if f"### {item_id}:" in path.read_text(encoding="utf-8"):
            return path
    raise AssertionError(f"no document under {feature_dirs[0]} contains item {item_id}")


def _new_dev_item(root: Path, feature_id: str, title: str) -> tuple[str, Path]:
    dev_id, _warning = commands.new_item(root, "dev", feature_id, title)
    path = _find_doc_with_item(root, feature_id, dev_id)
    return dev_id, path


def _rewrite_item_fields(path: Path, item_id: str, title: str, fields_text: str) -> None:
    """Replace everything from `### {item_id}:` to EOF with a controlled block.

    This makes the item's metadata fully deterministic regardless of
    whatever template `saalco new dev` filled in, following the exact
    `### ID: title` / `key: value` shape spec §8.2/§8.6 documents.
    """
    text = path.read_text(encoding="utf-8")
    heading = f"### {item_id}:"
    start = text.index(heading)
    new_block = f"### {item_id}: {title}\n\n{fields_text}"
    path.write_text(text[:start] + new_block, encoding="utf-8")


# DEV field values per spec §8.6's worked example, reused as a "valid closed
# DEV" baseline that every negative scenario is diffed against.
_BASE_DEV_FIELDS = {
    "rule": "6.4",
    "scope": "PLACEHOLDER",
    "status": "closed",
    "reason": "existing tests are impl_aware only",
    "resolution": "add a Specification-derived Test",
    "end_condition": "RTM の全項目が verified になった時点で終了",
    "decided_by": "tester",
    "decided_at": "2026-09-20",
    "closed_at": "2026-09-25",
    "closed_condition": "RTM の全項目が verified になった",
}


def _dev_fields_text(overrides: dict[str, str] | None = None, omit: tuple[str, ...] = ()) -> str:
    fields = dict(_BASE_DEV_FIELDS)
    if overrides:
        fields.update(overrides)
    for key in omit:
        fields.pop(key, None)
    return "".join(f"{key}: {value}\n" for key, value in fields.items())


@pytest.mark.verifies("DD-0005", spec="UT-0005")
def test_closed_dev_does_not_downgrade_but_open_dev_does(tmp_path: Path) -> None:
    root, feature_id, dd_id = _build_project_with_failing_verifies_test(tmp_path)
    evidence.create(root)
    # `current_manifest` only recognizes a *tracked* Evidence (spec I-1), so
    # the manifest `evidence.create` just wrote must be committed before it
    # counts as "current".
    _commit_all(root, "record evidence")

    dev_id, doc_path = _new_dev_item(root, feature_id, "DEV covering rule 6.4")

    closed_fields = _dev_fields_text({"rule": "6.4", "scope": dd_id, "status": "closed"})
    _rewrite_item_fields(doc_path, dev_id, "DEV covering rule 6.4", closed_fields)
    closed_report = checks.run(root, verification=True)

    open_fields = _dev_fields_text({"rule": "6.4", "scope": dd_id, "status": "open"})
    _rewrite_item_fields(doc_path, dev_id, "DEV covering rule 6.4", open_fields)
    open_report = checks.run(root, verification=True)

    only_when_closed = set(closed_report.errors) - set(open_report.errors)
    assert only_when_closed, (
        "expected `saalco check --verification` to keep reporting the rule-6.4 "
        f"violation for {dd_id} as an ERROR while a matching DEV is `closed` "
        "(DD-0005: 'closed の DEV は...ERRORをWARNINGに緩めないこと'); "
        f"closed errors={closed_report.errors!r} open errors={open_report.errors!r}"
    )
    # The WARNING text need not be byte-identical to the ERROR text (e.g. it
    # may add an "open DEV" attribution note); it only has to still convey
    # the same underlying violation, so a substring match is enough here.
    still_reported_as_warning = all(
        any(closed_message in warning for warning in open_report.warnings)
        for closed_message in only_when_closed
    )
    assert still_reported_as_warning, (
        "expected the same violation to reappear as a WARNING once the matching "
        "DEV is `open` (spec §8.6 downgrade rule, rule 6.4); "
        f"closed-only errors={only_when_closed!r} open warnings={open_report.warnings!r}"
    )


@pytest.mark.verifies("DD-0005", spec="UT-0005")
@pytest.mark.parametrize(
    "label, overrides, omit",
    [
        ("status line missing", {}, ("status",)),
        ("status value not open/closed", {"status": "resolved"}, ()),
        ("closed_at missing", {}, ("closed_at",)),
        ("closed_condition missing", {}, ("closed_condition",)),
        ("both closed_at and closed_condition missing", {}, ("closed_at", "closed_condition")),
        ("closed_at empty", {"closed_at": ""}, ()),
        ("closed_condition empty", {"closed_condition": ""}, ()),
    ],
)
def test_dev_field_violation_is_a_new_error_vs_valid_closed_baseline(
    tmp_path: Path, label: str, overrides: dict[str, str], omit: tuple[str, ...]
) -> None:
    root, feature_id = _build_light_project(tmp_path)
    dev_id, doc_path = _new_dev_item(root, feature_id, "DEV field violation test")

    valid_fields = _dev_fields_text({"scope": feature_id})
    _rewrite_item_fields(doc_path, dev_id, "DEV field violation test", valid_fields)
    valid_report = checks.run(root, verification=False)

    variant_overrides = dict(overrides)
    variant_overrides.setdefault("scope", feature_id)
    variant_fields = _dev_fields_text(variant_overrides, omit)
    _rewrite_item_fields(doc_path, dev_id, "DEV field violation test", variant_fields)
    variant_report = checks.run(root, verification=False)

    new_errors = set(variant_report.errors) - set(valid_report.errors)
    assert new_errors, (
        f"[{label}] expected `saalco check` to report a new ERROR for DEV {dev_id} "
        f"that a valid `closed` DEV (with status/closed_at/closed_condition all "
        f"present and non-empty) does not have, per DD-0005 / REQ-0005; "
        f"valid errors={valid_report.errors!r} variant errors={variant_report.errors!r}"
    )


@pytest.mark.verifies("DD-0005", spec="UT-0005")
def test_open_dev_without_closed_fields_is_not_an_error(tmp_path: Path) -> None:
    root, feature_id = _build_light_project(tmp_path)
    dev_id, doc_path = _new_dev_item(root, feature_id, "Open DEV without closed fields")

    closed_valid_fields = _dev_fields_text({"scope": feature_id, "status": "closed"})
    _rewrite_item_fields(doc_path, dev_id, "Open DEV without closed fields", closed_valid_fields)
    closed_report = checks.run(root, verification=False)

    open_fields = _dev_fields_text(
        {"scope": feature_id, "status": "open"}, omit=("closed_at", "closed_condition")
    )
    _rewrite_item_fields(doc_path, dev_id, "Open DEV without closed fields", open_fields)
    open_report = checks.run(root, verification=False)

    new_errors_mentioning_dev = [
        message
        for message in set(open_report.errors) - set(closed_report.errors)
        if dev_id in message
    ]
    assert not new_errors_mentioning_dev, (
        f"open DEV {dev_id} without closed_at/closed_condition must not be an ERROR "
        "(DD-0005: '`open` の DEV については、従来どおり例外として扱う' — the "
        "closed_at/closed_condition requirement applies only to `closed` DEVs); "
        f"unexpected new errors={new_errors_mentioning_dev!r}"
    )
