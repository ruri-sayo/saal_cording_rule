"""Unit tests for saalco.documents: header parse/serialize, content hashing.

pytestmark impl_aware: these tests read saalco.documents source directly to derive
expectations (exact hash formula, header key ordering), so per AGENTS.md they are
implementation-aware, not specification-derived.
"""

from pathlib import Path

import pytest

from saalco.documents import (
    atomic_write,
    content_hash,
    items,
    parse_document,
    serialize,
    set_header,
)

pytestmark = pytest.mark.impl_aware


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "doc.md"
    path.write_text(text)
    return path


def test_parse_preserves_unknown_keys_and_order(tmp_path: Path):
    path = _write(
        tmp_path,
        "---\nkind: DD\nfeature: F-001\nstatus: draft\nx_custom: hello\nzeta: last\n---\nBody\n",
    )
    doc = parse_document(path)
    assert list(doc.header.items()) == [
        ("kind", "DD"),
        ("feature", "F-001"),
        ("status", "draft"),
        ("x_custom", "hello"),
        ("zeta", "last"),
    ]
    text = serialize(doc)
    assert text.index("x_custom") < text.index("zeta")
    assert "x_custom: hello" in text


def test_parse_missing_opening_delimiter(tmp_path: Path):
    path = _write(tmp_path, "kind: DD\n---\nBody\n")
    with pytest.raises(Exception, match="opening"):
        parse_document(path)


def test_parse_missing_closing_delimiter(tmp_path: Path):
    path = _write(tmp_path, "---\nkind: DD\nBody\n")
    with pytest.raises(Exception, match="closing"):
        parse_document(path)


def test_parse_duplicate_key_rejected(tmp_path: Path):
    path = _write(tmp_path, "---\nkind: DD\nkind: AD\n---\nBody\n")
    with pytest.raises(Exception, match="duplicate"):
        parse_document(path)


def test_parse_non_flat_line_rejected(tmp_path: Path):
    path = _write(tmp_path, "---\nkind: DD\nnotakeyvalue\n---\nBody\n")
    with pytest.raises(Exception, match="flat"):
        parse_document(path)


def test_content_hash_excludes_approval_keys(tmp_path: Path):
    path = _write(tmp_path, "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\nBody\n")
    doc = parse_document(path)
    before = content_hash(doc)
    set_header(
        doc,
        {
            "status": "approved",
            "version": "1",
            "approved_by": "A",
            "approved_at": "now",
            "approved_hash": "irrelevant",
        },
    )
    assert content_hash(doc) == before


def test_content_hash_normalizes_crlf(tmp_path: Path):
    lf = _write(tmp_path, "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\nBody\ntext\n")
    crlf = tmp_path / "crlf.md"
    crlf.write_bytes(
        b"---\r\nkind: DD\r\nfeature: F-001\r\nstatus: draft\r\n---\r\nBody\r\ntext\r\n"
    )
    doc_lf = parse_document(lf)
    doc_crlf = parse_document(crlf)
    assert content_hash(doc_lf) == content_hash(doc_crlf)


def test_content_hash_changes_with_body():
    from saalco.documents import Document

    base = Document(Path("x.md"), {"kind": "DD", "status": "draft"}, "body one\n")
    changed = Document(Path("x.md"), {"kind": "DD", "status": "draft"}, "body two\n")
    assert content_hash(base) != content_hash(changed)


def test_atomic_write_then_reparse_roundtrip(tmp_path: Path):
    path = tmp_path / "out.md"
    path.write_text("---\nkind: DD\nfeature: F-001\nstatus: draft\n---\nBody\n")
    doc = parse_document(path)
    doc.header["status"] = "approved"
    atomic_write(doc)
    reread = parse_document(path)
    assert reread.header["status"] == "approved"
    # No leftover temp files.
    assert list(tmp_path.glob(".out.md.*")) == []


def test_items_extracts_id_kind_title_and_meta(tmp_path: Path):
    path = _write(
        tmp_path,
        "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\n"
        "# Design\n\n### DD-0001: First item\n\ncovers: REQ-0001\nverify: test\n"
        "\n### DD-0002: Second item\n\ncovers: REQ-0001\nverify: review\n",
    )
    doc = parse_document(path)
    parsed = items(doc)
    assert [i.id for i in parsed] == ["DD-0001", "DD-0002"]
    assert parsed[0].kind == "DD"
    assert parsed[0].title == "First item"
    assert parsed[0].meta == {"covers": "REQ-0001", "verify": "test"}
    assert parsed[1].meta == {"covers": "REQ-0001", "verify": "review"}


def test_items_stops_meta_block_at_next_heading(tmp_path: Path):
    path = _write(
        tmp_path,
        "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\n"
        "### DD-0001: Item\n\ncovers: -\n\n## Notes\n\nverify: test\n",
    )
    doc = parse_document(path)
    (item,) = items(doc)
    assert item.meta == {"covers": "-"}
