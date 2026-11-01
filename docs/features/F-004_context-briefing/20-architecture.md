---
kind: AD
feature: F-004
status: draft
---

# Architecture

### AD-0003: Read-only briefing module beside the CLI

covers: REQ-0007, REQ-0008
verify: test

新しいモジュール `saalco.context` に、工程の推定とブリーフィングの組み立てを置く。

- 責務の分担
  - `saalco.context`：工程の推定（DD-0007）、ブリーフィングのデータの組み立てとテキスト・JSON への整形（DD-0008）。読むだけで、ファイルを書かない。
  - `saalco.commands`（approve）：承認した文書の一覧（パス・version・Feature）を呼び出し元に返す（DD-0009）。表示はしない。
  - `saalco.cli`：`context` サブコマンドの追加と、approve の完了表示の出力（DD-0009）。
  - 他のモジュール（`checks`、`trace`、`markers`、`documents`、`evidence`、`ids`）は変更せず、`saalco.context` から読み取りのために呼ぶ。
- 依存の向き：`saalco.context` は `saalco.commands`・`saalco.cli` を import しない。`saalco.cli` が `saalco.context` を呼ぶ。approve の完了表示の工程は、`saalco.cli` が承認の後に `saalco.context` の工程の推定を呼んで求める。
- 外部ツール：既存の `saalco.checks.run`・`saalco.trace.generate(write=False)` が読み取りのために呼ぶ `git` 以外は使わない。新しい依存は追加しない。
