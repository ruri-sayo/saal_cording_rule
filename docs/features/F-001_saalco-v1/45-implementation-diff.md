---
kind: IMPLEMENTATION_DIFF
feature: F-001
status: draft
---

# Implementation Diff

## Implemented but not designed

- `src/saalco/coverage_contexts.py`: coverage.py test-context loader used by RTM `impl_files` and the §13-14 unapproved-design check (not yet described in 30/35 documents).
- `saalco new --non-interactive` flag (spec §2 lists it only for `init`).
- Manifest top-level `overall` and `coverage.json_path` fields (beyond the §17 field list).
- Generated `.gitignore` also ignores Python build artifacts (`__pycache__/`, `*.py[cod]`, `.venv/`, `*.egg-info/`, `.coverage`).

## Designed but not implemented

- Package layout differs from the recommended §6 sub-packages (flat modules; CLI and domain logic are still separated).
- Network-caused gate failures are not distinguished from ordinary FAIL (§16 asks for ERROR).
- Ledger ID retirement has no conforming path (see `docs/development-open-questions.md`).
