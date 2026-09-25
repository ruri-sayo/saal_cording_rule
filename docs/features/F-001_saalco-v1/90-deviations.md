---
kind: DEV
feature: F-001
status: draft
---

# Deviations

### DEV-0001: SAALCO bootstrap before design approval and RTM verification

rule: 6.8, 10.5
scope: F-001, src/saalco/, tests/
status: closed
reason: SAALCO は、自身の SAAL 文書（REQ・AD・DD・MD）が承認される前に実装された（規則 4.6 からの逸脱）。既存のテストは実装を見て書いたため impl_aware であり、Specification-derived Test が無いので RTM の REQ は verified にならない（規則 6.8 からの逸脱）。SAALCO 自身への適用は既存プロジェクトの移行として扱い、移行中の状態をここに記録する（規則 10.5、実装指示書 §20）。
resolution: 人間が H1〜H3 の承認を行ったあと、承認済みの文書と公開インターフェースだけから、実装を見ない別コンテキストで Specification-derived Test を作成し、RTM の全項目を verified にする。
end_condition: 4.6 = H1〜H3 の承認対象（10-requirements.md、20-architecture.md、00-meta.md、30-detailed-design.md、35-module-design.md）がすべて承認された時点で終了（2026-09-24 に承認が記録されたため終了し、rule から外した）; 6.8 = RTM の全項目が verified になった時点で終了（2026-09-24、REQ-0001〜0004 の全行が verified になり条件を満たした）; 10.5 = 4.6 と 6.8 がともに終了した時点で終了（2026-09-24 に条件を満たした）
decided_by: ruri-sayo
decided_at: 2026-09-24
closed_at: 2026-09-25
closed_condition: 6.8 = RTM の全項目（REQ-0001〜0004）が verified になった; 10.5 = 4.6 と 6.8 がともに終了した
