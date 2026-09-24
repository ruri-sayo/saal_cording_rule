# Human approval requests

SAALCO（エージェント）は、以下のどの文書も承認していない。人間が上から順に内容を確認し、問題が無ければ `saalco approve` を実行する。

## Design documents（`saalco approve` の対象）

| 順 | 介入点 | パス | 承認すべき理由 |
|---|---|---|---|
| 1 | H1 | `docs/features/F-001_saalco-v1/10-requirements.md` | REQ-0001（v1.0 の製品範囲）と、今回追加した REQ-0002（IDの廃止）が意図どおりかを確認する |
| 2 | H2 | `docs/features/F-001_saalco-v1/20-architecture.md` | CLI 層とドメインモジュールの分離という構造方針を確認する |
| 3 | H3 | `docs/features/F-001_saalco-v1/00-meta.md` | SAALCO v1.0 を Tier L とすることの妥当性を確認する（暫定解釈 I-7） |
| 4 | H3 | `docs/features/F-001_saalco-v1/30-detailed-design.md` | DD-0001 と、今回追加した DD-0002（台帳の行の状態と廃止IDの検査）の設計判断と検証方法を確認する |
| 5 | H3 | `docs/features/F-001_saalco-v1/35-module-design.md` | MD-0001 と、今回追加した MD-0002（ids・checks モジュールの責務）を確認する（Tier L で必須） |

1〜5 がすべて承認されると、DEV-0001 のうち規則 4.6 の部分が終了条件を満たす。

## Human decisions（`saalco approve` の対象外）

| 対象 | 確認してほしいこと |
|---|---|
| `docs/features/F-001_saalco-v1/90-deviations.md` の DEV-0001 | 規則逸脱の承認（H4）。対象規則（4.6・6.8・10.5）、scope、終了条件が意図どおりか。`decided_by` には 2026-09-24 の指示を出した人として `ruri-sayo`（git の user.name）を記入した。別の名前にすべきなら修正する |
| `SAAL-DEV-RULES.md` と `docs/rules/SAAL-DEV-RULES.md`（v1.1） | 第11.5項（記述言語）を追加した版を発行してよいか。front matter の `status: released` と発行日 2026-09-24 はエージェントが記入した |
| `SAALCO-v1.0-implementation-instructions.md`（改訂版 r3） | §9 の改訂内容（台帳の `status`・`reason`・`superseded_by`）が意図どおりか |
| `docs/input/SAALCO-v1.0-implementation-instructions.md` | エージェントは `docs/input/` を変更しないため、原仕様書の写しは r2 のまま残っている。r3 に更新するかどうかを人間が判断し、更新する場合は人間が行う |

## Test specifications

`40-unit-test-spec.md`、`50-integration-test-spec.md`、`60-system-e2e-spec.md` は、上の設計文書の確認に使う draft の入力である（規則 2.4 で人間の承認対象になっているのは REQ・AD・DD・MD）。既存の自動テストは意図的に `impl_aware` としている。承認のあと、承認済みの文書と公開インターフェースだけから、別のコンテキストで Specification-derived Test を作成する。
