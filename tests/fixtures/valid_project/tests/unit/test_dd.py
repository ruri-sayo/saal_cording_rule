"""Fixture unit test verifying DD-0001 (simulated user project, not saalco's own suite)."""

import pytest
from sample import add


@pytest.mark.verifies("DD-0001")
def test_dd_unit():
    assert add(2, 3) == 5
