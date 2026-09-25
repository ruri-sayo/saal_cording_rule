# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""Integration tests for AD-0001, derived from IT-0001.

Sources used:
- docs/features/F-001_saalco-v1/20-architecture.md (AD-0001)
- docs/features/F-001_saalco-v1/50-integration-test-spec.md (IT-0001)
- SAALCO-v1.0-implementation-instructions.md (r3), esp. §7, §10, §11, §12, §17
- public-interface.md (signatures/docstrings only)

IT-0001 allows "in-process" command invocation, so these tests call the documented Python
API (`saalco.commands`, `saalco.checks`, `saalco.trace`, `saalco.evidence`) directly rather
than spawning subprocesses; process-level behavior is covered by tests/e2e.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from saalco import checks, commands, documents, errors, evidence
from saalco import trace as trace_mod


@pytest.fixture(autouse=True)
def _allow_nontty_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    # implementation-instructions §11: approve normally requires a TTY; the documented
    # test-only escape hatch is SAALCO_ALLOW_NONTTY_APPROVE=1.
    monkeypatch.setenv("SAALCO_ALLOW_NONTTY_APPROVE", "1")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_git(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "it-test@example.com")
    _git(root, "config", "user.name", "IT Test")


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _require_uv() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv executable not available in this environment")


def _make_lockable_and_lock(root: Path, project_name: str) -> None:
    # REQ-0006 / DD-0006: `saalco evidence` refuses to run for a `language: python`
    # project unless `uv.lock` exists, is tracked by git, and matches pyproject.toml.
    # `saalco init` does not write a `[project]` table, so `uv lock` needs a minimal
    # dependency-free one to resolve; this is test scaffolding, not product behavior.
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8") if pyproject.exists() else ""
    if "[project]" not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += (
            f'\n[project]\nname = "{project_name}"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
        )
        pyproject.write_text(text, encoding="utf-8")

    lock_env = dict(os.environ)
    lock_env["UV_OFFLINE"] = "1"
    subprocess.run(
        ["uv", "lock"],
        cwd=root,
        env=lock_env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.verifies("AD-0001", spec="IT-0001")
@pytest.mark.parametrize("project_type", ["research", "system"])
def test_init_creates_standard_structure(tmp_path: Path, project_type: str) -> None:
    # IT-0001 "init": AD-0001 記載の標準構造一式が生成される。80-outcome.md のテンプレート
    # が種別に応じて異なる。
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "structure-proj", project_type, "python", [])

    expected_paths = [
        "AGENTS.md",
        "docs/project.md",
        "docs/ids.ledger",
        "docs/rules/SAAL-DEV-RULES.md",
        "docs/architecture",
        "docs/features",
        "docs/trace",
        "evidence",
        "src",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
    ]
    for rel in expected_paths:
        assert (root / rel).exists(), f"missing {rel} after init"

    feature_id = commands.new_feature(root, "Structure Feature", "S", "structure")
    feature_dir = next((root / "docs" / "features").glob(f"{feature_id}_*"))
    outcome_text = (feature_dir / "80-outcome.md").read_text(encoding="utf-8")
    if project_type == "research":
        assert any(term in outcome_text for term in ("dataset", "seed", "データセット", "乱数"))
    else:
        assert any(
            term in outcome_text
            for term in ("release version", "deployment", "リリース", "デプロイ")
        )


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_init_does_not_clobber_existing_files_and_reports_conflicts(tmp_path: Path) -> None:
    # IT-0001 "init": "既存 src/・tests/ があるディレクトリでも既存ファイルが壊れない".
    root = tmp_path
    (root / "src").mkdir()
    (root / "src" / "keep_me.py").write_text("# pre-existing\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "keep_me_too.py").write_text("# pre-existing test\n", encoding="utf-8")
    _init_git(root)

    conflicts = commands.init_project(root, "conflict-proj", "research", "python", [])

    assert (root / "src" / "keep_me.py").read_text(encoding="utf-8") == "# pre-existing\n"
    assert (root / "tests" / "keep_me_too.py").read_text(
        encoding="utf-8"
    ) == "# pre-existing test\n"
    assert isinstance(conflicts, list)


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_new_allocates_ledger_rows_and_appends_items(tmp_path: Path) -> None:
    # IT-0001 "new": docs/ids.ledger に行が追記され、対応する文書に項目が生成・追記される。
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "new-proj", "research", "python", [])
    feature_id = commands.new_feature(root, "New Item Feature", "S", "newitem")

    req_id, warning = commands.new_item(root, "req", feature_id, "Sample requirement")
    assert warning is None
    ledger_text = (root / "docs" / "ids.ledger").read_text(encoding="utf-8")
    assert req_id in ledger_text

    req_doc_path = next((root / "docs" / "features").rglob("10-requirements.md"))
    assert f"### {req_id}:" in req_doc_path.read_text(encoding="utf-8")


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_new_item_on_approved_document_invalidates_approval_with_warning(
    tmp_path: Path,
) -> None:
    # implementation-instructions §10: "承認済みの文書に追記した場合は、status: draft
    # に戻し、「承認が無効になった」とWARNINGを出す".
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "invalidate-proj", "research", "python", [])
    feature_id = commands.new_feature(root, "Invalidate Feature", "S", "invalidate")
    _req_id, _ = commands.new_item(root, "req", feature_id, "First requirement")

    req_doc_path = next((root / "docs" / "features").rglob("10-requirements.md"))

    commands.approve(root, [str(req_doc_path)])
    doc_before = documents.parse_document(req_doc_path)
    assert doc_before.header.get("status") == "approved"

    _second_id, warning = commands.new_item(root, "req", feature_id, "Second requirement")
    assert warning is not None
    doc_after = documents.parse_document(req_doc_path)
    assert doc_after.header.get("status") == "draft"


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_approve_edit_check_fail_reapprove_pass(tmp_path: Path) -> None:
    # IT-0001 "approve → 編集 → check FAIL → 再approve → PASS".
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "approve-proj", "research", "python", [])
    commands.new_feature(root, "Approve Feature", "S", "approveflow")
    meta_path = next((root / "docs" / "features").rglob("00-meta.md"))

    commands.approve(root, [str(meta_path)])
    doc = documents.parse_document(meta_path)
    assert doc.header.get("status") == "approved"
    approved_hash = doc.header.get("approved_hash")
    assert approved_hash

    report_after_approve = checks.run(root)
    assert not any(
        "approved_hash" in message and "does not match" in message
        for message in report_after_approve.errors
    )

    doc.body += "\nEdited after approval.\n"
    documents.atomic_write(doc)

    report_after_edit = checks.run(root)
    assert any(
        "approved_hash" in message or "hash" in message.lower()
        for message in report_after_edit.errors
    ), "editing an approved document must produce a hash-mismatch ERROR"

    commands.approve(root, [str(meta_path)])
    report_after_reapprove = checks.run(root)
    assert not any(
        "approved_hash" in message and "does not match" in message
        for message in report_after_reapprove.errors
    )


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_trace_output_matches_covers_graph(tmp_path: Path) -> None:
    # IT-0001 "trace": rtm.csv/rtm.md が生成され、checks.py が参照する項目・台帳・
    # マーカーの情報と一致する。
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "trace-proj", "research", "python", [])
    feature_id = commands.new_feature(root, "Trace Feature", "S", "traceflow")
    req_id, _ = commands.new_item(root, "req", feature_id, "Traced requirement")

    rows = trace_mod.generate(root, write=True)
    assert any(row["req_id"] == req_id for row in rows)
    assert (root / "docs" / "trace" / "rtm.csv").exists()
    assert (root / "docs" / "trace" / "rtm.md").exists()
    csv_text = (root / "docs" / "trace" / "rtm.csv").read_text(encoding="utf-8")
    assert req_id in csv_text


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_evidence_rejects_dirty_working_tree(tmp_path: Path) -> None:
    # IT-0001 "dirty treeの拒否": 未commitの変更がある作業ツリーでは Evidence を
    # 生成せず、exit code が非0になる (evidence.create docstring: raises
    # EnvironmentError when the tree is not clean).
    root = tmp_path
    _init_git(root)
    commands.init_project(root, "dirty-proj", "research", "python", [])
    (root / "src" / "dirty_marker.txt").write_text("uncommitted\n", encoding="utf-8")

    with pytest.raises((errors.SaalcoError, EnvironmentError, OSError)):
        evidence.create(root)


@pytest.mark.verifies("AD-0001", spec="IT-0001")
def test_evidence_generates_manifest_and_summary_for_clean_tree(tmp_path: Path) -> None:
    # IT-0001 "Evidence生成": クリーンな作業ツリーで evidence/<commit>/<run-id>/
    # manifest.json・summary.md と .saal/artifacts/<commit>/<run-id>/ が生成される。
    root = tmp_path
    _require_uv()
    _init_git(root)
    commands.init_project(root, "evidence-clean-proj", "research", "python", [])

    # REQ-0006 / DD-0006: satisfy the uv.lock precondition before the commit that
    # precedes the `evidence.create` call.
    _make_lockable_and_lock(root, "evidence-clean-proj")
    _commit_all(root, "init")

    manifest_path, overall = evidence.create(root)

    assert manifest_path.name == "manifest.json"
    assert manifest_path.exists()
    summary_path = manifest_path.parent / "summary.md"
    assert summary_path.exists()
    commit_dir = manifest_path.parent.parent
    run_id = manifest_path.parent.name
    artifacts_dir = root / ".saal" / "artifacts" / commit_dir.name / run_id
    assert artifacts_dir.exists()
    assert overall in ("PASS", "FAIL")
