---
kind: IT
feature: F-004
status: draft
---

# Integration Test Spec

### IT-0003: Briefing over a real project tree integration test specification

covers: AD-0003
verify: test

`saalco init` で作った一時プロジェクト（Git 管理、commit 済み）に、2つの Feature（片方がもう片方の REQ を `covers:` する）を `saalco new` で作り、次を確認する。

- `saalco.context` のブリーフィングが、`saalco.checks.run` の結果（件数）と一致する `Check` 節を含む。
- 上流の Feature の REQ が `Upstream:` に並ぶ。
- ブリーフィングの組み立ての前後で、`git status --porcelain` の出力が変わらない（ファイルを書かない）。
- `saalco.commands.approve`（`SAALCO_ALLOW_NONTTY_APPROVE=1`）の後に推定した工程が、承認した文書に応じて進む（REQ を承認すると Tier M では `ad`）。
