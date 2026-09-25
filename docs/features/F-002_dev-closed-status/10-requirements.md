---
kind: REQ
feature: F-002
status: approved
approved_by: ruri-sayo
approved_at: 2026-09-25T12:52:28+09:00
version: 1
approved_hash: 59665662be6792c92d8db9d581736935e092e224604c125e9d804c91f03ebe33
---

# Requirements

### REQ-0005: Validate DEV status values and closed records

covers: -
verify: test

`saalco check` が、DEV の `status` と閉じた DEV の記録を実装指示書 r4 §8.6 のとおり検査すること。

1. DEV の `status` が `open` と `closed` のどちらでもない場合、または `status` の行が無い場合は、ERRORとすること。
2. `closed` の DEV は、規則番号と `scope` が該当しても、ERRORをWARNINGに緩めないこと（`saalco check --verification` の Coverage、RTM、ゲート、verifies テスト、未承認の設計に対応する実装の各検査）。
3. `closed` の DEV に `closed_at` または `closed_condition` が無い場合、もしくは値が空の場合は、ERRORとすること。
4. `open` の DEV については、従来どおり例外として扱うこと。
