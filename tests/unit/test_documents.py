from pathlib import Path

import pytest

from saalco.documents import content_hash, parse_document, serialize

pytestmark = pytest.mark.impl_aware


def test_parse_serialize_and_hash(tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text("---\nkind: DD\nfeature: F-001\nstatus: draft\n---\nBody\n")
    doc = parse_document(path)
    assert doc.header["kind"] == "DD"
    before = content_hash(doc)
    doc.header.update(
        status="approved", approved_by="A", approved_at="now", approved_hash="x", version="1"
    )
    assert content_hash(doc) == before
    assert serialize(doc).startswith("---\nkind: DD")
