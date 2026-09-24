---
kind: UT
feature: F-001
status: draft
---

# Unit Test Spec

### UT-0001: Core document and ID unit tests

covers: DD-0001, MD-0001
verify: test

DD-0001／MD-0001 の各機能について、次を単体テストで確認する（実装指示書 §19「Unit」）。

- **ヘッダのパース・シリアライズ（`documents.parse_document`/`serialize`）**：入力＝`---`で囲んだフラットな `key: value` を含む文書テキスト。期待結果＝未知キーを保持すること、必須キー（`kind`・`feature`・`status`、`00-meta.md`では追加で`tier`）欠落を検出できること、キーの順序と本文が書き戻し時に変化しないこと。
- **content hash（`documents.content_hash`）**：入力＝承認関連5キー（`status`・`version`・`approved_by`・`approved_at`・`approved_hash`）を含む／含まない同一内容の文書。期待結果＝5キーを除いた内容から計算されること、改行がLFに正規化されること、同一内容からは常に同一hashになること。
- **原子的書き込み（`documents.atomic_write`）**：入力＝既存文書と変更後の内容。期待結果＝一時ファイル経由で置換され、書き込み中の異常でも元ファイルが破損しないこと。
- **台帳による採番（`ids.read_ledger`/`ids.allocate`）**：入力＝`docs/ids.ledger` の各種行（列省略、`status: active`、`status: retired`＋`reason`＋`superseded_by`）。期待結果＝種別ごとに「台帳内の同種別IDの最大値＋1」が採番されること、廃止済みIDの番号が再利用されないこと、`status` 列が無い行が `active` として扱われること、不正な `status` 値や存在しない／廃止済みの `superseded_by` を検出できること。
- **排他制御（`ids.lock`）**：入力＝同時に採番を試みる複数プロセス相当の呼び出し。期待結果＝`.saal/ids.lock` の `O_EXCL` 作成により後続の呼び出しが待機または失敗すること。
- **`covers:`/`verify:` のパース（`documents.items`）**：入力＝各種の `covers:`/`verify:` 行（正常、空、循環参照、種別表に無い参照、`verify:` 省略）。期待結果＝`verify:` 省略時に `test` とみなされること、種別ごとの参照可能表（§8.3）に従った妥当性判定ができること。
- **マーカーのAST解析（`markers.scan_tests`）**：入力＝関数デコレータ・クラスデコレータ・モジュール `pytestmark` それぞれで `verifies`/`impl_aware` を付けたテストコード、マーカー無しのテスト、`verifies(id, spec=...)` の2引数形式。期待結果＝実行・importせずに静的解析でき、マーカー無しは `impl_aware` として扱われること。
- **Tier規則（`templates.TIER_FILES`）**：入力＝Tier S/M/L。期待結果＝規則2.4の必須文書一覧と一致すること。
- **トレースグラフ（`trace.generate`）**：入力＝`covers:` で連結された REQ→AD→DD→MD→UT/IT/ST を含む文書群。期待結果＝REQからの到達可能な設計ID集合が正しく解決されること、同一入力から常に同一のRTM行（ID順ソート、タイムスタンプ無し）が生成されること。
- **差分Coverage計算（`evidence._coverage_result`/`_changed_lines`）**：入力＝`git diff -U0` 相当の追加・変更行と、coverage JSONの実行行・未実行行。期待結果＝差分カバレッジと全体カバレッジが正しく算出されること、コメント・空行のみの変更行が差分カバレッジ100%として扱われること、削除のみの変更が「変更行」に数えられないこと、算出不能な場合に `NOT_EVALUATED` を返すこと。
- **manifest生成（`evidence.create`）**：入力＝ゲート実行結果・テスト結果・Coverage結果のダミーデータ。期待結果＝実装指示書 §17 の記録項目（`schema_version` 等）を満たすJSONが生成されること。

### UT-0002: Ledger retirement unit test specification

covers: DD-0002, MD-0002
verify: test

次を確認する。`retired` のIDが不一致検査から外れること。廃止した番号の再利用（台帳の重複行、見出しでの再宣言）がERRORになること。廃止したIDへの参照（`covers:`、`verifies` マーカー、`rtm.csv`）がERRORになること。`status` の列が無い既存の行が従来どおり扱われること。`status` の値が不正な場合と `superseded_by` が不正な場合がERRORになること。採番で廃止した番号が再利用されないこと。

### UT-0003: Retire command unit test specification

covers: DD-0003, MD-0003
verify: test

`ids.retire`／`commands.retire` について、次を単体テストで確認する。

- 入力＝存在する `active` なID、`--reason`/`--superseded-by` あり／なし。期待結果＝対象行のみが `status: retired` に書き換えられ、他の行・他の列が変化しないこと。
- 入力＝存在しないID。期待結果＝exit code 2 相当の例外が送出され、対象ID・原因・次の操作を含むメッセージになること。
- 入力＝既に `retired` のID。期待結果＝exit code 2 相当の例外が送出されること。
- 入力＝存在しない／`retired` の `--superseded-by`。期待結果＝exit code 2 相当の例外が送出されること。
- 入力＝タブまたは改行を含む `--reason`。期待結果＝exit code 2 相当の例外が送出されること。
- 入力＝廃止操作の前後の台帳内容。期待結果＝行数が変化しないこと（削除されないこと）、書き換えが一時ファイル経由の原子的操作であること（中断を模した場合に元の行が残ること）。
- 入力＝廃止操作と同時に別のIDを採番する呼び出し。期待結果＝`.saal/ids.lock` により排他されること。

### UT-0004: Template language unit test specification

covers: DD-0004, MD-0004
verify: test

`templates.feature_document`／`templates.AGENTS` について、次を単体テストで確認する。

- 入力＝各 `name`（`45-implementation-diff.md`・`70-acceptance.md`・`80-outcome.md`、`project_type` は `research`/`system` 両方）。期待結果＝生成された本文が日本語であること（ASCII文字のみの行が無いこと、または既知の日本語文言と一致すること）。
- 入力＝同上。期待結果＝front matter のキー（`kind`・`feature`・`status`・`tier`）、節見出し（`## Overview`・`## Implemented but not designed`・`## Designed but not implemented`）が変更前と同じ英語表記のまま生成されること。
- 入力＝`saalco.templates.AGENTS`。期待結果＝日本語本文であり、現行 `AGENTS.md`（リポジトリルート）に記載の11項目と「## Language」節の内容と一致すること。
- 入力＝生成した文書を `documents.parse_document` でパースする。期待結果＝ヘッダの必須キーが欠落なく読めること（本文の言語変更がパーサに影響しないこと）。
- 入力＝生成した文書に対して `checks.run` を実行する（他の必須項目は別途満たした最小構成）。期待結果＝ヘッダ形式・Tier宣言・必須文書検査の結果が、本文が英語であった場合と変わらないこと。
