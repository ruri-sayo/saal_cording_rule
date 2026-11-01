# 問いカードの紙上試行（2026-11-01）

SAALCO v1.2 で導入する問いカード（`docs/input/SAALCO-v1.2-implementation-instructions.md` §5）の書式を、ツールを作る前に人間が実際に答えて評価するための試行である。対象は `docs/development-open-questions.md` に残っている未決事項のうち、選択肢を比べて決める形の3件である。

## 試行の制約

- `saalco new q` はまだ無いので、カードは**未採番**（`id: unassigned`）である。IDを手で採番しない規則に従い、ツールができた後に採番し直す。
- `saalco review` もまだ無いので、回答は人間がカードの `## Answer` 節に直接書く。エージェントは `## Answer` 節を編集しない。
- カードは `docs/features/` の外に置いているため、`saalco check` の対象にならない。

## 答え方

各カードの `## Answer` 節に、次のどれかを書く。

- `選択: A`（選択肢の記号）
- `自由記述: ...`
- `保留: ...`（理由があれば）

## 対象

| ファイル | 問い |
|---|---|
| [integration-exit-code-5.md](integration-exit-code-5.md) | 結合テストが1件も無いときの扱いをどうする？ |
| [init-coverage-subprocess-patch.md](init-coverage-subprocess-patch.md) | `saalco init` に Coverage の subprocess 設定を入れる？ |
| [evidence-exempt-user-docs.md](evidence-exempt-user-docs.md) | README・マニュアルの変更で Evidence を取り直さずに済ませる？ |

## Trial feedback

2026-11-01、3件ともチャットで回答された（各カードの `## Answer` 節）。書式の評価は一部だけ記録できた。

答えた後に、次を書いてほしい。v1.2 の指示書のカード書式（§5）は、この結果で直してから H1 に進める。

| 観点 | 記入欄 |
|---|---|
| 3件に答えるのにかかった時間 | 未記入 |
| 他の文書を開かずに答えられたか（開いたならどれを） | 開いていない。カード本文ではなく、チャットの選択UI（問い・Context・推奨を1段落にまとめ、各選択肢に帰結を付けたもの）で答えた（エージェントの観察） |
| 答えた判断を、自分の言葉で理由まで説明できるか | |
| 選択肢に欠けがあった・誘導的だと感じた箇所 | |
| Recommendation を選択肢の後に置く並びは読みやすかったか | |
| 書式で直したい点（節の順、長さ、Consequence の書き方など） | 未記入。注意：今回はファイルの書式そのものは読まれていない。ただし選択UIでは推奨が選択肢より前（問いの文中）に出ていた。3件とも推奨どおりに選ばれたことは、§5.4 の「推奨は選択肢の後」の効果を確かめる材料にはならない（エージェントの観察） |
