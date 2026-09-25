---
kind: UT
feature: F-002
status: draft
---

# Unit Test Spec

### UT-0005: DEV status validation unit test specification

covers: DD-0005
verify: test

次を単体テストで確認する。

- `status: closed` の DEV で、`rule` と `scope` が該当しても、ERRORがWARNINGに緩められないこと。
- `status: open` の DEV では、従来どおりWARNINGに緩められること。
- `status` の値が `open`・`closed` 以外（例：`resolved`）の場合と、`status` の行が無い場合に、ERRORになること。
- `closed` の DEV で `closed_at` または `closed_condition` が無い場合、値が空の場合に、ERRORになること。両方あればERRORにならないこと。
