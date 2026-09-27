# SAALCO

SAALCO は、SAAL ソフトウェア開発規則を、人間とコーディングエージェントが実際に運用できるようにするための CLI です。ローカルで完結し、ネットワークには接続しません。

文書の構造を作り、ID を採番し、人間の承認を記録し、トレーサビリティを検査し、RTM（要求トレーサビリティマトリクス）を生成し、品質ゲートの Evidence を記録します。

**使い方の詳細は [使い方マニュアル（docs/manual.md）](docs/manual.md) を読んでください。** インストールから、1つの機能を設計・実装・検証して受け入れるまでの手順を、実際に打つコマンドと書くファイルの例つきで説明しています。

## こんな人のためのツールです

- AI エージェントに実装の大半を任せつつ、「人間がコードを全部読んだから大丈夫」以外の根拠で品質を示したい
- 要件 → 設計 → テスト → Evidence の対応を、手で保守する表ではなく機械的に追跡したい
- 人間が判断すべき点（要件、構造、設計判断、受け入れ）だけに人間の時間を使いたい

## SAALCO がやること・やらないこと

| やること | やらないこと |
|---|---|
| ID の採番と台帳の管理 | 要件が「作るべきもの」だったかの判断（Validation は人間の責任） |
| 承認の記録と、承認後の改変の検出 | 人間が本当に文書を読んだことの証明 |
| `covers:` の参照切れ、テスト不足、Tier ごとの必須文書の検査 | 判定できないものを PASS にすること（`NOT_EVALUATED` と表示する） |
| 品質ゲート・テスト・Coverage を実行し、commit に紐づく Evidence を記録 | |
| RTM と Evidence Package の生成 | |

## 必要なもの

- Python 3.11 以上
- Git
- [uv](https://docs.astral.sh/uv/)（Python プロジェクトで `saalco evidence` を使う場合）

## インストール

リポジトリのルートで実行します。`saalco` と `saal`（同じコマンドの別名）が使えるようになります。

```bash
uv tool install .
```

```bash
saalco --version
```

`saalco approve` は `git config user.name` を承認者として記録するので、未設定なら設定しておきます。

```bash
git config --global user.name "your-name"
```

## 最短の流れ

```bash
mkdir example && cd example
saalco init --name example --type system --language python --non-interactive
saalco new feature "Login" --tier M --slug login
saalco new req --feature F-001 "利用者はログインできる"
saalco check
```

このあと、おおまかに次の順で進めます（各段階の詳細はマニュアルの「[開発プロセスの詳細](docs/manual.md#5-開発プロセスの詳細)」）。

1. 要件・設計を書き、人間が `saalco approve <path>...` で承認する
2. 試験仕様を書き、仕様由来テスト（`@pytest.mark.verifies("DD-0001")`）と実装を書く
3. `saalco check` を通し、全てを commit する
4. `saalco evidence` を実行し、生成された `evidence/` と `docs/trace/` を commit する。続けて `saalco trace` で RTM を生成し直し、`docs/trace/` を commit する
5. `saalco check --verification` で、要件が `verified` になっていることを確認する
6. 人間が `70-acceptance.md` に受け入れ判断を書く

## コマンド一覧

| コマンド | 内容 |
|---|---|
| `saalco init` | 標準のディレクトリ構造と雛形を置く |
| `saalco new <kind>` | Feature・項目（`req`/`ad`/`dd`/`md`/`ut`/`it`/`st`/`dev`）を採番して作る |
| `saalco approve <path>...` | 人間の承認を記録する（人間専用。TTY が必要） |
| `saalco retire <ID>` | ID を廃止し、番号を再利用させない |
| `saalco check [--verification]` | 規則への適合を検査する |
| `saalco trace` | RTM（`docs/trace/rtm.csv`・`rtm.md`）を生成する |
| `saalco evidence [--package F-nnn]` | ゲートとテストを実行して Evidence を記録する／Evidence Package を作る |

各オプションはマニュアルの「[コマンドリファレンス](docs/manual.md#11-コマンドリファレンス)」を参照してください。

## ID の廃止

番号を二度と使わないように ID を廃止するには、`saalco retire <ID> [--reason TEXT] [--superseded-by ID]` を実行します。このコマンドは `docs/ids.ledger` の該当行（status・reason・superseded_by の列）だけを書き換え、行は削除しません。文書には触れないので、項目の見出しと参照は、出力の案内に従って自分で削除してください。

## 承認の限界

承認では、設定された Git の user.name、日時、版、内容の SHA-256 hash を記録し、TTY 以外からの入力を拒否します。これにより承認後の改変は検出できますが、名前の記録された人間が実際に文書を確認したことを暗号的に証明するものではありません。運用上の管理は引き続き必要です。`SAALCO_ALLOW_NONTTY_APPROVE=1` は SAALCO 自身の自動テスト専用です。

## 終了コード

- `0`：成功
- `1`：規則への不適合、または検証の失敗
- `2`：使い方・設定の誤り
- `3`：環境・外部ツールの誤り

SAALCO は、評価していない検査を PASS にしません。Coverage の結果が無い、または使えない場合は `NOT_EVALUATED` になります。

## 関連文書

| 文書 | 内容 |
|---|---|
| [docs/manual.md](docs/manual.md) | 使い方マニュアル（まずはこれ） |
| [docs/rules/SAAL-DEV-RULES.md](docs/rules/SAAL-DEV-RULES.md) | SAAL ソフトウェア開発規則（正本） |
| [docs/glossary.md](docs/glossary.md) | 用語の対応表（日本語・英語） |
| [AGENTS.md](AGENTS.md) | AI エージェント向けの作業指示 |
| [docs/development-open-questions.md](docs/development-open-questions.md) | 暫定解釈と未決事項 |

## SAALCO 自身の開発

SAALCO 自身もこの規則に従って開発しています（設計文書は `docs/features/`、RTM は `docs/trace/`、Evidence は `evidence/`）。

```bash
uv sync --extra dev
```

```bash
uv run pytest
```
