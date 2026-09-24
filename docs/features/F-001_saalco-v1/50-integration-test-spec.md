---
kind: IT
feature: F-001
status: draft
---

# Integration Test Spec

### IT-0001: CLI workflow integration test

covers: AD-0001
verify: test

AD-0001 で定義したCLI層とドメインモジュール間の連携を、実際のコマンド呼び出し（プロセス内呼び出しでよい）で確認する（実装指示書 §19「Integration」）。

- **init**：入力＝空ディレクトリ、`--type research` と `--type system` それぞれ。期待結果＝AD-0001記載の標準構造一式が生成され、`80-outcome.md` のテンプレートが種別に応じて異なること。既存 `src/`・`tests/` があるディレクトリでも既存ファイルが壊れないこと。
- **new**：入力＝`new feature` に続けて `new req|ad|dd|md|ut|it|st|dev`。期待結果＝`docs/ids.ledger` に行が追記され、対応する文書に項目が生成・追記されること。標準出力が採番したIDのみであること。
- **approve → 編集 → check FAIL → 再approve → PASS**：入力＝承認対象文書の承認、承認後の本文編集、`check` 実行、再承認。期待結果＝承認直後は `check` の承認hash整合検査がPASSし、編集後はhash不一致をERRORとして検出し、再承認後は再びPASSすること。
- **trace**：入力＝REQ〜STまでの `covers:` が連結された文書群。期待結果＝`docs/trace/rtm.csv`・`rtm.md` が生成され、`checks.py` が参照する項目・台帳・マーカーの情報が一致すること。
- **Evidence生成**：入力＝クリーンな作業ツリー。期待結果＝`evidence/<commit>/<run-id>/manifest.json`・`summary.md` と `.saal/artifacts/<commit>/<run-id>/` が生成されること。
- **dirty treeの拒否**：入力＝未commitの変更がある作業ツリー。期待結果＝`saalco evidence` がEvidenceを生成せず、exit code が非0であること。
