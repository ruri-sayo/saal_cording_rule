# Glossary

英語のコードと日本語の文書で用語を揃えるための対応表である（規則 11.5）。コード・コメント・docstring では「英語」列の語を、文書の本文では「日本語」列の語を使う。新しい用語を導入するときは、先にこの表へ追加する。

「照合対象」列が「はい」の語は、SAALCO が文字列として照合する固定の名前である。翻訳せず、文書の中でもそのまま書く。

## ID・台帳

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 台帳 | ledger | `docs/ids.ledger` | 採番したIDの正本。行は削除しない |
| 採番 | ID allocation | — | `saalco new` が台帳の最大値＋1でIDを割り当てること |
| 廃止 | retired | はい（`retired`） | 台帳の行の状態。廃止したIDの番号は再利用しない |
| 有効 | active | はい（`active`） | 台帳の行の状態。列が無い行も有効とみなす |
| 廃止の理由 | reason | — | 台帳の任意列 |
| 置き換え先 | superseded_by | — | 台帳の任意列。置き換え先のID |
| 項目 | item | — | `### ID: title` の見出しで宣言する要件・設計・試験仕様の単位 |

## 文書と項目の種別

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 要件 | requirement | はい（`REQ`） | |
| 基本設計 | architecture design | はい（`AD`） | |
| 詳細設計 | detailed design | はい（`DD`） | |
| モジュール設計 | module design | はい（`MD`） | |
| 単体テスト仕様 | unit test specification | はい（`UT`） | |
| 結合テスト仕様 | integration test specification | はい（`IT`） | |
| システムテスト兼E2Eテスト仕様 | system / E2E test specification | はい（`ST`） | |
| 試験仕様 | test specification | — | UT・IT・ST の総称 |
| 逸脱記録 | deviation record | はい（`DEV`） | 規則を満たさずに進める場合の記録 |
| 終了条件 | end condition | はい（`end_condition:`） | DEV を閉じる条件 |
| 設計との差分レポート | implementation diff | `45-implementation-diff.md` | 設計に無いが実装したもの、設計にあるが未実装のもの |
| 受け入れ判断 | acceptance | `70-acceptance.md` | 人間による Validation の記録 |
| 成果 | outcome | `80-outcome.md` | |
| 文書ヘッダ | front matter / header | — | `---` で囲むフラットな `key: value` |
| 上流を指す参照 | covers | はい（`covers:`） | |
| 検証方法 | verification method | はい（`verify:`） | `test` / `review` / `static` |

## 検証とテスト

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 検証 | Verification | — | 仕様どおりに作られているかの確認 |
| 妥当性確認 | Validation | — | 目的に合っているかの人間による確認 |
| 仕様由来テスト | Specification-derived Test | はい（`verifies`） | 上流文書と公開インターフェースだけから作るテスト。充足に数える |
| 実装参照テスト | Implementation-aware Test | はい（`impl_aware`） | 実装を見て書いたテスト。充足に数えない |
| 要求トレーサビリティマトリクス | RTM (requirements traceability matrix) | `docs/trace/rtm.csv` | |
| 検証済み | verified | はい（`verified`） | RTM の `verify_status` |
| 未検証 | unverified | はい（`unverified`） | |
| 古い（current Evidence が無い） | stale | はい（`stale`） | |
| 未評価 | NOT_EVALUATED | はい | 判定できないもの。PASS として扱わない |
| 未設定 | NOT_CONFIGURED | はい | コマンドが空のゲート。PASS ではない |
| 差分カバレッジ | diff coverage | — | 前回の基準点からの変更行のカバレッジ |
| 全体カバレッジ | total coverage | — | |
| 基準点 | baseline | — | 差分カバレッジを計算する起点の commit |
| 測定コンテキスト | coverage context | — | coverage.py が行ごとに記録する、実行したテストの名前 |

## 品質ゲートと Evidence

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 品質ゲート | quality gate | はい（`gate.NN.*`） | `docs/project.md` に書くコマンド |
| 証拠 | Evidence | `evidence/<commit>/<run-id>/` | ゲートとテストの実行記録 |
| 現行の証拠 | current Evidence | — | HEAD に対して有効な Evidence（暫定解釈 I-1） |
| 生データ | raw artifacts | `.saal/artifacts/` | ログ、coverage JSON 等。Git 管理しない |
| 証拠パッケージ | Evidence Package | `.saal/packages/` | Feature 単位の参照の集まり |
| 作業ツリー | working tree | — | |
| 総合結果 | overall | はい（`overall`） | manifest の総合判定 |

## 承認と役割

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 承認 | approval | `saalco approve` | 人間だけが行う |
| 承認hash | approved hash | はい（`approved_hash`） | 承認時の内容の SHA-256 |
| 内容hash | content hash | — | 承認関連キーを除いたヘッダと本文の SHA-256 |
| 改変検知 | tamper detection | — | 承認hashと内容hashの比較 |
| 人間の介入点 | human intervention point | はい（`H1`〜`H6`） | |
| 移行 | migration | — | 既存プロジェクトを規則へ移行すること（規則 10.5） |

## Outcome の記録項目（`80-outcome.md`）

規則 9.1／9.2 が定める記録項目のラベル。`saalco` はこれらの行を機械的に照合しない（照合対象は無し）ため、翻訳しても `checks`/`trace` の判定に影響しない。

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| コードcommit | code commit | — | research：Evidence記録済みの対象commit |
| データセットバージョン | dataset version | — | research |
| モデル | model | — | research：名称・バージョンまたは重みのhash |
| 設定 | config | — | research |
| 乱数シード | seed | — | research |
| 実行環境 | environment | — | research |
| 結果の所在 | result location | — | research |
| 結果hash | result hash | — | research |
| リリースバージョン | release version | — | system |
| 対象commit | target commit | — | system |
| デプロイ先 | deployment target | — | system |
| リリース日 | release date | — | system |

## コード記述規則の固定項目名

| 日本語 | 英語 | 照合対象 | 説明 |
|---|---|---|---|
| 責務 | Responsibilities | はい | module docstring の必須項目 |
| 担当しない範囲 | Non-responsibilities | はい | module docstring の推奨項目 |
| 副作用 | Side Effects | はい | 関数 docstring で明記が必須の項目 |
