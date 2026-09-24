"""Fixture e2e test verifying REQ-0001 (simulated user project, not saalco's own suite)."""

import pytest


@pytest.mark.verifies("REQ-0001")
def test_thing_works():
    assert True
