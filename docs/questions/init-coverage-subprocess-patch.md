---
kind: Q
id: unassigned
feature: -
gate: -
type: question
status: answered
covers: -
escalated_by: dependency
blocks:
answered_by:
answered_at:
answer_hash:
---

## Question

`saalco init` が生成する `pyproject.toml` に、Coverage の `patch = ["subprocess"]` を最初から入れる？

## Context

E2E テストは CLI をサブプロセスとして起動することが多い。coverage.py は、`[tool.coverage.run]` に `patch = ["subprocess"]` が無いと、サブプロセスの中で実行された行を数えない。

2026-09-27 のデモプロジェクトでは、この設定が無いと全体 Coverage が 55.56% で FAIL、設定すると 100% で PASS になった。この設定は coverage.py 7.10 以降でしか使えない。

依存の下限を変えることになるので、格上げ対象（依存）に当たる（`escalated_by: dependency`）。

なお、SAALCO 自身に出ている「reached by no verifies test」の WARNING 3件（`__init__.py`・`__main__.py`・`errors.py`）は、この設定では消えない。import 時に実行される行と `python -m saalco` の行は、テストごとの測定コンテキストに入らないためである。この問いとは別の問題である。

## Options

- A: 入れない（今のまま）。マニュアルに書くだけ
  - Consequence: E2E がサブプロセスで CLI を動かすプロジェクトでは、全体 Coverage が実態より低く出て FAIL しうる。原因に気付くまで調べる手間がかかる。
- B: `saalco init` が `patch = ["subprocess"]` を書き、dev 依存の coverage の下限を 7.10 にする。既存の `pyproject.toml` があるときは書き換えず、案内だけ出す
  - Consequence: 新しいプロジェクトは最初から実態どおりの Coverage になる。coverage.py 7.10 未満は使えなくなる。既存プロジェクトは手で直す必要がある。
- C: `saalco init` は書かない。`saalco check` が、設定が無いことを WARNING で知らせる
  - Consequence: 依存の下限を固定しない。WARNING を読まなければ、A と同じく Coverage が低く出る。

## Recommendation

B。Coverage が低く出る原因は利用者には分かりにくく、最初から正しく測れる方が「判定できないものを PASS にしない」方針と合うため。下限 7.10 は 2026-11 時点で十分古い。

## Answer

選択: B（2026-11-01。ファイルを編集できない環境だったため、人間がチャットの選択UIで回答し、人間の指示によりエージェントがここに転記した）

## References

- `docs/development-open-questions.md`（Open、B、2026-09-27 の記録とその追記）
- SAALCO 自身の `pyproject.toml` の `[tool.coverage.run]`
