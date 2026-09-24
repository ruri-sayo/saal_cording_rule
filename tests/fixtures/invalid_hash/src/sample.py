"""Sample implementation module for fixture-based tests.

Responsibilities:
- Provide a trivial, deterministic function for coverage/trace fixture tests.

Non-responsibilities:
- Not part of the saalco package; this lives inside a simulated user project.
"""


def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b
