---
kind: Q
id: unassigned
feature: -
gate: -
type: question
status: open
covers: -
escalated_by:
blocks:
answered_by:
answered_at:
answer_hash:
---

## Question

結合テストが1件も無いとき、`test.integration` のゲートをどう扱う？

## Context

`test.integration` の既定値は `uv run pytest tests/integration` である。`tests/integration/` にテストが1件も無いと、pytest は終了コード5（テストが無い）で終わり、ゲートは FAIL になる。

結合テスト仕様が不要な Tier S だけのプロジェクトでは、これが必ず起きる。今は `docs/project.md` の `test.integration:` を空にして `NOT_CONFIGURED` にする回避策をマニュアル（4.8）に書いているだけである。2026-09-27、マニュアル用のデモプロジェクト（Tier S）で見つかった。

注意点：Tier M/L の Feature は結合テストが必須である（規則 2.4）。扱いを緩めた結果、本来必要な結合テストが無いのに通ってしまうことは避けたい。

## Options

- A: 今のまま（終了コード5は FAIL。Tier S だけなら利用者が `test.integration:` を空にする）
  - Consequence: ツールは変わらない。後から Tier M の Feature を足しても、設定が空のままだと結合テストが走らず、`NOT_CONFIGURED` のまま気付けない。
- B: 終了コード5を新しい結果 `NO_TESTS` として記録する。Tier M/L の Feature があるのに `NO_TESTS` なら FAIL、Tier S だけなら FAIL にしない
  - Consequence: Tier S のプロジェクトは設定なしで通る。Tier M を足した時点で自動的に止まる。結果の種類が1つ増え、manifest・summary・RTM の表示が変わる。
- C: 終了コード5は FAIL のまま。`saalco init` が「Tier S だけなら `test.integration:` を空にする」案内を表示する
  - Consequence: 判定は今と同じく厳しい。案内を見落とすと、初回の `saalco evidence` で FAIL する。A と同じく、後から Tier M を足したときの見落としは防げない。

## Recommendation

B。「テストが無い」を PASS とも FAIL とも偽らずに記録でき、Tier との照合で本当に足りないときだけ止められるため。

## Answer

<!-- 人間が記入する。エージェントは編集しない -->

## References

- `docs/development-open-questions.md`（Open、B、2026-09-27 の記録）
- `docs/manual.md` 4.8
- 規則 2.4（Tier ごとの必須成果物）
