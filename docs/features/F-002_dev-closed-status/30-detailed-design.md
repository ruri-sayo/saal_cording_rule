---
kind: DD
feature: F-002
status: approved
approved_by: ruri-sayo
approved_at: 2026-09-25T12:52:28+09:00
version: 1
approved_hash: f54254ce936f5170b238229efae66841445551d1fa2319aa3bcc47ffe274bacb
---

# Detailed Design

### DD-0005: DEV status validation and closed-record checks

covers: REQ-0005
verify: test

- DEV の `status` として受け付ける値を `open` と `closed` の2つに固定する。`saalco check`（静的検査）が DEV 項目ごとに値を確かめ、それ以外の値と欠落をERRORとする。メッセージには、文書のパス、DEV のID、原因、次に取るべき操作（`open` または `closed` を記入する）を含める。
- `closed` の DEV は、`closed_at` と `closed_condition` の両方に空でない値を持たなければならない。欠けていればERRORとする。`closed_at` の日付の書式は検査しない（`decided_at` と同じ扱い）。
- 逸脱の許容（ERRORをWARNINGに緩める処理）は、従来どおり `status: open` の DEV だけを対象とする。`closed` の DEV と、`status` が不正な DEV は許容に使わない。
- `status`・`closed_at`・`closed_condition` は人間が記入する欄であり、SAALCO は書き込まない。
