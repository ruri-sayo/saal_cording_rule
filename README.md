# SAALCO

SAALCO is a local, offline-first CLI that makes the SAAL software development rules operational for people and coding agents. It creates the document structure, allocates permanent IDs, records human approvals, checks traceability, generates an RTM, and records quality-gate Evidence.

## Install

Python 3.11 or newer and Git are required.

```bash
uv tool install .
saalco --help
saal --help
```

For development:

```bash
uv sync --extra dev
uv run pytest
```

## Shortest workflow

```bash
mkdir example && cd example
saalco init --name example --type system --language python --non-interactive
saalco new feature "Login" --tier M --slug login
saalco new req --feature F-001 "A user can log in"
saalco check
```

Use `saalco approve <path>...` at human intervention points. After implementation and tests are committed, run `saalco evidence`, commit `evidence/` and `docs/trace/`, then run `saalco check --verification`.

To retire an ID so its number is never reused, run `saalco retire <ID> [--reason TEXT] [--superseded-by ID]`. This only rewrites that ID's row in `docs/ids.ledger` (status/reason/superseded_by columns; the row is never deleted); it does not touch any document, so remove the item's heading and any references yourself, as the command's output reminds you to do.

## Approval limitation

Approval records the configured Git user, time, version, and a SHA-256 content hash, and refuses non-TTY input. This detects later modification but cannot cryptographically prove that the named human personally reviewed the document. Process controls remain necessary. `SAALCO_ALLOW_NONTTY_APPROVE=1` exists only for SAALCO's automated tests.

## Exit codes

- `0`: success
- `1`: conformance or verification failure
- `2`: usage or configuration error
- `3`: environment or external-tool error

SAALCO never turns an unevaluated check into PASS. A missing or unusable Coverage result is `NOT_EVALUATED`.

