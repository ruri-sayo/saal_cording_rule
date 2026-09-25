---
kind: FEATURE
feature: F-002
status: draft
tier: S
---

# Meta

## Overview

実装指示書 r4 の §8.6 で定めた DEV の `status` の値（`open` / `closed`）と、閉じた DEV の記録欄（`closed_at`・`closed_condition`）を `saalco check` で検査する。F-001 の承認済み文書を変更せずに進めるため、別の Feature とした。影響は `saalco.checks` の検査1つに限られ、外部IFは変わらないため Tier S とする。

