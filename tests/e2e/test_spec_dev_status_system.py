# Specification-derived tests (SAAL Rule 5.2): written only from approved
# documents and public interfaces, without reading the implementation.
"""System/E2E test for REQ-0005, following ST-0004 through the `saalco` CLI.

Built only from docs/features/F-002 REQ-0005 / ST-0004, spec §8.6 r4 and §2,
§5, §12, §13 (CLI behaviour), and saalco's public interface (`--help` text
and docstrings; no bodies).

ST-0004 (「Closed DEV handling through the CLI」):
  1. Build a temp project with an example violation and a matching `open`
     DEV; `saalco check --verification` must report it as a WARNING.
  2. Close that DEV (`status: closed`, with `closed_at`/`closed_condition`
     filled in); the same violation must now be an ERROR, and the command
     must exit 1.
  3. Set `status: resolved`; `saalco check` must report an ERROR for the
     invalid status.

ST-0004 uses "Coverage未達などの例外" ("...etc.") as an example category of
downgradable violation; REQ-0005 bullet 2 lists several such checks
(Coverage, RTM, gates, `verifies` tests, unapproved-design). This test uses
a `verifies`-test-not-PASS violation (spec §13 item 12 / rule 6.4, per
DD-0001's rule-number list in `_dev_downgrade`) as a concrete, CLI-only
constructible instance of that same downgrade behaviour.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SAALCO_CMD = [sys.executable, "-m", "saalco"]
RUN_TIMEOUT = 120


def _env_for_cli() -> dict[str, str]:
    env = dict(os.environ)
    # Test-only switch documented for non-interactive approval; harmless
    # here since this test never calls `saalco approve`.
    env["SAALCO_ALLOW_NONTTY_APPROVE"] = "1"
    return env


def _run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*SAALCO_CMD, *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT,
        env=_env_for_cli(),
        check=False,
    )


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _extract_id(output: str, prefix: str) -> str:
    match = re.search(rf"\b{prefix}-\d+\b", output)
    assert match, f"could not find a {prefix}-NNNN id in CLI output: {output!r}"
    return match.group(0)


def _parse_check_findings(stdout: str) -> tuple[list[str], list[str]]:
    """Split `saalco check`/`check --verification` output into findings.

    Per spec §5, each finding is an `ERROR `/`WARNING `-prefixed line,
    optionally followed by indented continuation lines (the worked example:
    `ERROR docs/.../30-detailed-design.md: approved_hash does not match
    current content.` followed by an indented "next step" line).
    """
    errors: list[str] = []
    warnings: list[str] = []
    current: list[str] | None = None
    for line in stdout.splitlines():
        if line.startswith("ERROR "):
            current = errors
            current.append(line[len("ERROR ") :])
        elif line.startswith("WARNING "):
            current = warnings
            current.append(line[len("WARNING ") :])
        elif current is not None and line.startswith(("  ", "\t")):
            current[-1] += "\n" + line
        else:
            current = None
    return errors, warnings


def _disable_network_gates(root: Path) -> None:
    """Rewrite `docs/project.md` gate/test commands so `saalco evidence`
    needs no network access: every gate is cleared (`NOT_CONFIGURED`, spec
    §7.2) and `test.unit` runs directly under this interpreter instead of
    `uv run ...`, avoiding a fresh `uv`-managed environment resolve/install
    for a throwaway temp project.
    """
    project_md = root / "docs" / "project.md"
    text = project_md.read_text(encoding="utf-8")
    replacements = {
        "gate.01.format": "",
        "gate.02.lint": "",
        "gate.03.typecheck": "",
        "gate.04.secret_scan": "",
        "gate.05.dependency_audit": "",
        "gate.06.static_analysis": "",
        "test.unit": f"{sys.executable} -m pytest tests/unit",
        "test.integration": "",
        "test.e2e": "",
    }
    lines = text.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        stripped = line.rstrip("\n")
        key = stripped.split(":", 1)[0] if ":" in stripped else None
        if key in replacements:
            value = replacements[key]
            new_lines.append(f"{key}: {value}\n" if value else f"{key}:\n")
        else:
            new_lines.append(line)
    project_md.write_text("".join(new_lines), encoding="utf-8")


def _set_dev_fields(doc_path: Path, dev_id: str, title: str, fields_text: str) -> None:
    text = doc_path.read_text(encoding="utf-8")
    heading = f"### {dev_id}:"
    start = text.index(heading)
    text = text[:start] + f"### {dev_id}: {title}\n\n{fields_text}"
    doc_path.write_text(text, encoding="utf-8")


def _find_doc_with_item(root: Path, feature_id: str, item_id: str) -> Path:
    feature_dirs = list((root / "docs" / "features").glob(f"{feature_id}_*"))
    assert feature_dirs, f"no feature directory found for {feature_id}"
    for path in sorted(feature_dirs[0].glob("*.md")):
        if f"### {item_id}:" in path.read_text(encoding="utf-8"):
            return path
    raise AssertionError(f"no document under {feature_dirs[0]} contains item {item_id}")


@pytest.mark.verifies("REQ-0005", spec="ST-0004")
def test_closed_dev_handling_through_the_cli(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    _run_git(root, "init")
    _run_git(root, "config", "user.email", "spec-dev-status-e2e@example.invalid")
    _run_git(root, "config", "user.name", "Spec Dev Status E2E")

    init_proc = _run_cli(
        root,
        "init",
        "--non-interactive",
        "--name",
        "dev-status-e2e",
        "--type",
        "research",
        "--language",
        "python",
    )
    assert init_proc.returncode == 0, f"saalco init failed: {init_proc.stdout}\n{init_proc.stderr}"

    _disable_network_gates(root)

    feature_proc = _run_cli(
        root,
        "new",
        "feature",
        "DEV status ST-0004 test feature",
        "--tier",
        "S",
        "--slug",
        "devst0004",
        "--non-interactive",
    )
    assert feature_proc.returncode == 0, (
        f"saalco new feature failed: {feature_proc.stdout}\n{feature_proc.stderr}"
    )
    feature_id = _extract_id(feature_proc.stdout + feature_proc.stderr, "F")

    dd_proc = _run_cli(
        root,
        "new",
        "dd",
        "Something that must be verified",
        "--feature",
        feature_id,
        "--non-interactive",
    )
    assert dd_proc.returncode == 0, f"saalco new dd failed: {dd_proc.stdout}\n{dd_proc.stderr}"
    dd_id = _extract_id(dd_proc.stdout + dd_proc.stderr, "DD")

    unit_dir = root / "tests" / "unit"
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "test_intentional_failure.py").write_text(
        f'''"""Deliberately-failing Specification-derived test for {dd_id},
used only to give this temp project a non-PASS `verifies` result
(rule 6.4) for `saalco check --verification` to react to."""

import pytest


@pytest.mark.verifies("{dd_id}")
def test_intentionally_fails():
    assert False, "intentional failure, used only to produce a non-PASS result"
''',
        encoding="utf-8",
    )

    # Materialize `uv.lock` (used internally by `saalco evidence`'s
    # `uv run coverage json` step, per spec §14) *before* the initial
    # commit. Otherwise it is created as a side effect of the first
    # `saalco evidence` run, landing outside the bookkeeping paths
    # (`evidence/`, `docs/trace/`, `docs/ids.ledger`) spec I-1 allows
    # between an Evidence's target commit and HEAD, which would make the
    # Evidence never "current".
    subprocess.run(["uv", "lock"], cwd=root, check=True, capture_output=True, text=True)

    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "initial commit for ST-0004 test project")

    evidence_proc = _run_cli(root, "evidence")
    assert evidence_proc.returncode in (0, 1), (
        f"saalco evidence errored unexpectedly (exit {evidence_proc.returncode}): "
        f"{evidence_proc.stdout}\n{evidence_proc.stderr}"
    )
    # `current_manifest` only recognizes a *tracked* Evidence (spec I-1), so
    # the manifest `saalco evidence` just wrote must be committed before it
    # counts as "current".
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-m", "record evidence")

    dev_proc = _run_cli(
        root,
        "new",
        "dev",
        "DEV covering rule 6.4",
        "--feature",
        feature_id,
        "--non-interactive",
    )
    assert dev_proc.returncode == 0, f"saalco new dev failed: {dev_proc.stdout}\n{dev_proc.stderr}"
    dev_id = _extract_id(dev_proc.stdout + dev_proc.stderr, "DEV")
    doc_path = _find_doc_with_item(root, feature_id, dev_id)

    common_fields = (
        f"rule: 6.4\n"
        f"scope: {dd_id}\n"
        "reason: existing tests are impl_aware only\n"
        "resolution: add a Specification-derived Test\n"
        "end_condition: RTM の全項目が verified になった時点で終了\n"
        "decided_by: tester\n"
        "decided_at: 2026-09-20\n"
    )

    # --- Step 1: `open` DEV downgrades the violation to WARNING. ---
    _set_dev_fields(doc_path, dev_id, "DEV covering rule 6.4", f"status: open\n{common_fields}")
    open_check = _run_cli(root, "check", "--verification")
    open_errors, open_warnings = _parse_check_findings(open_check.stdout)
    assert "WARNING" in open_check.stdout, (
        f"expected a WARNING in `saalco check --verification` output while DEV "
        f"{dev_id} is `open`: {open_check.stdout}"
    )

    # --- Step 2: `closed` DEV (with closed_at/closed_condition) does not
    # downgrade; same violation must be an ERROR, exit code 1. ---
    _set_dev_fields(
        doc_path,
        dev_id,
        "DEV covering rule 6.4",
        f"status: closed\n{common_fields}closed_at: 2026-09-25\n"
        "closed_condition: RTM の全項目が verified になった\n",
    )
    closed_check = _run_cli(root, "check", "--verification")
    closed_errors, _closed_warnings = _parse_check_findings(closed_check.stdout)
    assert closed_check.returncode == 1, (
        "expected `saalco check --verification` to exit 1 (ERROR) once DEV "
        f"{dev_id} is `closed` (DD-0005: closed DEVs do not downgrade ERRORs "
        f"to WARNINGs): {closed_check.stdout}\n{closed_check.stderr}"
    )
    assert "ERROR" in closed_check.stdout, (
        f"expected an ERROR in `saalco check --verification` output once DEV "
        f"{dev_id} is `closed`: {closed_check.stdout}"
    )

    # The rule-6.4 violation itself: an ERROR only while the matching DEV is
    # `closed`, downgraded to a (still-present) WARNING while it is `open`.
    # The project also has other, unrelated static findings (e.g. missing UT
    # coverage of the DD) that are identical in both runs and cancel out.
    only_when_closed = set(closed_errors) - set(open_errors)
    assert only_when_closed, (
        f"expected `saalco check --verification` to keep reporting the rule-6.4 "
        f"violation for {dd_id} as an ERROR while DEV {dev_id} is `closed` "
        "(DD-0005: 'closed の DEV は...ERRORをWARNINGに緩めないこと'); "
        f"closed errors={closed_errors!r} open errors={open_errors!r}"
    )
    still_reported_as_warning = all(
        any(message in warning for warning in open_warnings) for message in only_when_closed
    )
    assert still_reported_as_warning, (
        f"expected the rule-6.4 violation to reappear as a WARNING once DEV "
        f"{dev_id} is `open` (spec §8.6 downgrade rule); "
        f"closed-only errors={only_when_closed!r} open warnings={open_warnings!r}"
    )

    # --- Step 3: invalid `status` value is itself an ERROR (static check). ---
    _set_dev_fields(
        doc_path,
        dev_id,
        "DEV covering rule 6.4",
        f"status: resolved\n{common_fields}closed_at: 2026-09-25\n"
        "closed_condition: RTM の全項目が verified になった\n",
    )
    resolved_check = _run_cli(root, "check")
    assert resolved_check.returncode == 1, (
        f"expected `saalco check` to exit 1 for DEV {dev_id} with "
        f"`status: resolved` (REQ-0005 bullet 1): {resolved_check.stdout}\n"
        f"{resolved_check.stderr}"
    )
    assert "ERROR" in resolved_check.stdout, (
        f"expected an ERROR in `saalco check` output for DEV {dev_id} with "
        f"`status: resolved`: {resolved_check.stdout}"
    )
    assert dev_id in resolved_check.stdout, (
        f"expected the ERROR message to reference {dev_id} (spec §5: error "
        f"messages include the offending ID): {resolved_check.stdout}"
    )
