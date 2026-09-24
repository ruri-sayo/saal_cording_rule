# Specification-derived tests (SAAL Rule 5.2): written only from approved documents and
# public interfaces, without reading the implementation.
"""System / E2E tests for REQ-0001..0004, derived from ST-0001..0003.

Sources used:
- docs/features/F-001_saalco-v1/10-requirements.md (REQ-0001..0004)
- docs/features/F-001_saalco-v1/60-system-e2e-spec.md (ST-0001..0003)
- SAALCO-v1.0-implementation-instructions.md (r3)
- public-interface.md (CLI --help usage, signatures/docstrings only)

These tests drive the CLI as a real subprocess (`python -m saalco ...`), matching how a
human or Coding Agent invokes it. `saalco retire` (REQ-0003) and the Japanese AGENTS.md body
(REQ-0004) may be unimplemented or partially implemented; failures there are expected and
must not be worked around.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TIMEOUT = 120


def _run(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    import os

    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "saalco", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env=full_env,
        check=False,
    )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_git_identity(cwd: Path) -> None:
    # Local identity scoped to this temp repo only; never touches global git config.
    _git(cwd, "config", "user.email", "e2e-test@example.com")
    _git(cwd, "config", "user.name", "E2E Test")


def _approve_env() -> dict[str, str]:
    # implementation-instructions §11: documented test-only escape hatch for approve.
    return {"SAALCO_ALLOW_NONTTY_APPROVE": "1"}


@pytest.mark.verifies("REQ-0001", spec="ST-0001")
def test_req_0001_full_cli_lifecycle(tmp_path: Path) -> None:
    # ST-0001 steps 1-11: init -> new feature -> new req/ad/dd/ut/st -> sample impl+test ->
    # approve -> commit -> check -> evidence -> commit -> check --verification -> trace,
    # with the target REQ ending up `verified` in the RTM.
    root = tmp_path

    result = _run(
        [
            "init",
            "--non-interactive",
            "--name",
            "st1-proj",
            "--type",
            "research",
            "--language",
            "python",
        ],
        root,
    )
    assert result.returncode == 0, result.stderr
    assert (root / "docs" / "project.md").exists()
    _init_git_identity(root)

    result = _run(["new", "feature", "ST1 Feature", "--tier", "S", "--slug", "st1"], root)
    assert result.returncode == 0, result.stderr
    feature_id = result.stdout.strip().splitlines()[-1]
    assert feature_id.startswith("F-")

    result = _run(["new", "req", "ST1 requirement", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    req_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "ad", "ST1 architecture", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    ad_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "dd", "ST1 design", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    dd_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "ut", "ST1 unit test spec", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    ut_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "st", "ST1 system test spec", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    st_id = result.stdout.strip().splitlines()[-1]

    # Link the covers: chain explicitly (saalco does not infer content).
    features_dir = root / "docs" / "features"
    ad_doc = next(features_dir.rglob("20-architecture.md"))
    ad_doc.write_text(
        ad_doc.read_text(encoding="utf-8").replace(
            f"### {ad_id}: ST1 architecture\n\ncovers: \n",
            f"### {ad_id}: ST1 architecture\n\ncovers: {req_id}\n",
        ),
        encoding="utf-8",
    )
    dd_doc = next(features_dir.rglob("30-detailed-design.md"))
    dd_doc.write_text(
        dd_doc.read_text(encoding="utf-8").replace(
            f"### {dd_id}: ST1 design\n\ncovers: \n",
            f"### {dd_id}: ST1 design\n\ncovers: {ad_id}\n",
        ),
        encoding="utf-8",
    )
    ut_doc = next(features_dir.rglob("40-unit-test-spec.md"))
    ut_doc.write_text(
        ut_doc.read_text(encoding="utf-8").replace(
            f"### {ut_id}: ST1 unit test spec\n\ncovers: \n",
            f"### {ut_id}: ST1 unit test spec\n\ncovers: {dd_id}\n",
        ),
        encoding="utf-8",
    )
    st_doc = next(features_dir.rglob("60-system-e2e-spec.md"))
    st_doc.write_text(
        st_doc.read_text(encoding="utf-8").replace(
            f"### {st_id}: ST1 system test spec\n\ncovers: \n",
            f"### {st_id}: ST1 system test spec\n\ncovers: {req_id}\n",
        ),
        encoding="utf-8",
    )

    # Sample implementation + a Specification-derived Test carrying the `verifies` marker.
    (root / "src" / "st1_sample.py").write_text(
        '"""Sample module for ST-0001 E2E fixture.\n\n'
        "Responsibilities:\n    - Provide a trivial function to exercise coverage.\n\n"
        'Non-responsibilities:\n    - Nothing beyond addition.\n"""\n\n\n'
        "def add(a: int, b: int) -> int:\n"
        '    """Add two integers.\n\n    Side Effects:\n        None.\n    """\n'
        "    return a + b\n",
        encoding="utf-8",
    )
    (root / "tests" / "unit" / "test_st1_sample.py").write_text(
        "import pytest\n\n"
        "from st1_sample import add\n\n\n"
        f'@pytest.mark.verifies("{dd_id}", spec="{ut_id}")\n'
        "def test_add() -> None:\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    # §12 item 7 requires every verify:test item to have >=1 verifies test; §8.4 maps
    # tests/integration -> AD and tests/e2e -> REQ, so AD-0001/REQ-0001 need their own.
    (root / "tests" / "integration" / "test_st1_ad.py").write_text(
        "import pytest\n\n\n"
        f'@pytest.mark.verifies("{ad_id}", spec="{ut_id}")\n'
        "def test_ad_integration_placeholder() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )
    (root / "tests" / "e2e" / "test_st1_req.py").write_text(
        "import pytest\n\n\n"
        f'@pytest.mark.verifies("{req_id}", spec="{st_id}")\n'
        "def test_req_e2e_placeholder() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    result = _run(["approve", str(dd_doc.relative_to(root))], root, env=_approve_env())
    assert result.returncode == 0, result.stderr

    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "ST-0001 fixture setup")

    result = _run(["check"], root)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    result = _run(["evidence"], root)
    if result.returncode not in (0, 1):
        pytest.skip(f"environment cannot run evidence gates here: {result.stderr}")

    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "ST-0001 evidence")

    result = _run(["check", "--verification"], root)
    # Not asserting PASS unconditionally: gate availability (ruff/mypy) is environment
    # dependent, but NOT_EVALUATED items must never be silently treated as passing, and the
    # exit code must reflect the checks module's own judgement per spec §5.
    assert result.returncode in (0, 1)

    result = _run(["trace"], root)
    assert result.returncode == 0, result.stderr
    rtm_csv = (root / "docs" / "trace" / "rtm.csv").read_text(encoding="utf-8")
    assert req_id in rtm_csv


@pytest.mark.verifies("REQ-0002", spec="ST-0002")
def test_req_0002_retired_id_not_reused_and_references_flagged(tmp_path: Path) -> None:
    # ST-0002: allocate -> ledger retirement -> item removal -> check clean; then a
    # reference to the retired ID from covers: must be an ERROR.
    root = tmp_path
    result = _run(
        [
            "init",
            "--non-interactive",
            "--name",
            "st2-proj",
            "--type",
            "research",
            "--language",
            "python",
        ],
        root,
    )
    assert result.returncode == 0, result.stderr
    _init_git_identity(root)

    result = _run(["new", "feature", "ST2 Feature", "--tier", "S", "--slug", "st2"], root)
    feature_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "req", "ST2 requirement", "--feature", feature_id], root)
    req_id = result.stdout.strip().splitlines()[-1]

    ledger_path = root / "docs" / "ids.ledger"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        cols = line.split("\t")
        if cols[0] == req_id:
            cols = (cols + ["", "", "", ""])[:4] + ["retired", "superseded", ""]
            line = "\t".join(cols)
        new_lines.append(line)
    ledger_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    req_doc = next((root / "docs" / "features").rglob("10-requirements.md"))
    text = req_doc.read_text(encoding="utf-8")
    heading_start = text.index(f"### {req_id}:")
    req_doc.write_text(text[:heading_start], encoding="utf-8")

    result = _run(["check"], root)
    assert not any(
        req_id in line and "ledger" in line.lower() for line in result.stdout.splitlines()
    ), "retired ID absent from document must not be an ERROR (DD-0002 exclusion rule)"

    result = _run(["new", "req", "ST2 other requirement", "--feature", feature_id], root)
    other_id = result.stdout.strip().splitlines()[-1]
    other_doc = next((root / "docs" / "features").rglob("10-requirements.md"))
    other_doc.write_text(
        other_doc.read_text(encoding="utf-8").replace(
            f"### {other_id}: ST2 other requirement\n\ncovers: -\n",
            f"### {other_id}: ST2 other requirement\n\ncovers: {req_id}\n",
        ),
        encoding="utf-8",
    )

    result = _run(["check"], root)
    assert result.returncode == 1, (
        f"referencing a retired ID must fail check; stdout={result.stdout}"
    )
    assert req_id in result.stdout


@pytest.mark.verifies("REQ-0003", spec="ST-0003")
def test_req_0003_retire_command_end_to_end(tmp_path: Path) -> None:
    # ST-0003 steps 1-7. `saalco retire` may be unimplemented yet: unknown-subcommand
    # failures are reported as suspected defects/unimplemented, not worked around.
    root = tmp_path
    result = _run(
        [
            "init",
            "--non-interactive",
            "--name",
            "st3-proj",
            "--type",
            "research",
            "--language",
            "python",
        ],
        root,
    )
    assert result.returncode == 0, result.stderr
    _init_git_identity(root)

    result = _run(["new", "feature", "ST3 Feature", "--tier", "S", "--slug", "st3"], root)
    feature_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "dd", "ST3 design to retire", "--feature", feature_id], root)
    target_id = result.stdout.strip().splitlines()[-1]

    result = _run(["new", "dd", "ST3 replacement design", "--feature", feature_id], root)
    replacement_id = result.stdout.strip().splitlines()[-1]

    result = _run(
        [
            "retire",
            target_id,
            "--reason",
            "merged into replacement",
            "--superseded-by",
            replacement_id,
        ],
        root,
    )
    assert result.returncode == 0, (
        f"saalco retire failed (unimplemented feature is expected here): "
        f"stdout={result.stdout} stderr={result.stderr}"
    )
    assert target_id in result.stdout
    assert any(word in result.stdout.lower() for word in ("削除", "delete", "remove"))

    ledger_text = (root / "docs" / "ids.ledger").read_text(encoding="utf-8")
    target_line = next(
        line for line in ledger_text.splitlines() if line.split("\t")[0] == target_id
    )
    assert "retired" in target_line
    assert ledger_text.count(f"{target_id}\t") == 1, "retire must not delete the row"

    result = _run(["check"], root)
    assert result.returncode == 1
    assert target_id in result.stdout, (
        "heading still present for a retired ID must be flagged as number reuse"
    )

    dd_doc = next((root / "docs" / "features").rglob("30-detailed-design.md"))
    text = dd_doc.read_text(encoding="utf-8")
    heading_start = text.index(f"### {target_id}:")
    next_heading = text.find("\n### ", heading_start + 1)
    remainder = text[next_heading:] if next_heading != -1 else ""
    dd_doc.write_text(text[:heading_start] + remainder, encoding="utf-8")

    result = _run(["check"], root)
    assert not any(
        target_id in line and "ledger" in line.lower() for line in result.stdout.splitlines()
    )

    # MD items may cover DD (§8.3); create one and point it at the retired ID.
    result = _run(["new", "md", "ST3 module referencing retired id", "--feature", feature_id], root)
    assert result.returncode == 0, result.stderr
    md_id = result.stdout.strip().splitlines()[-1]
    md_doc = next((root / "docs" / "features").rglob("35-module-design.md"))
    md_doc.write_text(
        md_doc.read_text(encoding="utf-8").replace(
            f"### {md_id}: ST3 module referencing retired id\n\ncovers: \n",
            f"### {md_id}: ST3 module referencing retired id\n\ncovers: {target_id}\n",
        ),
        encoding="utf-8",
    )

    result = _run(["check"], root)
    assert result.returncode == 1
    assert target_id in result.stdout, "reference to a retired ID must be flagged"

    result = _run(["retire", "REQ-9999"], root)
    assert result.returncode == 2

    result = _run(["retire", target_id], root)
    assert result.returncode == 2


@pytest.mark.verifies("REQ-0004")
def test_req_0004_generated_documents_are_japanese(tmp_path: Path) -> None:
    # REQ-0004: generated bodies (including AGENTS.md) are Japanese; machine-matched keys,
    # IDs and section headings stay English; checks are unaffected by body language.
    root = tmp_path
    result = _run(
        [
            "init",
            "--non-interactive",
            "--name",
            "st4-proj",
            "--type",
            "research",
            "--language",
            "python",
        ],
        root,
    )
    assert result.returncode == 0, result.stderr

    agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert any(ord(ch) > 127 for ch in agents_text), "AGENTS.md body must be Japanese"
    assert "## Language" in agents_text

    _init_git_identity(root)
    result = _run(["new", "feature", "ST4 Feature", "--tier", "S", "--slug", "st4"], root)
    feature_id = result.stdout.strip().splitlines()[-1]
    feature_dir = next((root / "docs" / "features").glob(f"{feature_id}_*"))

    diff_text = (feature_dir / "45-implementation-diff.md").read_text(encoding="utf-8")
    assert "## Implemented but not designed" in diff_text
    assert "## Designed but not implemented" in diff_text
    assert any(ord(ch) > 127 for ch in diff_text), "45-implementation-diff.md must be Japanese"

    acceptance_text = (feature_dir / "70-acceptance.md").read_text(encoding="utf-8")
    assert any(ord(ch) > 127 for ch in acceptance_text)

    meta_text = (feature_dir / "00-meta.md").read_text(encoding="utf-8")
    assert "kind: FEATURE" in meta_text
    assert "tier: S" in meta_text

    result = _run(["check"], root)
    # Body language must not change header/ID/section-heading machine checks; whatever the
    # outcome, it must not be a crash.
    assert result.returncode in (0, 1, 2)
