---
kind: AD
feature: F-001
status: draft
---

# Architecture

### AD-0001: Separate CLI, documents, trace, checks, and evidence

covers: REQ-0001
verify: test

SAALCO は、CLI層とドメインロジックを分離し、単一の巨大ファイルにしない（実装指示書 §6）。実装ではパッケージをサブパッケージではなくフラットな `src/saalco/*.py` に配置しているが、責務の分離自体は満たしている（この構成差は `45-implementation-diff.md` に記録する）。

**CLI層**

- `cli.py`：`argparse` によるコマンドライン解析と、サブコマンド（`init`・`new`・`approve`・`check`・`trace`・`evidence`）へのディスパッチ、出力整形、例外から終了コード（実装指示書 §5）への変換を担う。ドメインロジックは持たない。

**ドメインモジュール**

- `project.py`：プロジェクトルート探索（`docs/project.md` の検出）、`docs/project.md` の読み込み、Git コマンドの実行。
- `documents.py`：文書ヘッダ（フラットな `key: value`）と本文のパース・シリアライズ、原子的書き込み、content hash 計算、項目（`### ID: title` とそのメタ情報）の抽出。
- `ids.py`：`docs/ids.ledger` の読み込みと採番、`.saal/ids.lock` による排他制御。
- `templates.py`：Tier別の必須文書一覧と、文書・項目の雛形生成。
- `commands.py`：`init`・`new feature`・`new <kind>`・`approve` の処理本体。`documents`・`ids`・`templates`・`project` を組み合わせる。
- `markers.py`：`tests/**` の AST 解析による `verifies`/`impl_aware` マーカーの走査。
- `checks.py`：静的検査（実装指示書 §12）と検証検査（§13）の実行。
- `trace.py`：RTM（`docs/trace/rtm.csv`・`rtm.md`）の生成。
- `coverage_contexts.py`：Evidence が生成した coverage JSON から、実装ファイルとテストの対応（測定コンテキスト）を読み込む。
- `evidence.py`：品質ゲート・テストの実行、Coverage 計算、manifest・summary・Evidence Package の生成。
- `errors.py`：終了コードに対応する例外階層。

**データフロー**

```
docs/features/**/*.md（人間・AIが記述） ─┐
tests/**（pytestマーカー） ──────────────┼─→ checks.py / trace.py → docs/trace/rtm.csv, rtm.md
docs/ids.ledger（saalco new が採番） ────┘

docs/project.md の gate.*/test.* → evidence.py が実行
  → .saal/artifacts/<commit>/<run-id>/（生データ、coverage JSON を含む）
  → evidence/<commit>/<run-id>/manifest.json, summary.md（Git管理）
  → coverage_contexts.py が読み戻し、checks.py（§13-14）・trace.py の impl_files 列に反映
```

すなわち、文書（要件・設計・試験仕様の項目と `covers:`/`verify:`）とID台帳から項目・依存関係のグラフを構成し、テストマーカーと coverage 測定コンテキストで実装・テストと結び付け、`check`/`trace` で検証状態を判定し、`evidence` で特定commitに対するEvidenceとして固定する、という一方向のデータフローを持つ。

**外部ツール**

- `git`：リポジトリ初期化、`user.name` の取得（承認記録）、作業ツリーのクリーン判定、diff の取得（差分Coverage計算）。
- `uv`：プロジェクト側の `pytest`・`ruff`・`mypy` 等のゲートコマンドを、プロジェクトの隔離環境で実行するために経由する。SAALCO 自身は uv tool の隔離環境で動作するため、プロジェクトの `.coverage` を直接読み込まず、`uv run coverage json --show-contexts` が出力するJSON経由で読み込む（実装指示書 §4、§14）。
- `pytest`：プロジェクト側の単体・結合・E2Eテストの実行。JUnit XML を出力させ、`evidence.py` がテストごとの結果を取得する。
- `coverage.py`：行カバレッジと測定コンテキストの取得。SAALCO 自体は Python標準ライブラリのみに依存し、`pytest`・`coverage.py` 等の外部ツールはあくまでサブプロセスとして呼び出す対象である（実装指示書 §4）。

**読み書きするファイル配置**

- 読む：`docs/project.md`、`docs/features/**/*.md`、`docs/ids.ledger`、`docs/glossary.md`（人間・Coding Agentが参照する対象であり SAALCO 自体は読まない）、`tests/**/test_*.py`、`.saal/artifacts/**`、Git の作業ツリー・履歴。
- 書く：`docs/ids.ledger`、`docs/features/**/*.md`（`new`・`approve` による追記・メタ情報更新のみ）、`docs/trace/rtm.csv`・`rtm.md`、`.saal/artifacts/**`、`evidence/**`、`.saal/packages/**`、`.saal/ids.lock`。
