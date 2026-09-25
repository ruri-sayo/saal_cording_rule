---
kind: FEATURE
feature: F-002
status: approved
tier: S
approved_by: ruri-sayo
approved_at: 2026-09-25T12:52:28+09:00
version: 1
approved_hash: d4108cfbc30b1b1ea1116acaae9cd6c6b3ad3d76fd8e71f9d53ff377cd4d9303
---

# Meta

## Overview

実装指示書 r4 の §8.6 で定めた DEV の `status` の値（`open` / `closed`）と、閉じた DEV の記録欄（`closed_at`・`closed_condition`）を `saalco check` で検査する。F-001 の承認済み文書を変更せずに進めるため、別の Feature とした。影響は `saalco.checks` の検査1つに限られ、外部IFは変わらないため Tier S とする。

