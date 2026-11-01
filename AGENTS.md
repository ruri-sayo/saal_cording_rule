# SAAL development instructions

- `docs/rules/SAAL-DEV-RULES.md` が正本である。規則中の `saal` コマンドは `saalco` と同じものである。
- `docs/input/` は人間が与えた原仕様書である。変更しない。導出した要件等は `docs/features/` に書く。
- IDを手で採番しない。必ず `saalco new` を使う。
- `saalco approve` は人間専用である。Agent は実行しない。承認が必要になったら、承認対象のパスを列挙して人間に依頼し、そこで停止する。
- Agent は `70-acceptance.md`（受け入れ判断）を accepted や PASS 等に書き換えない。
- 実装前に、Tier が要求する設計文書と試験仕様を作り、人間の承認を得る。
- Specification-derived Test（`verifies`）は、上流文書と公開インターフェースだけから作る。それ以外は `impl_aware` とする。
- 依存の追加・更新、設計に無い外部通信・ファイル書き込み・永続化・実機駆動は、人間の承認（H4）を得てから行う。
- 実装と設計の差分は `45-implementation-diff.md` に記録する。
- 完了を主張する前に `saalco check` を実行する。Evidence を取る前に全ての変更を commit する。
- check を通すために、マーカー・verify・status を事実と異なる値に変えない。逸脱は `saalco new dev` で記録する。

## Language

規則 11.5（記述言語）に従う。

| 対象 | 言語 |
|---|---|
| コード、コメント、docstring | 英語 |
| 設計文書・仕様書・報告文書の本文 | 日本語 |
| 見出し、front matter のキー、ID、機械が照合する固定の項目名（`Responsibilities`、`Side Effects` など） | 英語のまま固定 |

- 用語は `docs/glossary.md` の対応表に合わせる。新しい用語は先に対応表へ追加する。
- 既存文書で本文が英語のものは、指示があるまで翻訳しない。改訂する文書と新しく書く文書には、この規則を適用する。
- サブエージェントに作業を任せるときは、この節をプロンプトに含める。

## Context budget

- 承認点（H1〜H3）で作業を止めたら、そのセッションは終える。次の工程は新しいセッションで、文書から再開する。承認を依頼して停止するときは、「承認後は新しいセッションで再開すること」を人間向けに一言添える。
- ファイルは `cat` でまとめて表示しない。`grep -n` で位置を特定し、必要な行範囲だけを読む。
- サブエージェントは、読む量が多く返す結果が短い作業（調査、ログ・テスト出力の解析、独立レビュー）に限って使う。
- Featureの実装や数ファイル程度の修正は、サブエージェントに渡さずメインで行う。
- サブエージェントに渡すときは、読むファイルと行範囲、返す結果の形式と長さの上限をプロンプトに書く。

## Rules version

- 規則の正本は v1.2 である。ただし、このリポジトリ（SAALCO 自身）は `docs/project.md` のとおり v1.1 で運用中である。v1.2 で追加した問いカード・判断項目・格上げ検出は、`docs/input/SAALCO-v1.2-implementation-instructions.md` の機能を実装し、移行するまで適用しない。Context budget（上の節）と記述言語（規則 11.5）は今から適用する。
- リポジトリ直下の `SAAL-DEV-RULES.md` は、`saalco init` が配布する規則のコピーである。SAALCO v1.2 を実装するまで v1.1 のまま置く。
