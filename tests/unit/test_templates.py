"""Unit tests for saalco.templates: Japanese body text, fixed English machine-matched parts.

pytestmark impl_aware: asserts on exact generated template strings (rule 11.5 / DD-0004 /
MD-0004 / UT-0004).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saalco.documents import parse_document
from saalco.templates import AGENTS, feature_document

pytestmark = pytest.mark.impl_aware

_JAPANESE_BODY_NAMES = ["45-implementation-diff.md", "70-acceptance.md", "80-outcome.md"]


def _has_japanese(text: str) -> bool:
    return any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" for ch in text)


@pytest.mark.parametrize("name", _JAPANESE_BODY_NAMES)
@pytest.mark.parametrize("project_type", ["research", "system"])
def test_feature_document_body_is_japanese(name: str, project_type: str):
    text = feature_document(name, "F-001", "S", project_type)
    body = text.split("---\n", 2)[2]
    assert _has_japanese(body), f"{name} ({project_type}) body has no Japanese text: {body!r}"


@pytest.mark.parametrize("name", _JAPANESE_BODY_NAMES)
@pytest.mark.parametrize("project_type", ["research", "system"])
def test_feature_document_fixed_english_parts_unchanged(name: str, project_type: str):
    text = feature_document(name, "F-001", "S", project_type)
    assert "kind:" in text
    assert "feature: F-001" in text
    assert "status: draft" in text
    if name == "45-implementation-diff.md":
        assert "## Implemented but not designed" in text
        assert "## Designed but not implemented" in text


def test_feature_document_00_meta_overview_heading_unchanged():
    text = feature_document("00-meta.md", "F-001", "S", "system")
    assert "## Overview" in text
    assert "tier: S" in text


def test_feature_document_80_outcome_labels_match_glossary_research():
    text = feature_document("80-outcome.md", "F-001", "S", "research")
    for label in (
        "コードcommit",
        "データセットバージョン",
        "モデル",
        "設定",
        "乱数シード",
        "実行環境",
        "結果の所在",
        "結果hash",
    ):
        assert f"- {label}:" in text


def test_feature_document_80_outcome_labels_match_glossary_system():
    text = feature_document("80-outcome.md", "F-001", "S", "system")
    for label in ("リリースバージョン", "対象commit", "デプロイ先", "リリース日"):
        assert f"- {label}:" in text


def test_agents_constant_is_japanese_and_matches_repo_root():
    assert _has_japanese(AGENTS)
    assert "## Language" in AGENTS
    root_agents = Path(__file__).resolve().parents[2] / "AGENTS.md"
    assert AGENTS == root_agents.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", _JAPANESE_BODY_NAMES)
@pytest.mark.parametrize("project_type", ["research", "system"])
def test_generated_document_still_parses(tmp_path: Path, name: str, project_type: str):
    """Body-language change must not break the flat key: value header parser."""
    text = feature_document(name, "F-001", "S", project_type)
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    doc = parse_document(path)
    assert doc.header["kind"]
    assert doc.header["feature"] == "F-001"
    assert doc.header["status"] == "draft"
