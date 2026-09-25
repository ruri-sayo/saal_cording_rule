---
kind: ST
feature: F-002
status: draft
---

# System E2E Spec

### ST-0004: Closed DEV handling through the CLI

covers: REQ-0005
verify: test

CLI で、Coverage未達などの例外を `open` の DEV で許容している一時プロジェクトを作り、`saalco check --verification` がWARNINGを報告することを確認する。続けて、その DEV を `closed`（`closed_at` と `closed_condition` を記入）に変え、同じ違反がERRORとして報告され、exit 1 になることを確認する。最後に `status: resolved` と書き、`saalco check` がERRORを報告することを確認する。
