# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

**再確認のお願い**：`10-requirements.md`（REQ-0001）、`20-architecture.md`（AD-0001）、`30-detailed-design.md`（DD-0001）、`35-module-design.md`（MD-0001）は、これまで見出しのみで本文が空だった。今回、実装指示書から逆起こしして本文を新たに書いた（規則10.5「既存機能について、要件と設計を現状から逆起こしして文書化し、人間が承認する」）。過去にこれらの文書を確認したことがある場合でも、本文は新規である前提で再度読んでから承認すること。

## Design documents（`saalco approve` の対象）

| 順 | 介入点 | パス | 承認すべき理由 |
|---|---|---|---|
| 1 | H1 | `docs/features/F-001_saalco-v1/10-requirements.md` | REQ-0001（v1.0 の製品範囲。本文を今回新規に執筆）、REQ-0002（IDの廃止）、REQ-0003（`saalco retire` コマンド。今回追加）、REQ-0004（生成テンプレートの日本語化。今回追加）が意図どおりかを確認する |
| 2 | H2 | `docs/features/F-001_saalco-v1/20-architecture.md` | AD-0001（本文を今回新規に執筆）。CLI 層とドメインモジュールの分離、データフロー、外部ツール（git・uv・pytest・coverage.py）の扱いという構造方針を確認する |
| 3 | H3 | `docs/features/F-001_saalco-v1/00-meta.md` | SAALCO v1.0 を Tier L とすることの妥当性を確認する（暫定解釈 I-7） |
| 4 | H3 | `docs/features/F-001_saalco-v1/30-detailed-design.md` | DD-0001（本文を今回新規に執筆）、DD-0002（台帳の行の状態と廃止IDの検査）、DD-0003（`saalco retire` の入力検証と原子的書き換え。今回追加）、DD-0004（テンプレート日本語化の対象・非対象。今回追加）の設計判断と検証方法を確認する |
| 5 | H3 | `docs/features/F-001_saalco-v1/35-module-design.md` | MD-0001（本文を今回新規に執筆）、MD-0002（ids・checks モジュールの責務）、MD-0003（ids・commands モジュールへの `retire` 追加。今回追加）、MD-0004（templates モジュールの文言変更範囲。今回追加）を確認する（Tier L で必須） |

1〜5 がすべて承認されると、DEV-0001 のうち規則 4.6 の部分が終了条件を満たす。

## Human decisions（`saalco approve` の対象外）

| 対象 | 確認してほしいこと |
|---|---|
| `docs/features/F-001_saalco-v1/90-deviations.md` の DEV-0001 のクローズ | 対象規則 6.8・10.5 の終了条件が 2026-09-24 に満たされた（`saalco check --verification` が ERROR 0件、RTM の REQ-0001〜0004 がすべて verified）。DEV を閉じる（`status:` を変更し、`rule:` から 6.8・10.5 を外す）かどうかを人間が判断する。DEV の `status:` に使う値（例：`closed`）は仕様 §8.6 に定義が無いため、あわせて決める |

## Decided（2026-09-24 に人間が判断済み）

- DEV-0001 の対象規則・scope・終了条件と、`decided_by: ruri-sayo`
- 規則 v1.1（第11.5項 記述言語）の発行
- 実装指示書 r3（§9 の台帳の `status`・`reason`・`superseded_by`）
- `saalco retire` コマンドの新設（REQ-0003 以下。REQ → 設計 → 承認の順で進める）
- 生成する雛形（文書の雛形と `AGENTS.md` の雛形）の本文の日本語化（REQ-0004 以下）
- `docs/glossary.md` の「Outcome の記録項目」節の訳語
- `docs/input/` の仕様書の写しを r3 に更新すること（人間の指示により、エージェントが写しを更新した）
- H1〜H3 の設計文書5件の承認（`saalco approve` により記録済み）
- DEV-0001 のうち規則 4.6 の終了（承認の記録を受けて `rule:` から外した）

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。

## 承認後の次工程

Design documents（1〜5）が承認されたあと、実装を見ない別コンテキストのエージェントが、承認済みの文書と公開インターフェース定義だけから Specification-derived Test（`verifies` マーカー付き）を作成する（規則 5.2、実装指示書 §20「Codex はこれらを draft のまま残し、承認は人間が行う」に準ずる運用）。このエージェントには実装コードを見せない状態で起動すること。
