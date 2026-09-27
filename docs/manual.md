# SAALCO 使い方マニュアル

SAALCO（`saalco` コマンド）を使って、SAAL ソフトウェア開発規則（以下「規則」）に従った開発を進めるための手引きである。インストールから、Feature の登録、設計文書と試験仕様の作成、承認、実装、Evidence の記録、受け入れまでを、実際に打つコマンドと書くファイルの例とともに説明する。

- 規則の正本は [`docs/rules/SAAL-DEV-RULES.md`](rules/SAAL-DEV-RULES.md) である。本書は規則の「使い方」を説明するもので、規則と食い違う場合は規則が優先する。
- 規則中の `saal` コマンドは `saalco` と同じものである（どちらの名前でも起動できる）。
- 用語は [`docs/glossary.md`](glossary.md) の対応表に合わせている。
- 本書のコマンド例と出力例は、SAALCO 1.0.0 で実際に実行して確認したものである。

## 目次

1. [SAALCO とは](#1-saalco-とは)
2. [まず押さえる考え方](#2-まず押さえる考え方)
3. [インストール](#3-インストール)
4. [クイックスタート：15分で1周する](#4-クイックスタート15分で1周する)
5. [開発プロセスの詳細](#5-開発プロセスの詳細)
6. [文書の書き方リファレンス](#6-文書の書き方リファレンス)
7. [テストの書き方](#7-テストの書き方)
8. [`docs/project.md` の設定](#8-docsprojectmd-の設定)
9. [AI エージェントと一緒に使う](#9-ai-エージェントと一緒に使う)
10. [変更・廃止・逸脱の扱い](#10-変更廃止逸脱の扱い)
11. [コマンドリファレンス](#11-コマンドリファレンス)
12. [`saalco check` のメッセージと対処](#12-saalco-check-のメッセージと対処)
13. [トラブルシューティング](#13-トラブルシューティング)
14. [既存プロジェクトの移行](#14-既存プロジェクトの移行)
15. [制限事項](#15-制限事項)

---

## 1. SAALCO とは

SAALCO は、規則を「手で守る」のではなく「機械で確認できる」ようにするための、ローカルで動く CLI である。ネットワークには接続せず、外部の依存ライブラリも持たない（Python 標準ライブラリと Git だけで動く）。

### 1.1 SAALCO がやること

| やること | コマンド |
|---|---|
| 規則に沿ったディレクトリと文書の雛形を置く | `saalco init`、`saalco new feature` |
| ID（`F-001`、`REQ-0001` など）を採番し、台帳に記録する | `saalco new` |
| 人間の承認を、承認者・日時・版・内容hash とともに記録する | `saalco approve` |
| ID の参照切れ、テストの不足、承認後の改変などを検査する | `saalco check` |
| 要求トレーサビリティマトリクス（RTM）を生成する | `saalco trace` |
| 品質ゲートとテストを実行し、commit に紐づく Evidence を残す | `saalco evidence` |
| Feature 単位の Evidence Package（参照の一覧）を作る | `saalco evidence --package` |
| 使わなくなった ID を廃止し、番号を再利用させない | `saalco retire` |

### 1.2 SAALCO がやらないこと

- **要件が正しいかどうか（Validation）は判断しない。** SAALCO が示すのは「書いた要件どおりに作られ、検証された」こと（Verification）までである。作るべきものだったかは人間が判断し、`70-acceptance.md` に記録する。
- **人間が本当に文書を読んだことは証明できない。** 承認は Git の `user.name` と内容hash を記録するが、その人が内容を確認したことまでは暗号的に証明しない。運用上の管理が別途必要である。
- **判定できないものを PASS にしない。** Coverage が取れない、テスト結果が読めない、といった場合は `NOT_EVALUATED` と表示し、合格扱いにはしない。

### 1.3 動作環境

- Python 3.11 以上
- Git
- [uv](https://docs.astral.sh/uv/)（Python プロジェクトで `saalco evidence` を使う場合に必須）
- テスト関連の機能（マーカー、Coverage、RTM の `verified` 判定）は Python（pytest と coverage.py）を前提とする。Python 以外のプロジェクトでも文書管理・採番・承認・静的検査は使えるが、RTM は `NOT_EVALUATED` になる。

---

## 2. まず押さえる考え方

コマンドを覚える前に、次の8つを押さえておくと、`saalco check` のエラーの意味がすぐ分かるようになる。

### 2.1 開発の流れ：Bootstrap → V-cycle → Outcome

```
Bootstrap                 Development V-cycle（Feature ごと）                  Outcome
saalco init       REQ → AD → DD/MD → 試験仕様 → 実装 → ゲート → UT → IT → ST → 受け入れ  → リリース／結果の固定
saalco new feature                                                                         ↓
                    ↑────────────────── 不具合・改善要求・新要求 ──────────────────────────┘
```

全体はアジャイルに回し、1つの Feature の中ではV字モデルで設計→実装→検証を行う。V字の左右は次のように対応する。

| 設計工程 | 文書 | ID | 対応する試験 | 試験仕様 | ID |
|---|---|---|---|---|---|
| 要件定義 | `10-requirements.md` | `REQ` | システム／E2E テスト | `60-system-e2e-spec.md` | `ST` |
| 基本設計 | `20-architecture.md` | `AD` | 結合テスト | `50-integration-test-spec.md` | `IT` |
| 詳細設計 | `30-detailed-design.md` | `DD` | 単体テスト | `40-unit-test-spec.md` | `UT` |
| モジュール設計 | `35-module-design.md` | `MD` | 単体テスト | `40-unit-test-spec.md` | `UT` |

**試験仕様は実装より前に書く。** 試験は上流の文書から作り、実装から作らない。

### 2.2 Feature と Tier

作業の単位は Feature（`F-001` など）で、`docs/features/F-001_<slug>/` に1つのディレクトリを持つ。Feature ごとに規模に応じた Tier を宣言し、Tier によって必要な文書が変わる。

| | Tier S | Tier M | Tier L |
|---|---|---|---|
| 目安 | 単一モジュール内の小機能。外部IFの変更なし | 複数モジュールにまたがる。内部IFの変更あり | 外部IF・データ契約・永続化・HW・他システム連携に影響 |
| 基本設計 `20-` | 不要 | 必須 | 必須 |
| モジュール設計 `35-` | DD に統合 | DD に統合可 | 必須（分離） |
| 結合テスト仕様 `50-` | 不要 | 必須 | 必須 |
| 人間が承認する設計 | REQ・DD | REQ・AD・DD | REQ・AD・DD・MD |

Tier はAIが提案し、人間が承認する（`00-meta.md` を DD と一緒に承認する）。Tier を下げることも設計判断であり、記録の対象になる。

### 2.3 ID は必ずツールで採番する

`F-nnn`、`REQ-nnnn`、`AD-nnnn`、`DD-nnnn`、`MD-nnnn`、`UT-nnnn`、`IT-nnnn`、`ST-nnnn`、`DEV-nnnn` は全て `saalco new` が採番する。**人間も AI も番号を自分で決めない。** 採番の正本は `docs/ids.ledger`（台帳）で、ID はプロジェクト全体で一意（Feature ごとに番号がリセットされない）、廃止した番号は再利用しない。

### 2.4 項目は「covers」と「verify」だけを書く

設計文書の各項目は `### ID: タイトル` の見出しで宣言し、直下に2行だけ書く。

```markdown
### DD-0005: Adapter の共通インターフェース

covers: REQ-0012, REQ-0013
verify: test

（本文）
```

- `covers:` は「この項目がどの上流項目を満たすか」。REQ は起点なので `covers: -`。
- `verify:` は「どう検証するか」。`test`（テストで）、`review`（設計レビュー＝承認で）、`static`（静的検査ゲートで）のどれか。

対応表（RTM）は人が書かない。`covers:` の連鎖とテストのマーカーから SAALCO が生成する。

### 2.5 テストは2種類

| | Specification-derived Test（仕様由来テスト） | Implementation-aware Test（実装参照テスト） |
|---|---|---|
| 作り方 | 上流文書と公開IF（シグネチャ・型・docstring）**だけ**を見て作る | 実装を見て作ってよい |
| マーカー | `@pytest.mark.verifies("DD-0005")` | `@pytest.mark.impl_aware` |
| 検証充足に数えるか | 数える | 数えない |

実装を見て書いたテストを `verifies` にすると、実装の誤りをテストが写し取ってしまう（自己採点）。**迷ったら `impl_aware` にする。**

### 2.6 承認と改変検知

人間は `saalco approve <ファイル>` を実行するだけで承認できる。SAALCO が文書ヘッダに `status: approved`、承認者、日時、版、内容の SHA-256 を書き込む。承認後に文書を1文字でも変えると `saalco check` がhashの不一致を検出してエラーにするので、「承認された設計」と「実際の設計」がずれたまま進むことはない。

### 2.7 Evidence

`saalco evidence` は、品質ゲート（format・lint・型検査など）とテストを実行し、その結果を**特定の commit に紐づけて** `evidence/<commit>/<run-id>/manifest.json` と `summary.md` に保存する。ログや Coverage データなどの生データは `.saal/artifacts/` に置き、Git では管理しない。

Evidence はあとから「その commit でどのテストが何を検証して PASS したか」を確認できるようにするための記録である。「PASS しました」という一言だけでは証拠として扱わない。

### 2.8 人間の介入点（H1〜H6）

規則は、人間が関わる場所を次の6点に絞っている。これ以外は AI とツールで進めてよい。

| # | 介入点 | 人間がやること | 記録 |
|---|---|---|---|
| H1 | 要件定義 | 要件を決める | `saalco approve 10-requirements.md` |
| H2 | 基本設計 | 構造を決める（Tier M 以上） | `saalco approve 20-architecture.md` |
| H3 | 詳細設計 | 設計判断・Tier・検証方法を承認する | `saalco approve 00-meta.md 30-detailed-design.md`（Tier L は `35-module-design.md` も） |
| H4 | 依存・逸脱 | 依存の追加・更新、設計に無い副作用、規則からの逸脱を承認する | PR 上の承認、`90-deviations.md` |
| H5 | ST/E2E | 自動化できない試験を実施する | `60-system-e2e-spec.md` に結果を記録 |
| H6 | 受け入れ | 作ったものを受け入れるか判断する（Validation） | `70-acceptance.md` |

---

## 3. インストール

### 3.1 前提ツールを入れる

```bash
python3 --version
```

```bash
git --version
```

uv が無ければ公式手順で入れる。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3.2 SAALCO を入れる

このリポジトリを取得し、ルートで `uv tool install` を実行する。`saalco` と `saal` の2つのコマンドが PATH に入る。

```bash
git clone https://github.com/ruri-sayo/saal_cording_rule.git
```

```bash
cd saal_cording_rule
```

```bash
uv tool install .
```

確認する。

```bash
saalco --version
```

`saalco 1.0.0` と表示されれば完了である。

- 更新するときは、リポジトリを `git pull` したあと `uv tool install --reinstall .` を実行する。
- `dist/` にある wheel を使う場合は `uv tool install dist/saalco-1.0.0-py3-none-any.whl` でもよい。
- pip を使う場合は `pip install .` でもよい（仮想環境の中で行う）。

### 3.3 Git の名前を設定する

`saalco approve` は `git config user.name` を承認者として記録する。未設定だと承認できない。

```bash
git config --global user.name "your-name"
```

---

## 4. クイックスタート：15分で1周する

摂氏を華氏に変換する小さな機能を、Tier S で1周させる。ここに書いたコマンドと出力は、実際に実行して確認したものである。

### 4.1 プロジェクトを作る

```bash
mkdir demo && cd demo
```

```bash
saalco init --name demo --type system --language python --non-interactive
```

```
WARNING uv.lock not found. Run `uv lock` and commit uv.lock before `saalco evidence`.
Initialized SAALCO project.
```

`uv.lock` の WARNING はこの時点では正常である（4.5 で作る）。次の構造ができる。

```
demo/
  AGENTS.md                  # AI エージェント向けの作業指示
  pyproject.toml             # pytest マーカーの登録だけが入っている
  .gitignore                 # .saal/ などを除外
  docs/
    project.md               # 種別・品質ゲート・テストコマンド
    ids.ledger               # ID 台帳（空）
    rules/SAAL-DEV-RULES.md  # 適用する規則のコピー
    input/  architecture/  features/  trace/
  evidence/
  src/
  tests/unit/  tests/integration/  tests/e2e/
  .saal/artifacts/           # Git 管理外
```

Git リポジトリが無ければ `git init` も行われる。

### 4.2 `pyproject.toml` を整える

`saalco init` が作る `pyproject.toml` には pytest マーカーの登録しか入っていない。uv で依存を固定するため、`[project]` と開発用の依存を追加する。次は動作確認済みの完成形である。

```toml
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = ["pytest>=8", "pytest-cov>=5", "ruff>=0.6", "mypy>=1.11"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/demo"]

[tool.pytest.ini_options]
markers = [
  "verifies(id, spec=None): specification-derived test",
  "impl_aware(id=None): implementation-aware test",
]

[tool.coverage.run]
source = ["src"]
patch = ["subprocess"]
```

`[tool.coverage.run]` の `patch = ["subprocess"]` は、E2E テストが `subprocess` で起動したプロセスの Coverage も測るための設定である（coverage.py 7.10 以降）。これが無いと、E2E からしか通らない行が未実行扱いになり、Coverage 基準を満たせないことがある。

### 4.3 Feature と項目を作る

```bash
saalco new feature "Temperature conversion" --tier S
```

```
F-001
```

`docs/features/F-001_temperature-conversion/` に Tier S の文書一式ができる。続けて項目を採番する。出力されるのは採番された ID である。

```bash
saalco new req --feature F-001 "摂氏を華氏に変換できる"
```

```bash
saalco new dd --feature F-001 "celsius_to_fahrenheit 関数"
```

```bash
saalco new ut --feature F-001 "変換式の単体試験"
```

```bash
saalco new st --feature F-001 "CLI からの変換"
```

```
REQ-0001
DD-0001
UT-0001
ST-0001
```

この時点で `saalco check` を実行すると、まだ中身を書いていないのでエラーが並ぶ。これは「あと何を書けばよいか」の一覧として読める。

```bash
saalco check
```

```
ERROR docs/features/F-001_temperature-conversion/30-detailed-design.md DD-0001: covers is empty
ERROR docs/features/F-001_temperature-conversion/40-unit-test-spec.md UT-0001: covers is empty
ERROR docs/features/F-001_temperature-conversion/60-system-e2e-spec.md ST-0001: covers is empty
ERROR REQ-0001: no Specification-derived verifies test
ERROR DD-0001: no Specification-derived verifies test
ERROR DD-0001: no UT specification covers this item
WARNING REQ-0001: not covered by a downstream item
WARNING DD-0001: not covered by a downstream item
6 errors, 2 warnings
```

### 4.4 文書を書く

各ファイルの `covers:` を埋め、本文を書く。**ヘッダ（`---` で囲まれた部分）は触らない。**

`00-meta.md` の `## Overview` の下：

```markdown
## Overview

摂氏から華氏への変換関数と CLI を提供する。単一モジュールで外部IFを持たないため Tier S とする。
```

`10-requirements.md`：

```markdown
### REQ-0001: 摂氏を華氏に変換できる

covers: -
verify: test

`python -m demo.convert 100` を実行すると、標準出力に `212.0` を表示する。
```

`30-detailed-design.md`：

```markdown
### DD-0001: celsius_to_fahrenheit 関数

covers: REQ-0001
verify: test

`demo.convert.celsius_to_fahrenheit(c: float) -> float` は `c * 9 / 5 + 32` を返す。
```

`40-unit-test-spec.md`：

```markdown
### UT-0001: 変換式の単体試験

covers: DD-0001
verify: test

- 0 → 32.0、100 → 212.0、-40 → -40.0 となること。
```

`60-system-e2e-spec.md`：

```markdown
### ST-0001: CLI からの変換

covers: REQ-0001
verify: test

- `python -m demo.convert 100` の標準出力が `212.0` であること。
```

### 4.5 人間が承認する（H1・H3）

Tier S で人間が承認するのは REQ と DD、それに Tier 宣言（`00-meta.md`）である。**これは人間がターミナルで直接実行する**（AI エージェントには実行させない）。

```bash
saalco approve docs/features/F-001_temperature-conversion/00-meta.md docs/features/F-001_temperature-conversion/10-requirements.md docs/features/F-001_temperature-conversion/30-detailed-design.md
```

承認後の `30-detailed-design.md` のヘッダは次のようになる。

```
---
kind: DD
feature: F-001
status: approved
approved_by: your-name
approved_at: 2026-09-27T21:17:20+09:00
version: 1
approved_hash: e2c345237dfea7545ff8db4c4c42f4aed04bee3e9a1155acda7d0f38413e0064
---
```

### 4.6 テストと実装を書く

先に仕様由来テストを書く。入力は上の文書と公開IFだけである。

`tests/unit/test_convert.py`：

```python
import pytest

from demo.convert import celsius_to_fahrenheit


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.parametrize(("c", "f"), [(0, 32.0), (100, 212.0), (-40, -40.0)])
def test_celsius_to_fahrenheit(c, f):
    assert celsius_to_fahrenheit(c) == f
```

`tests/e2e/test_cli.py`：

```python
import subprocess
import sys

import pytest


@pytest.mark.verifies("REQ-0001", spec="ST-0001")
def test_cli_prints_fahrenheit():
    out = subprocess.run(
        [sys.executable, "-m", "demo.convert", "100"], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "212.0"
```

実装 `src/demo/__init__.py`（空ファイル）と `src/demo/convert.py`：

```python
"""Temperature conversion.

Responsibilities:
- Convert Celsius to Fahrenheit and expose it as a small CLI.
"""

import sys


def celsius_to_fahrenheit(c: float) -> float:
    """Return the Fahrenheit value for a Celsius temperature."""
    return c * 9 / 5 + 32


def main(argv: list[str] | None = None) -> int:
    """Print the converted value of the first argument."""
    args = sys.argv[1:] if argv is None else argv
    print(celsius_to_fahrenheit(float(args[0])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 4.7 検査・ロック・テスト

```bash
saalco check
```

```
0 errors, 0 warnings
```

```bash
uv lock
```

```bash
uv run ruff format .
```

```bash
uv run pytest
```

### 4.8 Tier S 用にゲートを調整する

Tier S には結合テストが無く、`tests/integration/` が空のままだと pytest が「テストが1件も無い」（終了コード5）で終わり、ゲートが FAIL になる。`docs/project.md` の `test.integration:` の値を空にして、実行しないようにする。

```
test.integration:
```

値が空のゲートは `NOT_CONFIGURED` になり、FAIL にはならない（PASS にもならない）。

### 4.9 commit して Evidence を取る

Evidence は作業ツリーがクリーンなときしか取れない。全て commit してから実行する。

```bash
git add -A && git commit -m "F-001: design, tests, implementation"
```

```bash
saalco evidence
```

```
Created evidence/caabd4bb34004f2b47c8a372e2908373f7f09a16/20260927T211745/manifest.json
Overall: PASS
Commit evidence/ and docs/trace/.
```

`summary.md` には各ゲートの結果、テストの件数、Coverage が並ぶ。

```
## Gates
- format: PASS
- lint: PASS
- typecheck: PASS
- secret_scan: NOT_CONFIGURED
- dependency_audit: NOT_CONFIGURED
- static_analysis: NOT_CONFIGURED
- saalco-check: PASS
- test.unit: PASS
- test.e2e: PASS

## Coverage
- Total: 100.0
- Diff: 100.0
- Status: PASS
```

出力の指示どおり、生成物を commit する。

```bash
git add evidence docs/trace && git commit -m "Record evidence"
```

続けて RTM を生成し直し、commit する。`saalco evidence` が書き出す RTM は、Evidence がまだ commit されていない時点で作られるので、要件が `stale` になっている。Evidence を commit した後に `saalco trace` を実行すると、その Evidence をもとに `verified` の RTM になる。

```bash
saalco trace
```

```bash
git add docs/trace && git commit -m "Sync RTM to evidence"
```

`docs/trace/` の変更だけなので、この commit で Evidence が current でなくなることはない。

### 4.10 検証まで含めて検査する

```bash
saalco check --verification
```

```
WARNING src/demo/__init__.py: reached by no verifies test
WARNING gate.04.secret_scan: NOT_CONFIGURED
WARNING gate.05.dependency_audit: NOT_CONFIGURED
0 errors, 3 warnings
```

エラーが0件なら、要件は `verified` になっている。RTM で確かめる。

```bash
cat docs/trace/rtm.md
```

| req_id | requirement | feature | design_ids | impl_files | unit_tests | e2e_tests | verify_status |
|---|---|---|---|---|---|---|---|
| REQ-0001 | 摂氏を華氏に変換できる | F-001 | DD-0001 | src/demo/convert.py | tests/unit/test_convert.py::test_celsius_to_fahrenheit | tests/e2e/test_cli.py::test_cli_prints_fahrenheit | verified |

（実際の表には `integration_tests` と `evidence_commit` の列もある。）

WARNING はエラーではないが、Secret Scan と Dependency Audit は規則上「常時実行」とされているので、実プロジェクトでは設定すること（8.2 参照）。

### 4.11 受け入れと Evidence Package

最後に人間が `70-acceptance.md` に受け入れ判断を書き（H6）、Evidence Package を作る。

```bash
saalco evidence --package F-001
```

`.saal/packages/F-001/index.md` と `package.json` ができる。要件定義書、RTM、manifest、承認記録、逸脱記録、差分レポートへの参照の一覧である（内容のコピーは作らない）。

以上で1周である。

---

## 5. 開発プロセスの詳細

クイックスタートを、実際の開発で使う粒度で工程ごとに説明する。各工程の「誰が」は、規則の役割分担に従う。

### 5.1 Bootstrap：プロジェクトを始める

```bash
saalco init --name <名前> --type <research|system> --language <python|other>
```

- `--type`：`research`（再現可能な研究結果が最終成果）か `system`（運用されるシステムが最終成果）か。`80-outcome.md` の記録項目が変わる。
- `--language`：`python` なら Evidence でテスト・Coverage・`uv.lock` の確認を行う。`other` ならそれらを行わず、RTM は `NOT_EVALUATED` になる。
- `--spec <ファイル>`：人間が書いた原仕様書を `docs/input/` にコピーする。複数指定できる。`docs/input/` の文書は以後変更しない。要件などはそこから導出して `docs/features/` に書く。
- オプションを省略すると対話的に聞かれる。スクリプトや CI では `--non-interactive` を付ける（必須値が無いとエラーになる）。
- 既にあるファイルは上書きしない。上書きしなかったものは `WARNING not overwritten: ...` と表示される。既存の `pyproject.toml` がある場合は、追加すべき pytest マーカーの設定が表示されるので、手で追記する。

その後、4.2 のように `pyproject.toml` を整え、`uv lock` して `uv.lock` を commit する。

### 5.2 Feature を登録する

```bash
saalco new feature "<タイトル>" --tier <S|M|L> [--slug <slug>]
```

- ディレクトリ名は `F-nnn_<slug>` になる。slug はタイトルから自動生成するが、タイトルが日本語などで ASCII の slug が作れない場合は `--slug` が必要になる（対話モードなら入力を求められる）。slug は `^[a-z0-9][a-z0-9-]*$` に合う必要がある。

```bash
saalco new feature "ログイン" --tier M --slug login
```

- Tier に応じて必要な文書が一度に作られる。

| ファイル | S | M | L |
|---|:-:|:-:|:-:|
| `00-meta.md`（Tier・概要） | ○ | ○ | ○ |
| `10-requirements.md` | ○ | ○ | ○ |
| `20-architecture.md` | | ○ | ○ |
| `30-detailed-design.md` | ○ | ○ | ○ |
| `35-module-design.md` | | | ○ |
| `40-unit-test-spec.md` | ○ | ○ | ○ |
| `45-implementation-diff.md`（設計との差分レポート） | ○ | ○ | ○ |
| `50-integration-test-spec.md` | | ○ | ○ |
| `60-system-e2e-spec.md` | ○ | ○ | ○ |
| `70-acceptance.md`（受け入れ判断） | ○ | ○ | ○ |
| `80-outcome.md`（成果） | ○ | ○ | ○ |
| `90-deviations.md`（逸脱記録） | ○ | ○ | ○ |

- Tier に必要なファイルを消すと `saalco check` が `required for Tier X` でエラーにする。
- `00-meta.md` の `## Overview` に、Feature の概要と Tier をそう判断した理由を書く。

### 5.3 要件を書く（H1）

**主担当：人間**（AI は整理、抜け漏れの指摘、選択肢の提示を補助する）

```bash
saalco new req --feature F-001 "<要件のタイトル>"
```

- 1要件は1つの**検証可能な**主張にする。「〜が望ましい」「使いやすい」のように合否を判定できない書き方は要件にしない。
- REQ は `covers: -`、`verify: test`（ST/E2E で検証）が原則。`review`/`static` にする場合は理由を本文に書く。
- 書き終えたら人間が承認する。

```bash
saalco approve docs/features/F-001_login/10-requirements.md
```

### 5.4 基本設計を書く（H2、Tier M 以上）

**主担当：人間＋AI　承認：人間**

```bash
saalco new ad --feature F-001 "<設計項目>"
```

構成、主要コンポーネント、責務の分割、通信方式、データフロー、外部との境界を決める。AD は `covers:` に REQ を書く。複数の Feature にまたがる全体設計は `docs/architecture/` に置く。

```bash
saalco approve docs/features/F-001_login/20-architecture.md
```

### 5.5 詳細設計・モジュール設計を書く（H3）

**主担当：AI　承認：人間**

```bash
saalco new dd --feature F-001 "<設計項目>"
```

```bash
saalco new md --feature F-001 "<モジュール>"
```

クラス構成、状態管理、主要インターフェース、処理フロー、例外処理を書く。MD は各モジュール・クラス・主要関数の責務、入出力、依存、制約を書く（Tier S/M では DD に統合してよい）。

人間は H3 でコードの代わりに次を確認する。

- 責務の分割が適切か
- 不自然な依存関係が無いか
- 状態の所有者が明確か
- 将来の変更を妨げる構造になっていないか
- 各項目の `verify:`（`test`/`review`/`static`）が妥当か
- Tier の判断が妥当か

```bash
saalco approve docs/features/F-001_login/00-meta.md docs/features/F-001_login/30-detailed-design.md
```

### 5.6 試験仕様を書く

**主担当：AI**（人間の個別承認は不要。網羅は `saalco check` が機械的に確認する）

設計の承認後、**実装に着手する前に**書く。

```bash
saalco new ut --feature F-001 "<単体試験>"
```

```bash
saalco new it --feature F-001 "<結合試験>"
```

```bash
saalco new st --feature F-001 "<システム／E2E試験>"
```

| 試験仕様 | 導出元 | `covers:` に書けるもの |
|---|---|---|
| UT（`40-unit-test-spec.md`） | DD / MD | DD、MD |
| IT（`50-integration-test-spec.md`） | AD | AD |
| ST（`60-system-e2e-spec.md`） | REQ | REQ |

`verify: test` の DD/MD には、それを `covers:` する UT が最低1つ必要である（無いと `no UT specification covers this item`）。

自動化できない ST（実機での確認、目視確認、操作感など）は、人間が実施して結果を記録する（H5、6.6 参照）。

### 5.7 テストを書き、実装する

**主担当：AI**

1. 仕様由来テストを、**実装コードを見ない別のコンテキスト**（別セッション、別エージェントなど）で、上流文書と公開IFだけから書く。書き方は第7章。
2. 承認済みの設計に従って実装する。
3. 実装を見て追加したいテスト（境界値、分岐網羅、回帰など）は `impl_aware` にする。

実装中、次のことは人間の承認（H4）が要る。勝手に進めない。

- 依存ライブラリの追加・更新（`uv.lock` の変更を含む）
- 設計文書に無い外部通信・ファイル書き込み・永続化・実機駆動の追加
- 設計からの逸脱

### 5.8 設計との差分レポートを書く

実装が終わったら `45-implementation-diff.md` に、設計と実装のずれを書く。

```markdown
## Implemented but not designed

- `main()` で引数が無い場合のエラー処理を追加した（設計に記載なし）。

## Designed but not implemented

- なし
```

全コードレビューの代わりに、設計と実装の乖離を安く見つけるための記録である。ずれが設計の変更を意味する場合は、設計文書を改訂して再承認する（10.1）。

### 5.9 検査して commit する

```bash
saalco check
```

エラーが0件になるまで直す。**エラーを消すためにマーカー・`verify:`・`status` を事実と違う値に書き換えてはいけない。** 規則を満たせないまま進む場合は逸脱として記録する（10.3）。

```bash
git add -A && git commit -m "F-001: ..."
```

規則上、設計の変更を伴う実装は、設計文書の更新と同じ commit（または PR）に含める。

### 5.10 Evidence を記録する

```bash
saalco evidence
```

実行される順番は次のとおり。

1. 作業ツリーがクリーンかを確認（汚れていれば中止、exit 3）
2. `language: python` なら `uv.lock` が存在し、Git 管理され、最新かを確認（満たさなければ中止、exit 2）
3. `docs/project.md` の `gate.*` を番号順に実行
4. `saalco check`（静的検査）
5. `test.unit` → `test.integration` → `test.e2e` を実行（Coverage と JUnit XML を自動で取る）
6. Coverage を計算
7. `evidence/<commit>/<run-id>/manifest.json`・`summary.md` と `docs/trace/rtm.*` を書き出す

- `uv run ...` で始まるコマンドには自動で `--locked` が付く。Evidence の実行中に `uv.lock` が書き換わることはない。
- 途中のステップが追跡対象のファイルを変更した（例：formatter がファイルを書き換えた）場合、そのステップは FAIL になる。
- `Overall: PASS` の条件は、全ゲートが PASS か NOT_CONFIGURED で、Coverage が PASS であること。FAIL でも manifest は作られ、exit 1 で終わる。

終わったら、生成物を**別の commit** で追加する。

```bash
git add evidence docs/trace && git commit -m "Record evidence"
```

その後、RTM を生成し直して commit する。`saalco evidence` の途中で書き出す RTM は、Evidence がまだ commit されていない時点のものなので、要件が `stale` になっている。

```bash
saalco trace
```

```bash
git add docs/trace && git commit -m "Sync RTM to evidence"
```

Evidence は対象 commit そのものには入れられないので、後続の commit に入れる。対象 commit から HEAD までの変更が `evidence/`・`docs/trace/`・`docs/ids.ledger` だけなら、その Evidence は HEAD に対しても有効（current）とみなされる。コードや文書を1つでも変えたら、Evidence を取り直す。

### 5.11 検証を確認する

```bash
saalco check --verification
```

静的検査に加えて、次を確認する。

- current な Evidence があるか
- `verifies` テストが全て PASS したか
- 品質ゲートに FAIL/ERROR が無いか
- Coverage が PASS か
- 実装に到達したテストが、承認済み（かつ改変されていない）DD/MD を検証しているか
- RTM の全 REQ が `verified` か

### 5.12 受け入れ判断（H6）

**人間だけが行う。** ST/E2E が PASS したことは「要件定義書に書いたとおりのものができた」ことを示すにすぎない。作るべきものだったかを人間が判断し、`70-acceptance.md` に書く。AI はこのファイルを「accepted」「PASS」などに書き換えない。

規則は、次の工夫を推奨している（必須ではない）。

- 要件定義書だけを AI に渡し、設計意図を伝えない状態で、要件と実装のずれを監査させる
- 要件定義と受け入れ判断の間に時間を置く

### 5.13 Outcome

`80-outcome.md` に記録する。

- `system`：リリースバージョン、対象commit、デプロイ先、リリース日。リリースは Evidence Package が揃った commit に対してのみ行う。
- `research`：コードcommit（Evidence 記録済みのもの）、データセットバージョン、モデル、設定、乱数シード、実行環境、結果の所在、結果hash。再実験した場合は新しい記録を追加し、既存の記録を上書きしない。

```bash
saalco evidence --package F-001
```

運用や実験から出た不具合・改善要求・新要求は、新しい REQ または REQ の改訂として V-cycle の入口に戻す。

---

## 6. 文書の書き方リファレンス

### 6.1 文書ヘッダ

```
---
kind: DD
feature: F-001
status: draft
---
```

- ネスト、リスト、クオートは使えない。フラットな `key: value` だけである。
- `status` は `draft` / `approved` / `superseded`。
- `version`、`approved_by`、`approved_at`、`approved_hash` は `saalco approve` だけが書く。人間も AI も手で編集しない。
- `00-meta.md` には `tier: S|M|L` が必要。

### 6.2 項目

```markdown
### <ID>: <タイトル>

covers: <上流ID>, <上流ID>
verify: test

本文
```

- 見出しは `###` で、`ID: タイトル` の形。ID は `saalco new` が書いたものをそのまま使う。
- `covers:`・`verify:` などのメタ情報行は見出しの直下に置く。
- 見出し、キー名、ID は日本語に訳さない（SAALCO が文字列で照合するため）。本文は日本語で書く。

### 6.3 `covers:` に書ける参照

| 項目 | `covers:` に書けるもの |
|---|---|
| REQ | `-` のみ |
| AD | REQ |
| DD | AD、REQ |
| MD | DD、AD、REQ |
| UT | DD、MD |
| IT | AD |
| ST | REQ |

これ以外を書くと `cannot cover` エラー、存在しない ID は `unknown covers ID` エラー、循環すると循環エラーになる。

### 6.4 `verify:` の種類と充足条件

| 値 | 使う場面 | 充足条件 |
|---|---|---|
| `test`（既定） | 振る舞いをテストで確かめられる | `verifies` テストが1件以上あり、current な Evidence で全て PASS |
| `review` | 構造・方針などの設計判断 | その文書が承認済みで、承認後に改変されていない |
| `static` | lint や型検査などで担保できる | `static:` 行で指定したゲートが current な Evidence で PASS |

`verify:` を省略すると `test` とみなす。テストで検証するのは `verify: test` の項目だけでよい。設計判断そのものを無理にテストしない。

`static` の例：

```markdown
### DD-0010: 全モジュールに docstring を書く

covers: REQ-0003
verify: static
static: lint

ruff の `D` ルールで docstring の有無と書式を検査する。
```

`static:` の値は `docs/project.md` の `gate.NN.<名前>` の `<名前>` 部分（`format`、`lint`、`typecheck` など）である。

### 6.5 REQ から ST までの例（Tier M）

```markdown
<!-- 10-requirements.md -->
### REQ-0002: 正しいパスワードでログインできる
covers: -
verify: test

<!-- 20-architecture.md -->
### AD-0001: 認証は AuthService に集約し、Web 層はトークンだけを扱う
covers: REQ-0002
verify: test

<!-- 30-detailed-design.md -->
### DD-0003: AuthService.login(user, password) -> Token
covers: AD-0001
verify: test

### DD-0004: パスワードは argon2 でハッシュ化する
covers: AD-0001
verify: review

<!-- 40-unit-test-spec.md -->
### UT-0003: login の正常系・異常系
covers: DD-0003
verify: test

<!-- 50-integration-test-spec.md -->
### IT-0001: Web 層から AuthService を経由したログイン
covers: AD-0001
verify: test

<!-- 60-system-e2e-spec.md -->
### ST-0002: ブラウザからログインしてトップ画面が表示される
covers: REQ-0002
verify: test
```

この場合、REQ-0002 が `verified` になるには、REQ-0002・AD-0001・DD-0003 のそれぞれに PASS した `verifies` テストがあり、DD-0004 の文書が承認済みで改変されていないことが必要である。

### 6.6 人間が実施した ST（H5）

自動化できない試験は、人間が実施して ST 項目に結果を書く。

```markdown
### ST-0003: 実機での起動確認

covers: REQ-0012
method: manual
result: PASS
commit: <実施した commit のフルhash>
executed_by: your-name
executed_at: 2026-09-27
```

`commit` が current Evidence の対象 commit と同じ扱いになる場合（その後の変更が `evidence/`・`docs/trace/`・`docs/ids.ledger` だけの場合）に、この結果を REQ の検証充足に数える。コードを変えたら実施し直す。

Tier S の簡易記録でも、commit hash と日付は省略しない。

### 6.7 逸脱記録（DEV）

規則を満たさずに進める場合は、必ず記録する。**記録の無い逸脱は認めない。**

```bash
saalco new dev --feature F-001 "<逸脱の内容>"
```

`90-deviations.md` に雛形が追記されるので、人間の判断をもとに埋める。

```markdown
### DEV-0002: 外部 API の結合テストを一時的に省略する

rule: 7.3
scope: F-001, src/demo/external/
status: open
reason: 外部 API のテスト環境が用意できるまで、該当行の Coverage が取れないため
resolution: テスト環境の用意後に結合テストを追加する
end_condition: 結合テストを追加し、差分 Coverage が 80% 以上になった時点で終了
decided_by: your-name
decided_at: 2026-09-27
```

| 欄 | 意味 |
|---|---|
| `rule` | 逸脱した規則の条項番号。カンマ区切りで複数書ける |
| `scope` | 影響範囲。Feature ID、項目 ID、ファイルパスの先頭部分をカンマ区切りで書く |
| `status` | `open`（逸脱が続いている）か `closed`（終了条件を満たした）。それ以外はエラー |
| `reason` / `resolution` / `end_condition` | 理由、解消の予定、終了条件 |
| `decided_by` / `decided_at` | 判断した人と日付（人間が記入する） |

`status: open` の DEV は、次の規則番号のエラーを WARNING に下げる。`rule` と `scope` が該当するものだけが対象である。

| `rule` | 下がるエラー |
|---|---|
| `4.6` | 承認されていない（または承認後に改変された）設計に対応する実装がある、Coverage の測定コンテキストが得られない |
| `6.4` | `verifies` テストが PASS していない |
| `6.8` | RTM の REQ が `verified` になっていない |
| `7.1` | 品質ゲートが FAIL/ERROR |
| `7.3` | Coverage が基準を満たしていない |

逸脱が解消したら、人間が `status: closed` にし、`closed_at`（閉じた日付）と `closed_condition`（満たした終了条件）を書く。どちらかが無い `closed` の DEV はエラーになる。`closed` の DEV はエラーを下げない。

### 6.8 受け入れ判断・成果

- `70-acceptance.md`：人間の判断の記録。規則が担保する証拠ではない。書式は自由だが、判断者・日付・対象 commit・判断内容を書いておくとよい。
- `80-outcome.md`：雛形に並んだ項目（`- リリースバージョン:` など）を埋める。

---

## 7. テストの書き方

### 7.1 マーカー

```python
import pytest

@pytest.mark.verifies("DD-0005")                  # 単体テスト → DD/MD
def test_adapter_interface(): ...

@pytest.mark.verifies("AD-0002")                  # 結合テスト → AD
def test_bridge_adapter_wiring(): ...

@pytest.mark.verifies("REQ-0012", spec="ST-0004") # E2E → REQ（試験仕様も指定）
def test_caller_is_model_agnostic(): ...

@pytest.mark.impl_aware                           # 補助テスト（充足に数えない）
def test_adapter_rejects_empty_path(): ...

@pytest.mark.impl_aware("DD-0005")                # 関連を示してもよいが、充足には数えない
def test_regression_issue_42(): ...
```

- 第1引数は検証する設計・要件の ID。`spec=` は任意で、そのテストが実装している試験仕様（UT/IT/ST）の ID を書く。存在しない ID を書くとエラーになる。
- `from pytest import mark` として `@mark.verifies(...)` と書いてもよい。
- クラスに付けたマーカーはそのメソッド全てに、モジュールの `pytestmark = pytest.mark.verifies("DD-0005")` はそのファイルのテスト全てに適用される。関数に直接付けたものが優先される。
- マーカーの無いテストは `impl_aware` として扱われる。
- 1つのテストに `verifies` を複数付けてもよい。
- マーカーは AST で静的に読むので、ID は文字列リテラルで書く（変数や f-string は読めない）。
- `parametrize` したテストは、全ケースが PASS したときだけ PASS になる。

### 7.2 置き場所

| ディレクトリ | 種別 | 参照すべき ID |
|---|---|---|
| `tests/unit/` | 単体テスト | DD、MD |
| `tests/integration/` | 結合テスト | AD |
| `tests/e2e/` | システム／E2E テスト | REQ |

ディレクトリと参照先の種別が合わない場合は WARNING になる。ファイル名は `test_*.py` にする。`tests/fixtures/` 以下は読まない。

### 7.3 仕様由来テストを書く条件

- 実装コードを参照しないコンテキストで書く。AI に書かせるなら、別のセッションやサブエージェントを使い、渡すのは上流文書と公開IF（シグネチャ・型・docstring）だけにする。
- 実装後に追加する場合も同じ条件を守る。
- 守れなかったテストは `impl_aware` にする。ツールではこの条件を強制できないので、分類は正直に行う。

### 7.4 Coverage

`saalco evidence` は pytest に `--cov=src --cov-context=test` を自動で付けて実行する。自分で付ける必要は無い。

- **差分 Coverage**：前回 PASS した Evidence（HEAD の祖先で最も近いもの）から変わった `src/` の行のうち、80% 以上が実行されていること。
- **全体 Coverage**：前回の Evidence の値より下がっていないこと。
- 両方を満たせば PASS。取れなかった場合は `NOT_EVALUATED`（PASS ではない）。
- 満たせない場合は DEV（`rule: 7.3`）を記録すれば WARNING として通過できる。

---

## 8. `docs/project.md` の設定

### 8.1 既定値

```
---
kind: PROJECT
name: demo
type: system
language: python
saal_rules_version: 1.1
saalco_version: 1.0.0
raw_evidence_location: .saal/artifacts
raw_evidence_retention: until next release
gate.01.format: uv run ruff format --check .
gate.02.lint: uv run ruff check .
gate.03.typecheck: uv run mypy src
gate.04.secret_scan:
gate.05.dependency_audit:
gate.06.static_analysis:
test.unit: uv run pytest tests/unit
test.integration: uv run pytest tests/integration
test.e2e: uv run pytest tests/e2e
---
```

| キー | 意味 |
|---|---|
| `type` / `language` | `saalco init` で指定した値 |
| `saal_rules_version` | 適用している規則の版。`1.0` か `1.1` のみ対応。規則の改訂は既存プロジェクトに自動では適用されない |
| `raw_evidence_location` / `raw_evidence_retention` | 生データの退避先と保持期間。プロジェクトで決めて書く |
| `gate.NN.<名前>` | 品質ゲート。`NN` の順に実行する。値が空なら `NOT_CONFIGURED` |
| `test.unit` / `test.integration` / `test.e2e` | テストの実行コマンド。値が空なら実行しない |

### 8.2 ゲートを設定する

Secret Scan と Dependency Audit は、規則上は常時実行とされている。空のままだと `check --verification` で WARNING が出続ける。例：

```
gate.04.secret_scan: gitleaks detect --no-banner
gate.05.dependency_audit: uv run pip-audit
```

ゲートのツールを追加することは依存の追加にあたるので、H4 の承認を得る。ゲートを追加・削除してもよい（`gate.07.xxx:` など）。ゲートのコマンドが作業ツリーのファイルを書き換えると FAIL になるので、formatter は `--check` のように書き換えないモードで使う。

### 8.3 Tier S のプロジェクト

結合テストが無い場合は、`test.integration:` を空にする（4.8）。

### 8.4 E2E テストの Coverage

E2E テストがサブプロセスで CLI を起動する場合、`pyproject.toml` に次を入れておくと、サブプロセス側の実行も Coverage に数えられる（coverage.py 7.10 以降）。

```toml
[tool.coverage.run]
source = ["src"]
patch = ["subprocess"]
```

---

## 9. AI エージェントと一緒に使う

SAALCO は、人間と AI エージェント（Claude Code、Codex など）が一緒に使うことを前提にしている。

### 9.1 `AGENTS.md`

`saalco init` はプロジェクト直下に `AGENTS.md` を置く。エージェントが守るべきことが書いてある。

- ID は手で採番しない。`saalco new` を使う。
- `saalco approve` は実行しない。承認が必要になったら、承認対象のパスを並べて人間に頼み、そこで止まる。
- `70-acceptance.md` を accepted や PASS に書き換えない。
- 仕様由来テストは上流文書と公開IFだけから作る。それ以外は `impl_aware`。
- 依存の追加・設計に無い副作用は、人間の承認（H4）を得てから。
- 完了を主張する前に `saalco check` を実行し、Evidence を取る前に全て commit する。
- check を通すために、マーカー・verify・status を事実と違う値に変えない。

Claude Code を使う場合は、`CLAUDE.md` に `@AGENTS.md` と書いて読み込ませる（このリポジトリの `CLAUDE.md` が例である）。

### 9.2 役割分担

| 工程 | 人間 | AI エージェント |
|---|---|---|
| Feature 登録・Tier | Tier を承認 | Tier を提案し、`saalco new feature` を実行 |
| 要件 | 決める・承認する | 整理・抜け漏れの指摘 |
| 基本設計 | 方向を決める・承認する | 案を作る |
| 詳細設計・モジュール設計 | 承認する | 書く |
| 試験仕様・テスト・実装 | （結果とゲート通過を確認） | 書く |
| `saalco check` / `evidence` / `trace` | 結果を見る | 実行する |
| `saalco approve` | **実行する** | 実行しない |
| DEV の判断・closed への変更 | **判断・記入する** | 雛形を作り、判断を依頼する |
| 受け入れ判断 | **判断・記入する** | 触らない |

### 9.3 典型的な依頼の流れ

1. 人間：「`docs/input/spec.md` をもとに、ログイン機能を Feature として登録して、要件を書いて」
2. AI：`saalco new feature ... --tier M`、`saalco new req ...` を実行し、要件を書く。「次の文書の承認をお願いします」とパスを並べて止まる。
3. 人間：内容を確認し、`saalco approve ...` を実行する。
4. AI：基本設計・詳細設計を書き、承認を依頼して止まる。
5. 人間：確認して承認する。
6. AI：試験仕様を書く。別コンテキストで仕様由来テストを書く。実装し、`45-implementation-diff.md` を書き、`saalco check`、commit、`saalco evidence`、Evidence の commit、`saalco check --verification` まで進める。
7. 人間：結果を確認し、`70-acceptance.md` に受け入れ判断を書く。

承認待ちの一覧を `docs/human-approval-requests.md` のようなファイルにまとめさせると、人間が確認しやすい（このリポジトリで使っている方法）。

### 9.4 仕様由来テストを別コンテキストで書かせる

例えば Claude Code なら、サブエージェントに次のような指示を与える。

> `docs/features/F-001_login/30-detailed-design.md` と `40-unit-test-spec.md`、および `src/app/auth.py` の公開関数のシグネチャと docstring だけを読んで、UT-0003 のテストを `tests/unit/test_auth.py` に書いてください。関数本体の実装は読まないでください。各テストに `@pytest.mark.verifies("DD-0003", spec="UT-0003")` を付けてください。

---

## 10. 変更・廃止・逸脱の扱い

### 10.1 承認済みの文書を変える

1. 文書を編集する。`saalco check` が `approved_hash does not match current content; ask a human to re-approve` を出す。
2. 変更が下流（試験仕様、テスト、実装）に波及するなら、それらも直す。
3. 人間が再承認する。`version` が1つ上がる。

承認済みの文書に `saalco new` で項目を追加すると、その文書は自動で `status: draft` に戻り、承認関連の欄が消える（`WARNING ... approval invalidated; status reset to draft` と表示される）。追加後に再承認する。

既存の Feature を改訂するときは、影響を受ける最も上流の工程からやり直す。影響しない工程の成果物はそのまま使ってよい。

### 10.2 ID を廃止する

使わなくなった項目は、見出しを消す前に ID を廃止する。

```bash
saalco retire REQ-0013 --reason "要件を REQ-0020 に統合" --superseded-by REQ-0020
```

```
Retired REQ-0013.
Remove its item heading and any references from the documents now (otherwise `saalco check` will report the ID as reused/still referenced).
```

このコマンドは `docs/ids.ledger` の該当行を `retired` にするだけで、文書は変更しない。出力のとおり、項目の見出しと、`covers:` やテストマーカーからの参照を自分で消す。台帳の行は削除されず、番号は再利用されない。

### 10.3 欠陥が見つかったとき

1. 原因の工程を分類して記録する：要件漏れ／設計漏れ／実装誤り／テスト漏れ。
2. その工程まで戻る。設計が原因なら設計文書を改訂して再承認する。コードだけ直して設計文書を古いまま残さない。
3. 再発防止の回帰テストを追加する（原則 `impl_aware`）。
4. 要件漏れ・設計漏れなら、仕様由来テストも追加する。
5. 既存の自動テストを全て再実行する（`saalco evidence` が全て実行する）。部分実行だけで完了としない。

### 10.4 規則を守れないまま進める

6.7 のとおり `saalco new dev` で記録する。人間の判断（`decided_by`・`decided_at`）が必要である。終了条件を満たしたら人間が `closed` にする。

---

## 11. コマンドリファレンス

どのコマンドも、カレントディレクトリから上にたどって `docs/project.md` があるディレクトリをプロジェクトのルートとみなす（`init` を除く）。

### `saalco init`

```
saalco init [--name NAME] [--type research|system] [--language python|other]
            [--spec FILE]... [--non-interactive]
```

標準構造と雛形を置く。既存ファイルは上書きしない。Git リポジトリが無ければ `git init` する。

### `saalco new`

```
saalco new feature TITLE --tier S|M|L [--slug SLUG] [--non-interactive]
saalco new req|ad|dd|md|ut|it|st|dev TITLE --feature F-nnn
```

ID を採番し、台帳に記録し、雛形を作るか追記する。採番した ID を標準出力に出す。

| kind | 追記先 |
|---|---|
| `req` | `10-requirements.md` |
| `ad` | `20-architecture.md` |
| `dd` | `30-detailed-design.md` |
| `md` | `35-module-design.md` |
| `ut` | `40-unit-test-spec.md` |
| `it` | `50-integration-test-spec.md` |
| `st` | `60-system-e2e-spec.md` |
| `dev` | `90-deviations.md` |

### `saalco approve`

```
saalco approve PATH...
```

人間専用。`docs/features/` 以下の `.md` だけが対象。TTY（ターミナルからの直接実行）でないと拒否する。全パスを検証してから書き込むので、1つでも不正なパスがあれば何も書き込まない。

### `saalco retire`

```
saalco retire ID [--reason TEXT] [--superseded-by ID]
```

台帳の行を `retired` にする。文書は変更しない。`--superseded-by` には有効な（廃止されていない）ID を指定する。

### `saalco check`

```
saalco check [--verification] [--json]
```

読み取り専用の検査。エラーがあれば exit 1。`--verification` で Evidence に基づく検査を加える。`--json` で `{"ok": ..., "errors": [...], "warnings": [...]}` を出す。

### `saalco trace`

```
saalco trace [--json]
```

`docs/trace/rtm.csv` と `rtm.md` を生成する。`--json` で行データを標準出力にも出す。RTM は `saalco evidence` のときにも生成されるが、その時点では Evidence がまだ commit されていないため `stale` になる。Evidence を commit した後に `saalco trace` を実行し直し、その結果を commit する（5.10）。

`verify_status` の値：

| 値 | 意味 |
|---|---|
| `verified` | REQ と、それを `covers:` する全ての設計項目の検証が current な Evidence で充足している |
| `unverified` | current な Evidence はあるが、どこかが充足していない |
| `stale` | current な Evidence が無い（Evidence 後にコードや文書が変わった） |
| `NOT_EVALUATED` | 判定できない（`language: other` など） |

### `saalco evidence`

```
saalco evidence
saalco evidence --package F-nnn
```

品質ゲートとテストを実行し、Evidence を記録する（5.10）。`--package` は current な Evidence をもとに、Feature の Evidence Package を `.saal/packages/F-nnn/` に作る。

### 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功 |
| 1 | 規則への不適合、または検証の失敗（`check` のエラー、`evidence` の Overall FAIL） |
| 2 | 使い方・設定の誤り（引数不足、Feature が見つからない、`uv.lock` が古いなど） |
| 3 | 環境・外部ツールの誤り（Git が無い、作業ツリーが汚れている、uv が実行できないなど） |

---

## 12. `saalco check` のメッセージと対処

| メッセージ | 原因 | 対処 |
|---|---|---|
| `covers is empty` | `covers:` が空 | 上流の ID を書く |
| `REQ covers must be '-'` | REQ に上流を書いた | `covers: -` にする |
| `unknown covers ID X` | 存在しない ID を参照 | ID を直す。廃止済みなら参照を消す |
| `cannot cover X` | 参照できない種別（6.3） | 正しい上流を参照する |
| `invalid verify 'x'` | `verify:` の値が不正 | `test`/`review`/`static` にする |
| `unknown static gate` | `static:` が無い、またはそのゲートが無い | `static: lint` のように既存のゲート名を書く |
| `X: no Specification-derived verifies test` | `verify: test` の項目を検証する `verifies` テストが無い | 仕様由来テストを書く（7.3） |
| `X: no UT specification covers this item` | DD/MD を covers する UT が無い | `saalco new ut` で試験仕様を書く |
| `approved_hash does not match current content; ask a human to re-approve` | 承認後に文書が変わった | 変更が正しければ人間が再承認する |
| `required for Tier X` | Tier に必要な文書が無い | ファイルを戻す。Tier を見直すなら人間に相談する |
| `tier must be S, M, or L` | `00-meta.md` の Tier が不正 | 正しい値にする |
| `documented ID is missing from docs/ids.ledger` | 手で書いた ID | 見出しを消し、`saalco new` で採番し直す |
| `docs/ids.ledger: X has no corresponding document item` | 台帳にあるが文書に無い | 見出しを戻すか、`saalco retire` する |
| `retired ID X reused` / `references retired ID X` | 廃止した ID が残っている | 見出しや参照を消す |
| `duplicate ID X` | 同じ ID が2か所にある | 片方を消す |
| `verifies unknown ID X` | テストが存在しない ID を参照 | マーカーを直す |
| `invalid DEV status` / `closed DEV is missing ...` | DEV の記入不足 | 6.7 のとおり記入する（人間） |
| `X: not covered by a downstream item`（WARNING） | 下流の項目から参照されていない | 設計・試験仕様を書く |
| `unit test references X`（WARNING） | テストの置き場所と参照先の種別が合わない | 7.2 のとおり置き直す |

`--verification` で出るもの：

| メッセージ | 対処 |
|---|---|
| `no current Evidence; run saalco evidence and commit it` | commit して `saalco evidence` を実行し、生成物を commit する |
| `... verifies test did not PASS` | テストか実装を直す |
| `gate X: result is FAIL` | `.saal/artifacts/<commit>/<run-id>/gate-X.log` を見て直す |
| `coverage is FAIL` / `coverage is NOT_EVALUATED` | テストを足す。取れない理由を調べる（13 章） |
| `X: reached by verifies test for unapproved/stale DD-nnnn` | その DD/MD の文書を人間に承認してもらう |
| `unapproved-design check NOT_EVALUATED: coverage contexts unavailable` | Coverage の JSON が取れていない。`language: python` と pytest-cov の設定を確認する |
| `REQ-nnnn: RTM status is unverified, not verified` | `docs/trace/rtm.md` を見て、足りない検証を足す |
| `X: reached by no verifies test`（WARNING） | 仕様由来テストで通らないファイル。必要ならテストを足す |
| `gate.04.secret_scan: NOT_CONFIGURED`（WARNING） | ゲートを設定する（8.2） |

---

## 13. トラブルシューティング

**`ERROR ...: not inside a SAALCO project. Run saalco init.`**
プロジェクトの外で実行している。`docs/project.md` のあるディレクトリ（またはその下）に移動する。

**`ERROR title produces no ASCII slug; pass --slug SLUG.`**
日本語のタイトルから slug が作れない。`--slug login` のように指定する。

**`ERROR approve requires a TTY and must be run by a human.`**
パイプやエージェント経由で実行している。人間がターミナルで直接実行する。`SAALCO_ALLOW_NONTTY_APPROVE=1` は SAALCO 自身の自動テスト専用で、通常の運用では使わない。

**`ERROR git config user.name is required for approval.`**
3.3 のとおり設定する。

**`ERROR working tree is dirty; commit all changes before saalco evidence.`**
`git status` で未 commit の変更と、未追跡のファイルを確認する。不要な生成ファイルは `.gitignore` に入れる。

**`ERROR uv.lock: not found` / `not tracked by git` / `out of date; needs uv lock`**
`uv lock` を実行して `uv.lock` を commit する。`uv.lock` の変更は依存の追加・更新にあたるので、人間の承認（H4）を得る。

**`test.integration: FAIL` なのにテストは全部通っている**
`tests/integration/` にテストが1件も無いと、pytest は終了コード5で終わる。結合テストが無いなら `test.integration:` を空にする（4.8）。

**Coverage が低すぎる／E2E で通った行が数えられていない**
E2E がサブプロセスで起動している場合は 8.4 の設定を入れる。`summary.md` の Coverage と `.saal/artifacts/` の `coverage.json` で、どの行が実行されていないか確認する。

**ゲートが FAIL するが、手で実行すると通る**
- ゲートがファイルを書き換えていないか確認する（書き換えると FAIL になる）。
- `uv run` には `--locked` が付くので、`uv.lock` が最新でないと失敗する。
- ログは `.saal/artifacts/<commit>/<run-id>/` にある。

**Evidence を commit したのに、`docs/trace/rtm.md` が `stale` のまま**
`saalco evidence` が書き出した RTM は、Evidence が commit される前の時点のものである。`saalco trace` を実行し直して commit する（5.10）。

**Evidence を取ったのに `stale` になる**
Evidence の対象 commit のあと、`evidence/`・`docs/trace/`・`docs/ids.ledger` 以外のファイルを変更して commit した。Evidence を取り直す。

**`saalco` が見つからない**
`uv tool install .` のあと、uv のツールディレクトリ（多くは `~/.local/bin`）に PATH が通っているか確認する。`uv tool update-shell` で設定できる。

---

## 14. 既存プロジェクトの移行

既存のプロジェクトも Bootstrap から始める（規則 10.5）。

1. プロジェクトのルートで `saalco init` を実行する。既存の `src/`・`tests/` は、標準構造に合わせて移動してよい。
2. 既存の機能を Feature として登録する（`saalco new feature`）。
3. 要件と設計を、現状から逆起こしして書き、人間が承認する。
4. 既存のテストは実装を見て書かれたものなので、原則 `impl_aware` とする。
5. `verify: test` の項目に対して、仕様由来テストを別コンテキストで追加し、RTM を `verified` にする。
6. 移行途中の状態は DEV に記録する（例：`rule: 6.8, 10.5`、`scope: F-001, src/`）。
7. 移行が終わるまで、その Feature について規則準拠を主張しない。

SAALCO 自身の開発も既存プロジェクトの移行として扱われた。その記録は [`docs/features/F-001_saalco-v1/90-deviations.md`](features/F-001_saalco-v1/90-deviations.md) の DEV-0001 にある。

---

## 15. 制限事項

- 承認は、人間が本当に文書を確認したことを暗号的には証明しない。Git の `user.name` と内容hash で、あとからの改変を検出できるだけである。
- 仕様由来テストが実装を見ずに書かれたかどうかは、ツールでは強制できない。手続きで守る。
- テスト関連の機能は Python（pytest・coverage.py・uv）を前提とする。
- Evidence は対象 commit と同じ commit には保存できないため、後続の commit に入れる。
- 実装の細部と、規則・仕様のあいだの暫定解釈は [`docs/development-open-questions.md`](development-open-questions.md) にまとめてある。
