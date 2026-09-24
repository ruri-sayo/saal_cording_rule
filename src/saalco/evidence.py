"""Evidence collection: quality gates, tests, coverage, and manifest/package generation.

Responsibilities:
    - Run the ordered quality gates and test suites declared in `docs/project.md` (spec §16),
      recording each step's command, timing, exit code, and
      PASS/FAIL/NOT_CONFIGURED/ERROR result.
    - Compute diff and total coverage against the nearest PASS-status ancestor Evidence
      (spec §15, Rule 7.3), never letting a FAIL/NOT_EVALUATED Evidence become the coverage
      baseline.
    - Parse each test suite's JUnit XML report to attach a PASS/FAIL/NOT_EVALUATED result to
      every (test, marker) pair discovered by `markers.scan_tests`, aggregating parametrized
      cases under one nodeid.
    - Write the Evidence manifest and human-readable summary (spec §17), and the Evidence
      Package view (spec §17.1) — the package is a set of references to existing artifacts,
      never a copy of their content.
    - Detect whether a step dirtied the tracked working tree (outside `evidence/`) and fail
      that step accordingly (spec §17).

Non-responsibilities:
    - Document/ID validation and static traceability checks (see `checks.py`).
    - RTM computation (see `trace.py`); this module only invokes it and reads its own output
      indirectly through `current_manifest`.

External dependencies: git, `uv run coverage json` (coverage export), and the project's
configured `gate.*` / `test.*` commands (`docs/project.md`), all invoked as subprocesses.

Filesystem effects: writes raw, untracked artifacts under
`.saal/artifacts/<commit>/<run-id>/`; writes the tracked manifest and summary under
`evidence/<commit>/<run-id>/`; writes `.saal/packages/<feature>/` (untracked).

Environment assumptions: run from inside a SAALCO project (`docs/project.md` present); `git`
on PATH; a completely clean working tree at the start of `create`.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from .documents import Item, items, parse_document
from .errors import EnvironmentError, SaalcoError
from .markers import scan_tests
from .project import config, git


def _sha(path: Path) -> str:
    """Return the sha256 hex digest of a file's contents.

    Side Effects:
        Reads `path`.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_manifests(root: Path) -> list[dict[str, object]]:
    """Load every Evidence manifest that is committed to git.

    An Evidence manifest not yet committed (e.g. from a run still in progress) is not
    "Evidence" in the spec §8 sense and must never influence baselines or lookups.

    Side Effects:
        Runs `git ls-files --error-unmatch` once per candidate `evidence/*/*/manifest.json`
        and reads each tracked one.
    """
    result: list[dict[str, object]] = []
    for path in sorted((root / "evidence").glob("*/*/manifest.json")):
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(root))],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode:
            continue
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return result


def _nearest_manifest(
    candidates: list[tuple[int, str, dict[str, object]]],
) -> dict[str, object] | None:
    """Pick the candidate with the smallest distance, ties broken by the greatest run_id.

    Args:
        candidates: (ancestor distance, run_id, manifest) tuples.

    Returns:
        The selected manifest, or None if `candidates` is empty. Deterministic regardless of
        input order (contract 3 / 9).
    """
    if not candidates:
        return None
    best_distance = min(distance for distance, _run_id, _data in candidates)
    nearest = [c for c in candidates if c[0] == best_distance]
    return max(nearest, key=lambda c: c[1])[2]


def current_manifest(root: Path) -> dict[str, object] | None:
    """Return the current Evidence manifest applicable to HEAD.

    "Current" means: a tracked Evidence whose target commit is HEAD or an ancestor of it, and
    whose only changes between that commit and HEAD are bookkeeping paths (`evidence/`,
    `docs/trace/`, `docs/ids.ledger`) — i.e. the code at HEAD is unchanged from what that
    Evidence exercised. The nearest such target commit wins; ties are broken by the latest
    `run_id` (contract 3).

    Returns:
        The manifest dict, or None if HEAD cannot be resolved or no qualifying Evidence
        exists.

    Side Effects:
        Runs git (rev-parse, ls-files, merge-base, diff, rev-list).
    """
    try:
        head = git(root, "rev-parse", "HEAD")
    except SaalcoError:
        return None
    candidates: list[tuple[int, str, dict[str, object]]] = []
    for data in _tracked_manifests(root):
        try:
            target = str(data["target_commit"])
            proc = subprocess.run(
                ["git", "merge-base", "--is-ancestor", target, head], cwd=root, check=False
            )
            if proc.returncode:
                continue
            changed = set(git(root, "diff", "--name-only", f"{target}..{head}").splitlines())
            allowed = all(
                p.startswith(("evidence/", "docs/trace/")) or p == "docs/ids.ledger"
                for p in changed
            )
            if not allowed:
                continue
            distance = int(git(root, "rev-list", "--count", f"{target}..{head}"))
            candidates.append((distance, str(data.get("run_id", "")), data))
        except (KeyError, ValueError, SaalcoError):
            continue
    return _nearest_manifest(candidates)


def _coverage_baseline(root: Path, target: str) -> dict[str, object] | None:
    """Find the nearest strict-ancestor Evidence usable as the coverage baseline (spec §15).

    Only a tracked Evidence whose target commit is a *strict* ancestor of `target` and whose
    `coverage.status == "PASS"` may become the baseline; FAIL/NOT_EVALUATED Evidence is
    skipped, so re-running Evidence can never launder a FAIL into a PASS baseline. Ties (same
    ancestor distance) are broken by the latest `run_id`.

    Returns:
        The baseline manifest, or None when no qualifying ancestor Evidence exists — the
        caller then diffs against the empty tree.

    Side Effects:
        Runs git (merge-base, rev-list) once per candidate manifest.
    """
    candidates: list[tuple[int, str, dict[str, object]]] = []
    for data in _tracked_manifests(root):
        commit = data.get("target_commit")
        coverage = data.get("coverage")
        if not isinstance(commit, str) or not isinstance(coverage, dict):
            continue
        if commit == target or coverage.get("status") != "PASS":
            continue
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, target],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode:
            continue
        try:
            distance = int(git(root, "rev-list", "--count", f"{commit}..{target}"))
        except SaalcoError:
            continue
        candidates.append((distance, str(data.get("run_id", "")), data))
    return _nearest_manifest(candidates)


def _changed_lines(diff_text: str) -> dict[str, set[int]]:
    """Map each changed file to its added/modified line numbers from a `git diff -U0`.

    A pure-deletion hunk (`@@ -a,b +c,0 @@`, i.e. added-line count 0) contributes no line
    numbers and does not register the file as changed: a file with only deleted lines has
    nothing new that needs covering.
    """
    changed: dict[str, set[int]] = {}
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@") and current_file:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not match:
                continue
            start, count = int(match.group(1)), int(match.group(2) or "1")
            if count == 0:
                continue
            changed.setdefault(current_file, set()).update(range(start, start + count))
    return changed


def _empty_coverage() -> dict[str, object]:
    """Return the default, all-`NOT_EVALUATED` coverage block."""
    return {
        "total": None,
        "diff": None,
        "diff_base_commit": None,
        "status": "NOT_EVALUATED",
        "json_path": None,
    }


def _coverage_result(root: Path, target: str, coverage_path: Path) -> dict[str, object]:
    """Compute total/diff coverage and PASS/FAIL/NOT_EVALUATED status (spec §15, Rule 7.3).

    Diff coverage is covered / measurable executable lines among changed lines under `src/`
    (per `_changed_lines`), against the nearest qualifying ancestor Evidence
    (`_coverage_baseline`). It is 100.0 when there are no changed lines, or when the changed
    lines contain nothing executable (e.g. a comment-only change) — there is nothing to
    cover, so the diff trivially passes. `status` is PASS only when diff >= 80% and the total
    has not dropped below the baseline's own recorded total (using that same baseline; no
    baseline means no drop is possible). Any failure to read or compute coverage yields
    NOT_EVALUATED — never an accidental FAIL or PASS.

    Args:
        root: project root.
        target: target commit hash being evaluated (HEAD at `create` time).
        coverage_path: path to the exported coverage JSON (`coverage json --show-contexts`).

    Returns:
        A `coverage` manifest block: `{total, diff, diff_base_commit, status, json_path}`.

    Side Effects:
        Reads `coverage_path` and every tracked Evidence manifest; runs git (diff,
        merge-base, rev-list, hash-object).
    """
    try:
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
        total = round(float(data["totals"]["percent_covered"]), 2)
        json_path = coverage_path.relative_to(root).as_posix()

        baseline = _coverage_baseline(root, target)
        base_ref = (
            str(baseline["target_commit"])
            if baseline
            else git(root, "hash-object", "-t", "tree", "/dev/null")
        )
        diff_text = git(root, "diff", "--unified=0", base_ref, target, "--", "src")
        changed = _changed_lines(diff_text)

        covered = measurable = 0
        files = data.get("files", {})
        for name, line_numbers in changed.items():
            file_data = files.get(name) or files.get(str((root / name).resolve()))
            if not file_data:
                continue
            executed = set(file_data.get("executed_lines", []))
            missing = set(file_data.get("missing_lines", []))
            relevant = line_numbers & (executed | missing)
            measurable += len(relevant)
            covered += len(relevant & executed)
        # No changed lines, or changed lines contain nothing executable: vacuously 100%.
        diff_percent = (covered / measurable * 100) if measurable else 100.0

        baseline_coverage = baseline.get("coverage") if baseline else None
        baseline_total = (
            baseline_coverage.get("total") if isinstance(baseline_coverage, dict) else None
        )
        passed = diff_percent >= 80 and (baseline_total is None or total >= float(baseline_total))
        return {
            "total": total,
            "diff": round(diff_percent, 2),
            "diff_base_commit": str(baseline["target_commit"]) if baseline else None,
            "status": "PASS" if passed else "FAIL",
            "json_path": json_path,
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, SaalcoError):
        return _empty_coverage()


def _tool_version(command: str) -> str | None:
    """Best-effort `<tool> --version` lookup for a gate/test command's first token.

    Advisory only: never blocks or fails a gate. Returns None when the command can't be
    parsed, the binary is missing, or the process fails or exceeds its timeout.

    Side Effects:
        Runs `<first token of command> --version` with a 5 second timeout.
    """
    try:
        tool = shlex.split(command)[0]
    except (ValueError, IndexError):
        return None
    try:
        proc = subprocess.run(
            [tool, "--version"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in (proc.stdout or proc.stderr).splitlines():
        if line.strip():
            return line.strip()
    return None


def _dirty(root: Path) -> bool:
    """Return True if git shows tracked changes outside `evidence/` (spec §17 step check).

    Side Effects:
        Runs `git status --porcelain`.
    """
    for line in git(root, "status", "--porcelain").splitlines():
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if path and not path.startswith("evidence/"):
            return True
    return False


def _run(
    root: Path, command: str, log: Path, environment: dict[str, str] | None = None
) -> tuple[int, str, str, str]:
    """Run one gate/test command, capturing its output to `log`.

    Args:
        root: working directory for the command.
        command: shell-style command line (split with `shlex`).
        log: file to receive combined stdout/stderr.
        environment: extra environment variables layered on top of the current environment.

    Returns:
        (exit_code, result, started_at, ended_at). `result` is "PASS" (exit 0), "FAIL"
        (non-zero exit), or "ERROR" (the executable could not be found/launched — exit_code
        127 in that case).

    Side Effects:
        Runs `command` as a subprocess; writes `log`.
    """
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        args = shlex.split(command)
        proc = subprocess.run(
            args,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env={**os.environ, **(environment or {})},
        )
        log.write_text(proc.stdout, encoding="utf-8")
        code = proc.returncode
        result = "PASS" if code == 0 else "FAIL"
    except OSError as exc:
        log.write_text(str(exc), encoding="utf-8")
        code, result = 127, "ERROR"
    ended = datetime.now().astimezone().isoformat(timespec="seconds")
    return code, result, started, ended


def _junit_nodeid(root: Path, classname: str, name: str, file: str | None) -> str | None:
    """Map one JUnit `<testcase>` to its contract-1 nodeid, stripping any `[param]` suffix.

    `classname` is the pytest-produced dotted module path plus an optional dotted class name
    (`tests.unit.test_x` or `tests.unit.test_x.TestFoo`). `file`, when pytest reports it, is
    the test file's path and is preferred since it resolves the module/class split
    unambiguously; otherwise the split is found by checking which prefix of `classname`,
    read as a path, is an actual file under `root`.

    Returns:
        `tests/.../test_x.py::test_name` or `tests/.../test_x.py::Class::test_name`, or None
        if no plausible source file can be found.
    """
    base_name = re.sub(r"\[.*\]$", "", name)
    if file:
        rel = file.replace("\\", "/")
        if not rel.endswith(".py"):
            rel = f"{rel}.py"
        module = rel[:-3].replace("/", ".")
        if classname == module:
            return f"{rel}::{base_name}"
        if classname.startswith(f"{module}."):
            cls = classname[len(module) + 1 :]
            return f"{rel}::{cls}::{base_name}"
        return f"{rel}::{base_name}"
    parts = classname.split(".")
    for split_at in range(len(parts), 0, -1):
        rel = "/".join(parts[:split_at]) + ".py"
        if (root / rel).is_file():
            cls_parts = parts[split_at:]
            if cls_parts:
                return f"{rel}::{'.'.join(cls_parts)}::{base_name}"
            return f"{rel}::{base_name}"
    return None


def _parse_junit(root: Path, path: Path) -> dict[str, str]:
    """Parse a JUnit XML report into aggregated per-nodeid PASS/FAIL results.

    Parametrized cases sharing a nodeid (after stripping the `[param]` suffix) are
    aggregated: PASS only if every case passed; any failure/error makes the nodeid FAIL.
    A nodeid whose cases are skipped-only, or that has no cases at all, is simply absent from
    the result (the caller treats a missing nodeid as NOT_EVALUATED).

    Side Effects:
        Reads `path` (a `--junitxml` report written by `_run`); tolerates a missing or
        malformed file by returning an empty mapping.
    """
    outcomes: dict[str, list[str]] = {}
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError):
        return {}
    for case in tree.getroot().iter("testcase"):
        nodeid = _junit_nodeid(
            root, case.get("classname", ""), case.get("name", ""), case.get("file")
        )
        if nodeid is None:
            continue
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "FAIL"
        elif case.find("skipped") is not None:
            outcome = "SKIPPED"
        else:
            outcome = "PASS"
        outcomes.setdefault(nodeid, []).append(outcome)
    results: dict[str, str] = {}
    for nodeid, cases in outcomes.items():
        if "FAIL" in cases:
            results[nodeid] = "FAIL"
        elif all(case == "PASS" for case in cases):
            results[nodeid] = "PASS"
        # else: skipped-only -> left absent, i.e. NOT_EVALUATED by lookup default.
    return results


def _open_devs(root: Path) -> list[Item]:
    """Collect open DEV (deviation) items across every feature, for the Evidence summary.

    Side Effects:
        Reads each `docs/features/F-*/90-deviations.md`.
    """
    result: list[Item] = []
    for path in sorted((root / "docs/features").glob("F-*/90-deviations.md")):
        try:
            doc = parse_document(path)
        except SaalcoError:
            continue
        result.extend(
            item for item in items(doc) if item.kind == "DEV" and item.meta.get("status") == "open"
        )
    return result


def create(root: Path) -> tuple[Path, str]:
    """Run all configured gates and test suites for HEAD and record an Evidence manifest.

    Executes, in order: `gate.*` commands (per `docs/project.md`, numeric order), then
    `saalco check` (static), then `test.unit` / `test.integration` / `test.e2e`, then the
    coverage JSON export. Refuses to run unless the working tree is completely clean
    (spec §17). After each gate/test step, a change to the tracked tree outside `evidence/`
    fails that step (spec §17).

    Returns:
        `(manifest_path, overall)`. `overall` is "PASS" only if every gate result is PASS or
        NOT_CONFIGURED (this includes the `test.*` gate entries), coverage status is PASS,
        and no step dirtied the tree; otherwise "FAIL".

    Raises:
        EnvironmentError: if the working tree is not clean at the start.

    Side Effects:
        Runs git, the project's `gate.*`/`test.*` commands, `uv run coverage json`, and
        `saalco check` in-process. Writes raw artifacts under
        `.saal/artifacts/<target>/<run-id>/` (untracked); writes the manifest and summary
        under `evidence/<target>/<run-id>/`; calls `trace.generate(root)`, which writes
        `docs/trace/`.
    """
    if git(root, "status", "--porcelain"):
        raise EnvironmentError(
            "ERROR working tree is dirty; commit all changes before `saalco evidence`."
        )
    target = git(root, "rev-parse", "HEAD")
    cfg = config(root)

    base_run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    run_id = base_run_id
    raw = root / ".saal/artifacts" / target / run_id
    attempt = 1
    while True:
        try:
            raw.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            attempt += 1
            run_id = f"{base_run_id}-{attempt}"
            raw = root / ".saal/artifacts" / target / run_id

    gates: list[dict[str, object]] = []
    sequence = sorted((k, v) for k, v in cfg.items() if k.startswith("gate."))
    for key, command in sequence:
        name = key.split(".", 2)[-1]
        if not command:
            gates.append(
                {
                    "name": name,
                    "command": "",
                    "started_at": None,
                    "ended_at": None,
                    "exit_code": None,
                    "result": "NOT_CONFIGURED",
                    "tool_version": None,
                }
            )
            continue
        code, result, started, ended = _run(root, command, raw / f"gate-{name}.log")
        if result != "ERROR" and _dirty(root):
            result = "FAIL"
        gates.append(
            {
                "name": name,
                "command": command,
                "started_at": started,
                "ended_at": ended,
                "exit_code": code,
                "result": result,
                "tool_version": _tool_version(command),
            }
        )

    from .checks import run as check

    static = check(root)
    gates.append(
        {
            "name": "saalco-check",
            "command": "saalco check",
            "started_at": None,
            "ended_at": None,
            "exit_code": 0 if static.ok else 1,
            "result": "PASS" if static.ok else "FAIL",
            "tool_version": "1.0.0",
        }
    )

    per_test_results: dict[str, str] = {}
    pytest_run = 0
    for key in ("test.unit", "test.integration", "test.e2e"):
        command = cfg.get(key, "")
        category = key.split(".")[1]
        if not command:
            continue
        is_pytest = "pytest" in shlex.split(command)
        executed_command = command
        if cfg.get("language") == "python" and is_pytest:
            append = " --cov-append" if pytest_run else ""
            executed_command += f" --cov=src --cov-context=test{append}"
            pytest_run += 1
        junit_path = raw / f"junit-{category}.xml"
        if is_pytest:
            executed_command += f" -p no:cacheprovider --junitxml={junit_path}"
        code, result, started, ended = _run(
            root,
            executed_command,
            raw / f"test-{category}.log",
            {
                "COVERAGE_FILE": str(raw / "coverage.data"),
                "PYTHONPYCACHEPREFIX": str(raw / "pycache"),
            },
        )
        if result != "ERROR" and _dirty(root):
            result = "FAIL"
        gates.append(
            {
                "name": key,
                "command": executed_command,
                "started_at": started,
                "ended_at": ended,
                "exit_code": code,
                "result": result,
                "tool_version": _tool_version(command),
            }
        )
        if is_pytest and junit_path.exists():
            per_test_results.update(_parse_junit(root, junit_path))

    markers_found = scan_tests(root)
    tests: list[dict[str, object]] = [
        {
            "nodeid": m.nodeid,
            "category": m.category,
            "marker": m.marker,
            "referenced_id": m.referenced_id,
            "spec": m.spec,
            "result": per_test_results.get(m.nodeid, "NOT_EVALUATED"),
        }
        for m in markers_found
    ]

    coverage: dict[str, object] = _empty_coverage()
    coverage_path = raw / "coverage.json"
    proc = subprocess.run(
        ["uv", "run", "coverage", "json", "--show-contexts", "-o", str(coverage_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "COVERAGE_FILE": str(raw / "coverage.data")},
    )
    if proc.returncode == 0 and coverage_path.exists():
        coverage = _coverage_result(root, target, coverage_path)

    lock = next(
        (
            root / name
            for name in ("uv.lock", "poetry.lock", "requirements.txt")
            if (root / name).exists()
        ),
        None,
    )
    artifacts = [
        {
            "path": p.relative_to(root).as_posix(),
            "sha256": _sha(p),
            "retention_location": cfg.get("raw_evidence_location", ".saal/artifacts"),
        }
        for p in sorted(raw.glob("*"))
        if p.is_file()
    ]

    overall = (
        "PASS"
        if all(g["result"] in {"PASS", "NOT_CONFIGURED"} for g in gates)
        and coverage["status"] == "PASS"
        else "FAIL"
    )
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "saal_rules_version": cfg["saal_rules_version"],
        "saalco_version": "1.0.0",
        "target_commit": target,
        "run_id": run_id,
        "executed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
            "arch": platform.machine(),
        },
        "lockfile": {"path": lock.name, "sha256": _sha(lock)}
        if lock
        else {"path": None, "sha256": None},
        "gates": gates,
        "tests": tests,
        "coverage": coverage,
        "artifacts": artifacts,
        "overall": overall,
    }
    destination = root / "evidence" / target / run_id
    destination.mkdir(parents=True)
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    from .trace import generate

    rtm_rows = generate(root)
    dev_items = _open_devs(root)

    category_counts: dict[str, dict[str, int]] = {
        category: {"PASS": 0, "FAIL": 0, "NOT_EVALUATED": 0}
        for category in ("unit", "integration", "e2e")
    }
    for m in markers_found:
        counts = category_counts.get(m.category)
        if counts is None:
            continue
        counts[per_test_results.get(m.nodeid, "NOT_EVALUATED")] += 1

    rtm_counts: dict[str, int] = {}
    for row in rtm_rows:
        rtm_counts[row["verify_status"]] = rtm_counts.get(row["verify_status"], 0) + 1

    summary = [
        f"# Evidence {run_id}",
        "",
        f"- Target commit: `{target}`",
        f"- Executed at: {manifest['executed_at']}",
        f"- Overall: **{overall}**",
        "",
        "## Gates",
        "",
    ]
    summary.extend(f"- {g['name']}: {g['result']}" for g in gates)
    summary += ["", "## Tests", ""]
    summary.extend(
        f"- {category}: PASS={c['PASS']} FAIL={c['FAIL']} NOT_EVALUATED={c['NOT_EVALUATED']}"
        for category, c in category_counts.items()
    )
    summary += [
        "",
        "## Coverage",
        "",
        f"- Total: {coverage['total']}",
        f"- Diff: {coverage['diff']}",
        f"- Base: {coverage['diff_base_commit']}",
        f"- Status: {coverage['status']}",
        "",
        "## RTM",
        "",
    ]
    if rtm_counts:
        summary.extend(f"- {status}: {count}" for status, count in sorted(rtm_counts.items()))
    else:
        summary.append("- (no requirements)")
    summary += ["", "## Open DEV", ""]
    if dev_items:
        summary.extend(f"- {dev.id}: {dev.title}" for dev in dev_items)
    else:
        summary.append("- (none)")
    summary += ["", "## Raw artifacts", "", f"- `{raw.relative_to(root)}`", ""]
    (destination / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return manifest_path, overall


def package(root: Path, feature: str) -> Path:
    """Build the Evidence Package view for one feature (spec §17.1, Rule 8.5).

    Writes `.saal/packages/<feature>/package.json` and `index.md` as *references* to
    existing documents and records — the requirements document, the feature's RTM rows, the
    current manifest's path (not its content) plus its target_commit/run_id/overall, each
    feature document's approval record, the feature's open DEVs, and the
    implementation/design diff document. Nothing is copied.

    Args:
        root: project root.
        feature: feature ID, e.g. `F-001`.

    Returns:
        The `.saal/packages/<feature>` directory.

    Raises:
        SaalcoError: if there is no current Evidence, or the feature directory is
            missing/ambiguous.

    Side Effects:
        Calls `trace.generate(root, write=False)` (read-only) and `current_manifest(root)`
        (reads git and `evidence/`); reads each feature document; writes
        `.saal/packages/<feature>/package.json` and `index.md`.
    """
    manifest = current_manifest(root)
    if not manifest:
        raise SaalcoError("ERROR no current Evidence available for packaging.")
    feature_dirs = list((root / "docs/features").glob(f"{feature}_*"))
    if len(feature_dirs) != 1:
        raise SaalcoError(f"ERROR {feature}: feature directory not found.")
    feature_dir = feature_dirs[0]

    from .trace import generate

    rtm_rows = [row for row in generate(root, write=False) if row.get("feature") == feature]

    doc_paths = sorted(p.relative_to(root).as_posix() for p in feature_dir.glob("*.md"))
    approvals = []
    for rel in doc_paths:
        doc = parse_document(root / rel)
        approvals.append(
            {
                "path": rel,
                "status": doc.header.get("status", ""),
                "version": doc.header.get("version"),
                "approved_by": doc.header.get("approved_by"),
                "approved_at": doc.header.get("approved_at"),
                "approved_hash": doc.header.get("approved_hash"),
            }
        )

    dev_path = feature_dir / "90-deviations.md"
    open_devs = (
        [
            {"id": item.id, "rule": item.meta.get("rule"), "scope": item.meta.get("scope")}
            for item in items(parse_document(dev_path))
            if item.kind == "DEV" and item.meta.get("status") == "open"
        ]
        if dev_path.exists()
        else []
    )

    requirements_path = feature_dir / "10-requirements.md"
    diff_path = feature_dir / "45-implementation-diff.md"
    requirements_rel = (
        requirements_path.relative_to(root).as_posix() if requirements_path.exists() else None
    )
    diff_rel = diff_path.relative_to(root).as_posix() if diff_path.exists() else None
    manifest_rel = (
        (
            root
            / "evidence"
            / str(manifest["target_commit"])
            / str(manifest["run_id"])
            / "manifest.json"
        )
        .relative_to(root)
        .as_posix()
    )

    data = {
        "feature": feature,
        "requirements": requirements_rel,
        "rtm_rows": rtm_rows,
        "evidence": {
            "manifest_path": manifest_rel,
            "target_commit": manifest.get("target_commit"),
            "run_id": manifest.get("run_id"),
            "overall": manifest.get("overall"),
        },
        "approvals": approvals,
        "open_devs": open_devs,
        "implementation_diff": diff_rel,
    }
    destination = root / ".saal/packages" / feature
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "package.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def link(rel: str | None) -> str:
        return f"- [{rel}](../../../{rel})" if rel else "- (missing)"

    lines = [f"# Evidence Package {feature}", "", "## Requirements", link(requirements_rel), ""]
    lines.append("## RTM rows")
    if rtm_rows:
        lines.extend(f"- {row['req_id']}: {row['verify_status']}" for row in rtm_rows)
    else:
        lines.append("- (none)")
    evidence_line = (
        f"- [{manifest_rel}](../../../{manifest_rel}) "
        f"(target `{manifest.get('target_commit')}`, run `{manifest.get('run_id')}`, "
        f"overall {manifest.get('overall')})"
    )
    lines += ["", "## Evidence manifest", evidence_line, "", "## Approvals"]
    if approvals:
        lines.extend(
            f"- [{a['path']}](../../../{a['path']}): {a['status']} v{a['version']} "
            f"by {a['approved_by']} at {a['approved_at']}"
            for a in approvals
        )
    else:
        lines.append("- (none)")
    lines += ["", "## Open DEV"]
    if open_devs:
        lines.extend(
            f"- {dev['id']} (rule {dev['rule']}, scope {dev['scope']})" for dev in open_devs
        )
    else:
        lines.append("- (none)")
    lines += ["", "## Implementation diff", link(diff_rel), ""]
    (destination / "index.md").write_text("\n".join(lines), encoding="utf-8")
    return destination
