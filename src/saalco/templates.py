"""Document templates for SAAL features and projects.

Responsibilities:
- Provide mapping between item kinds (REQ, DD, etc.) and file names.
- Define Tier-specific required documents.
- Generate document skeletons with proper headers and metadata.

Non-responsibilities:
- Content validation.
- Dynamic content generation (only static templates).
"""

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
    "M": COMMON + ["20-architecture.md", "50-integration-test-spec.md"],
    "L": COMMON + ["20-architecture.md", "35-module-design.md", "50-integration-test-spec.md"],
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
    """Generate a feature document template.

    Args:
        name: Document file name (e.g., '30-detailed-design.md').
        feature: Feature ID (e.g., 'F-001').
        tier: Tier (S, M, or L).
        project_type: Project type ('research' or 'system').

    Returns:
        Document text with header and body skeleton.
    """
    kind = KIND_FOR_FILE[name]
    extra = f"tier: {tier}\n" if name == "00-meta.md" else ""
    heading = name.removesuffix(".md").split("-", 1)[-1].replace("-", " ").title()
    body = f"\n# {heading}\n"
    if name == "00-meta.md":
        body += "\n## Overview\n\n"
    elif name == "45-implementation-diff.md":
        body += (
            "\n## Implemented but not designed\n\n- なし\n\n"
            "## Designed but not implemented\n\n- なし\n"
        )
    elif name == "70-acceptance.md":
        body += "\n人間のみによる妥当性確認の記録である。SAALCOは受け入れ判断を行わない。\n"
    elif name == "80-outcome.md":
        fields = (
            [
                "コードcommit",
                "データセットバージョン",
                "モデル",
                "設定",
                "乱数シード",
                "実行環境",
                "結果の所在",
                "結果hash",
            ]
            if project_type == "research"
            else ["リリースバージョン", "対象commit", "デプロイ先", "リリース日"]
        )
        body += "\n" + "".join(f"- {field}:\n" for field in fields)
    return f"---\nkind: {kind}\nfeature: {feature}\nstatus: draft\n{extra}---\n{body}"


def project_document(name: str, project_type: str, language: str) -> str:
    """Generate a project.md template.

    Args:
        name: Project name.
        project_type: Project type ('research' or 'system').
        language: Programming language ('python' or 'other').

    Returns:
        Project document text with standard gates, tests, and metadata.
    """
    return f"""---
kind: PROJECT
name: {name}
type: {project_type}
language: {language}
saal_rules_version: 1.1
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

- `docs/rules/SAAL-DEV-RULES.md` が正本である。規則中の `saal` コマンドは `saalco` と同じものである。
- `docs/input/` は人間が与えた原仕様書である。変更しない。導出した要件等は `docs/features/` に書く。
- IDを手で採番しない。必ず `saalco new` を使う。
- `saalco approve` は人間専用である。Agent は実行しない。承認が必要になったら、承認対象のパスを列挙して人間に依頼し、そこで停止する。
- Agent は `70-acceptance.md`（受け入れ判断）を accepted や PASS 等に書き換えない。
- 実装前に、Tier が要求する設計文書と試験仕様を作り、人間の承認を得る。
- Specification-derived Test（`verifies`）は、上流文書と公開インターフェースだけから作る。それ以外は `impl_aware` とする。
- 依存の追加・更新、設計に無い外部通信・ファイル書き込み・永続化・実機駆動は、人間の承認（H4）を得てから行う。
- 実装と設計の差分は `45-implementation-diff.md` に記録する。
- 完了を主張する前に `saalco check` を実行する。Evidence を取る前に全ての変更を commit する。
- check を通すために、マーカー・verify・status を事実と異なる値に変えない。逸脱は `saalco new dev` で記録する。

## Language

規則 11.5（記述言語）に従う。

| 対象 | 言語 |
|---|---|
| コード、コメント、docstring | 英語 |
| 設計文書・仕様書・報告文書の本文 | 日本語 |
| 見出し、front matter のキー、ID、機械が照合する固定の項目名（`Responsibilities`、`Side Effects` など） | 英語のまま固定 |

- 用語は `docs/glossary.md` の対応表に合わせる。新しい用語は先に対応表へ追加する。
- 既存文書で本文が英語のものは、指示があるまで翻訳しない。改訂する文書と新しく書く文書には、この規則を適用する。
- サブエージェントに作業を任せるときは、この節をプロンプトに含める。
"""
