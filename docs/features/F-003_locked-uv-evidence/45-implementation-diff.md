---
kind: IMPLEMENTATION_DIFF
feature: F-003
status: draft
---

# Implementation Diff

## Implemented but not designed

- DD-0006 が文言を定めていない2つのエラー（`uv.lock` が Git 管理されていない場合、更新が必要な場合）のメッセージは、実装で英語の短い文を決めた。どちらも末尾は DD-0006 と同じ案内文（`uv lock` の実行、commit、再実行）である。

## Designed but not implemented

- なし

## Notes

- 2026-09-25、F-003 の実装の結果、F-001 の Specification-derived Test のうち2件（`tests/e2e/test_spec_system.py` と `tests/integration/test_spec_integration.py` の Evidence を取るテスト）が、`uv.lock` の無い一時プロジェクトで Evidence を取ろうとして exit 2 になり、広すぎるスキップ条件によってスキップされた。その結果、Evidence の総合結果は FAIL になった（テストの NOT_EVALUATED と、全体 Coverage が基準点の 88.01% から 87.84% に下がったため）。実装を読まない別のエージェントが、承認済みの文書（F-001、F-003）だけをもとに2件を修正した。一時プロジェクトで `uv.lock` を作って commit するようにし、スキップは `uv` が見つからない場合だけに狭めた。修正後の Evidence は PASS である。
- `saalco init` が生成する `pyproject.toml` には `[project]` の表が無い。この状態でも `uv lock` は成功するが、`requires-python` が無いという警告が出る。雛形の改善は今回の範囲外とした。

