# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

現在、承認待ちの文書は無い。

## Human decisions（`saalco approve` の対象外）

現在、判断待ちの事項は無い。

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
- DEV-0001 を閉じること（2026-09-25。`status: closed` とする）
- 実装指示書 r4（§8.6 の DEV の `status` の値 `open` / `closed`、`closed_at`・`closed_condition`）の承認と、`docs/input/` の写しの r4 への差し替え（人間の指示により、エージェントが写しを更新した）
- F-002 の設計文書3件の承認（`saalco approve` により記録済み）
- DEV-0001 を閉じる記入（`status: closed`、`closed_at`、`closed_condition`）。2026-09-25 の人間の指示により、この回に限りエージェントが記入した

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。
