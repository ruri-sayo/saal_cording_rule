# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

SAALCO v1.2 実装指示書 §3 の順1として、Feature F-004（`saalco context` と、`saalco approve` の完了表示）を作った。新しいモジュール `saalco.context` を加え、`saalco.commands` と `saalco.cli` を変えるため Tier M とした。問いカードの出力は、後の Feature で追加する。

| 順 | 介入点 | パス | 承認すべき理由 |
|---|---|---|---|
| 1 | H1 | `docs/features/F-004_context-briefing/10-requirements.md` | REQ-0007（approve の完了表示）と REQ-0008（ブリーフィングの内容、200行の上限、ファイルを書かないこと、ERROR があっても exit 0）が意図どおりかを確認する |
| 2 | H2 | `docs/features/F-004_context-briefing/20-architecture.md` | AD-0003（`saalco.context` を読み取り専用で置き、既存モジュールは変えずに呼ぶ）を確認する |
| 3 | H3 | `docs/features/F-004_context-briefing/00-meta.md` | Tier M の妥当性を確認する |
| 4 | H3 | `docs/features/F-004_context-briefing/30-detailed-design.md` | DD-0007（工程の推定）・DD-0008（出力の形式と上限）・DD-0009（approve の表示）を確認する |

```bash
uv run saalco approve docs/features/F-004_context-briefing/10-requirements.md docs/features/F-004_context-briefing/20-architecture.md docs/features/F-004_context-briefing/00-meta.md docs/features/F-004_context-briefing/30-detailed-design.md
```

設計上、指示書から変えた判断が2点ある。

- 工程 `impl` を「紐付く仕様由来テストが無い」、`verification` を「RTM で verified でない」に分けた（DD-0007）。指示書の「テストが PASS していない」は、current な Evidence が無いと判定できないためである。
- approve の `Next:` 行の工程は、文書の種類から決めず、承認後の状態から推定する（DD-0009）。

`saalco approve` は TTY が要るため、クラウドのセッションでは実行できない。ローカルの端末で実行してほしい。設計の承認までは、仕様由来テストが無いため `saalco check` は ERROR 6件（F-004 の項目に verifies テストが無い）になる（F-003 と同じ）。

## Human decisions（`saalco approve` の対象外）

### 1. 問いカードの紙上試行

2026-11-01 に回答済み（下の Decided を参照）。

### 2. 規則 v1.2 と v1.2 実装指示書

2026-11-01、エージェントが決めた4点（§8.3、§9.1、§7.6、§10.2）について、人間から異議なしの回答を得た。

段階1の Context budget は、`AGENTS.md` ではなく `CLAUDE.md` に置いた。`AGENTS.md` は `saalco init` の雛形と同じ内容に保つことが要件（REQ-0004）で、仕様由来テストが一致を検査しているためである。Codex など `CLAUDE.md` を読まないエージェントには、SAALCO v1.2 で雛形を更新する（v1.2 実装指示書 §10.1）まで届かない。

承認・回答の後は、新しいセッションで再開してほしい（規則 3.5）。

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
- SAALCO 改良計画（Notion、2026-11-01）の段階1（Context budget）を `AGENTS.md` に反映すること（2026-11-01）
- 段階2のツールを作る前に、問いカードの紙上試行を行うこと（2026-11-01）
- 段階2の原仕様（v1.2 実装指示書）をエージェントが起草すること（2026-11-01）
- `saalco approve`・`saalco review` の TTY 要求は誤操作の防止と割り切り、人間だけの操作の強制は求めないこと（2026-11-01）
- 今回の改訂の版を v1.2 とし、main にマージすること（2026-11-01）
- 紙上試行の3件（2026-11-01、チャットで回答。各カードに転記）：結合テストが無いときは `NO_TESTS` として記録し Tier と照合する（B）／`saalco init` が `patch = ["subprocess"]` を書き coverage の下限を 7.10 にする（B）／`README.md` と `docs/manual.md` の2ファイルを名前で Evidence の例外に加える（B）。実装はまだしていない
- v1.2 実装指示書でエージェントが決めた4点に異議なし（2026-11-01）

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。
