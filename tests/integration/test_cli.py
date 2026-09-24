"""Integration tests for the saalco CLI, invoked in-process via `saalco.cli.main`.

Calling `main()` directly (rather than spawning a subprocess) keeps these runs inside the
coverage-measured process, per the shared brief's coverage-must-reflect-reality goal.

pytestmark impl_aware: asserts on exact CLI output strings/exit codes from the implementation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from saalco.cli import main

pytestmark = pytest.mark.impl_aware

ENV_NONTTY_APPROVE = "SAALCO_ALLOW_NONTTY_APPROVE"


def _git_config(root: Path) -> None:
    for args in (["user.name", "Test Human"], ["user.email", "test@example.invalid"]):
        subprocess.run(["git", "config", *args], cwd=root, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def test_init_research_vs_system_outcome_templates_differ(tmp_path, monkeypatch):
    research = tmp_path / "research"
    system = tmp_path / "system"
    research.mkdir()
    system.mkdir()

    monkeypatch.chdir(research)
    assert (
        main(
            [
                "init",
                "--name",
                "r",
                "--type",
                "research",
                "--language",
                "python",
                "--non-interactive",
            ]
        )
        == 0
    )
    assert main(["new", "feature", "Thing", "--tier", "S", "--slug", "thing"]) == 0

    monkeypatch.chdir(system)
    assert (
        main(
            ["init", "--name", "s", "--type", "system", "--language", "python", "--non-interactive"]
        )
        == 0
    )
    assert main(["new", "feature", "Thing", "--tier", "S", "--slug", "thing"]) == 0

    research_outcome = (research / "docs/features/F-001_thing/80-outcome.md").read_text()
    system_outcome = (system / "docs/features/F-001_thing/80-outcome.md").read_text()
    assert "dataset version" in research_outcome
    assert "deployment target" in system_outcome
    assert research_outcome != system_outcome


def test_init_does_not_touch_existing_src_and_tests(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.py").write_text("# pre-existing\n")
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_keep.py").write_text("def test_keep():\n    pass\n")

    monkeypatch.chdir(tmp_path)
    assert (
        main(
            ["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"]
        )
        == 0
    )

    assert (tmp_path / "src" / "keep.py").read_text() == "# pre-existing\n"
    assert (
        tmp_path / "tests" / "unit" / "test_keep.py"
    ).read_text() == "def test_keep():\n    pass\n"


def test_init_gitignore_contains_saal_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            ["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"]
        )
        == 0
    )
    assert ".saal/" in (tmp_path / ".gitignore").read_text()


def test_init_existing_pyproject_reports_snippet(tmp_path, monkeypatch, capsys):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            ["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "pyproject.toml" in captured.err
    assert "markers" in captured.err
    # The existing file is untouched.
    assert (tmp_path / "pyproject.toml").read_text() == "[project]\nname = 'x'\n"


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


def test_new_allocates_sequential_ids(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"])
    capsys.readouterr()
    main(["new", "feature", "First", "--tier", "S", "--slug", "first"])
    out = capsys.readouterr().out.strip()
    assert out == "F-001"
    main(["new", "feature", "Second", "--tier", "S", "--slug", "second"])
    out = capsys.readouterr().out.strip()
    assert out == "F-002"
    main(["new", "req", "Need X", "--feature", "F-001"])
    out = capsys.readouterr().out.strip()
    assert out == "REQ-0001"


@pytest.mark.parametrize("extra", [[], ["--non-interactive"]])
def test_new_feature_non_ascii_title_without_slug_exits_2(tmp_path, monkeypatch, extra):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"])
    code = main(["new", "feature", "日本語タイトル", "--tier", "S", *extra])
    assert code == 2


@pytest.mark.parametrize("tier", ["M", "L"])
def test_new_feature_tier_m_or_l_creates_tier_documents(tmp_path, monkeypatch, tier):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"])
    code = main(["new", "feature", "Big", "--tier", tier, "--slug", "big"])
    assert code == 0
    folder = tmp_path / "docs/features/F-001_big"
    assert (folder / "20-architecture.md").is_file()
    assert (folder / "50-integration-test-spec.md").is_file()
    assert (folder / "35-module-design.md").is_file() == (tier == "L")


def test_new_item_on_approved_document_resets_to_draft_with_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"])
    main(["new", "feature", "First", "--tier", "S", "--slug", "first"])
    capsys.readouterr()
    main(["new", "req", "Need X", "--feature", "F-001"])
    capsys.readouterr()
    req = tmp_path / "docs/features/F-001_first/10-requirements.md"
    _git_config(tmp_path)
    monkeypatch.setenv(ENV_NONTTY_APPROVE, "1")
    assert main(["approve", str(req)]) == 0
    assert "status: approved" in req.read_text()

    assert main(["new", "req", "Need Y", "--feature", "F-001"]) == 0
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "approval invalidated" in captured.err
    assert "status: draft" in req.read_text()
    assert "status: approved" not in req.read_text()


# ---------------------------------------------------------------------------
# approve -> edit -> check FAIL -> re-approve -> PASS
# ---------------------------------------------------------------------------


def test_approve_edit_check_fail_reapprove_pass(saal_project, monkeypatch, capsys):
    root = saal_project("valid_project")
    _git_config(root)
    monkeypatch.chdir(root)
    monkeypatch.setenv(ENV_NONTTY_APPROVE, "1")

    dd_path = root / "docs/features/F-001_sample/30-detailed-design.md"
    dd_path.write_text(dd_path.read_text() + "\n<!-- tampered -->\n")
    code = main(["check"])
    capsys.readouterr()
    assert code == 1

    assert main(["approve", str(dd_path)]) == 0
    capsys.readouterr()
    code = main(["check"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "0 errors" in out


def test_approve_rejected_without_tty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "x", "--type", "system", "--language", "python", "--non-interactive"])
    main(["new", "feature", "First", "--tier", "S", "--slug", "first"])
    req = tmp_path / "docs/features/F-001_first/10-requirements.md"
    monkeypatch.delenv(ENV_NONTTY_APPROVE, raising=False)
    assert main(["approve", str(req)]) == 2


def test_approve_rejected_outside_docs_features(saal_project, monkeypatch):
    root = saal_project("valid_project")
    _git_config(root)
    monkeypatch.chdir(root)
    monkeypatch.setenv(ENV_NONTTY_APPROVE, "1")
    outside = root / "docs" / "project.md"
    assert main(["approve", str(outside)]) == 2


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_detects_broken_reference(saal_project):
    root = saal_project("broken_reference")
    from saalco.checks import run

    report = run(root)
    assert not report.ok
    assert any("unknown covers ID REQ-9999" in e for e in report.errors)


def test_check_detects_missing_tier_document(saal_project):
    root = saal_project("missing_document")
    from saalco.checks import run

    report = run(root)
    assert not report.ok
    assert any("required for Tier L" in e for e in report.errors)


def test_check_json_output(saal_project, monkeypatch, capsys):
    root = saal_project("invalid_hash")
    monkeypatch.chdir(root)
    code = main(["check", "--json"])
    out = capsys.readouterr().out
    assert code == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert any("approved_hash does not match" in e for e in data["errors"])


# ---------------------------------------------------------------------------
# trace
# ---------------------------------------------------------------------------


def test_trace_output_is_deterministic(saal_project, monkeypatch, capsys):
    root = saal_project("valid_project")
    monkeypatch.chdir(root)
    assert main(["trace"]) == 0
    first_csv = (root / "docs/trace/rtm.csv").read_text()
    assert main(["trace"]) == 0
    second_csv = (root / "docs/trace/rtm.csv").read_text()
    assert first_csv == second_csv
    assert "REQ-0001" in first_csv


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------


def test_evidence_refuses_dirty_tree(saal_project, monkeypatch, capsys):
    root = saal_project("valid_project")
    monkeypatch.chdir(root)
    (root / "docs" / "features" / "F-001_sample" / "00-meta.md").write_text("dirty\n")
    code = main(["evidence"])
    err = capsys.readouterr().err
    assert code == 3
    assert "dirty" in err


def test_evidence_package_content(saal_project, monkeypatch, write_manifest_fn):
    root = saal_project("valid_project")
    write_manifest_fn(root, tests=[])
    monkeypatch.chdir(root)
    code = main(["evidence", "--package", "F-001"])
    assert code == 0
    package_path = root / ".saal/packages/F-001/package.json"
    assert package_path.is_file()
    data = json.loads(package_path.read_text())
    assert data["feature"] == "F-001"
    assert data["requirements"] == "docs/features/F-001_sample/10-requirements.md"
    assert (root / ".saal/packages/F-001/index.md").is_file()


# ---------------------------------------------------------------------------
# check --verification: coverage FAIL, with and without a matching open DEV (Rule 7.3)
# ---------------------------------------------------------------------------


def _passing_tests() -> list[dict[str, object]]:
    return [
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
    ]


def test_check_verification_coverage_fail_without_dev(
    saal_project, write_manifest_fn, write_coverage_fn, head_commit
):
    root = saal_project("valid_project")
    target = head_commit(root)
    json_path = write_coverage_fn(
        root,
        target,
        "20240101T000000",
        {"src/sample.py": {"1": ["tests/unit/test_dd.py::test_dd_unit|run"]}},
    )
    write_manifest_fn(
        root,
        tests=_passing_tests(),
        coverage={
            "total": 50.0,
            "diff": 40.0,
            "diff_base_commit": None,
            "status": "FAIL",
            "json_path": json_path,
        },
        target=target,
    )
    from saalco.checks import run

    report = run(root, verification=True)
    assert not report.ok
    assert any("coverage is FAIL" in e for e in report.errors)


def test_check_verification_coverage_fail_downgraded_by_matching_open_dev(
    saal_project, write_manifest_fn, write_coverage_fn, head_commit
):
    """coverage_failure fixture ships an open DEV-0001 (rule 7.3, scope F-001): the coverage
    FAIL becomes a WARNING instead of an ERROR (§8.6 DEV-downgrade mechanism)."""
    root = saal_project("coverage_failure")
    target = head_commit(root)
    json_path = write_coverage_fn(
        root,
        target,
        "20240101T000000",
        {"src/sample.py": {"1": ["tests/unit/test_dd.py::test_dd_unit|run"]}},
    )
    write_manifest_fn(
        root,
        tests=_passing_tests(),
        coverage={
            "total": 50.0,
            "diff": 40.0,
            "diff_base_commit": None,
            "status": "FAIL",
            "json_path": json_path,
        },
        target=target,
    )
    from saalco.checks import run

    report = run(root, verification=True)
    assert report.ok, report.errors
    assert any("coverage is FAIL" in w and "covered by an open DEV" in w for w in report.warnings)
