---
kind: MD
feature: F-001
status: draft
---

# Module Design

### MD-0001: SAALCO Python package modules

covers: DD-0001
verify: test

各モジュールの責務と公開関数（名前・シグネチャのみ）は次のとおり。

**cli**
- 責務：コマンドライン解析とサブコマンドへのディスパッチ、出力整形、終了コードへの変換。
- `parser() -> argparse.ArgumentParser`
- `dispatch(args: argparse.Namespace) -> int`
- `main(argv: list[str] | None = None) -> int`

**commands**
- 責務：`init`・`new feature`・`new <kind>`・`approve` の処理本体。
- `init_project(...)`
- `new_feature(root: Path, title: str, tier: str, slug: str | None) -> str`
- `new_item(root: Path, kind: str, feature: str, title: str) -> tuple[str, str | None]`
- `approve(root: Path, paths: list[str]) -> None`

**documents**
- 責務：文書ヘッダ・本文のパース／シリアライズ、原子的書き込み、content hash、項目抽出。
- `class Document`
- `class Item`
- `parse_document(path: Path) -> Document`
- `serialize(doc: Document) -> str`
- `atomic_write(doc: Document) -> None`
- `content_hash(doc: Document) -> str`
- `items(doc: Document) -> list[Item]`
- `set_header(doc: Document, values: dict[str, str]) -> None`

**ids**
- 責務：`docs/ids.ledger` の読み込みと採番、排他制御。
- `class LedgerRow`
- `read_ledger(root: Path) -> list[LedgerRow]`
- `lock(root: Path)`
- `allocate(root: Path, kind: str, feature: str, title: str) -> str`

**project**
- 責務：プロジェクトルート探索、`docs/project.md` の読み込み、Gitコマンド実行。
- `discover(start: Path | None = None) -> Path`
- `config(root: Path) -> dict[str, str]`
- `git(root: Path, *args: str, check: bool = True) -> str`

**markers**
- 責務：`tests/**/test_*.py` のAST解析による `verifies`/`impl_aware` マーカー走査。
- `class TestMarker`
- `scan_tests(root: Path) -> list[TestMarker]`

**checks**
- 責務：静的検査（実装指示書 §12）と検証検査（§13）の実行、結果の集約。
- `class Report`
- `run(root: Path, verification: bool = False) -> Report`

**trace**
- 責務：RTM（`docs/trace/rtm.csv`・`rtm.md`）の生成。
- `generate(root: Path, write: bool = True) -> list[dict[str, str]]`

**coverage_contexts**
- 責務：Evidence実行時に出力されたcoverage JSONから、実装ファイルとテストの対応を読み込む。
- `load(root: Path, manifest: dict) -> dict[str, set[str]] | None`

**evidence**
- 責務：品質ゲート・テストの実行、差分／全体Coverageの計算、manifest・summary・Evidence Packageの生成。
- `current_manifest(root: Path) -> dict[str, object] | None`
- `create(root: Path) -> tuple[Path, str]`
- `package(root: Path, feature: str) -> Path`

**templates**
- 責務：種別ごとのファイル名対応、Tier別必須文書一覧、文書雛形の生成。
- `feature_document(name: str, feature: str, tier: str, project_type: str) -> str`
- `project_document(name: str, project_type: str, language: str) -> str`

**errors**
- 責務：終了コードに対応する例外階層の定義。
- `class SaalcoError(Exception)`
- `class CheckFailed(SaalcoError)`
- `class ToolError(SaalcoError)`

### MD-0002: Ledger parsing and retirement validation in ids and checks modules

covers: DD-0002
verify: test

`saalco.ids` が台帳の行を構造化して読む（行番号、状態、理由、置き換え先を保持する）。採番時には、タイトル中のタブを空白に置き換える。`saalco.checks` が DD-0002 の検査を行う。DEV の `rule:` にはカンマ区切りで複数の規則番号を書けるようにし、各番号と完全一致で照合する。

### MD-0003: Retire command implementation in ids and commands modules

covers: DD-0003
verify: test

`saalco.ids` に、台帳1行を廃止状態へ書き換える関数を追加する。既存の `LedgerRow`（MD-0002）を用いて対象行を検証し、原子的に書き換える。

- `retire(root: Path, ident: str, reason: str | None, superseded_by: str | None) -> LedgerRow`：対象IDの行を `status: retired` に書き換え、更新後の行を返す。未知ID・廃止済みID・不正な `superseded_by`・改行やタブを含む `reason` の場合は `saalco.errors` の例外を送出する。

`saalco.commands` に、CLIから呼び出すコマンド本体を追加する。

- `retire(root: Path, ident: str, reason: str | None, superseded_by: str | None) -> str`：`ids.retire` を呼び出し、案内メッセージ（項目見出しと参照を文書から削除すること）を含む標準出力用の文字列を返す。

`saalco.cli` に、`retire` サブコマンドのパーサ登録とディスパッチを追加する（`--reason`・`--superseded-by` オプション）。

### MD-0004: Template text changes in the templates module

covers: DD-0004
verify: test

`saalco.templates` の既存の公開関数（シグネチャは変更しない）の内部文言のみを変更する。

- `feature_document(name: str, feature: str, tier: str, project_type: str) -> str`：`45-implementation-diff.md`・`70-acceptance.md`・`80-outcome.md` の固定文言・項目ラベルを日本語にする。
- `AGENTS`（モジュールレベル定数 `str`）：本文を日本語（現行リポジトリの `AGENTS.md` と同内容）にする。
- `project_document(name: str, project_type: str, language: str) -> str`：変更しない（キーとゲートコマンドのみで、翻訳対象の本文を持たない）。
- `FILE_FOR_KIND`・`TIER_FILES`・`KIND_FOR_FILE`：変更しない。
