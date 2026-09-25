---
kind: UT
feature: F-003
status: draft
---

# Unit Test Spec

### UT-0006: Lockfile precheck and --locked injection unit test specification

covers: DD-0006
verify: test

次を単体テストで確認する（外部コマンドは置き換えて確認してよい）。

- `--locked` の付与：`uv run pytest tests/unit` → `uv run --locked pytest tests/unit`。`uv run --locked ...` と `uv run --frozen ...` は変更されない。`python -m pytest`、`ruff check .` など `uv run` で始まらないコマンドは変更されない。
- 事前条件：`uv.lock` が無い → exit 2 のエラー。Git 管理されていない → exit 2。`uv lock --check` が exit 1 → exit 2。`uv lock --check` がそれ以外で失敗、または `uv` が見つからない → exit 3。`uv lock --check` が exit 0 → エラーなし。`language: other` → 確認しない。
- init の案内：`language: python` で `uv.lock` が無い → 案内を出す。`uv.lock` がある → 出さない。`language: other` → 出さない。
