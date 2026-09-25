---
kind: DD
feature: F-003
status: draft
---

# Detailed Design

### DD-0006: uv.lock precheck, --locked injection, and init guidance

covers: AD-0002, REQ-0006
verify: test

**uv の挙動の確認結果**（2026-09-25、uv 0.11.8、依存の無い一時プロジェクトで `--offline` を付けて確認）

| 状況 | `uv run --locked` | `uv run --frozen` | `uv lock --check` | `uv run`（指定なし） |
|---|---|---|---|---|
| `uv.lock` が無い | exit 2 で停止。`uv.lock` は作らない（`.venv` は作る） | exit 2 で停止 | exit 2 | `uv.lock` を作る |
| `uv.lock` が古い | exit 2 で停止。`uv.lock` は変えない | exit 0 で実行を続ける。`uv.lock` は変えない | exit 1 | `uv.lock` を書き換える |
| `uv.lock` が最新 | exit 0 | exit 0 | exit 0 | exit 0 |

`--frozen` はロックファイルが古くても実行を続け、古さを検出しない。そのため `--locked` を使う。

**事前条件の確認**（`language: python` のときだけ行う。作業ツリーがクリーンであることの確認の直後、出力先のディレクトリを作る前に行う）

1. ルートに `uv.lock` が無い → exit 2。メッセージ：`ERROR uv.lock: not found; Evidence requires a locked environment.` と、次に取るべき操作 `` Run `uv lock`, commit uv.lock, then rerun `saalco evidence`. ``
2. `git ls-files --error-unmatch uv.lock` が失敗する（Git 管理されていない。`.gitignore` で除外されている場合を含む）→ exit 2。`uv.lock` を commit するよう案内する。
3. `uv lock --check` を実行する。exit 0 → 続行。exit 1 → exit 2（`uv.lock` の更新が必要。`uv lock` を実行して commit するよう案内する）。それ以外の終了コード、または `uv` が見つからない → exit 3（`uv lock --check` の出力の先頭行をメッセージに含める）。

**`--locked` の付与**

- `gate.NN.*` と `test.*` のコマンド、および Coverage の書き出し（`uv run coverage json ...`）のうち、字句に分けたとき先頭の2語が `uv` と `run` のものは、`run` の直後に `--locked` を挿入して実行する。manifest の `command` には挿入後のコマンドを記録する。
- すでに `--locked` または `--frozen` を含むコマンドは変更しない（`--frozen` でも、事前条件の確認で `uv.lock` が最新であることは確かめ済みである）。
- `uv run` で始まらないコマンドは変更しない。
- 実行後に `uv.lock` が変わっていれば、既存の「作業ツリーが変化したら FAIL」の検査で検出される（`uv.lock` は 2 により Git 管理されている）。

**`saalco init` の案内**

- `language: python` で、init の処理の後にルートの `uv.lock` が無ければ、標準エラー出力に `` WARNING uv.lock not found. Run `uv lock` and commit uv.lock before `saalco evidence`. `` を出す。exit code は 0 のまま（init は成功している）。
- `uv lock` は実行しない。`language: other` では案内しない。

**メッセージの言語**：CLI のメッセージは、既存のメッセージに合わせて英語とする（規則 11.5 の対象はコードと文書であり、CLI の出力は既存の方針に従う）。
