"""Unit tests for saalco.ids: ledger read/allocate and lock contention.

pytestmark impl_aware: exercises the ledger file format and lock file directly.
"""

from pathlib import Path

import pytest

from saalco.errors import SaalcoError
from saalco.ids import LedgerRow, allocate, lock, read_ledger, retire

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
    assert [r.id for r in rows] == ["F-001", "F-002", "REQ-0001", "REQ-0002"]
    assert all(r.status == "active" for r in rows)


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
    with pytest.raises(SaalcoError, match="tab-separated fields"):
        read_ledger(root)


def test_read_ledger_rejects_too_many_fields(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text(
        "REQ-0001\tF-001\tstamp\ttitle\tactive\treason\tREQ-0002\textra\n"
    )
    with pytest.raises(SaalcoError, match="tab-separated fields"):
        read_ledger(root)


def test_read_ledger_rejects_invalid_id_format(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("bad-id\tF-001\tstamp\ttitle\n")
    with pytest.raises(SaalcoError, match="invalid ID format"):
        read_ledger(root)


def test_read_ledger_legacy_four_field_row_is_active(tmp_path: Path):
    """A legacy 4-field row (no status column) behaves exactly as before: status 'active'."""
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("REQ-0001\tF-001\tstamp\ttitle\n")
    rows = read_ledger(root)
    assert rows == [
        LedgerRow(id="REQ-0001", feature="F-001", allocated_at="stamp", title="title", line=1)
    ]
    assert rows[0].status == "active"
    assert rows[0].reason == ""
    assert rows[0].superseded_by == ""


def test_read_ledger_empty_status_field_is_active(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("REQ-0001\tF-001\tstamp\ttitle\t\n")
    assert read_ledger(root)[0].status == "active"


def test_read_ledger_retired_row_with_reason_and_superseded_by(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text(
        "REQ-0001\tF-001\tstamp\ttitle\tretired\tsplit into two\tREQ-0002\n"
    )
    row = read_ledger(root)[0]
    assert row.status == "retired"
    assert row.reason == "split into two"
    assert row.superseded_by == "REQ-0002"


def test_read_ledger_rejects_invalid_status(tmp_path: Path):
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text("REQ-0001\tF-001\tstamp\ttitle\tarchived\n")
    with pytest.raises(SaalcoError, match="invalid ledger status"):
        read_ledger(root)


def test_allocate_sanitizes_tabs_in_title(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "title\twith\ttabs")
    row = read_ledger(root)[0]
    assert row.title == "title with tabs"
    assert "\t" not in row.title


def test_allocate_never_reuses_a_retired_number(tmp_path: Path):
    """Retired rows still count toward the max when computing the next number (spec §9)."""
    root = _init(tmp_path)
    (root / "docs/ids.ledger").write_text(
        "REQ-0001\tF-001\tstamp\tone\tactive\n"
        "REQ-0002\tF-001\tstamp\ttwo\tretired\tsuperseded\tREQ-0003\n"
    )
    assert allocate(root, "REQ", "F-001", "three") == "REQ-0003"


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


# ---------------------------------------------------------------------------
# retire (REQ-0003 / DD-0003 / MD-0003 / UT-0003)
# ---------------------------------------------------------------------------


def test_retire_active_id_sets_retired_status_only(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    allocate(root, "REQ", "F-001", "two")
    before = read_ledger(root)

    row = retire(root, "REQ-0001", reason="merged", superseded_by="REQ-0002")

    assert row.id == "REQ-0001"
    assert row.status == "retired"
    assert row.reason == "merged"
    assert row.superseded_by == "REQ-0002"
    after = read_ledger(root)
    # Only REQ-0001's status/reason/superseded_by changed; everything else is untouched.
    assert after[0].feature == before[0].feature
    assert after[0].allocated_at == before[0].allocated_at
    assert after[0].title == before[0].title
    assert after[1] == before[1]


def test_retire_without_reason_or_superseded_by(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    row = retire(root, "REQ-0001")
    assert row.status == "retired"
    assert row.reason == ""
    assert row.superseded_by == ""


def test_retire_unknown_id_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with pytest.raises(SaalcoError, match="unknown ID"):
        retire(root, "REQ-9999")


def test_retire_already_retired_id_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    retire(root, "REQ-0001")
    with pytest.raises(SaalcoError, match="already retired"):
        retire(root, "REQ-0001")


def test_retire_superseded_by_unknown_id_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with pytest.raises(SaalcoError, match="not in docs/ids.ledger"):
        retire(root, "REQ-0001", superseded_by="REQ-9999")


def test_retire_superseded_by_retired_id_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    allocate(root, "REQ", "F-001", "two")
    retire(root, "REQ-0002")
    with pytest.raises(SaalcoError, match="itself"):
        retire(root, "REQ-0001", superseded_by="REQ-0002")


def test_retire_superseded_by_malformed_id_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with pytest.raises(SaalcoError, match="not a valid ID"):
        retire(root, "REQ-0001", superseded_by="not-an-id")


def test_retire_reason_with_tab_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with pytest.raises(SaalcoError, match="tab or newline"):
        retire(root, "REQ-0001", reason="bad\treason")


def test_retire_reason_with_newline_raises(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with pytest.raises(SaalcoError, match="tab or newline"):
        retire(root, "REQ-0001", reason="bad\nreason")


def test_retire_never_deletes_a_row(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    allocate(root, "REQ", "F-001", "two")
    allocate(root, "REQ", "F-001", "three")
    retire(root, "REQ-0002")
    rows = read_ledger(root)
    assert [r.id for r in rows] == ["REQ-0001", "REQ-0002", "REQ-0003"]
    assert (root / "docs/ids.ledger").read_text().count("\n") == 3


def test_retire_interrupted_replace_leaves_original_row_intact(tmp_path: Path, monkeypatch):
    """Simulates an interruption between the temp-file write and the atomic replace: the
    original ledger must survive untouched, and the temp file must not linger.
    """
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    original = (root / "docs/ids.ledger").read_text()

    import saalco.ids as ids_module

    def _broken_replace(*args, **kwargs):
        raise OSError("simulated interruption before replace")

    monkeypatch.setattr(ids_module.os, "replace", _broken_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        retire(root, "REQ-0001")
    assert (root / "docs/ids.ledger").read_text() == original
    assert read_ledger(root)[0].status == "active"
    assert list((root / "docs").glob(".ids.ledger.*")) == []


def test_retire_uses_same_lock_as_allocate(tmp_path: Path):
    root = _init(tmp_path)
    allocate(root, "REQ", "F-001", "one")
    with (
        lock(root),
        pytest.raises(SaalcoError, match="another ID allocation is in progress"),
    ):
        retire(root, "REQ-0001")
    # Ledger is unchanged since retire never got past the lock.
    assert read_ledger(root)[0].status == "active"
