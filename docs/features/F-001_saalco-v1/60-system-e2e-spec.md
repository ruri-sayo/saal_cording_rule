---
kind: ST
feature: F-001
status: draft
---

# System E2E Spec

### ST-0001: Installed CLI end-to-end workflow

covers: REQ-0001
verify: test

### ST-0002: Retired ID handling through the CLI

covers: REQ-0002
verify: test

CLIから、IDの採番、台帳の行への廃止情報の追記、文書項目の削除を順に行い、`saalco check` が不一致を報告しないことを確認する。続けて、廃止したIDを `covers:` から参照し、`saalco check` がERRORを報告することを確認する。
