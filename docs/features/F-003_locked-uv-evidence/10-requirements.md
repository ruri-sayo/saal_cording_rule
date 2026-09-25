---
kind: REQ
feature: F-003
status: approved
approved_by: ruri-sayo
approved_at: 2026-09-25T14:24:13+09:00
version: 1
approved_hash: 59763cda8ff43995ebf29f4d16fe2c5a2ae60cb8ca66b62a5ad90268be51788c
---

# Requirements

### REQ-0006: Evidence requires an up-to-date uv.lock and never changes it

covers: -
verify: test

`language: python` のプロジェクトで、Evidence の取得がロックファイルを変更しないこと。

1. `saalco evidence` は、プロジェクトのルートに `uv.lock` が無い場合、Evidence を取らずに exit 2 で止まり、`uv lock` を実行して `uv.lock` を commit するよう案内すること。
2. `uv.lock` が Git 管理されていない場合も、同様に exit 2 で止まり、`uv.lock` を commit するよう案内すること。
3. `uv.lock` が `pyproject.toml` と整合しておらず更新が必要な場合も、Evidence を取らずに exit 2 で止まり、`uv lock` の実行と commit を案内すること。
4. 1〜3 で止まる場合は、`evidence/` と `.saal/artifacts/` に何も作らないこと。
5. Evidence の取得中に `uv run` で実行するゲート・テスト・Coverage の書き出しは、`uv run --locked` で実行し、`uv.lock` を作成・変更しないこと。
6. `uv` が見つからない場合など、ロックファイルを確認できない場合は exit 3（環境・外部ツールのエラー）とし、Evidence を PASS として扱わないこと。
7. `saalco init` は、`language: python` で `uv.lock` が無い場合、`uv lock` を実行して `uv.lock` を commit するよう案内すること。`saalco init` 自身は `uv lock` を実行しない（依存関係の更新をしないため。実装指示書 §18）。
8. `language: other` のプロジェクトには、1〜7 を適用しないこと。
