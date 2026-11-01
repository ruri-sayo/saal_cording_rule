---
kind: ST
feature: F-004
status: draft
---

# System E2E Spec

### ST-0006: Briefing and approve hint through the CLI

covers: REQ-0007, REQ-0008
verify: test

CLI で次の流れを確認する。

1. `saalco init` → `saalco new feature --tier S` → `saalco new req` → commit。
2. `saalco context F-001` が exit 0 で、`Phase: req (inferred)` を含む。`saalco context F-001 --json` の `phase` が `req`。
3. `saalco approve`（`SAALCO_ALLOW_NONTTY_APPROVE=1`）で REQ を承認すると、標準出力に `Approved: docs/features/<dir>/10-requirements.md (version 1)` と `` Next: start a new session and run `saalco context F-001 --phase dd` `` が出る。
4. `saalco context F-001 --phase impl` が `Phase: impl (given; inferred: dd)` を含む。
5. 2回続けて実行した `saalco context F-001` の出力が一致し、テキストが200行以内である。実行の前後で `git status --porcelain` が変わらない。
6. `saalco context F-999` が exit 2。
7. TTY でない環境で（環境変数なしで）`saalco approve` を実行すると、従来どおり拒否され、標準出力に `Approved:` が出ない。
