"""SAALCO: SAAL compliance operations toolkit.

Responsibilities:
- Provide CLI and API for managing SAAL projects (init, new, approve, check, trace, evidence).
- Implement project discovery, ID allocation, document management, and traceability tracking.

Non-responsibilities:
- Test execution (delegated to pytest).
- Code compilation or deployment.
- Proof of correctness (done by human review).

External dependencies:
- git: for repository management.
- subprocess: for running quality gates and tests.
- pytest: for test collection and markers (not executed by saalco).
"""

__version__ = "1.0.0"
