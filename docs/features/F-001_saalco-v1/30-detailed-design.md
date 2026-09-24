---
kind: DD
feature: F-001
status: draft
---

# Detailed Design

### DD-0001: Implement deterministic document and verification services

covers: AD-0001
verify: test

### DD-0002: Ledger row status and retired-ID checks

covers: REQ-0002
verify: test

台帳の各行に任意の列 `status`（`active` / `retired`）、`reason`、`superseded_by` を追加する。列が無い既存の行は `active` とみなす。`saalco check` は次をERRORにする。

- `status` の値が不正であること
- `retired` のIDが台帳に複数行あること、文書の項目見出しや Feature ディレクトリとしてまだ宣言されていること（番号の再利用）
- `covers:`、`verifies` マーカー（参照先と `spec=`）、DEV の `scope:`、`docs/trace/rtm.csv` に、廃止したIDへの参照が残っていること
- `superseded_by` が、存在しないIDまたは廃止されたIDを指していること

`retired` のIDは、台帳と文書の不一致検査から除外する。採番は廃止したIDの行も含めた最大値＋1とする。
