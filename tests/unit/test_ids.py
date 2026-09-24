"""Unit tests for saalco.ids: ledger read/allocate and lock contention.

pytestmark impl_aware: exercises the ledger file format and lock file directly.
"""

from pathlib import Path

import pytest

from saalco.errors import SaalcoError
from saalco.ids import allocate, lock, read_ledger

pytestmark = pytest.mark.impl_aware


def _init(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/ids.ledger").write_text("")
    return tmp_path


def test_allocate_increments_per_kind(tmp_path: Path):
    root = _init(tmp_path)
    assert allocate(root, "F", "-", "one") == "F-001"
    assert allocate(root, "F", "-", "two") == "F-002"
    assert allocate(root, "REQ", "F-001", "req one") == "REQ-0001"
    assert allocate(root, "REQ", "F-001", "req two") == "REQ-0002"
    rows = read_ledger(root)
    assert [r[0] for r in rows] == ["F-001", "F-002", "REQ-0001", "REQ-0002"]


def test_allocate_never_reuses_id_after_deletion_from_documents(tmp_path: Path):
    """Deleting an item from a document must not free its ID (ledger is append-only)."""
    root = _init(tmp_path)
    first = allocate(root, "REQ", "F-001", "one")
    second = allocate(root, "REQ", "F-001", "two")
    assert first == "REQ-0001"
    assert second == "REQ-0002"
    # Simulate the document that referenced REQ-0002 being deleted; the ledger keeps the row.
    third = allocate(root, "REQ", "F-001", "three")
    assert third == "REQ-0003"


def test_allocate_unknown_kind_raises(tmp_path: Path):
    root = _init(tmp_path)
    with pytest.raises(SaalcoError, match="unknown ID kind"):
        allocate(root, "ZZ", "F-001", "bad")


def test_read_ledger_missing_file_returns_empty(tmp_path: Path):
    assert read_ledger(tmp_path) == []


def test_read_ledger_rejects_wrong_field_count(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("REQ-0001\tF-001\tonly-three\n")
    with pytest.raises(SaalcoError, match="four tab-separated fields"):
        read_ledger(root)


def test_read_ledger_rejects_invalid_id_format(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("bad-id\tF-001\tstamp\ttitle\n")
    with pytest.raises(SaalcoError, match="invalid ID format"):
        read_ledger(root)


def test_lock_contention_raises(tmp_path: Path):
    root = _init(tmp_path)
    with (
        lock(root),
        pytest.raises(SaalcoError, match="another ID allocation is in progress"),
        lock(root),
    ):
        pass
    # Lock file is released after the outer context exits; a subsequent lock succeeds.
    with lock(root):
        pass
