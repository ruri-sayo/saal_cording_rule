from __future__ import annotations

FILE_FOR_KIND = {
    "REQ": "10-requirements.md",
    "AD": "20-architecture.md",
    "DD": "30-detailed-design.md",
    "MD": "35-module-design.md",
    "UT": "40-unit-test-spec.md",
    "IT": "50-integration-test-spec.md",
    "ST": "60-system-e2e-spec.md",
    "DEV": "90-deviations.md",
}

COMMON = [
    "00-meta.md",
    "10-requirements.md",
    "30-detailed-design.md",
    "40-unit-test-spec.md",
    "45-implementation-diff.md",
    "60-system-e2e-spec.md",
    "70-acceptance.md",
    "80-outcome.md",
    "90-deviations.md",
]
TIER_FILES = {
    "S": COMMON,
    "M": COMMON + ["20-architecture.md", "50-integration-test-spec.md", "60-system-e2e-spec.md"],
    "L": COMMON
    + [
        "20-architecture.md",
        "35-module-design.md",
        "50-integration-test-spec.md",
        "60-system-e2e-spec.md",
    ],
}

KIND_FOR_FILE = {
    "00-meta.md": "FEATURE",
    "10-requirements.md": "REQ",
    "20-architecture.md": "AD",
    "30-detailed-design.md": "DD",
    "35-module-design.md": "MD",
    "40-unit-test-spec.md": "UT",
    "45-implementation-diff.md": "IMPLEMENTATION_DIFF",
    "50-integration-test-spec.md": "IT",
    "60-system-e2e-spec.md": "ST",
    "70-acceptance.md": "ACCEPTANCE",
    "80-outcome.md": "OUTCOME",
    "90-deviations.md": "DEV",
}


def feature_document(name: str, feature: str, tier: str, project_type: str) -> str:
    kind = KIND_FOR_FILE[name]
    extra = f"tier: {tier}\n" if name == "00-meta.md" else ""
    heading = name.removesuffix(".md").split("-", 1)[-1].replace("-", " ").title()
    body = f"\n# {heading}\n"
    if name == "00-meta.md":
        body += "\n## Overview\n\n"
    elif name == "45-implementation-diff.md":
        body += "\n## Implemented but not designed\n\n- None\n\n## Designed but not implemented\n\n- None\n"
    elif name == "70-acceptance.md":
        body += "\nHuman-only validation record. SAALCO does not decide acceptance.\n"
    elif name == "80-outcome.md":
        fields = (
            [
                "code commit",
                "dataset version",
                "model",
                "config",
                "seed",
                "environment",
                "result location",
                "result hash",
            ]
            if project_type == "research"
            else ["release version", "target commit", "deployment target", "release date"]
        )
        body += "\n" + "".join(f"- {field}:\n" for field in fields)
    return f"---\nkind: {kind}\nfeature: {feature}\nstatus: draft\n{extra}---\n{body}"


def project_document(name: str, project_type: str, language: str) -> str:
    return f"""---
kind: PROJECT
name: {name}
type: {project_type}
language: {language}
saal_rules_version: 1.0
saalco_version: 1.0.0
raw_evidence_location: .saal/artifacts
raw_evidence_retention: until next release
gate.01.format: uv run ruff format --check .
gate.02.lint: uv run ruff check .
gate.03.typecheck: uv run mypy src
gate.04.secret_scan:
gate.05.dependency_audit:
gate.06.static_analysis:
test.unit: uv run pytest tests/unit
test.integration: uv run pytest tests/integration
test.e2e: uv run pytest tests/e2e
---

# {name}
"""


AGENTS = """# SAAL development instructions

- `docs/rules/SAAL-DEV-RULES.md` is normative; `saal` and `saalco` are aliases.
- Do not modify `docs/input/`. Write derived artifacts under `docs/features/`.
- Never allocate IDs manually; use `saalco new`.
- Only a human may run `saalco approve`. Stop and request approval with exact paths.
- Agents must not mark `70-acceptance.md` accepted or PASS.
- Create and obtain approval for Tier-required design/test specs before implementation.
- Specification-derived tests use only upstream documents and public interfaces; otherwise mark `impl_aware`.
- Obtain H4 approval before dependency changes or undesigned external I/O/persistence/device effects.
- Record implementation/design differences in `45-implementation-diff.md`.
- Run `saalco check` before claiming completion; commit all changes before Evidence.
- Never falsify markers, verification, or status to pass; record deviations with `saalco new dev`.
"""
