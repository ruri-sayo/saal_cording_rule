from pathlib import Path

import pytest

from saalco.ids import allocate, read_ledger

pytestmark = pytest.mark.impl_aware


def test_ledger_allocation_never_reuses(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/ids.ledger").write_text("")
    assert allocate(tmp_path, "REQ", "F-001", "one") == "REQ-0001"
    assert allocate(tmp_path, "REQ", "F-001", "two") == "REQ-0002"
    assert len(read_ledger(tmp_path)) == 2
