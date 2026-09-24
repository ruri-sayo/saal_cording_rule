"""Unit tests for saalco.checks: Tier rules, DEV downgrade scope matching, cycles.

pytestmark impl_aware: asserts on the exact ERROR/WARNING strings produced by checks.py.
"""

from pathlib import Path

import pytest

from saalco.checks import _dev_downgrade, run
from saalco.documents import Item

pytestmark = pytest.mark.impl_aware


def _dev(rule: str, scope: str, status: str = "open") -> Item:
    return Item(
        id="DEV-0001",
        kind="DEV",
        title="fixture",
        path=Path("docs/features/F-001_x/90-deviations.md"),
        meta={"rule": rule, "scope": scope, "status": status},
    )


def test_dev_downgrade_matches_exact_token_not_substring():
    """F-001 must not match F-0012 (exact-token scope matching, not substring)."""
    dev = _dev("7.3", "F-0012")
    assert _dev_downgrade([dev], "7.3", feature="F-001") is False
    assert _dev_downgrade([dev], "7.3", feature="F-0012") is True


def test_dev_downgrade_requires_open_status():
    dev = _dev("7.3", "F-001", status="resolved")
    assert _dev_downgrade([dev], "7.3", feature="F-001") is False


def test_dev_downgrade_requires_matching_rule():
    dev = _dev("6.4", "F-001")
    assert _dev_downgrade([dev], "7.3", feature="F-001") is False


def test_dev_downgrade_item_id_token():
    dev = _dev("6.8", "REQ-0001, DD-0002")
    assert _dev_downgrade([dev], "6.8", item_id="DD-0002") is True
    assert _dev_downgrade([dev], "6.8", item_id="DD-0003") is False


def test_dev_downgrade_file_prefix_token():
    """A scope token is a path *prefix* of the violating file (`file.startswith(token)`)."""
    dev = _dev("4.6", "src/pkg/")
    assert _dev_downgrade([dev], "4.6", file="src/pkg/module.py") is True
    assert _dev_downgrade([dev], "4.6", file="src/other.py") is False


def test_dev_downgrade_multi_rule_matches_any_listed_token():
    """`rule:` may list several rule numbers, comma-separated (§8.6 extension)."""
    dev = _dev("4.6, 6.8, 10.5", "F-001")
    assert _dev_downgrade([dev], "4.6", feature="F-001") is True
    assert _dev_downgrade([dev], "6.8", feature="F-001") is True
    assert _dev_downgrade([dev], "10.5", feature="F-001") is True
    assert _dev_downgrade([dev], "7.1", feature="F-001") is False


def test_dev_downgrade_multi_rule_no_substring_match():
    """`6.8` must not match a listed `6.81` token (exact token match only)."""
    dev = _dev("6.81, 10.5", "F-001")
    assert _dev_downgrade([dev], "6.8", feature="F-001") is False
    assert _dev_downgrade([dev], "6.81", feature="F-001") is True


def test_dev_downgrade_global_check_ignores_scope():
    """feature/item_id/file all None: any matching-rule open DEV applies regardless of scope."""
    dev = _dev("7.3", "totally-unrelated-scope")
    assert _dev_downgrade([dev], "7.3") is True


def test_tier_s_requires_common_files_only(saal_project):
    root = saal_project("valid_project")
    report = run(root)
    assert report.ok, report.errors


def test_tier_l_missing_documents_reported(saal_project):
    root = saal_project("missing_document")
    report = run(root)
    assert not report.ok
    missing = {e for e in report.errors if "required for Tier L" in e}
    assert any("20-architecture.md" in e for e in missing)
    assert any("35-module-design.md" in e for e in missing)
    assert any("50-integration-test-spec.md" in e for e in missing)


def test_invalid_hash_detected(saal_project):
    root = saal_project("invalid_hash")
    report = run(root)
    assert any("approved_hash does not match" in e for e in report.errors)


def test_broken_reference_detected(saal_project):
    root = saal_project("broken_reference")
    report = run(root)
    assert any("unknown covers ID REQ-9999" in e for e in report.errors)


# --- Ledger `retired` status (spec §9 revised) --------------------------------------------
#
# All tests below start from the `valid_project` fixture (a clean, all-OK Tier S project
# with a legacy 4-field `docs/ids.ledger`) and append or edit a single ledger row / document
# to exercise one retired-ID rule in isolation.

_RETIRED_REQ_ROW = "REQ-0002\tF-001\t2024-01-01T00:00:00+00:00\tRetired req\tretired\n"


def test_legacy_four_field_ledger_rows_are_active_and_ok(saal_project):
    """`valid_project`'s ledger uses the legacy 4-field format; behavior is unchanged."""
    root = saal_project("valid_project")
    report = run(root)
    assert report.ok, report.errors


def test_retired_id_excluded_from_ledger_document_mismatch_check(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(ledger.read_text(encoding="utf-8") + _RETIRED_REQ_ROW, encoding="utf-8")
    report = run(root)
    assert report.ok, report.errors


def test_retired_id_reused_via_duplicate_ledger_row_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "REQ-0001\tF-001\t2024-01-01T00:00:00+00:00\tDo the thing\tretired\n",
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any("retired ID REQ-0001 reused" in e for e in report.errors)


def test_retired_id_still_declared_as_document_heading_is_error(saal_project):
    """Retiring REQ-0001 in place while `### REQ-0001: ...` is still in the document."""
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    text = ledger.read_text(encoding="utf-8").replace(
        "REQ-0001\tF-001\t2024-01-01T00:00:00+00:00\tDo the thing\n",
        "REQ-0001\tF-001\t2024-01-01T00:00:00+00:00\tDo the thing\tretired\n",
    )
    assert text != ledger.read_text(encoding="utf-8")
    ledger.write_text(text, encoding="utf-8")
    report = run(root)
    assert not report.ok
    assert any("retired ID REQ-0001 reused" in e for e in report.errors)


def test_retired_feature_id_reused_as_directory_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "F-002\tF-001\t2024-01-01T00:00:00+00:00\tOld attempt\tretired\n",
        encoding="utf-8",
    )
    (root / "docs/features/F-002_reused").mkdir()
    report = run(root)
    assert not report.ok
    assert any("retired ID F-002 reused" in e for e in report.errors)


def test_covers_reference_to_retired_id_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "REQ-0002\tF-001\t2024-01-01T00:00:00+00:00\tRetired req\tretired\t\tREQ-0001\n",
        encoding="utf-8",
    )
    dd_path = root / "docs/features/F-001_sample/30-detailed-design.md"
    dd_path.write_text(
        dd_path.read_text(encoding="utf-8").replace("covers: REQ-0001", "covers: REQ-0002"),
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any(
        "references retired ID REQ-0002 (superseded by REQ-0001)" in e for e in report.errors
    )


def test_covers_reference_to_retired_id_reports_retired_message_not_unknown_id(saal_project):
    """The retired message replaces the generic "unknown covers ID" error (spec §9, item 3)."""
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(ledger.read_text(encoding="utf-8") + _RETIRED_REQ_ROW, encoding="utf-8")
    dd_path = root / "docs/features/F-001_sample/30-detailed-design.md"
    dd_path.write_text(
        dd_path.read_text(encoding="utf-8").replace("covers: REQ-0001", "covers: REQ-0002"),
        encoding="utf-8",
    )
    report = run(root)
    assert not any("unknown covers ID REQ-0002" in e for e in report.errors)
    assert any("references retired ID REQ-0002" in e for e in report.errors)


def test_verifies_marker_referencing_retired_id_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "DD-0002\tF-001\t2024-01-01T00:00:00+00:00\tRetired design\tretired\n",
        encoding="utf-8",
    )
    test_path = root / "tests/unit/test_dd.py"
    test_path.write_text(
        test_path.read_text(encoding="utf-8").replace('"DD-0001"', '"DD-0002"'), encoding="utf-8"
    )
    report = run(root)
    assert not report.ok
    assert any(
        "tests/unit/test_dd.py::test_dd_unit: references retired ID DD-0002" in e
        for e in report.errors
    )


def test_dev_scope_referencing_retired_id_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "DD-0002\tF-001\t2024-01-01T00:00:00+00:00\tRetired design\tretired\n",
        encoding="utf-8",
    )
    dev_path = root / "docs/features/F-001_sample/90-deviations.md"
    dev_path.write_text(
        dev_path.read_text(encoding="utf-8") + "\n### DEV-0001: legacy scope reference\n\n"
        "rule: 4.6\nscope: DD-0002\nstatus: open\nreason: x\nresolution:\n"
        "decided_by:\ndecided_at:\n",
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any("DEV-0001: references retired ID DD-0002" in e for e in report.errors)


def test_committed_rtm_csv_referencing_retired_id_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(ledger.read_text(encoding="utf-8") + _RETIRED_REQ_ROW, encoding="utf-8")
    trace_dir = root / "docs/trace"
    trace_dir.mkdir()
    (trace_dir / "rtm.csv").write_text(
        "req_id,requirement,feature,design_ids,impl_files,unit_tests,integration_tests,"
        "e2e_tests,verify_status,evidence_commit\n"
        "REQ-0002,Retired req,F-001,,,,,,,\n",
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any("rtm.csv" in e and "references retired ID REQ-0002" in e for e in report.errors)


def test_superseded_by_unknown_id_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "REQ-0002\tF-001\t2024-01-01T00:00:00+00:00\tRetired req\tretired\t\tREQ-9999\n",
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any("superseded_by REQ-9999 is not present in the ledger" in e for e in report.errors)


def test_superseded_by_itself_retired_is_error(saal_project):
    root = saal_project("valid_project")
    ledger = root / "docs/ids.ledger"
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + "REQ-0002\tF-001\t2024-01-01T00:00:00+00:00\tOld\tretired\t\tREQ-0003\n"
        + "REQ-0003\tF-001\t2024-01-01T00:00:00+00:00\tAlso retired\tretired\n",
        encoding="utf-8",
    )
    report = run(root)
    assert not report.ok
    assert any("superseded_by REQ-0003 is itself retired" in e for e in report.errors)
