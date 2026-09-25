---
kind: ST
feature: F-003
status: draft
---

# System E2E Spec

### ST-0005: Evidence with missing, outdated, and current uv.lock through the CLI

covers: REQ-0006
verify: test

CLI で次の流れを確認する。`saalco init`（`language: python`）→ `uv.lock` が無い旨の案内が出る → `saalco evidence` が exit 2 で止まり `uv lock` を案内する → `uv lock` を実行して commit → `saalco evidence` が Evidence を作る → `pyproject.toml` の `version` を変えて commit → `saalco evidence` が exit 2 で止まり `uv lock` を案内する → `uv lock` を実行して commit → `saalco evidence` が Evidence を作る。各段階で、止まった場合に `uv.lock` が変わっていないことを確かめる。
