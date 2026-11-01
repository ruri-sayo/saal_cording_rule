---
kind: REQ
feature: F-004
status: draft
---

# Requirements

### REQ-0007: approve prints a next-step hint for a new session

covers: -
verify: test

`saalco approve` は、承認に成功したら、次の工程を新しいセッションで始めるよう利用者に知らせること。

1. 承認した文書ごとに、標準出力に `Approved: <path> (version <n>)` の1行を出すこと。`<path>` はプロジェクトのルートからの相対パス（区切りは `/`）、`<n>` は承認後の `version` とする。
2. 続けて、承認した文書が属する Feature ごとに（Feature ID の昇順）、`` Next: start a new session and run `saalco context <F-nnn> --phase <phase>` `` の1行を出すこと。`<phase>` は、承認を記録した後のリポジトリの状態から REQ-0008 の工程の推定で求めた工程とする。
3. 承認が失敗した場合（TTY でない、`git config user.name` が無い、パスが不正など）は、1・2 を出さず、既存の動作（エラーメッセージと終了コード）を変えないこと。
4. 文書ヘッダに記録する内容（`status`・`approved_by`・`approved_at`・`approved_hash`・`version`）は変えないこと。

### REQ-0008: saalco context prints a deterministic session briefing

covers: -
verify: test

`saalco context <F-nnn> [--phase <phase>] [--json]` は、新しいセッションのエージェントが最初に読むブリーフィングを出力すること。

1. 出力は、Feature の ID・名前・Tier と Tier の承認状態、工程、Tier が要求する各文書の状態、項目の一覧、次に読むべき箇所、参照すべき規則の節、`saalco check`（静的）の結果の要約を含むこと。
2. 項目の一覧は、この Feature の項目と、`covers:` を上流へ辿って到達する他の Feature の項目からなり、各項目について ID・見出し・`verify:`・ファイルの相対パスと行範囲だけを示すこと。項目の本文は出さないこと。
3. 工程は `req`・`ad`・`dd`・`test-spec`・`impl`・`verification`・`acceptance` のいずれかとする。`--phase` を指定しなければ、リポジトリの状態から推定すること。指定した場合はその工程を使い、推定した工程も併せて示すこと。
4. 同じリポジトリの状態に対して、常に同じ出力になること（実行日時などを含めない）。
5. テキスト出力は200行を超えないこと。超える場合は項目の一覧を絞り、省いた件数を示すこと。
6. `--json` を指定したら、同じ内容を JSON で出力すること。JSON は行数で絞らない。
7. ファイルを書かず、作業ツリーを変えないこと。LLM や外部のネットワークを使わないこと。
8. 存在しない Feature を指定したら exit 2 とすること。`saalco check` が ERROR を出す状態でも、ブリーフィングは出して exit 0 とすること（ブリーフィングは判定ではないため）。
9. `docs/project.md` の `saal_rules_version` が 1.0・1.1 のどちらでも動作すること。
