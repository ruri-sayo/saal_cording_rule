---
kind: PROJECT
name: fixture
type: system
language: python
saal_rules_version: 1.0
saalco_version: 1.0.0
raw_evidence_location: .saal/artifacts
raw_evidence_retention: until next release
gate.01.format:
gate.02.lint:
gate.03.typecheck:
gate.04.secret_scan:
gate.05.dependency_audit:
gate.06.static_analysis:
test.unit:
test.integration:
test.e2e:
---

# fixture
