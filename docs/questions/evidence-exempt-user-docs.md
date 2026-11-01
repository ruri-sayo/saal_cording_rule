---
kind: Q
id: unassigned
feature: -
gate: -
type: question
status: answered
covers: -
escalated_by:
blocks:
answered_by:
answered_at:
answer_hash:
---

## Question

`README.md` と `docs/manual.md` を変更しても、Evidence が current のまま扱われるようにする？

## Context

Evidence は、対象 commit から HEAD までの変更が `evidence/`・`docs/trace/`・`docs/ids.ledger` に限られるときだけ current とみなす（暫定解釈 I-1）。そのため、利用者向けの文書を直すたびに `saalco evidence` を取り直し、RTM を同期する commit が2つ増える（2026-09-27 の README 日本語化とマニュアル追加で起きた）。

これらの文書は、品質ゲートやテストの結果に影響しない。一方で、例外のパスを増やすほど、「この Evidence は HEAD のコードを検証した」という主張の範囲を個別に説明する必要が出てくる。判断者は三浦。

## Options

- A: 加えない（今のまま）
  - Consequence: 主張の範囲は単純なまま（HEAD と同じ内容を検証した）。利用者向けの文書を直すたびに Evidence を取り直す。
- B: `README.md` と `docs/manual.md` の2ファイルだけを、ファイル名で加える
  - Consequence: この2ファイルの修正では Evidence を取り直さない。例外の範囲は明示的で狭い。利用者向けの文書を新しく足すたびに、例外の追加を判断し直す。
- C: 規則で管理していない文書をまとめて加える（`README.md` と、`docs/` のうち `features/`・`rules/`・`input/`・`project.md`・`trace/`・`ids.ledger` 以外）
  - Consequence: 文書の整備がいちばん楽になる。`docs/glossary.md` や `docs/questions/` の変更も Evidence の対象外になり、例外の範囲がパスの列挙ではなく「除外のルール」になる。

## Recommendation

B。取り直しの手間がかかっているのは実際にこの2ファイルであり、範囲を名前で固定しておけば、Evidence の主張を説明し直す必要が無いため。

## Answer

選択: B（2026-11-01。ファイルを編集できない環境だったため、人間がチャットの選択UIで回答し、人間の指示によりエージェントがここに転記した）

判断者は三浦とされていた。今回の回答は、チャットで回答した本人のものとして記録する。

## References

- `docs/development-open-questions.md`（Open、C、2026-09-27 の記録）
- 実装指示書 §1 の暫定解釈 I-1
