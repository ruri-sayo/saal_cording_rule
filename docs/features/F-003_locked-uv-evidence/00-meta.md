---
kind: FEATURE
feature: F-003
status: draft
tier: M
---

# Meta

## Overview

`saalco evidence` が、Evidence の取得中にロックファイル（`uv.lock`）を作ったり書き換えたりしないようにする。`uv.lock` が無い場合と更新が必要な場合は、Evidence を取らずに止まり、`uv lock` の実行を案内する。`saalco init` でも `uv.lock` が無ければ案内する。2026-09-25 の人間の判断（B 案）による。

変更は `saalco.evidence`（Evidence の事前条件とコマンドの組み立て）と `saalco.commands`（init の案内）の2つのモジュールにまたがるため、Tier M とする。

