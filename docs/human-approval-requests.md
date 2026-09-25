# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

`uv.lock` 問題の対応（B 案）として、新しい Feature F-003 を作った。`saalco.evidence` と `saalco.commands`（init）の2つのモジュールにまたがるため Tier M とし、基本設計（AD）と結合テスト仕様（IT）も用意した。`--locked` と `--frozen` の実際の挙動の確認結果は DD-0006 に記録した。

| 順 | 介入点 | パス | 承認すべき理由 |
|---|---|---|---|
| 1 | H1 | `docs/features/F-003_locked-uv-evidence/10-requirements.md` | REQ-0006（`uv.lock` が無い・Git 管理されていない・更新が必要な場合に exit 2 で止まること、`uv run --locked` の使用、init の案内）が意図どおりかを確認する |
| 2 | H2 | `docs/features/F-003_locked-uv-evidence/20-architecture.md` | AD-0002（ゲートより前に事前条件の確認段階を置くこと、モジュール間の責務の分担）を確認する |
| 3 | H3 | `docs/features/F-003_locked-uv-evidence/00-meta.md` | F-003 を Tier M とすることの妥当性を確認する |
| 4 | H3 | `docs/features/F-003_locked-uv-evidence/30-detailed-design.md` | DD-0006（uv の挙動の確認結果、事前条件の順序と終了コード、`--locked` の付与規則、init の案内）を確認する |

```bash
uv run saalco approve docs/features/F-003_locked-uv-evidence/10-requirements.md docs/features/F-003_locked-uv-evidence/20-architecture.md docs/features/F-003_locked-uv-evidence/00-meta.md docs/features/F-003_locked-uv-evidence/30-detailed-design.md
```

設計上、確認してほしい判断が2点ある。

- `--locked` を付けるのは、テストだけでなく、`uv run` で始まるゲートと Coverage の書き出しにも広げた。これらも `uv.lock` を書き換えうるためである。
- すでに `--frozen` を含むコマンドは書き換えない。事前条件の確認で `uv.lock` が最新であることを確かめているためである。

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
- `uv.lock` 問題を B 案（`uv.lock` が無い・古い場合は止めて `uv lock` を案内し、`uv run --locked` を使う）で対応すること（2026-09-25）

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。
