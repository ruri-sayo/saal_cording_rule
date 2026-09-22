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
