---
kind: UT
feature: F-001
status: draft
---

# Unit Test Spec

### UT-0001: Core document and ID unit tests

covers: DD-0001, MD-0001
verify: test

### UT-0002: Ledger retirement unit test specification

covers: DD-0002, MD-0002
verify: test

次を確認する。`retired` のIDが不一致検査から外れること。廃止した番号の再利用（台帳の重複行、見出しでの再宣言）がERRORになること。廃止したIDへの参照（`covers:`、`verifies` マーカー、`rtm.csv`）がERRORになること。`status` の列が無い既存の行が従来どおり扱われること。`status` の値が不正な場合と `superseded_by` が不正な場合がERRORになること。採番で廃止した番号が再利用されないこと。
