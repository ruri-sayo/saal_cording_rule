# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""Unit tests for DD-0001..0004 / MD-0001..0004, derived from UT-0001..0004.

Sources used (all under docs/, none of it src/ or tests/ implementation):
- docs/features/F-001_saalco-v1/30-detailed-design.md (DD-0001..0004)
- docs/features/F-001_saalco-v1/35-module-design.md (MD-0001..0004)
- docs/features/F-001_saalco-v1/40-unit-test-spec.md (UT-0001..0004)
- SAALCO-v1.0-implementation-instructions.md (r3) referenced sections
- public-interface.md (signatures/docstrings only)

`saalco retire` (REQ-0003/DD-0003/MD-0003) and Japanese AGENTS body (REQ-0004/DD-0004/
MD-0004) may be unimplemented or partially implemented at the time these tests run; that is
expected per the task brief and must not be worked around by weakening assertions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saalco import documents, errors, ids, markers, templates
from saalco import trace as trace_mod

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_git(root: Path) -> None:
    """Minimal local git identity, scoped to the temp repo only (never global config)."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "spec-test@example.com")
    _git(root, "config", "user.name", "Spec Test")


# ---------------------------------------------------------------------------
# DD-0001 / MD-0001 (UT-0001): document services, ID ledger, markers, templates, trace
# ---------------------------------------------------------------------------


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_header_roundtrip_preserves_unknown_keys(tmp_path: Path) -> None:
    # DD-0001 §"文書ヘッダとcontent hash": "未知のキーは保持し、書き戻すときにキーの
    # 順序と無関係な本文を変更しない".
    path = tmp_path / "doc.md"
    path.write_text(
        "---\n"
        "kind: DD\n"
        "feature: F-001\n"
        "status: draft\n"
        "custom_unknown_key: kept\n"
        "---\n\n"
        "# Body\n\ncontent line\n",
        encoding="utf-8",
    )
    doc = documents.parse_document(path)
    assert doc.header.get("custom_unknown_key") == "kept"
    text = documents.serialize(doc)
    path.write_text(text, encoding="utf-8")
    doc2 = documents.parse_document(path)
    assert doc2.header.get("custom_unknown_key") == "kept"
    assert doc2.header.get("kind") == "DD"
    assert "content line" in doc2.body


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_content_hash_excludes_approval_keys_and_is_deterministic(tmp_path: Path) -> None:
    # DD-0001: hash "status, version, approved_by, approved_at, approved_hash の5キーを
    # 除いたヘッダと本文を対象とする" and "同じ内容からは常に同じhashになること".
    path = tmp_path / "doc.md"
    base = "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\n\nbody text\n"
    path.write_text(base, encoding="utf-8")
    doc_a = documents.parse_document(path)
    hash_a1 = documents.content_hash(doc_a)
    hash_a2 = documents.content_hash(doc_a)
    assert hash_a1 == hash_a2

    approved = (
        "---\nkind: DD\nfeature: F-001\nstatus: approved\nversion: 3\n"
        "approved_by: someone\napproved_at: 2026-01-01T00:00:00+09:00\n"
        "approved_hash: deadbeef\n---\n\nbody text\n"
    )
    path.write_text(approved, encoding="utf-8")
    doc_b = documents.parse_document(path)
    hash_b = documents.content_hash(doc_b)
    assert hash_a1 == hash_b, "approval keys must not affect content_hash"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_content_hash_normalizes_line_endings(tmp_path: Path) -> None:
    # DD-0001: "改行はLFに正規化" before hashing.
    path_lf = tmp_path / "lf.md"
    path_crlf = tmp_path / "crlf.md"
    lf_text = "---\nkind: DD\nfeature: F-001\nstatus: draft\n---\n\nline one\nline two\n"
    crlf_text = lf_text.replace("\n", "\r\n")
    path_lf.write_text(lf_text, encoding="utf-8", newline="")
    path_crlf.write_text(crlf_text, encoding="utf-8", newline="")
    doc_lf = documents.parse_document(path_lf)
    doc_crlf = documents.parse_document(path_crlf)
    assert documents.content_hash(doc_lf) == documents.content_hash(doc_crlf)


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_atomic_write_round_trips_through_reparse(tmp_path: Path) -> None:
    # DD-0001: atomic_write is "一時ファイルへの書き出し、再パースで検証してから
    # 原子的に置換する".
    path = tmp_path / "doc.md"
    path.write_text("---\nkind: DD\nfeature: F-001\nstatus: draft\n---\n\nold body\n")
    doc = documents.parse_document(path)
    doc.header["status"] = "approved"
    documents.atomic_write(doc)
    reread = documents.parse_document(path)
    assert reread.header["status"] == "approved"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_ledger_allocate_is_sequential_per_kind(tmp_path: Path) -> None:
    # UT-0001: "種別ごとに「台帳内の同種別IDの最大値＋1」が採番されること".
    root = tmp_path
    (root / "docs").mkdir()
    first = ids.allocate(root, "REQ", "F-001", "First requirement")
    second = ids.allocate(root, "REQ", "F-001", "Second requirement")
    assert first == "REQ-0001"
    assert second == "REQ-0002"
    # A different kind starts its own sequence.
    ad_first = ids.allocate(root, "AD", "F-001", "First architecture item")
    assert ad_first == "AD-0001"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_ledger_status_column_missing_treated_as_active(tmp_path: Path) -> None:
    # implementation-instructions §9: "status の列が無い既存の行は、従来どおり有効な
    # IDとして扱う". UT-0001: "status 列が無い行が active として扱われること".
    root = tmp_path
    (root / "docs").mkdir()
    ledger = root / "docs" / "ids.ledger"
    ledger.write_text("REQ-0001\tF-001\t2026-01-01T00:00:00+09:00\tLegacy row\n")
    rows = ids.read_ledger(root)
    assert len(rows) == 1
    assert rows[0].status == "active"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_ledger_allocate_never_reuses_retired_number(tmp_path: Path) -> None:
    # implementation-instructions §9: "廃止したIDの行も最大値の計算に含めるため、
    # 廃止した番号が再利用されることは無い".
    root = tmp_path
    (root / "docs").mkdir()
    ledger = root / "docs" / "ids.ledger"
    ledger.write_text(
        "REQ-0001\tF-001\t2026-01-01T00:00:00+09:00\tOld\tactive\t\t\n"
        "REQ-0002\tF-001\t2026-01-01T00:00:00+09:00\tRetired one\tretired\tsuperseded\tREQ-0001\n"
    )
    new_id = ids.allocate(root, "REQ", "F-001", "New requirement")
    assert new_id == "REQ-0003"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_ids_lock_excludes_concurrent_allocation(tmp_path: Path) -> None:
    # UT-0001: ".saal/ids.lock の O_EXCL 作成により後続の呼び出しが待機または失敗すること".
    root = tmp_path
    (root / "docs").mkdir()
    with ids.lock(root), pytest.raises(errors.SaalcoError), ids.lock(root):
        pass  # nested lock acquisition must fail while held


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_document_items_default_verify_and_covers_dash_for_req(tmp_path: Path) -> None:
    # DD-0001 §8.2: "verify: の値は... 省略時は test とする. REQ項目は covers: - とする".
    path = tmp_path / "10-requirements.md"
    path.write_text(
        "---\nkind: REQ\nfeature: F-001\nstatus: draft\n---\n\n"
        "# Requirements\n\n"
        "### REQ-0001: Sample requirement\n\ncovers: -\n\nBody text.\n\n"
        "### REQ-0002: Another requirement\n\ncovers: -\nverify: review\n\nBody text.\n",
        encoding="utf-8",
    )
    doc = documents.parse_document(path)
    parsed = documents.items(doc)
    ids_by_id = {item.id: item for item in parsed}
    assert ids_by_id["REQ-0001"].meta.get("covers") == "-"
    # verify: omitted must default to "test" per DD-0001.
    assert ids_by_id["REQ-0001"].meta.get("verify", "test") == "test"
    assert ids_by_id["REQ-0002"].meta.get("verify") == "review"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_markers_scan_handles_function_class_module_and_unmarked(tmp_path: Path) -> None:
    # DD-0001 §"テストマーカー": AST-only, no import/execution; function/class/module
    # pytestmark decorators; "マーカーの無いテストは impl_aware として扱う";
    # UT-0001: "verifies(id, spec=...) の2引数形式" must be recognized.
    root = tmp_path
    unit_dir = root / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    (unit_dir / "test_sample.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.verifies('DD-0099')\n"
        "def test_function_level():\n"
        "    assert True\n\n"
        "@pytest.mark.verifies('DD-0100', spec='UT-0099')\n"
        "def test_function_level_with_spec():\n"
        "    assert True\n\n"
        "def test_unmarked():\n"
        "    assert True\n\n"
        "@pytest.mark.verifies('DD-0101')\n"
        "class TestClassLevel:\n"
        "    def test_method_a(self):\n"
        "        assert True\n\n"
        "    def test_method_b(self):\n"
        "        assert True\n",
        encoding="utf-8",
    )
    (unit_dir / "test_module_marker.py").write_text(
        "import pytest\n\n"
        "pytestmark = pytest.mark.verifies('DD-0102')\n\n"
        "def test_uses_module_marker():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    found = markers.scan_tests(root)
    by_nodeid: dict[str, list] = {}
    for marker in found:
        by_nodeid.setdefault(marker.nodeid, []).append(marker)

    func_markers = [
        m for nid, ms in by_nodeid.items() if nid.endswith("test_function_level") for m in ms
    ]
    assert any(m.marker == "verifies" and m.referenced_id == "DD-0099" for m in func_markers)

    func_spec_markers = [
        m
        for nid, ms in by_nodeid.items()
        if nid.endswith("test_function_level_with_spec")
        for m in ms
    ]
    assert any(
        m.marker == "verifies" and m.referenced_id == "DD-0100" and m.spec == "UT-0099"
        for m in func_spec_markers
    )

    unmarked = [m for nid, ms in by_nodeid.items() if nid.endswith("test_unmarked") for m in ms]
    assert unmarked, "unmarked tests must still be reported"
    assert all(m.marker == "impl_aware" for m in unmarked)

    class_markers = [
        m for nid, ms in by_nodeid.items() if "TestClassLevel::test_method_a" in nid for m in ms
    ]
    assert any(m.marker == "verifies" and m.referenced_id == "DD-0101" for m in class_markers)

    module_markers = [
        m for nid, ms in by_nodeid.items() if nid.endswith("test_uses_module_marker") for m in ms
    ]
    assert any(m.marker == "verifies" and m.referenced_id == "DD-0102" for m in module_markers)


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_tier_files_include_common_required_documents(tmp_path: Path) -> None:
    # implementation-instructions §10: "45-implementation-diff.md・70-acceptance.md・
    # 80-outcome.md・90-deviations.md は全Tierで生成する".
    common = {
        "45-implementation-diff.md",
        "70-acceptance.md",
        "80-outcome.md",
        "90-deviations.md",
    }
    for tier in ("S", "M", "L"):
        files = set(templates.TIER_FILES[tier])
        assert common <= files, f"Tier {tier} must include the common documents"


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_trace_generate_is_deterministic_and_sorted(tmp_path: Path) -> None:
    # UT-0001: "同一入力から常に同一のRTM行（ID順ソート、タイムスタンプ無し）が
    # 生成されること".
    from saalco import commands

    root = tmp_path
    _init_git(root)
    commands.init_project(root, "trace-proj", "research", "python", [])
    feature_id = commands.new_feature(root, "Trace Feature", "S", "trace")
    req_id, _ = commands.new_item(root, "req", feature_id, "Trace requirement")

    rows_first = trace_mod.generate(root, write=False)
    rows_second = trace_mod.generate(root, write=False)
    assert rows_first == rows_second, "same input must produce identical RTM rows"
    req_ids = [row["req_id"] for row in rows_first]
    assert req_ids == sorted(req_ids)
    assert req_id in req_ids
    for row in rows_first:
        assert "timestamp" not in row


@pytest.mark.verifies("DD-0001", spec="UT-0001")
@pytest.mark.verifies("MD-0001", spec="UT-0001")
def test_current_manifest_is_none_without_evidence(tmp_path: Path) -> None:
    # DD-0001 §"current Evidence": no Evidence recorded yet -> nothing can be current.
    from saalco import commands, evidence

    root = tmp_path
    _init_git(root)
    commands.init_project(root, "evidence-proj", "research", "python", [])
    manifest = evidence.current_manifest(root)
    assert manifest is None


# ---------------------------------------------------------------------------
# DD-0002 / MD-0002 (UT-0002): ledger retirement bookkeeping and checks
# ---------------------------------------------------------------------------


def _minimal_research_project(tmp_path: Path):
    from saalco import commands

    root = tmp_path
    _init_git(root)
    commands.init_project(root, "ledger-proj", "research", "python", [])
    feature_id = commands.new_feature(root, "Ledger Feature", "S", "ledger")
    return root, feature_id


@pytest.mark.verifies("DD-0002", spec="UT-0002")
@pytest.mark.verifies("MD-0002", spec="UT-0002")
def test_retired_id_excluded_from_ledger_document_mismatch(tmp_path: Path) -> None:
    # DD-0002: "retired のIDは、台帳と文書の不一致検査から除外する".
    from saalco import checks, commands

    root, feature_id = _minimal_research_project(tmp_path)
    req_id, _ = commands.new_item(root, "req", feature_id, "Retirable requirement")

    ledger_path = root / "docs" / "ids.ledger"
    text = ledger_path.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines():
        cols = line.split("\t")
        if cols[0] == req_id:
            cols = (cols + ["", "", "", ""])[:4] + ["retired", "no longer needed", ""]
            line = "\t".join(cols)
        new_lines.append(line)
    ledger_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Remove the item heading from the document so the ledger/document pair disagree.
    req_doc_path = None
    for candidate in (root / "docs" / "features").rglob("10-requirements.md"):
        req_doc_path = candidate
    assert req_doc_path is not None
    doc = documents.parse_document(req_doc_path)
    doc.body = doc.body.split(f"### {req_id}:")[0]
    documents.atomic_write(doc)

    report = checks.run(root)
    assert not any(req_id in message and "ledger" in message.lower() for message in report.errors)


@pytest.mark.verifies("DD-0002", spec="UT-0002")
@pytest.mark.verifies("MD-0002", spec="UT-0002")
def test_retired_id_number_reuse_is_error(tmp_path: Path) -> None:
    # DD-0002: "retired のIDが台帳に複数行あること...（番号の再利用）" is an ERROR.
    from saalco import checks, commands

    root, feature_id = _minimal_research_project(tmp_path)
    req_id, _ = commands.new_item(root, "req", feature_id, "Reused requirement")

    ledger_path = root / "docs" / "ids.ledger"
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{req_id}\t{feature_id}\t2026-01-01T00:00:00+09:00\tDuplicate\n")

    report = checks.run(root)
    assert report.errors, "duplicate/reused retired ID must be reported"


@pytest.mark.verifies("DD-0002", spec="UT-0002")
@pytest.mark.verifies("MD-0002", spec="UT-0002")
def test_reference_to_retired_id_is_error(tmp_path: Path) -> None:
    # DD-0002: covers:/verifies/DEV scope/rtm.csv references to a retired ID are ERRORs.
    from saalco import checks, commands

    root, feature_id = _minimal_research_project(tmp_path)
    req_id, _ = commands.new_item(root, "req", feature_id, "Base requirement")
    _ad_id, _ = commands.new_item(root, "ad", feature_id, "Dependent architecture item")

    ledger_path = root / "docs" / "ids.ledger"
    text = ledger_path.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines():
        cols = line.split("\t")
        if cols[0] == req_id:
            cols = (cols + ["", "", "", ""])[:4] + ["retired", "superseded", ""]
            line = "\t".join(cols)
        new_lines.append(line)
    ledger_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    ad_doc_path = next((root / "docs" / "features").rglob("20-architecture.md"))
    doc = documents.parse_document(ad_doc_path)
    doc.body = doc.body.replace("covers: \n", f"covers: {req_id}\n")
    documents.atomic_write(doc)

    report = checks.run(root)
    assert any(req_id in message for message in report.errors), (
        "reference to a retired ID from covers: must be an ERROR"
    )


@pytest.mark.verifies("DD-0002", spec="UT-0002")
@pytest.mark.verifies("MD-0002", spec="UT-0002")
def test_superseded_by_pointing_to_unknown_or_retired_is_error(tmp_path: Path) -> None:
    # DD-0002: "superseded_by が、存在しないIDまたは廃止されたIDを指していること" is ERROR.
    from saalco import checks, commands

    root, feature_id = _minimal_research_project(tmp_path)
    req_id, _ = commands.new_item(root, "req", feature_id, "Superseded requirement")

    ledger_path = root / "docs" / "ids.ledger"
    text = ledger_path.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines():
        cols = line.split("\t")
        if cols[0] == req_id:
            cols = (cols + ["", "", "", ""])[:4] + ["retired", "bad ref", "REQ-9999"]
            line = "\t".join(cols)
        new_lines.append(line)
    ledger_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    report = checks.run(root)
    assert any(
        "REQ-9999" in message or "superseded" in message.lower() for message in report.errors
    )


# ---------------------------------------------------------------------------
# DD-0003 / MD-0003 (UT-0003): `saalco retire` — may be unimplemented yet.
# ---------------------------------------------------------------------------


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_updates_only_target_row(tmp_path: Path) -> None:
    # MD-0003: "対象IDの行のみを status: retired に書き換え、更新後の行を返す".
    from saalco import commands

    root, feature_id = _minimal_research_project(tmp_path)
    keep_id, _ = commands.new_item(root, "req", feature_id, "Untouched requirement")
    target_id, _ = commands.new_item(root, "req", feature_id, "Retire me")

    before = (root / "docs" / "ids.ledger").read_text(encoding="utf-8")
    keep_line_before = next(line for line in before.splitlines() if line.split("\t")[0] == keep_id)

    row = ids.retire(root, target_id, reason="merged", superseded_by=None)
    assert row.status == "retired"
    assert row.id == target_id

    after = (root / "docs" / "ids.ledger").read_text(encoding="utf-8")
    keep_line_after = next(line for line in after.splitlines() if line.split("\t")[0] == keep_id)
    assert keep_line_before == keep_line_after, "other ledger rows must be untouched"
    assert len(after.splitlines()) == len(before.splitlines()), "no row may be deleted"


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_unknown_id_raises_usage_error(tmp_path: Path) -> None:
    # DD-0003: unknown ID -> exit code 2 with target/cause/next-step message.
    root, _ = _minimal_research_project(tmp_path)
    with pytest.raises(errors.SaalcoError) as excinfo:
        ids.retire(root, "REQ-9999", reason=None, superseded_by=None)
    assert excinfo.value.exit_code == 2


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_already_retired_raises(tmp_path: Path) -> None:
    # DD-0003: retiring an already-retired ID -> exit code 2.
    root, feature_id = _minimal_research_project(tmp_path)
    from saalco import commands

    target_id, _ = commands.new_item(root, "req", feature_id, "Retire twice")
    ids.retire(root, target_id, reason="first", superseded_by=None)
    with pytest.raises(errors.SaalcoError) as excinfo:
        ids.retire(root, target_id, reason="second", superseded_by=None)
    assert excinfo.value.exit_code == 2


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_rejects_bad_superseded_by(tmp_path: Path) -> None:
    # DD-0003: superseded-by must exist and not be retired, else exit code 2.
    from saalco import commands

    root, feature_id = _minimal_research_project(tmp_path)
    target_id, _ = commands.new_item(root, "req", feature_id, "Needs replacement")

    with pytest.raises(errors.SaalcoError) as excinfo_unknown:
        ids.retire(root, target_id, reason=None, superseded_by="REQ-9999")
    assert excinfo_unknown.value.exit_code == 2

    retired_other_id, _ = commands.new_item(root, "req", feature_id, "Already gone")
    ids.retire(root, retired_other_id, reason="gone", superseded_by=None)
    with pytest.raises(errors.SaalcoError) as excinfo_retired:
        ids.retire(root, target_id, reason=None, superseded_by=retired_other_id)
    assert excinfo_retired.value.exit_code == 2


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_rejects_reason_with_tab_or_newline(tmp_path: Path) -> None:
    # DD-0003 / REQ-0003 bullet 5: reason with tab/newline -> exit code 2 (ledger is
    # tab-separated).
    from saalco import commands

    root, feature_id = _minimal_research_project(tmp_path)
    target_id, _ = commands.new_item(root, "req", feature_id, "Bad reason")

    with pytest.raises(errors.SaalcoError) as excinfo_tab:
        ids.retire(root, target_id, reason="bad\treason", superseded_by=None)
    assert excinfo_tab.value.exit_code == 2

    with pytest.raises(errors.SaalcoError) as excinfo_nl:
        ids.retire(root, target_id, reason="bad\nreason", superseded_by=None)
    assert excinfo_nl.value.exit_code == 2


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_commands_retire_reports_guidance_and_id(tmp_path: Path) -> None:
    # MD-0003: commands.retire "案内メッセージ（項目見出しと参照を文書から削除する
    # こと）を含む標準出力用の文字列を返す".
    from saalco import commands

    root, feature_id = _minimal_research_project(tmp_path)
    target_id, _ = commands.new_item(root, "req", feature_id, "Guided retirement")
    message = commands.retire(root, target_id, reason="tidy up", superseded_by=None)
    assert target_id in message
    assert any(word in message.lower() for word in ("削除", "delete", "remove"))


@pytest.mark.verifies("DD-0003", spec="UT-0003")
@pytest.mark.verifies("MD-0003", spec="UT-0003")
def test_ids_retire_uses_same_lock_as_allocate(tmp_path: Path) -> None:
    # REQ-0003 bullet 8 / DD-0003: retire uses the same .saal/ids.lock as allocation.
    from saalco import commands

    root, feature_id = _minimal_research_project(tmp_path)
    target_id, _ = commands.new_item(root, "req", feature_id, "Locked retirement")
    with ids.lock(root), pytest.raises(errors.SaalcoError):
        ids.retire(root, target_id, reason=None, superseded_by=None)


# ---------------------------------------------------------------------------
# DD-0004 / MD-0004 (UT-0004): Japanese template bodies with fixed English machine labels
# ---------------------------------------------------------------------------


def _has_non_ascii(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


@pytest.mark.verifies("DD-0004", spec="UT-0004")
@pytest.mark.verifies("MD-0004", spec="UT-0004")
@pytest.mark.parametrize("name", ["45-implementation-diff.md", "70-acceptance.md", "80-outcome.md"])
@pytest.mark.parametrize("project_type", ["research", "system"])
def test_feature_document_body_is_japanese(name: str, project_type: str) -> None:
    # DD-0004: fixed body text for these files becomes Japanese.
    text = templates.feature_document(name, "F-001", "S", project_type)
    assert _has_non_ascii(text), f"{name} ({project_type}) body should contain Japanese text"


@pytest.mark.verifies("DD-0004", spec="UT-0004")
@pytest.mark.verifies("MD-0004", spec="UT-0004")
@pytest.mark.parametrize("name", ["45-implementation-diff.md", "70-acceptance.md", "80-outcome.md"])
def test_feature_document_keeps_machine_matched_headings_in_english(name: str) -> None:
    # DD-0004 "変更しない部分": front matter keys and the `## Overview` /
    # `## Implemented but not designed` / `## Designed but not implemented` section
    # headings stay fixed English.
    text = templates.feature_document(name, "F-001", "S", "research")
    assert "kind:" in text
    assert "feature:" in text
    assert "status:" in text
    if name == "45-implementation-diff.md":
        assert "## Implemented but not designed" in text
        assert "## Designed but not implemented" in text


@pytest.mark.verifies("DD-0004", spec="UT-0004")
@pytest.mark.verifies("MD-0004", spec="UT-0004")
def test_generated_feature_document_still_parses_with_required_headers() -> None:
    # UT-0004: "本文の言語変更がパーサに影響しないこと".
    import tempfile

    text = templates.feature_document("70-acceptance.md", "F-001", "S", "system")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "70-acceptance.md"
        path.write_text(text, encoding="utf-8")
        doc = documents.parse_document(path)
        for key in ("kind", "feature", "status"):
            assert key in doc.header


@pytest.mark.verifies("DD-0004", spec="UT-0004")
@pytest.mark.verifies("MD-0004", spec="UT-0004")
def test_templates_agents_constant_matches_repository_agents_md() -> None:
    # DD-0004: "AGENTS 定数...現行リポジトリの AGENTS.md...と同内容・同じ11項目＋
    # 「## Language」節...を、生成コードの側にも反映する".
    agents_constant = getattr(templates, "AGENTS", None)
    assert agents_constant is not None, "templates.AGENTS must exist (REQ-0004/DD-0004)"
    repo_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert agents_constant.strip() == repo_agents.strip()
    assert "## Language" in agents_constant
    assert _has_non_ascii(agents_constant)
