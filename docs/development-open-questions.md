# Development open questions

The v1.0 implementation follows the temporary interpretations in the implementation instructions. These remain rule-level questions and are not silently treated as PASS.

- C / I-1: Evidence cannot share the target commit; it is current only when intervening changes are limited to `evidence/`, `docs/trace/`, and `docs/ids.ledger`.
- C / I-2: Checking is split into pre-test `check` and post-test `check --verification`.
- C / I-3: `docs/ids.ledger` is the allocation authority so retired IDs cannot be reused.
- C / I-4: A current manual ST result may satisfy a requirement.
- C / I-5: Deviations use structured `DEV-nnnn` items so exceptions are machine-readable.
- C / I-6: Implementation/design differences live in `45-implementation-diff.md`.
- C / I-7: Tier metadata is approved together with detailed design at H3.
- C / I-8: Both `saal` and `saalco` invoke the same CLI.
- B: A test-command aggregate exit code does not identify individual parametrized case results; v1.0 records the suite result for every statically discovered marker.
- D: Coverage JSON alone does not reliably associate every implementation line with a test on every coverage.py version. Missing context is `NOT_EVALUATED`, never PASS.
- D: §9 says ledger rows are never deleted when an ID is retired, but also that a ledger/document mismatch is an ERROR. v1.0 keeps the ERROR (safe side); retiring an ID therefore has no conforming path yet and needs a rule/tool decision.
- B: The diff-coverage baseline (§15 "直前 Evidence") is interpreted as the nearest ancestor Evidence whose coverage status is PASS; FAIL/NOT_EVALUATED Evidence never becomes a baseline, so re-running `saalco evidence` cannot turn a coverage FAIL into PASS.
- A: Changed source lines that coverage.py does not consider executable (comments, blank lines) count as 100% diff coverage; pure deletions are not "changed lines".
- B: DEV exceptions (§8.6) are matched by exact rule number and exact scope tokens (feature ID, item ID, or path prefix). Rules used: 6.4 verifies test not PASS, 6.8 RTM not verified, 7.1 gate FAIL/ERROR, 7.3 coverage, 13.5 unapproved-design implementation.
- A: A tool missing inside `uv run` (e.g. pytest not installed in the project venv) is recorded as FAIL rather than ERROR; it is non-PASS either way.
- A: Files under `tests/fixtures/` are sample data and are never scanned for markers or collected by pytest.
