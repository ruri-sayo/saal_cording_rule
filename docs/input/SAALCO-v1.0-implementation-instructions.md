# SAALCO v1.0 実装指示書（改訂版 r2）

## 0. この指示書の目的と今回の方針

`SAALCO` は、SAAL ソフトウェア開発規則 v1.0（以下「規則」）を実際の開発で運用するためのローカルCLIツールである。

想定利用者は人間に加え、Codex・Claude Code 等の Coding Agent である。利用の流れは次のとおり。

1. 人間が仕様を決定する
2. SAALCOでプロジェクトを初期化する
3. Coding Agentへ仕様書とSAAL規則を渡す
4. Coding AgentがSAALCOを使いながら設計・実装・テストを進める
5. 人間は規則で定義された承認点（H1〜H6）でのみ介入する

**今回の開発方針：動く実物を早く作り、実運用で欠点を洗い出して改善する。**

- エッジケースの作り込みより、主要フロー（init → new → approve → check → trace → evidence）が実プロジェクトで一通り動くことを優先する。
- 本指示書で定義していない細部は、安全側の最小実装で進めてよい。判断した内容は `docs/development-open-questions.md` に1行で記録する。
- ただし、ID管理・承認・トレーサビリティ・Verification判定・Evidenceは品質保証の根幹なので簡略化しない。ここで「迷ったらPASS」にしてはならない。**判定できないものは `NOT_EVALUATED` とし、PASSとして扱わない。**

---

## 1. Normative Source と v1.0 暫定解釈

正本は `SAAL-DEV-RULES.md`（version 1.0、released 2026-09-21）である。本指示書と規則が矛盾する場合は、規則を優先する。

ただし、規則をそのまま実装すると成立しない、または未定義の箇所がある。それらについては、本節の**暫定解釈**をSAALCO v1.0の仕様とする。暫定解釈は、`docs/development-open-questions.md` に分類C（規則との衝突・規則の未定義）として初期記載しておくこと。

| # | 規則の該当箇所 | 問題 | v1.0 暫定解釈 |
|---|---|---|---|
| I-1 | 6.8 / 8.4 | Evidenceは対象commitの後続commitに保存されるため、HEADと「同一commit」になることが無い | 対象commitからHEADまでの差分が `evidence/`・`docs/trace/`・`docs/ids.ledger` のみなら、そのEvidenceを HEAD に対して **current** とみなす |
| I-2 | 7.1 / 13.5 | 規則7.1でゲート内の `saal check` はテストより前に置かれているのに、13.5の検査項目にはテスト結果とCoverageが含まれる | check を2段に分ける。`saalco check`（静的・テスト前）と `saalco check --verification`（テスト結果・Coverage・RTM。current Evidence が必要） |
| I-3 | 6.2 | 「廃止IDを再利用しない」は、既存IDの最大値＋1による採番では満たせない | Git管理の採番台帳 `docs/ids.ledger` を正本にする（§9） |
| I-4 | 4.8 / 6.4 | 人間が実施するST（H5）の結果が、検証充足に数える経路を持たない | ST項目に `method: manual` と実施結果を記録できるようにし、RTMで充足に数える（§8.5） |
| I-5 | 12.3 / 13.5-9 | 逸脱記録が機械可読でないため、Coverage未達の例外を判定できない | 逸脱記録を `DEV-nnnn` 項目として構造化する（§8.6） |
| I-6 | 4.6 / 8.5 | 設計差分レポートの置き場が未定義 | `docs/features/F-xxx/45-implementation-diff.md` に置く |
| I-7 | 2.4 | Tierの人間承認が、どの介入点（H1〜H6）にも紐付いていない | H3（詳細設計承認）のときに `00-meta.md` も合わせて `approve` する |
| I-8 | 13章 | 規則のコマンド名は `saal` | `saal` と `saalco` の両方をエントリポイントとして登録する（同一の実体） |

---

## 2. v1.0 の完成状態

次の操作が実プロジェクトで使用可能であること。

```bash
saalco init [--name N --type research|system --language python|other --spec PATH --non-interactive]
saalco new feature "Name" --tier S|M|L [--slug SLUG]
saalco new req|ad|dd|md|ut|it|st|dev --feature F-001 "Title"
saalco approve <path> [<path> ...]
saalco check [--verification] [--json]
saalco trace [--json]
saalco evidence
saalco evidence --package F-001
```

`saal` は `saalco` の別名として、どのサブコマンドでも同じ動作をすること。

---

## 3. 基本設計思想

SAALCOはLLMではない。要件や設計の内容を考えない。`covers:` の中身を推測して埋めない。

SAALCOの責務は次に限定する。

- 構造生成
- テンプレート配置
- ID採番
- 文書構造の機械的管理
- 承認記録と改変検知
- トレーサビリティ検査
- RTM生成
- テスト・Coverage情報の取得
- 品質ゲート実行
- Evidence生成

文章の内容を作るのは、人間とCoding Agentの責務である。

---

## 4. 実装技術

- Python 3.11以上。パッケージ管理は `uv`。
- `uv sync` / `uv run pytest` / `uv tool install .` が通ること。
- `pyproject.toml` の `[project.scripts]` に `saalco` と `saal` を登録する。
- ランタイム依存は原則として標準ライブラリのみとする（argparse, pathlib, hashlib, subprocess, json, csv, datetime, tomllib, importlib.resources, ast）。
- YAMLライブラリは使用しない。
- **プロジェクト側のpytest・coverageはプロジェクトのvenvで実行する。** saalcoは uv tool の隔離環境にいるため、プロジェクトの `.coverage` を直接読み込まない。§14で定めるJSONエクスポートを経由する。
- 開発用依存：pytest, pytest-cov, ruff, 型チェッカ（mypy を推奨）。
- 対象OS：macOS / Linux。Windowsはv1.0の対象外とする。

---

## 5. CLI UX

- **対話モード**：引数が不足していれば質問する。
- **`--non-interactive`**：質問しない。必要な引数が不足していれば exit 2 で終了する。
- **終了コード**
  - `0`：成功
  - `1`：検査失敗
  - `2`：使い方・設定のエラー
  - `3`：環境・外部ツール実行のエラー
- **`--json`**：`check` と `trace` で機械可読な出力を返す。内部データモデルはJSON化できる形で持つ。
- **エラーメッセージ**：対象ファイル・ID・原因・次に取るべき操作を1〜2行で示す。

  ```text
  ERROR docs/features/F-001_x/30-detailed-design.md: approved_hash does not match current content.
    Ask a human to review and run `saalco approve <path>`.
  ```

- **`check` の出力**：全ての違反を列挙してから終了する。最初の1件で止めない。最後に `N errors, M warnings` を出す。

---

## 6. パッケージ構成

推奨構成は次のとおり。完全一致は必須ではないが、単一の巨大ファイルにはしないこと。CLI層とドメインロジックは分離すること。

```text
src/saalco/
  cli.py
  commands/   init.py new.py approve.py check.py trace.py evidence.py
  project/    discovery.py config.py git.py
  documents/  header.py parser.py items.py hash.py
  ids/        ledger.py
  trace/      graph.py markers.py coverage_json.py rtm.py
  checks/     static.py verification.py runner.py
  evidence/   gates.py manifest.py artifacts.py package.py
  templates/v1/   （規則ファイル・AGENTS.md・文書テンプレート・pyproject断片）
tests/ unit/ integration/ e2e/ fixtures/
```

---

## 7. `saalco init`

### 7.1 生成物

```text
<project>/
  AGENTS.md
  docs/
    project.md
    ids.ledger
    rules/SAAL-DEV-RULES.md      # 同梱版をコピー。以後自動更新しない
    input/                       # --spec 指定時。複数可
    architecture/
    features/
    trace/
  evidence/
  src/
  tests/unit/ tests/integration/ tests/e2e/
  .saal/artifacts/               # .gitignore に追加
```

- テンプレートはパッケージに同梱する。ネットワーク接続なしで完結すること。
- 既存の `.git/`・`src/`・`tests/` は破壊しない。既存ファイルと衝突する場合は上書きせず、衝突したファイルを列挙して通知する（既存プロジェクトの移行）。
- Git未初期化であれば `git init` する。
- `pyproject.toml` が存在しない場合は雛形を生成する。存在する場合は、マーカー登録の断片を追記せず、「追記すべき内容」を表示する。マーカー登録の断片は次のとおり。

  ```toml
  [tool.pytest.ini_options]
  markers = [
    "verifies(id, spec=None): specification-derived test",
    "impl_aware(id=None): implementation-aware test",
  ]
  ```

### 7.2 `docs/project.md`

ヘッダはフラットな `key: value` のみとする。ゲートのコマンドもここに書く。

```text
---
kind: PROJECT
name: mdsk-rag
type: research
language: python
saal_rules_version: 1.0
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

- 値が空のゲートは `NOT_CONFIGURED` として記録する（PASSではない）。
- 規則7.1で常時実行とされる secret_scan と dependency_audit が未設定の場合は、`check --verification` でWARNINGを出す。
- saalcoは `saal_rules_version` を読み、未対応のバージョンであれば exit 2 で終了する。

### 7.3 `language: other`

initと文書管理（new / approve / check の静的検査 / trace）は動作すること。テスト・Coverageの判定は `NOT_EVALUATED` とする。

### 7.4 `AGENTS.md`（短く保つ。規則全文を複製しない）

最低限、次の内容を含める。

```text
- docs/rules/SAAL-DEV-RULES.md が正本。規則中の `saal` コマンドは `saalco` と同じもの。
- docs/input/ は人間が与えた原仕様書。変更しない。導出した要件等は docs/features/ に書く。
- IDを手で採番しない。必ず `saalco new` を使う。
- `saalco approve` は人間専用。Agentは実行しない。承認が必要になったら、承認対象のパスを列挙して人間に依頼し、そこで停止する。
- 70-acceptance.md（受け入れ判断）を Agent が accepted/PASS 等に書き換えない。
- 実装前に、Tierが要求する設計文書と試験仕様を作る。設計文書が承認されるまで実装に進まない。
- Specification-derived Test（verifies）は、実装コードを見ない別コンテキストで、上流文書と公開IFだけから作る。
  実装を見て書いたテストは必ず impl_aware にする。迷ったら impl_aware。
- 依存の追加・更新、設計に無い外部通信・ファイル書き込み・永続化・実機駆動は、人間の承認（H4）を得てから行う。
- 実装後、45-implementation-diff.md に設計との差分（設計に無いが実装したもの／設計にあるが未実装のもの）を書く。
- 完了を主張する前に `saalco check` を実行する。Evidence を取る前に全ての変更を commit する。
- check を通すために、マーカー・verify・status を事実と異なる値に変えない。通らないものは逸脱記録（saalco new dev）に残す。
```

---

## 8. 文書形式

### 8.1 ヘッダ

ヘッダは `---` で囲んだフラットな `key: value` の並びとする。ネスト・リスト・クォートの意味解釈はしない。

- 未知のkeyは保持する。
- 書き戻すときは、キーの順序と無関係な本文を変更しない。
- 必須キー：`kind`, `feature`, `status`（`draft` / `approved` / `superseded`）。
- `00-meta.md` は追加で `tier`（S / M / L）を必須とする。

### 8.2 項目

見出しの直下に、項目のメタ情報行を置く。

```markdown
### DD-0005: Adapterの共通インターフェース

covers: REQ-0012, REQ-0013
verify: test
```

- `verify:` の値は `test` / `review` / `static` のいずれか。省略時は `test` とする。
- REQ項目は `covers: -` とする。
- `verify: static` の項目には、`static: <gate名>`（例：`static: lint`）を必須とする。そのゲートが存在し、current EvidenceでPASSしていれば充足とする。

### 8.3 `covers:` に書ける参照先

| 項目 | covers: に書けるID |
|---|---|
| REQ | `-` |
| AD | REQ |
| DD | AD, REQ |
| MD | DD, AD, REQ |
| UT | DD, MD |
| IT | AD |
| ST | REQ |
| DEV | （`covers:` は使わず、`scope:` を使う） |

この表に無い参照先を書いた場合、存在しないIDを参照した場合、重複ID、循環参照、`covers:` が空の場合は、いずれもERRORとする。下流から一度も参照されていないREQ・AD・DD・MDはWARNINGとする。

### 8.4 テストマーカー

```python
@pytest.mark.verifies("DD-0005")                  # Specification-derived（充足に数える）
@pytest.mark.verifies("DD-0005", spec="UT-0003")  # 試験仕様項目への紐付け（v1.0では任意）
@pytest.mark.impl_aware                           # 補助テスト（充足に数えない）
@pytest.mark.impl_aware("DD-0005")                # 参照付きの補助テスト（充足に数えない）
```

- **マーカーの無いテストは `impl_aware` として扱う**。既存テストの移行も含む。
- マーカーはASTで解析する。関数デコレータ、クラスデコレータ、モジュールの `pytestmark` に対応すること。
- parametrize されたテストは、全ケースがPASSした場合に1件のPASSとする。
- verifies の参照先の種別は次のとおりとする。
  - `tests/unit` のテスト → DD / MD
  - `tests/integration` のテスト → AD
  - `tests/e2e` のテスト → REQ

  ディレクトリと参照先の種別が一致しない場合はWARNINGとする。

### 8.5 手動ST（暫定解釈 I-4）

`60-system-e2e-spec.md` のST項目には、次のように手動実施の結果を記録できる。

```markdown
### ST-0003: 実機での起動確認

covers: REQ-0012
method: manual
result: PASS
commit: <full hash>
executed_by: miura
executed_at: 2026-09-22
```

`commit` が current Evidence と同じ扱いになる場合（差分が I-1 の範囲のみ）、この結果をREQの検証充足に数える。

### 8.6 逸脱記録（暫定解釈 I-5）

`90-deviations.md` に、次の形式で記録する。

```markdown
### DEV-0001: 移行中の未検証REQ

rule: 10.5
scope: F-001, src/saalco/ids/
status: open
reason: 既存テストはimpl_awareのため
resolution: F-001のSpecification-derived Test追加で解消
decided_by: miura
decided_at: 2026-09-22
```

- Coverage未達などの例外は、`status: open` かつ `rule` と `scope` が該当する DEV があれば許容する。この場合、ERRORではなくWARNINGとして表示する。
- DEVの採番も `saalco new dev` で行う。

---

## 9. ID採番（暫定解釈 I-3）

- 対象：`F-nnn`, `REQ-nnnn`, `AD-nnnn`, `DD-nnnn`, `MD-nnnn`, `UT-nnnn`, `IT-nnnn`, `ST-nnnn`, `DEV-nnnn`。
- 全てプロジェクト内でグローバルに一意とする。Featureごとのカウンタにしない。
- **正本は Git 管理の `docs/ids.ledger`** とする。追記専用で、1行が1IDに対応する。

  ```text
  REQ-0012	F-001	2026-09-22T17:30:00+09:00	Caller is model-agnostic
  ```

- 次のIDは「台帳内の同種別IDの最大値＋1」とする。文書からIDを削除しても、台帳の行は消さない。したがって再利用は起きない。
- 単一マシン上の同時実行は、`.saal/ids.lock`（`O_EXCL` で作成）で排他する。
- 並行ブランチでの衝突は、マージ時の台帳コンフリクトとして表面化させる。台帳の重複や、文書と台帳の不一致は `check` がERRORにする。v1.0では自動振り直しは行わない。

---

## 10. `saalco new`

- `feature`
  - 次の `F-nnn` を採番し、`docs/features/F-nnn_<slug>/00-meta.md` を作成する。
  - slug はタイトルをASCII化して作る。空になる場合（日本語タイトル等）は `--slug` を要求する。non-interactive で `--slug` が無ければ exit 2。
  - Tierに応じて必要な文書をテンプレートから生成する。Tier別のテンプレートを3重に管理せず、共通テンプレートの生成・省略で表現する。
  - `project.md` の `type`（research / system）に応じて、`80-outcome.md` のテンプレートを切り替える。
- その他の kind
  - `--feature` を必須とする。
  - 該当する文書が無ければテンプレートから生成し、あれば末尾に項目の雛形を追記する。
  - 採番したIDだけを標準出力に返す（Agentが後続処理でパースしやすくするため）。
  - **承認済みの文書に追記した場合は、`status: draft` に戻し、「承認が無効になった」とWARNINGを出す。**

生成する項目の雛形は次のとおり。

```markdown
### DD-0012: Connection state management

covers:
verify: test
```

Tier別の必須文書は規則2.4に従う。`45-implementation-diff.md`・`70-acceptance.md`・`80-outcome.md`・`90-deviations.md` は全Tierで生成する。

---

## 11. `saalco approve`（人間専用）

- 複数のパスを受け付ける（I-7：`00-meta.md` と `30-detailed-design.md` を同時に承認するため）。
- **`stdin` がTTYでなければ exit 2 で拒否する。** 追加の質問はしない。例外として、環境変数 `SAALCO_ALLOW_NONTTY_APPROVE=1` のときだけ許可する。これはSAALCO自身のテスト専用であり、AGENTS.md には記載しない。
- 処理内容：
  1. ヘッダと本文をパースする。
  2. content hash を計算する。
  3. `status: approved`、`approved_by`（`git config user.name`。取得できなければ exit 2）、`approved_at`（タイムゾーン付きISO 8601）、`approved_hash`、`version`（＋1）を書き込む。
  4. 一時ファイルに書き出し、再パースで検証してから、原子的に置換する。
- **hashの計算方法**
  - SHA-256 を使う。
  - `status`, `version`, `approved_by`, `approved_at`, `approved_hash` の5キーを除いたヘッダと本文を対象とする。
  - 改行をLFに正規化してから計算する。
  - 同じ内容なら同じhashになること。
- 限界として、承認の真正性（本当に人間が承認したか）は手続きで担保するものであり、ツールでは完全には強制できない。READMEにこの限界を明記する。

---

## 12. `saalco check`（静的検査・テスト前）

品質ゲートの中で、テストより前に実行する。検査項目は次のとおり。

1. ヘッダの形式と必須キー
2. `00-meta.md` の Tier 宣言
3. Tier に応じた必須文書の存在
4. ID の重複と、台帳との不一致（§9）
5. `covers:` / `verifies` の参照先が存在すること、参照先の種別が §8.3 に従っていること、循環が無いこと
6. 承認済み文書の hash が `approved_hash` と一致すること
7. `verify: test` の項目に、Specification-derived Test（verifies）が1件以上紐付いていること
8. `verify: test` の DD / MD に、それを `covers:` する UT 項目が1件以上あること（規則4.5：試験仕様が上流を網羅していること）
9. `verify: static` の項目に `static:` 行があり、指定したゲートが `project.md` に存在すること
10. `70-acceptance.md` 以外に、Agent が編集してはならない承認キーが、承認記録と矛盾していないこと（`status: approved` なのに `approved_hash` が無い、等）

## 13. `saalco check --verification`（テスト後・current Evidence が必要）

`saalco check` の全項目に加え、次を検査する。

11. current Evidence が存在すること（I-1）。無ければERRORとし、「`saalco evidence` を実行すること」と案内する。
12. current Evidence において、`verifies` のテストが全てPASSしていること
13. Coverage 基準（§15）
14. **未承認の設計に対応する実装**（規則13.5-5）
    - coverage context から「実装ファイル → そのファイルを通過する verifies テスト → 参照先の DD / MD」と辿る。
    - 参照先の文書が未承認、または hash 不一致であればERRORとする。
    - どの verifies テストからも到達しない `src/` 以下のファイルはWARNINGとする。
15. RTM 上で `verified` になっていない REQ
16. 逸脱に対応する DEV 記録（open な DEV が該当すれば、ERRORではなくWARNINGとして表示）
17. `NOT_CONFIGURED` のまま設定されていない secret_scan / dependency_audit（WARNING）

---

## 14. トレース・RTM

- **入力**：Feature 文書、`covers:` / `verify:`、マーカー（AST 解析）、coverage context、current Evidence の manifest。
- **coverage context の取得**：Evidence 実行時に、プロジェクトの環境で次を実行し、出力された JSON を読む。

  ```bash
  uv run coverage json --show-contexts -o .saal/artifacts/<commit>/<run>/coverage.json
  ```

  pytest は `--cov=src --cov-context=test` を付けて実行する。
- **出力**：`docs/trace/rtm.csv` と `docs/trace/rtm.md`。列は次のとおり。

  ```text
  req_id, requirement, feature, design_ids, impl_files, unit_tests, integration_tests, e2e_tests, verify_status, evidence_commit
  ```

- **決定性**：同じ入力からは同じ出力を生成すること。タイムスタンプは含めない。行はIDでソートする。
- **`verify_status` の値**：`verified` / `unverified` / `stale`（current Evidence が無い）/ `NOT_EVALUATED`。
- **`verified` の条件**：次の全てを満たすこと。
  - REQ 自身の検証が充足している（verifies の ST が PASS、手動 ST が PASS、または `review` / `static` の条件を満たす）
  - その REQ を直接または間接に `covers:` する全ての設計項目が、`verify:` の種類に応じて充足している
  - `review` の充足条件は、承認済みかつ hash が一致していること
  - 根拠となる Evidence が全て current であること

---

## 15. Coverage

- **差分の基準点**：HEAD の祖先にある直前 Evidence の対象 commit を基準にする。Evidence が1つも無ければ、空ツリーを基準にする（初回は全コードが新規扱いになる）。
- **基準**：
  - 差分の行カバレッジが80%以上であること
  - 全体のカバレッジが直前 Evidence の値を下回らないこと
- 差分カバレッジは、`git diff -U0` の追加・変更行と、coverage JSON の実行行・未実行行を突き合わせて自前で計算する。
- 計算できない場合は `NOT_EVALUATED` とする。**`NOT_EVALUATED` は、該当する DEV が無ければ FAIL として扱う。**

---

## 16. 品質ゲート runner

- `project.md` に書かれた `gate.NN.*` と `test.*` を、番号順に実行する。
- 各ステップについて、コマンド・開始時刻・終了時刻・終了コード・結果（`PASS` / `FAIL` / `NOT_CONFIGURED` / `ERROR`）・ツールのバージョン（取得できれば）を記録する。
- **ゲートはファイルを書き換えないモードで実行すること。** Formatter は `--check` モードで実行する。書き換えるコマンドが設定されている場合でも、実行後に working tree が変化していれば、その時点でFAILとする。
- 実行順序：`gate.*` → `saalco check`（静的）→ `test.unit` → `test.integration` → `test.e2e` → coverage JSON のエクスポート。
- 生成物の出力先は `.saal/artifacts/` 以下に固定する（`COVERAGE_FILE` の指定、`--junitxml` の出力先など）。
- ネットワークが必要なツール（dependency audit 等）がネットワークに起因して失敗した場合は、`ERROR` として記録する（PASS にはしない）。

---

## 17. `saalco evidence`

- 前提条件：
  - Git リポジトリであること
  - `git status --porcelain` の出力が空であること（未コミットの変更が無いこと）
- 対象 commit は、開始時点の HEAD とする（完全な40桁の hash）。
- 出力先：
  - `evidence/<commit>/<run-id>/manifest.json`
  - `evidence/<commit>/<run-id>/summary.md`
  - 生データ：`.saal/artifacts/<commit>/<run-id>/`
  - `run-id` は `YYYYMMDDTHHMMSS` 形式とする。同じ commit で再実行しても上書きせず、新しい run-id で追記する。
- 実行後、Git 管理下のファイルが（`evidence/` 以外で）変化していれば、テストが作業ツリーを汚したとみなし、全体を FAIL とする。
- 終了時に `saalco trace` を自動実行し、「`evidence/` と `docs/trace/` を commit すること」と案内する。
- **manifest の記録項目**（JSON schema をリポジトリ内に置く）：

  ```text
  schema_version, saal_rules_version, saalco_version,
  target_commit, run_id, executed_at,
  environment {os, python, arch},
  lockfile {path, sha256},
  gates [{name, command, started_at, ended_at, exit_code, result, tool_version}],
  tests [{nodeid, category, marker, referenced_id, spec, result}],
  coverage {total, diff, diff_base_commit, status},
  artifacts [{path, sha256, retention_location}]
  ```

- **summary.md の記載内容**：対象 commit、実行日時、総合結果、ゲート別の結果、UT / IT / E2E の結果、Coverage、RTM の集計、open な DEV、生データの所在。

### 17.1 `saalco evidence --package F-001`

`.saal/packages/F-001/` に、`index.md` と `package.json` を生成する。これは既存ファイルへの参照をまとめたビューであり、ファイルを複製しない。含める内容は次のとおり。

- 要件定義書
- 当該 Feature の RTM 行
- current Evidence の manifest
- 承認記録（誰が・いつ・どのバージョン・どの hash を承認したか）
- open な DEV
- `45-implementation-diff.md`

---

## 18. Acceptance / Outcome / Safety

- **`70-acceptance.md`**：人間による Validation の記録である。SAALCO は判定もステータス変更も行わない。
- **`80-outcome.md`**：
  - research：code commit, dataset version, model, config, seed, environment, result location, result hash
  - system：release version, target commit, deployment target, release date
- **Safety**：SAALCO は次の操作を行わない。
  - git push / reset --hard
  - ブランチの強制変更
  - リモートリポジトリの作成
  - ファイル削除
  - 既存文書の上書き（承認メタデータの更新を除く）
  - 依存関係の更新
  - OS 全体の設定変更
- 既存ファイルを書き換えるときは、一時ファイルに書き出し、検証してから原子的に置換する。

---

## 19. SAALCO 自身のテスト

各 Phase の終わりにテストを実行する。最後にまとめてテストを書く方式にしない。

- **Unit**：ヘッダのパース・シリアライズ、hash、台帳による採番、covers / verify のパース、マーカーの AST 解析、Tier 規則、トレースグラフ、差分カバレッジ計算、manifest 生成
- **Integration**：init、new、approve → 編集 → check FAIL → 再 approve → PASS、trace、Evidence 生成、dirty tree の拒否
- **E2E（subprocess 経由で実際の `saalco` を実行）**：一時ディレクトリで次の一連を通す。
  1. init
  2. feature 作成
  3. REQ / AD / DD / UT / ST の作成
  4. サンプル実装とテストの配置
  5. approve
  6. commit
  7. check
  8. evidence
  9. evidence の commit
  10. `check --verification` が PASS
  11. trace
- **Fixtures**：`tests/fixtures/` に最小限のものを置く。
  - valid_project
  - invalid_hash
  - broken_reference
  - missing_document
  - coverage_failure

---

## 20. Dogfooding（SAALCO 自身への適用）

- `saalco init` が動いた時点で、SAALCO リポジトリ自身に適用する。適用は既存プロジェクトの移行（規則10.5）として扱う。
- SAALCO 自身の REQ / AD / DD / 試験仕様は、本指示書から逆起こしして作成する。**Codex はこれらを `draft` のまま残し、承認は人間が行う。**
- Codex が実装を見て書いたテストは、全て `impl_aware` とする。**check を通すために `verifies` へ付け替えてはならない。**
- 移行中であることは、DEV 記録（rule: 10.5）として残す。

---

## 21. 実装順序

1. **Core**：CLI エントリポイント（saalco / saal）、プロジェクト探索、テンプレート、init、ヘッダパーサ、ID 台帳、new、approve
   → ここで init → new → approve → 編集 → check（hash のみ）を E2E で確認する。
2. **Verification**：マーカー解析、トレースグラフ、静的 check、RTM
3. **Evidence**：ゲート runner、coverage JSON の取り込み、差分カバレッジ、manifest / summary、evidence、`check --verification`、package
4. **Production readiness**：既存プロジェクトの移行、エラーメッセージの改善、`--json`、README、dogfooding、全体 E2E

---

## 22. 設計変更と未決事項

実装中に本指示書どおりでは成立しない点を見つけた場合は、次の4つに分類する。

- **A. 実装の細部**：Codex が判断して進めてよい。
- **B. 仕様の曖昧さ**
- **C. 規則との衝突**
- **D. 本指示書の欠陥**

B〜D は `docs/development-open-questions.md` に記録し、安全側の最小実装で継続する。§1 の暫定解釈 I-1〜I-8 は、C として最初から記載しておく。

---

## 23. 完成条件

- `uv tool install .` の後、`saalco --help` と `saal --help` が成功する。
- 空ディレクトリで research / system の両方の種別を init でき、`80-outcome.md` のテンプレートが種別に応じて異なる。
- 既存の `src/` / `tests/` があるディレクトリで init しても、既存ファイルが壊れない。
- Feature と各種項目を CLI から作成でき、ID が台帳経由で一意に採番される。
- approve 後に文書を編集すると check が FAIL し、再 approve で PASS に戻る。TTY でない環境では approve が拒否される。
- broken reference・種別違反・Tier 別の必須文書の不足を、check が検出する。
- `verifies` と `impl_aware` を区別でき、`impl_aware` だけでは REQ が verified にならない。
- clean な commit に対して evidence が生成され（manifest / summary / 生データ）、dirty tree では拒否される。
- evidence を commit した後、`check --verification` と RTM が、その Evidence を current として扱う。
- Coverage を判定でき、判定できない場合は `NOT_EVALUATED`（DEV が無ければ FAIL）になる。
- Feature 単位の Evidence Package を生成できる。
- SAALCO 自身の unit / integration / E2E テストが全て PASS する。
- SAALCO リポジトリ自身に対する `saalco check`（静的）の結果が得られる。**`check --verification` は、移行中の DEV を伴う状態での結果でよい。緑にすることを完成条件にしない。**

---

## 24. 最終成果物

1. 実装済みの SAALCO
2. SAALCO 自身の SAAL 文書（draft のまま）と、**人間への承認依頼一覧**（承認対象のパスと、承認すべき理由を1行ずつ）
3. 自動テスト一式と、最終のテスト結果・Coverage
4. README（インストール方法、最短の利用例、承認の限界、終了コード）
5. サンプルプロジェクト、または E2E 用 fixture
6. 最終の `saalco check` / `saalco check --verification` の出力と、Evidence
7. `docs/development-open-questions.md`

---

## 25. 最終指示

目的は、CLI を高度化することではなく、**SAAL 規則を人間と Coding Agent が低コストで実際に守れる状態にすること**である。過剰な設計はしない。

一方で、判定できないものを PASS にしないこと、そして正直な赤を偽の緑より優先すること、この2点は守ること。この版は、実運用で欠点を洗い出すための叩き台である。
