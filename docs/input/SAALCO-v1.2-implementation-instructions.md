# SAALCO v1.2 実装指示書（初版 r1）

## 0. この指示書の位置付け

本書は、SAALCO v1.0 実装指示書（改訂版 r4、以下「v1.0指示書」）への追加・変更を定める。v1.0指示書のうち本書で変えない部分は、v1.2 でもそのまま有効である。

- 作成：2026-11-01。人間（本人）の指示により、エージェントが起草した。`docs/input/` は人間が与えた原仕様書を置く場所であり、本書は人間の指示による例外として置く（前例：r3・r4 の写しの更新）。
- 経緯：Notion「SAALCO 改良計画｜Human Validation・トークン効率の再設計（議論メモ 2026-11-01）」での議論と合意。
- 対応する規則：SAAL ソフトウェア開発規則 v1.2（`docs/rules/SAAL-DEV-RULES.md`）。本書と規則が矛盾する場合は規則を優先する。
- **問いカードの書式（§5）は、紙上試行（`docs/questions/`）の結果で直してから、Feature の H1 に進める。**

---

## 1. 改訂の動機（実運用で見つかった問題）

| ID | 問題 | 根拠 |
|---|---|---|
| U-01 | トークン消費が過大 | 2026-07-13〜10-31 の69セッションのうち、saalco 関連の10セッション（14%）が入力換算トークンの50%を消費した |
| U-02 | 承認が形骸化する | 承認に必要な閲覧量が多く、承認すべき内容を把握しきれない |
| U-03 | 人間向けの説明の質が低い | エージェントが書く文書は、人間が判断するための読みやすさを考えていない |
| U-04 | 文書間の移動が多い | 確認対象が散らばっていて、全体像と関係が掴みにくい |
| U-05 | AIに説明させるのも非効率 | 既存の文書を毎回 LLM に説明させると、余分にトークンを使う |

トークン消費の主因は、saalco のコマンドや規則文書を読む量（数%）ではなく、作業の進め方であった。cache read が53〜67%を占め、auto-compact が起きずにコンテキストが約380kまで増え続けていた。サブエージェントが47〜62%を占め、工程ごとに同じ資料を読み直していた。

最も重い問題は、**承認の記録は残っても、人間が理解して Validation したとは限らない**ことである。

---

## 2. v1.2 の方針

1. **Verification の証拠体系は軽くしない。** REQ → 設計 → テスト → Evidence の追跡、`NOT_EVALUATED` を PASS にしないこと、承認hashによる改変検知は v1.0 のまま維持する。
2. **人間には「承認させる」のではなく「答えさせる」。** 人間が決めるべき判断を、選択肢と帰結の付いた問いカードとして示し、人間の回答を記録する。人間が要約や文書全体を承認する形にしない。
3. **H3 で人間が承認するのは、詳細設計の全文ではなく判断項目である。** 判断項目でない細部（ユニット単位の設計）の保証は、Verification としてシステムが担う。追跡はできるまま残す。
4. **LLM には必要な文脈だけを渡す。** 承認点でセッションを切り、次のセッションは `saalco context` が決定論的に組み立てたブリーフィングから再開する。
5. **集約・表示はツールが決定論的に行う。** LLM による要約を承認の対象にしない。

---

## 3. 変更一覧と実装順序

次の順に、SAALCO 自身の V-cycle に Feature として載せる。各 Feature の Tier はエージェントが提案し、H3 で人間が承認する。

| 順 | 機能 | 本書の節 | 規則 v1.2 の該当箇所 |
|---|---|---|---|
| 1 | `saalco approve` の完了表示、`saalco context` | §4 | 3.5、13.3、13.10 |
| 2 | 問いカード（`Q`）：文書形式、`saalco new q`、`check` の検査 | §5、§6 | 3.4、6.2、13.2、13.5 |
| 3 | `saalco review`：回答の記録と、承認点の承認 | §7 | 3.2、3.4、13.9 |
| 4 | 判断項目と、判断項目への承認hash | §8 | 4.3、5.2、6.4、6.5 |
| 5 | 格上げ対象の検出 | §9 | 6.9、13.5 |
| 6 | `saalco init` の生成物の更新、版の更新、SAALCO 自身の v1.2 への移行 | §10 | 10.1、11.5、15 |

順1は規則の意味を変えないため、最初に実装してよい。順4・5は承認の意味を変えるため、順2・3が動いてから実装する。

---

## 4. セッションの区切りと `saalco context`

### 4.1 `saalco approve` の完了表示

承認に成功したら、標準出力の最後に次を表示する。

```text
Approved: <path> (version <n>)
Next: start a new session and run `saalco context <F-nnn> --phase <phase>`
```

- `<phase>` は §4.3 の工程のうち、承認した文書の次の工程とする。複数の文書を承認した場合は、最も後ろの工程の次とする。
- Feature 外の文書（`docs/project.md` など）を承認した場合は、`Next:` 行を出さない。
- 表示は英語とする（ツール出力のため。規則 11.5）。

### 4.2 `saalco context <F-nnn> [--phase <phase>] [--json]`

新しいセッションのエージェントが最初に読むブリーフィングを、決定論的に出力する。ファイルは書かない。LLM を使わない。

出力する内容：

1. Feature の ID・名前・Tier・Tier の承認状態
2. 現在の工程（`--phase` が無ければ §4.3 の規則で推定する）
3. 各文書の状態（存在、`status`、承認が current か、hash の不一致）
4. 依存閉包：この Feature の項目と、`covers:` を上流へ辿って到達する項目の一覧。各項目は ID・見出し・`verify:`・ファイルパスと行範囲だけを出し、本文は出さない
5. 回答済みの問いカード：問いと回答を1件1行で出す
6. 未回答の問いカード（`open`・`held`）と、それが `blocks` している項目
7. この工程で参照すべき規則の節番号（§4.3 の表）
8. `saalco check`（静的）の ERROR・WARNING の件数と、この Feature に関係するものの1行ずつの要約
9. 次に読むべきファイルと行範囲

上限：テキスト出力は、項目数が多くても200行を超えないようにする。超える場合は依存閉包を Feature 内の項目と直接の上流に絞り、残りは件数だけ出す。

### 4.3 工程

| 工程 `--phase` | 推定条件（上から最初に当てはまるもの） | 参照する規則の節 |
|---|---|---|
| `req` | REQ 文書が無い、または未承認 | 4.1、6.4 |
| `ad` | Tier M/L で AD が無い、または未承認 | 4.2 |
| `dd` | DD（Tier L は MD も）が無い、未承認、または H3 の問いカードが未回答 | 4.3、4.4、3.4、6.4 |
| `test-spec` | Tier が要求する試験仕様が無い | 4.5、5.2 |
| `impl` | `verify: test` の項目に紐付くテストが PASS していない | 4.6、4.7、6.6 |
| `verification` | current Evidence が無い、または `check --verification` が ERROR | 4.8、7、8 |
| `acceptance` | 上記を全て満たす | 4.9、9 |

---

## 5. 問いカード（kind `Q`）

### 5.1 3つの分類

設計中にエージェントが当たる判断は、次の3つに分ける。

| 分類 | 誰が決めるか | 人間への見せ方 |
|---|---|---|
| 問い（`question`） | 人間 | 選択肢を比べて選ばせる |
| 確認（`confirm`） | エージェントが決めた。ただし格上げ対象（§9）に触れる | 「こうした。帰結はこう。異議はある？」と聞く |
| 記録のみ | エージェント | 人間には見せない。追跡できるように設計文書に残す |

- 問いカードは、判断に当たった作業中のエージェントが、その時点で書く。別のエージェントに書かせない（全文を読み直すことになるため）。
- エージェントは問いカードを書き出したら停止し、セッションを終える。問いカードがそのまま引き継ぎ書になる。
- 回答するのは人間だけであり、`saalco review` を使う（§7）。

### 5.2 配置

```
docs/features/F-nnn_<name>/questions/Q-nnnn.md
```

1枚につき1ファイルとする。Feature に属さない問いは `docs/questions/Q-nnnn.md` に置き、`feature: -` とする。

### 5.3 文書ヘッダ

規則 6.3 のとおり、フラットな `key: value` だけで書く。リスト記法・コメントは使わない。複数の値はカンマ区切りとする。

```text
---
kind: Q
id: Q-0003
feature: F-003
gate: H3
type: question
status: open
covers: REQ-0006, DD-0006
escalated_by: external_if
blocks: DD-0006
answer:
answered_by:
answered_at:
answer_hash:
---
```

| キー | 値 | 書く人 |
|---|---|---|
| `kind` | `Q` | `saalco new q` |
| `id` | `Q-nnnn` | `saalco new q` |
| `feature` | `F-nnn` または `-` | `saalco new q` |
| `gate` | `H1` / `H2` / `H3` / `H4` / `H6` | `saalco new q` |
| `type` | `question` / `confirm` | `saalco new q` |
| `status` | `open` / `answered` / `held` / `withdrawn` | 作成時 `open`。`answered`・`held` は `saalco review` だけが書く。`withdrawn` はエージェントが `open` のカードにだけ書ける |
| `covers` | 関係する項目ID（カンマ区切り、または `-`） | エージェント |
| `escalated_by` | 格上げの理由（§9.1 の分類、カンマ区切り） | `saalco new q --escalated-by` だけ |
| `blocks` | 答えが出るまで実装できない項目ID | エージェント |
| `answer` | `question` は選んだ記号（`A` 等）・`free`・`hold`。`confirm` は `no_objection`・`objection` | `saalco review` だけ |
| `answered_by` | `git config user.name` | `saalco review` だけ |
| `answered_at` | タイムゾーン付き ISO 8601 | `saalco review` だけ |
| `answer_hash` | §6.2 | `saalco review` だけ |

### 5.4 本文（`type: question`）

見出しは英語で固定する（機械照合のため）。本文は日本語で書く（規則 11.5）。

```markdown
## Question
uv run --locked をどこまで付ける？

## Context
--locked は uv.lock が古いと実行を止める。付けないと実行中に lock が書き換わりうる。

## Options
- A: テストだけ
  - Consequence: 速い。ゲート・Coverage 書き出し中の lock 変更に気づけない
- B: uv run で始まる全コマンド
  - Consequence: Evidence の lock 固定が全体で保証される。既存コマンド定義を書き換える

## Recommendation
B。Evidence の前提が一部でも崩れると、再現性の主張ができないため。

## Answer
<!-- saalco review が書き込む。エージェントは編集しない -->

## References
DD-0006 / docs/features/F-003_locked-uv-evidence/30-detailed-design.md
```

- 節の順は `Question` → `Context` → `Options` → `Recommendation` → `Answer` → `References` に固定する。推奨を選択肢の後に置くのは、先に推奨を見ると選択肢を公平に読まなくなるためである。
- `Options` は2つ以上とし、記号は `A`・`B`… の英大文字とする。各選択肢に `Consequence:` を必ず付ける。実装の説明ではなく「何が起きるか」を書く。
- `Context` に長さの上限は設けない。ただし、答えるために他の文書を開く必要が無いように書く。
- 回答の種類は「選ぶ」「自由記述」「保留」の3つである。自由記述と保留の理由は `## Answer` 節に書かれる。

### 5.5 本文（`type: confirm`）

```markdown
## Decision
（エージェントが決めたこと）

## Consequence
（それによって何が起きるか。格上げの理由に当たる影響を必ず書く）

## Answer
<!-- saalco review が書き込む。エージェントは編集しない -->

## References
```

### 5.6 `saalco new q`

```text
saalco new q [--feature F-nnn] --gate H3 [--type question|confirm] [--escalated-by <category>[,<category>]] "<title>"
```

- 台帳（`docs/ids.ledger`）から `Q-nnnn` を採番し、§5.2 の場所に雛形を作る。`<title>` は `## Question`（`confirm` では `## Decision`）の最初の行に入れる。
- `--type` の既定は `question` とする。
- `--escalated-by` には、その時点で §9 の検出に実際に現れている分類だけを指定できる。現れていない分類を指定したら exit 2 で拒否する。

### 5.7 取り下げ

エージェントは、`open` のカードに限り `status: withdrawn` にでき、そのとき `## Withdrawal reason` 節を `## Answer` の前に追加する。回答済み（`answered`・`held`）のカードは取り下げられない。判断を変えたい場合は、新しいカードを作り、`covers` で同じ項目を指す。

---

## 6. `saalco check` に追加する検査

### 6.1 静的検査（`saalco check`）

| # | 検査 | 結果 |
|---|---|---|
| Q-1 | 問いカードのヘッダの必須キー欠落、未定義の値、§5.4・§5.5 の節の欠落・順序違い | ERROR |
| Q-2 | `question` の `Options` が2つ未満、または `Consequence:` の無い選択肢がある | ERROR |
| Q-3 | `answered`・`held` なのに `answer_hash` などの回答キーが無い、または `open` なのに回答キーや `## Answer` の本文がある（`saalco review` 以外で回答が書かれた） | ERROR |
| Q-4 | 回答済みのカードの現在のhashが `answer_hash` と一致しない（回答後に問いが変わった） | ERROR |
| Q-5 | `blocks` にある項目について、そのカードが `open`・`held`、または `confirm` で `objection` のまま、その項目に対応する実装がある（規則 4.6 と同じ方法で判定する） | ERROR |
| Q-6 | 判断項目の `decision:` 行（§8.1）が、存在しない、別 Feature の、または回答済みでないカードを指している | ERROR |
| Q-7 | `withdrawn` のカードに `## Withdrawal reason` 節が無い | ERROR |
| Q-8 | §9 で検出した格上げ対象に、対応する回答済みのカードが無い | ERROR |

Q-5 と Q-8 は、規則 6.8・4.6 と同じく DEV による例外の照合対象とする（規則番号は 3.4 と 6.9）。

### 6.2 `answer_hash` の計算

- SHA-256 を使い、改行を LF に正規化する。
- 対象は、ヘッダのうち `status`・`answer`・`answered_by`・`answered_at`・`answer_hash` を除いたキーと、本文全体（`## Answer` 節を含む）である。
- したがって、回答後に問い・選択肢・回答のどれを変えても Q-4 で検出される。

---

## 7. `saalco review`

### 7.1 呼び出し

```text
saalco review <F-nnn> [--gate H1|H2|H3|H4|H6]
```

- 対象 Feature の未回答のカード（`open`・`held`）を、`--gate` があればその承認点に絞って、1件ずつ示す。
- **stdin が TTY でなければ exit 2 で拒否する。** エージェントが使える非対話のオプション（`--answer` など）は作らない。
- 例外として、環境変数 `SAALCO_ALLOW_NONTTY_REVIEW=1` のときだけ、標準入力から1行ずつ回答を読む（§7.5）。SAALCO 自身のテスト専用であり、`AGENTS.md` には書かない。
- **限界：** TTY の要求は、エージェントが誤って回答してしまうことを防ぐためのものであり、人間だけが答えることを強制するものではない（環境変数を設定すれば回避できる）。人間が答えたことの真正性は、`saalco approve` と同じく手続きで担保する。README とマニュアルにこの限界を書く。

### 7.2 問い（`question`）の回答

1. `Question`・`Context`・`Options`（各 `Consequence` を含む）・`Recommendation` の順に表示する。
2. 選択肢を矢印キーで選び、Enter で決定する。選択肢の後ろに「自由記述」と「保留」を並べる。
3. 自由記述を選んだときだけ入力欄を開く（`$EDITOR` があればエディタ）。保留では理由の入力を任意で求める。
4. ツールが `## Answer` 節と回答キーを書き込む（`answer`、`answered_by`、`answered_at`、`answer_hash`、`status`）。保留は `status: held`、`answer: hold` とする。

### 7.3 確認（`confirm`）の回答

1. 対象の確認を一覧で表示する（`Decision` と `Consequence`）。
2. 異議のある項目だけをスペースで選ぶ。何も選ばずに Enter を押すと「全て異議なし」とする。
3. 異議を付けた項目だけ、理由の入力に進む。
4. 異議なしは `answer: no_objection`、異議ありは `answer: objection` とし、どちらも `status: answered` とする。`objection` のカードが `blocks` している項目は実装できない（Q-5）。エージェントは設計を直し、新しいカードを作る。

### 7.4 承認点の承認

H1〜H3 のカードを全て回答し、保留と異議が無くなったら、続けて承認に進む。

1. 承認する文書のパスと、H3 では判断項目の一覧（ID・見出し・根拠のカードと回答）を表示する。
2. `承認する？ [y/N]` を聞く。`y` のときだけ、その承認点の文書を `saalco approve` と同じ処理で承認する（H3 では §8.2 のhash）。
3. 承認した文書のヘッダに `approved_with: Q-0003, Q-0004` を書き、承認に含めた回答を記録する。
4. 完了表示は §4.1 と同じとする。

`saalco approve <path>` は残す。問いカードが無い承認点（例：問いの無い REQ）では、従来どおり `approve` を使う。H3 で `decision:` を持つ項目があるのに、それが指すカードが回答済みでなければ、`approve` は exit 2 で拒否する。

### 7.5 テスト用の非対話入力（`SAALCO_ALLOW_NONTTY_REVIEW=1`）

1行が1回答に対応する。

| 対象 | 行の形式 |
|---|---|
| 問い | `A`（記号）／ `free:<text>` ／ `hold:<text>` |
| 確認の一覧 | 空行（全て異議なし）／ `object:Q-0005:<reason>` を必要な数だけ並べ、最後に空行 |
| 承認の確認 | `y` ／ `n` |

### 7.6 UI の実装

- 選択 UI は Python 標準ライブラリの `curses` で作る。`curses` が使えない環境では、番号を入力して Enter で決める形に切り替える。
- 新しい依存は追加しない（依存を足す場合は H4 の承認が必要になるため）。

---

## 8. 判断項目と承認hash

### 8.1 判断項目

詳細設計（`30-detailed-design.md`）とモジュール設計（`35-module-design.md`）の項目のうち、`decision:` 行を持つものを**判断項目**とする。

```markdown
### DD-0006: uv run に --locked を付ける範囲

covers: REQ-0006
verify: review
decision: Q-0003

（本文）
```

- `decision:` には、その判断の根拠になった回答済みのカード（`question` または `confirm` の `no_objection`）の ID を書く。カンマ区切りで複数書ける。
- `decision:` の無い項目を**細部**とする。
- 基本設計（AD）と要件（REQ）は、従来どおり文書全体を承認する。

### 8.2 H3 の承認hash

DD・MD の承認hashは、文書全体ではなく判断項目の集合にかける。

- 対象：承認関連キー（`status`・`version`・`approved_by`・`approved_at`・`approved_hash`・`approved_with`）を除くヘッダ、判断項目の ID の一覧（昇順）、判断項目それぞれの見出し行と本文（次の項目見出しの前まで）。
- 改行を LF に正規化し、SHA-256 で計算する。
- 結果：細部の追加・変更では承認は失効しない。判断項目の本文の変更、判断項目の追加・削除、`decision:` 行の削除（判断項目から細部への格下げ）では失効する。
- `00-meta.md`（Tier）は、従来どおり文書全体のhashで承認する。

### 8.3 `verify:` の制約と充足条件

| 項目 | 使える `verify:` | `test` の充足条件 |
|---|---|---|
| REQ・AD・判断項目 | `test` / `review` / `static` | Specification-derived Test（`verifies`）が1件以上あり、最新 Evidence で PASS（従来どおり） |
| 細部 | `test` / `static` | `verifies` または `impl_aware` のテストが1件以上その項目を指し、最新 Evidence で PASS。かつ、その項目の `covers:` の上流が verified である |

- 細部に `verify: review` を書いたら ERROR とする（承認されない項目を「承認済みで改変されていない」ことで検証できないため）。
- 細部の `test` を `impl_aware` で満たせるのは、細部の保証がシステムの責任（Verification）であり、人間の承認に基づかないためである。RTM には、どちらの種類のテストで満たしたかを表示する。

### 8.4 Specification-derived Test の導出元

`verifies` のテストを作ってよい導出元は、承認済みの REQ・AD・判断項目と、公開インターフェース（シグネチャ・型・docstring）に限る。細部の本文から作ったテストは `impl_aware` とする。

---

## 9. 格上げ対象の検出

### 9.1 分類

| 分類 | 検出方法（決定論的） |
|---|---|
| `dependency` | `pyproject.toml` の `[project].dependencies`・`[project.optional-dependencies]`・`[dependency-groups]` の変更、または `uv.lock` の変更 |
| `external_if` | `docs/project.md` の `escalate.public_paths:` に挙げたパス（カンマ区切り、前方一致）のファイルの変更 |
| `side_effect` | `src/` の Python ファイルで、`escalate.side_effect_modules:` に挙げたモジュールの import 文が追加されたこと |
| `tier` | `00-meta.md` の `tier:` の変更 |

- `escalate.side_effect_modules:` の既定値（`saalco init` が書く）は `subprocess, socket, shutil, sqlite3, pickle, shelve, urllib, http, requests, httpx` とする。
- 比較の基点は、HEAD の祖先にある Evidence のうち最も近いものの commit とする（差分 Coverage の基点と同じ選び方。ただし PASS かどうかは問わない）。Evidence が無ければ、最初の commit とする。
- 検出した分類ごとに、基点から HEAD までの間に追加された回答済みのカードで、`escalated_by` にその分類を持つものが1件以上あれば満たしたとする（Q-8）。

### 9.2 限界

この検出は網羅的ではない（動的 import、設定ファイル経由の外部通信などは検出できない）。検出されないことは「格上げ対象に触れていない」ことの証拠にならない。エージェントは、検出の有無にかかわらず、`AGENTS.md` の H4 の規定に従う。`saalco check` の出力と README にこの限界を書く。

### 9.3 `saalco check --escalations`

検出した分類と、その根拠（ファイル・行）、対応するカードの有無を一覧で出す。エージェントは、これを見て `saalco new q --escalated-by` でカードを作る。

---

## 10. 生成物・版・移行

### 10.1 `saalco init` の生成物

- `AGENTS.md` の雛形（v1.0指示書 §7.4）に、次を追加する。
  - Context budget の節（規則 3.5 の要約。承認点でセッションを終えること、`cat` でまとめて表示しないこと、サブエージェントの使い方）
  - 「判断に当たったら `saalco new q` で問いカードを書き、停止する。`## Answer` 節を編集しない。`saalco review` は人間専用」
  - 「新しいセッションは `saalco context F-nnn` から始める」
- `docs/project.md` の雛形に `escalate.public_paths:`（空）と `escalate.side_effect_modules:`（§9.1 の既定値）を追加する。
- 規則のコピーは v1.2 を配置し、`saal_rules_version: 1.2` を記録する。配布元であるリポジトリ直下の `SAAL-DEV-RULES.md` を、このとき v1.2 に更新する（それまでは v1.1 のまま置く）。

### 10.2 版

- SAALCO の版を `1.2.0` とする（規則の版と揃える）。
- `saal_rules_version: 1.1` のプロジェクトでは、§5〜§9 の検査（Q-1〜Q-8、§8 の hash と `verify:` の制約）を行わない。`saalco context` と §4.1 の表示は、規則の版によらず使える。
- 既存の承認済み DD は、`saal_rules_version: 1.2` に上げた時点で、`decision:` 行が無いため判断項目が0件になり、承認hashが一致しなくなる。移行は、判断項目に `decision:` を付ける（必要なら問いカードを後から作って回答する）か、DD 全体を判断項目として `saalco review` で承認し直すことで行う。移行手順をマニュアルに書く。

### 10.3 SAALCO 自身の移行

順1〜5の Feature が受け入れられた後、SAALCO 自身の `docs/project.md` を `saal_rules_version: 1.2` に上げる。それまでは v1.1 で運用する。

---

## 11. SAALCO 自身のテスト

- v1.0指示書 §19 に従う。
- `saalco review` の E2E テストは `SAALCO_ALLOW_NONTTY_REVIEW=1` と §7.5 の入力で行う。TTY でないときに拒否されることも試験する。
- `curses` の画面描画そのものは自動テストの対象にしない（`impl_aware` の範囲で、選択の状態遷移を関数として試験する）。

---

## 12. 完成条件

- §3 の順1〜6の Feature が、それぞれ H1〜H3 の承認を経て実装され、Evidence が current で、`70-acceptance.md` の受け入れ判断を人間が行える状態にある。
- `saalco context` の出力が、同じリポジトリの状態に対して常に同じである。
- `saalco review` 以外の方法で回答を書き込むと、`saalco check` が ERROR を出す。
- 判断項目の本文を変えると承認が失効し、細部を変えても失効しない。
- 格上げ対象を検出したのにカードが無いと、`saalco check` が ERROR を出す。
- 改善前後の比較（§13）の記録がある。

---

## 13. 効果の測り方

改善前後で、同じクラスの小さな Feature を比べる。

| 指標 | 測り方 |
|---|---|
| 入力換算トークン / Feature | 2026-11-01 の集計と同じ方法（cache read、サブエージェントの内訳を含む） |
| 人間の回答・承認の所要時間 | `saalco review` の開始から終了までの時間（ツールは記録しない。人間が記録する） |
| 承認内容の理解度 | 回答後に、判断と理由を自分の言葉で説明できるか（人間が自己評価する） |
| Traceability と Verification の結果 | RTM の欠落・破損が無いこと。同じ検証条件での PASS / FAIL / `NOT_EVALUATED` が劣化しないこと |

---

## 14. 今回は扱わないこと

- 問いカードの立て方を独立した AI にレビューさせる機能（ツールには組み込まない。運用で試す場合は、問いカードと差分だけを読ませる）
- 実験用の軽量トラック
- 試験仕様をテストコード側で正本にする案
- teach-back（承認時に、何を承認したかと主なリスクを1行書く）

---

## 改訂履歴

| 版 | 日付 | 内容 |
|---|---|---|
| r1 | 2026-11-01 | 初版。人間の指示によりエージェントが起草した。Notion の改良計画（段階1・段階2）の合意事項と、2026-11-01 の検討報告で挙げた5点（ヘッダ形式、TTY の位置付け、格上げの検出方法、`verify: review` との整合、原仕様の起草者）への解決を反映した |
