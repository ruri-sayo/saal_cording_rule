# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

現在、承認待ちの設計文書は無い（F-003 の4件は `saalco approve` により承認済み）。

## Human decisions（`saalco approve` の対象外）

### 1. 問いカードの紙上試行に答える

`docs/questions/` の3枚に答え、`docs/questions/README.md` の「Trial feedback」に評価を書いてほしい。答え方は README に書いた（`## Answer` 節に `選択: A` などを書く）。この結果で v1.2 実装指示書のカード書式（§5）を直してから、v1.2 の最初の Feature（`saalco context` と approve の完了表示）の H1 に進む。

| ファイル | 問い |
|---|---|
| `docs/questions/integration-exit-code-5.md` | 結合テストが1件も無いときの扱いをどうする？ |
| `docs/questions/init-coverage-subprocess-patch.md` | `saalco init` に Coverage の subprocess 設定を入れる？ |
| `docs/questions/evidence-exempt-user-docs.md` | README・マニュアルの変更で Evidence を取り直さずに済ませる？（判断者：三浦） |

### 2. 規則 v1.2 と v1.2 実装指示書の内容を確認する

- `docs/rules/SAAL-DEV-RULES.md`（v1.2）：第3.4項・第3.5項・第6.9項の追加、第3.2項・第4.3項・第5.2項・第6.4項・第6.5項・第11.5項・第13章・第15章の改訂。
- `docs/input/SAALCO-v1.2-implementation-instructions.md`（r1）：人間の指示によりエージェントが起草した。特に、エージェントが決めた次の4点を確認してほしい。
  - 細部の `verify: test` は `impl_aware` のテストでも満たせる（§8.3）。
  - 格上げ対象の検出は、依存・公開パス・副作用モジュールの import・Tier の4分類を、直前の Evidence からの差分で見る（§9.1）。
  - 選択 UI は標準ライブラリの `curses` で作り、依存を増やさない（§7.6）。
  - SAALCO の版を規則に揃えて `1.2.0` とする（§10.2）。

このリポジトリ自身は、移行するまで規則 v1.1 で運用する（`docs/project.md` は変えていない）。`saalco init` が配布するリポジトリ直下の `SAAL-DEV-RULES.md` も v1.1 のままである。

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

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。
