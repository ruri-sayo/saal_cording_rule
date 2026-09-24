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
    dev = _dev("13.5", "src/pkg/")
    assert _dev_downgrade([dev], "13.5", file="src/pkg/module.py") is True
    assert _dev_downgrade([dev], "13.5", file="src/other.py") is False


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
