---
kind: IT
feature: F-003
status: draft
---

# Integration Test Spec

### IT-0002: Evidence runner and uv lockfile integration test specification

covers: AD-0002
verify: test

一時プロジェクト（依存の無い `pyproject.toml`、`language: python`）で `saalco evidence` を実行し、次を確認する。

- `uv.lock` が無い → exit 2。`evidence/` と `.saal/artifacts/` に新しい出力が無い。`uv.lock` が作られていない。
- `uv.lock` が Git 管理されていない（`.gitignore` で除外）→ exit 2。
- `pyproject.toml` を変更して `uv.lock` が古い状態で commit → exit 2。`uv.lock` が変わっていない。
- `uv.lock` が最新 → Evidence が作られ、manifest に記録された `uv run` で始まるコマンドに `--locked` が含まれる。実行の前後で `uv.lock` が変わっていない。
