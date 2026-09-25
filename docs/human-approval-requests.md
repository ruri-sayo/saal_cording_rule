# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

F-001 の設計文書5件は承認済みである（下の「Decided」を参照）。今回は、DEV の `status` を検査する新しい Feature F-002（Tier S）の文書の承認をお願いする。F-001 の承認済み文書を変更しないよう、別の Feature に分けた。

| 順 | 介入点 | パス | 承認すべき理由 |
|---|---|---|---|
| 1 | H1 | `docs/features/F-002_dev-closed-status/10-requirements.md` | REQ-0005（DEV の `status` の値の検査、`closed` の DEV を許容に使わないこと、`closed_at`・`closed_condition` の必須化）が意図どおりかを確認する |
| 2 | H3 | `docs/features/F-002_dev-closed-status/00-meta.md` | F-002 を Tier S とすることの妥当性を確認する（暫定解釈 I-7） |
| 3 | H3 | `docs/features/F-002_dev-closed-status/30-detailed-design.md` | DD-0005 の設計判断と検証方法を確認する（Tier S のため MD は DD に統合） |

```bash
uv run saalco approve docs/features/F-002_dev-closed-status/10-requirements.md docs/features/F-002_dev-closed-status/00-meta.md docs/features/F-002_dev-closed-status/30-detailed-design.md
```

1〜3 と下の実装指示書 r4 が承認されたあと、実装を見ないエージェントに Specification-derived Test を書かせ、SAALCO を実装する。

## Human decisions（`saalco approve` の対象外）

| 対象 | 確認してほしいこと |
|---|---|
| `SAALCO-v1.0-implementation-instructions.md`（改訂版 r4） | §8.6 の改訂内容（DEV の `status` の値 `open` / `closed`、`closed` の DEV を許容に使わないこと、`closed_at`・`closed_condition`、未定義の値をERRORとすること）を承認するか |
| `docs/input/SAALCO-v1.0-implementation-instructions.md` | 写しは r3 のままである。r4 に更新するか（前回と同じく、指示があればエージェントが更新する） |
| `docs/features/F-001_saalco-v1/90-deviations.md` の DEV-0001 | 2026-09-25 の判断により閉じる。三浦さんが `status: closed` と `closed_at:` を記入する。`closed_condition:`（満たした終了条件）も人間の記入欄としたので、あわせて記入する（例：`6.8 = RTM の全項目が verified になった; 10.5 = 4.6 と 6.8 がともに終了した`）。エージェントはどの欄も記入しない |

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
- DEV の `status` に `closed` を追加する仕様改訂（r4）を行うこと（内容の承認は上の「Human decisions」）

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。
