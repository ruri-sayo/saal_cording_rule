from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from .errors import EnvironmentError, SaalcoError
from .markers import scan_tests
from .project import config, git


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_manifest(root: Path) -> dict | None:
    manifests = sorted((root / "evidence").glob("*/*/manifest.json"), reverse=True)
    try:
        head = git(root, "rev-parse", "HEAD")
    except SaalcoError:
        return None
    for path in manifests:
        try:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(path.relative_to(root))],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if tracked.returncode:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            target = data["target_commit"]
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
            if allowed:
                return data
        except (OSError, KeyError, json.JSONDecodeError):
            continue
    return None


def _coverage_result(root: Path, target: str, coverage_path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "total": None,
        "diff": None,
        "diff_base_commit": None,
        "status": "NOT_EVALUATED",
    }
    try:
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
        total = float(data["totals"]["percent_covered"])
        prior = None
        for path in sorted((root / "evidence").glob("*/*/manifest.json"), reverse=True):
            candidate = json.loads(path.read_text(encoding="utf-8"))
            commit = candidate.get("target_commit")
            if (
                commit != target
                and subprocess.run(
                    ["git", "merge-base", "--is-ancestor", str(commit), target],
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                ).returncode
                == 0
            ):
                prior = candidate
                break
        base = (
            prior["target_commit"] if prior else git(root, "hash-object", "-t", "tree", "/dev/null")
        )
        diff = git(root, "diff", "--unified=0", str(base), target, "--", "src")
        changed: dict[str, set[int]] = {}
        current_file = ""
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("@@") and current_file:
                match = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if match:
                    start, count = int(match.group(1)), int(match.group(2) or "1")
                    changed.setdefault(current_file, set()).update(range(start, start + count))
        covered = 0
        measurable = 0
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
        diff_percent = (
            100.0 if not changed else ((covered / measurable * 100) if measurable else None)
        )
        previous_total = prior.get("coverage", {}).get("total") if prior else None
        rounded_total = round(total, 2)
        passed = (
            diff_percent is not None
            and diff_percent >= 80
            and (previous_total is None or rounded_total >= float(previous_total))
        )
        result.update(
            total=rounded_total,
            diff=round(diff_percent, 2) if diff_percent is not None else None,
            diff_base_commit=prior["target_commit"] if prior else None,
            status="PASS" if passed else "FAIL",
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, SaalcoError):
        pass
    return result


def _run(
    root: Path, command: str, log: Path, environment: dict[str, str] | None = None
) -> tuple[int, str, str, str]:
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


def create(root: Path) -> Path:
    if git(root, "status", "--porcelain"):
        raise EnvironmentError(
            "ERROR working tree is dirty; commit all changes before `saalco evidence`."
        )
    target = git(root, "rev-parse", "HEAD")
    cfg = config(root)
    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    raw = root / ".saal/artifacts" / target / run_id
    raw.mkdir(parents=True, exist_ok=False)
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
        if git(root, "status", "--porcelain"):
            result = "FAIL"
        gates.append(
            {
                "name": name,
                "command": command,
                "started_at": started,
                "ended_at": ended,
                "exit_code": code,
                "result": result,
                "tool_version": None,
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
    test_suite_results: dict[str, str] = {}
    pytest_run = 0
    for key in ("test.unit", "test.integration", "test.e2e"):
        command = cfg.get(key, "")
        category = key.split(".")[1]
        if not command:
            test_suite_results[category] = "NOT_CONFIGURED"
            continue
        executed_command = command
        if cfg.get("language") == "python" and "pytest" in shlex.split(command):
            append = " --cov-append" if pytest_run else ""
            executed_command += f" --cov=src --cov-context=test{append}"
            pytest_run += 1
        if "pytest" in shlex.split(command):
            executed_command += " -p no:cacheprovider"
        code, result, started, ended = _run(
            root,
            executed_command,
            raw / f"test-{category}.log",
            {
                "COVERAGE_FILE": str(raw / "coverage.data"),
                "PYTHONPYCACHEPREFIX": str(raw / "pycache"),
            },
        )
        if git(root, "status", "--porcelain"):
            result = "FAIL"
        test_suite_results[category] = result
        gates.append(
            {
                "name": key,
                "command": executed_command,
                "started_at": started,
                "ended_at": ended,
                "exit_code": code,
                "result": result,
                "tool_version": None,
            }
        )
    tests = [
        {
            "nodeid": m.nodeid,
            "category": m.category,
            "marker": m.marker,
            "referenced_id": m.referenced_id,
            "spec": m.spec,
            "result": test_suite_results.get(m.category, "NOT_EVALUATED"),
        }
        for m in scan_tests(root)
    ]
    coverage: dict[str, object] = {
        "total": None,
        "diff": None,
        "diff_base_commit": None,
        "status": "NOT_EVALUATED",
    }
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
    manifest = {
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
    }
    destination = root / "evidence" / target / run_id
    destination.mkdir(parents=True)
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    overall = (
        "PASS"
        if all(x["result"] in {"PASS", "NOT_CONFIGURED"} for x in gates)
        and coverage["status"] == "PASS"
        else "FAIL"
    )
    summary = [
        f"# Evidence {run_id}",
        "",
        f"- Target commit: `{target}`",
        f"- Executed at: {manifest['executed_at']}",
        f"- Overall: **{overall}**",
        f"- Coverage: {coverage['status']}",
        f"- Raw artifacts: `{raw.relative_to(root)}`",
        "",
        "## Gates",
        "",
    ]
    summary.extend(f"- {x['name']}: {x['result']}" for x in gates)
    (destination / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    from .trace import generate

    generate(root)
    return manifest_path


def package(root: Path, feature: str) -> Path:
    manifest = current_manifest(root)
    if not manifest:
        raise SaalcoError("ERROR no current Evidence available for packaging.")
    feature_dirs = list((root / "docs/features").glob(f"{feature}_*"))
    if len(feature_dirs) != 1:
        raise SaalcoError(f"ERROR {feature}: feature directory not found.")
    destination = root / ".saal/packages" / feature
    destination.mkdir(parents=True, exist_ok=True)
    docs = sorted(p.relative_to(root).as_posix() for p in feature_dirs[0].glob("*.md"))
    data = {
        "feature": feature,
        "documents": docs,
        "evidence": manifest,
        "rtm": "docs/trace/rtm.csv",
    }
    (destination / "package.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (destination / "index.md").write_text(
        "# Evidence Package "
        + feature
        + "\n\n"
        + "".join(f"- [{p}](../../../{p})\n" for p in docs),
        encoding="utf-8",
    )
    return destination
