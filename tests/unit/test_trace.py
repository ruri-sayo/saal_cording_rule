"""Unit tests for saalco.trace.generate: verified/unverified status and RTM rows.

pytestmark impl_aware: builds Evidence manifests directly (bypassing the real gate/test
pipeline) to control which verify_status each row lands in.
"""

import pytest

from saalco.documents import content_hash, parse_document
from saalco.trace import _commit_is_current, generate

pytestmark = pytest.mark.impl_aware


def test_no_manifest_yields_stale(saal_project):
    """No Evidence at all yields `stale` (not `unverified`, which requires a manifest)."""
    root = saal_project("valid_project")
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "stale"


def test_verifies_test_pass_yields_verified(saal_project, write_manifest_fn):
    root = saal_project("valid_project")
    write_manifest_fn(
        root,
        tests=[
            {
                "nodeid": "tests/e2e/test_req.py::test_thing_works",
                "category": "e2e",
                "marker": "verifies",
                "referenced_id": "REQ-0001",
                "spec": None,
                "result": "PASS",
            },
            {
                "nodeid": "tests/unit/test_dd.py::test_dd_unit",
                "category": "unit",
                "marker": "verifies",
                "referenced_id": "DD-0001",
                "spec": None,
                "result": "PASS",
            },
        ],
        coverage={
            "total": 90.0,
            "diff": 100.0,
            "diff_base_commit": None,
            "status": "PASS",
            "json_path": None,
        },
    )
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "verified"


def test_verifies_test_not_pass_yields_unverified(saal_project, write_manifest_fn):
    root = saal_project("valid_project")
    write_manifest_fn(
        root,
        tests=[
            {
                "nodeid": "tests/e2e/test_req.py::test_thing_works",
                "category": "e2e",
                "marker": "verifies",
                "referenced_id": "REQ-0001",
                "spec": None,
                "result": "FAIL",
            },
            {
                "nodeid": "tests/unit/test_dd.py::test_dd_unit",
                "category": "unit",
                "marker": "verifies",
                "referenced_id": "DD-0001",
                "spec": None,
                "result": "PASS",
            },
        ],
    )
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "unverified"


def test_impl_aware_alone_never_verifies_a_req(saal_project, write_manifest_fn):
    """A test marked only impl_aware (no verifies marker) must never satisfy a REQ."""
    root = saal_project("valid_project")
    write_manifest_fn(
        root,
        tests=[
            {
                "nodeid": "tests/e2e/test_req.py::test_thing_works",
                "category": "e2e",
                "marker": "impl_aware",
                "referenced_id": None,
                "spec": None,
                "result": "PASS",
            }
        ],
    )
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "unverified"


def _rewrite(doc) -> None:
    doc.path.write_text(
        "---\n" + "".join(f"{k}: {v}\n" for k, v in doc.header.items()) + "---\n" + doc.body
    )


def test_review_item_satisfied_only_when_approved_and_hash_matches(
    saal_project, write_manifest_fn, commit_all_fn
):
    """verify: review items require status approved AND a matching approved_hash."""
    root = saal_project("valid_project")
    dd_path = root / "docs/features/F-001_sample/30-detailed-design.md"
    dd_path.write_text(dd_path.read_text().replace("verify: test", "verify: review"))
    doc = parse_document(dd_path)
    doc.header["approved_hash"] = content_hash(doc)
    _rewrite(doc)
    # Commit the document edit first so the Evidence manifest's target lands *after* it and
    # the manifest-only commit that follows stays a bookkeeping-only diff (contract 3).
    commit_all_fn(root, "switch DD-0001 to verify: review")
    req_test = {
        "nodeid": "tests/e2e/test_req.py::test_thing_works",
        "category": "e2e",
        "marker": "verifies",
        "referenced_id": "REQ-0001",
        "spec": None,
        "result": "PASS",
    }
    write_manifest_fn(root, tests=[req_test])
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "verified"

    # Now corrupt the approved DD content after approval; the hash no longer matches.
    dd_path.write_text(dd_path.read_text() + "\nextra unapproved text\n")
    commit_all_fn(root, "corrupt approved DD-0001 content")
    write_manifest_fn(root, tests=[req_test], run_id="20240102T000000")
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "unverified"


def test_commit_is_current_bookkeeping_only_diff(saal_project, head_commit, commit_all_fn):
    root = saal_project("valid_project")
    commit_a = head_commit(root)
    (root / "evidence" / "dummy.txt").parent.mkdir(parents=True, exist_ok=True)
    (root / "evidence" / "dummy.txt").write_text("bookkeeping\n")
    commit_b = commit_all_fn(root, "bookkeeping only")
    assert _commit_is_current(root, commit_a, commit_b) is True


def test_commit_is_current_false_for_non_bookkeeping_diff(saal_project, head_commit, commit_all_fn):
    root = saal_project("valid_project")
    commit_a = head_commit(root)
    (root / "src" / "sample.py").write_text((root / "src" / "sample.py").read_text() + "\n# x\n")
    commit_b = commit_all_fn(root, "src change")
    assert _commit_is_current(root, commit_a, commit_b) is False


def test_manual_st_satisfies_when_current_and_pass(saal_project, write_manifest_fn, head_commit):
    """A manual ST verifies its REQ when method=manual, result=PASS, and commit == the
    current Evidence's target_commit (the trivial-equality branch of `_commit_is_current`).

    The manual-ST fields are written to the working tree only (not committed): trace.py
    reads document content live from disk, while only the Evidence manifest itself needs a
    git-committed, currently-valid target — so the recorded `commit:` can legitimately equal
    that already-committed target without any self-referential hash trick.
    """
    root = saal_project("valid_project")
    target = head_commit(root)
    dd_test = {
        "nodeid": "tests/unit/test_dd.py::test_dd_unit",
        "category": "unit",
        "marker": "verifies",
        "referenced_id": "DD-0001",
        "spec": None,
        "result": "PASS",
    }
    write_manifest_fn(root, tests=[dd_test], target=target)
    st_path = root / "docs/features/F-001_sample/60-system-e2e-spec.md"
    st_path.write_text(st_path.read_text() + f"\nmethod: manual\nresult: PASS\ncommit: {target}\n")
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "verified"


def test_manual_st_wrong_result_does_not_satisfy(saal_project, write_manifest_fn, head_commit):
    root = saal_project("valid_project")
    target = head_commit(root)
    dd_test = {
        "nodeid": "tests/unit/test_dd.py::test_dd_unit",
        "category": "unit",
        "marker": "verifies",
        "referenced_id": "DD-0001",
        "spec": None,
        "result": "PASS",
    }
    write_manifest_fn(root, tests=[dd_test], target=target)
    st_path = root / "docs/features/F-001_sample/60-system-e2e-spec.md"
    st_path.write_text(st_path.read_text() + f"\nmethod: manual\nresult: FAIL\ncommit: {target}\n")
    rows = generate(root, write=False)
    (row,) = [r for r in rows if r["req_id"] == "REQ-0001"]
    assert row["verify_status"] == "unverified"


def test_join_unique_drops_duplicate_nodeids_in_order():
    from saalco.trace import _join_unique

    assert _join_unique(["a::t1", "a::t2", "a::t1"]) == "a::t1,a::t2"
