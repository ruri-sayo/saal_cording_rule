---
kind: REQ
feature: F-001
status: draft
---

# Requirements

### REQ-0001: Operate the SAAL development lifecycle locally

covers: -
verify: test

### REQ-0002: Retire IDs without reusing their numbers

covers: -
verify: test

IDを廃止できること。廃止したIDの台帳の行は削除せず、その番号を二度と採番しない。廃止したIDに対応する文書項目が無くても、`saalco check` は台帳と文書の不一致として扱わない。廃止したIDの再利用と、廃止したIDへの参照の残存は `saalco check` がERRORにする（実装指示書 §9、改訂版 r3）。
