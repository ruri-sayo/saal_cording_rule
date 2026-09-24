---
kind: ST
feature: F-001
status: draft
---

# System E2E Spec

### ST-0001: Installed CLI end-to-end workflow

covers: REQ-0001
verify: test

`uv tool install .` でインストールした実際の `saalco`（`saal` 別名を含む）を、subprocess経由で一時ディレクトリに対して実行し、REQ-0001に列挙した一連の操作が実利用と同じ入口から成立することを確認する（実装指示書 §19「E2E」）。

1. `saalco init --non-interactive` で一時ディレクトリを初期化する。期待結果＝§7.1の標準構造一式が生成されること。
2. `saalco new feature` でFeatureを作成する。期待結果＝`F-nnn` が採番され、Tier別の文書一式が生成されること。
3. `saalco new req`・`ad`・`dd`・`ut`・`st` で各項目を作成する。期待結果＝各IDが重複無く採番され、`covers:`/`verify:` の雛形が追記されること。
4. サンプル実装とテスト（`verifies` マーカー付き）を `src/`・`tests/` に配置する。
5. `saalco approve` で必要な文書を承認する（TTY経由、または `SAALCO_ALLOW_NONTTY_APPROVE=1`）。期待結果＝`status: approved` と承認hashが記録されること。
6. 変更一式をcommitする。
7. `saalco check` を実行する。期待結果＝ヘッダ・Tier・ID台帳・`covers:`/`verifies` 参照・承認hashの検査が全てPASSすること（テスト実行前のため exit code 0）。
8. `saalco evidence` を実行する。期待結果＝ゲート・テストが実行され、`evidence/<commit>/<run-id>/` と `.saal/artifacts/` が生成されること。
9. `evidence/` と `docs/trace/` をcommitする。
10. `saalco check --verification` を実行する。期待結果＝手順9のEvidenceがcurrentとして扱われ、PASSすること（`NOT_EVALUATED` が紛れ込んでいないこと）。
11. `saalco trace` を実行する。期待結果＝`docs/trace/rtm.csv`・`rtm.md` が生成され、対象REQの `verify_status` が `verified` であること。

### ST-0002: Retired ID handling through the CLI

covers: REQ-0002
verify: test

CLIから、IDの採番、台帳の行への廃止情報の追記、文書項目の削除を順に行い、`saalco check` が不一致を報告しないことを確認する。続けて、廃止したIDを `covers:` から参照し、`saalco check` がERRORを報告することを確認する。

### ST-0003: Retire command end-to-end workflow

covers: REQ-0003
verify: test

インストールした `saalco` で、次を一連の操作として確認する。

1. `saalco new dd "..." --feature F-001` で試験用のIDを採番する。
2. `saalco retire <ID> --reason "統合のため" --superseded-by <別ID>` を実行する。期待結果＝コマンドが廃止したIDと、文書からの見出し・参照削除を促す案内を出力すること。
3. `docs/ids.ledger` を確認する。期待結果＝対象行に `retired`・理由・置き換え先が追記され、行が削除されていないこと。
4. 文書に対応する項目見出しが残っている場合、`saalco check` を実行する。期待結果＝「廃止した番号の再利用」としてERRORが報告されること。
5. 項目見出しを文書から削除したうえで再度 `saalco check` を実行する。期待結果＝台帳と文書の不一致としては報告されないこと（DD-0002の除外規則）。
6. 廃止したIDを別項目の `covers:` から参照させ、`saalco check` を実行する。期待結果＝廃止したIDへの参照としてERRORが報告されること。
7. 存在しないIDや既に廃止済みのIDに対して `saalco retire` を実行する。期待結果＝exit code 2 で拒否されること。
