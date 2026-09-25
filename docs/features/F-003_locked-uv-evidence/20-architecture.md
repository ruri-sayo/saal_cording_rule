---
kind: AD
feature: F-003
status: approved
approved_by: ruri-sayo
approved_at: 2026-09-25T14:24:13+09:00
version: 1
approved_hash: f51f96e26785dc2fec2106f7bdc5a2d6b78e91eb3e85a24e7ed75c6493f9a797
---

# Architecture

### AD-0002: Lockfile precondition before evidence gates and tests

covers: REQ-0006
verify: test

Evidence の取得の流れに、ゲートより前の「事前条件の確認」段階を置く。現在の流れ（作業ツリーがクリーンであることの確認 → ゲート → `saalco check` → テスト → Coverage の書き出し）の、作業ツリーの確認の直後に、ロックファイルの確認を入れる。

- 責務の分担
  - `saalco.evidence`：ロックファイルの事前条件の確認と、`uv run` で始まるコマンドへの `--locked` の付与。
  - `saalco.commands`（init）：`uv.lock` が無いときの案内の出力。
  - 他のモジュール（checks、trace、ids など）は変更しない。
- 外部ツール：`uv`（`uv lock --check` と `uv run --locked`）と `git`（`uv.lock` が Git 管理されているかの確認）を、読み取りのためだけに呼ぶ。SAALCO は `uv lock` や `uv sync` を実行しない。
- 事前条件を満たさない場合は、Evidence の出力先（`evidence/<commit>/<run-id>/`、`.saal/artifacts/<commit>/<run-id>/`）を作る前に止まる。
