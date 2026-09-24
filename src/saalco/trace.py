"""Requirements Traceability Matrix (RTM) generation (spec §14, Rule 6.8).

Responsibilities:
    - Resolve each REQ's transitive `covers:` ancestors (AD/DD/MD/UT/IT/ST) across
      `docs/features/**/*.md`.
    - Join test markers (`saalco.markers.scan_tests`) and the current evidence manifest to
      compute each REQ's `verify_status` (verified / unverified / stale / NOT_EVALUATED).
    - Fill `impl_files` from coverage.py test contexts (`saalco.coverage_contexts`),
      listing the `src/` files reached by any test related to the row.
    - Emit deterministic `docs/trace/rtm.csv` and `docs/trace/rtm.md` (sorted rows, no
      timestamps), per contract 4/14.

Non-responsibilities:
    - Does not run tests or coverage; only reads the current evidence manifest and coverage
      JSON that `saalco.evidence.create` already produced.
    - Does not judge approval/static-gate correctness beyond what §14's `verified` condition
      requires; deeper policy checks (e.g. unapproved-design) live in checks.py.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from .coverage_contexts import load as load_contexts
from .documents import content_hash, items, parse_document
from .errors import SaalcoError
from .evidence import current_manifest
from .markers import scan_tests
from .project import config, git

COLUMNS = [
    "req_id",
    "requirement",
    "feature",
    "design_ids",
    "impl_files",
    "unit_tests",
    "integration_tests",
    "e2e_tests",
    "verify_status",
    "evidence_commit",
]

#: Paths a manual-ST `commit` (§8.5) or a picked manifest (I-1) may differ from HEAD/target
#: by without invalidating "current" status: only Evidence bookkeeping changed.
_EVIDENCE_ONLY_PREFIXES = ("evidence/", "docs/trace/")


def _commit_is_current(root: Path, commit: str, target: str) -> bool:
    """Return True if `commit` is evidence-equivalent to `target` (spec §8.5, I-1).

    Equivalent means identical, or the diff between the two touches only Evidence
    bookkeeping paths (`evidence/`, `docs/trace/`, `docs/ids.ledger`) — e.g. a manual ST
    result recorded against a commit that was later only re-stamped with Evidence/RTM/ledger
    updates still counts as verifying the current target commit.

    Side Effects:
        Invokes `git diff` via `saalco.project.git` (read-only).
    """
    if not commit or not target:
        return False
    if commit == target:
        return True
    try:
        changed = git(root, "diff", "--name-only", f"{commit}..{target}").splitlines()
    except SaalcoError:
        return False
    return all(p.startswith(_EVIDENCE_ONLY_PREFIXES) or p == "docs/ids.ledger" for p in changed)


def _as_dicts(value: object) -> list[dict[str, Any]]:
    """Coerce a manifest field expected to be a list of dicts, tolerating malformed input."""
    return value if isinstance(value, list) else []


def generate(root: Path, write: bool = True) -> list[dict[str, str]]:
    """Compute RTM rows and, by default, write `docs/trace/rtm.csv` / `rtm.md`.

    Args:
        root: project root.
        write: when False, only compute and return rows — no files are written. Used by
            `saalco check --verification`, which must not modify the working tree
            (contract 4).

    Returns:
        One dict per REQ item (sorted by `req_id`), with keys matching `COLUMNS`.

    Side Effects:
        When `write` is True: creates `docs/trace/` if missing and overwrites
        `docs/trace/rtm.csv` and `docs/trace/rtm.md`. Reads test markers (parses
        `tests/**/test_*.py`), the current evidence manifest, and — when available — the
        coverage JSON it references (invokes `git` read-only via `_commit_is_current`).
    """
    all_items = []
    for path in sorted((root / "docs/features").glob("F-*/*.md")):
        all_items.extend(items(parse_document(path)))
    tests = scan_tests(root)
    manifest = current_manifest(root)
    language = config(root).get("language")
    contexts = load_contexts(root, manifest) if manifest else None
    rows = []
    for req in sorted((x for x in all_items if x.kind == "REQ"), key=lambda x: x.id):
        ancestors = {req.id}
        changed = True
        while changed:
            before = len(ancestors)
            for item in all_items:
                refs = {x.strip() for x in item.meta.get("covers", "").split(",")}
                if refs & ancestors:
                    ancestors.add(item.id)
            changed = len(ancestors) != before
        related_tests = [t for t in tests if t.referenced_id in ancestors]
        status = (
            "NOT_EVALUATED" if language == "other" else ("stale" if not manifest else "unverified")
        )
        if manifest and language != "other":
            results = {x.get("nodeid"): x.get("result") for x in _as_dicts(manifest.get("tests"))}
            gates = {x.get("name"): x.get("result") for x in _as_dicts(manifest.get("gates"))}
            target = str(manifest.get("target_commit", ""))

            def satisfied(
                item_id: str,
                related=related_tests,
                gate_results=gates,
                test_results=results,
                target_commit=target,
            ) -> bool:
                item = next(x for x in all_items if x.id == item_id)
                verify = item.meta.get("verify", "test")
                if verify == "review":
                    doc = parse_document(item.path)
                    return doc.header.get("status") == "approved" and doc.header.get(
                        "approved_hash"
                    ) == content_hash(doc)
                if verify == "static":
                    return gate_results.get(item.meta.get("static")) == "PASS"
                matching = [
                    test
                    for test in related
                    if test.marker == "verifies" and test.referenced_id == item_id
                ]
                if matching and all(test_results.get(test.nodeid) == "PASS" for test in matching):
                    return True
                return any(
                    x.kind == "ST"
                    and item_id in {v.strip() for v in x.meta.get("covers", "").split(",")}
                    and x.meta.get("method") == "manual"
                    and x.meta.get("result") == "PASS"
                    and _commit_is_current(root, x.meta.get("commit", ""), target_commit)
                    for x in all_items
                )

            required = [x for x in ancestors if x.startswith(("REQ-", "AD-", "DD-", "MD-"))]
            if required and all(satisfied(item_id) for item_id in required):
                status = "verified"
        related_nodeids = {t.nodeid for t in related_tests}
        impl_files = (
            sorted(f for f, nodeids in contexts.items() if nodeids & related_nodeids)
            if contexts
            else []
        )
        rows.append(
            {
                "req_id": req.id,
                "requirement": req.title,
                "feature": parse_document(req.path).header.get("feature", ""),
                "design_ids": ",".join(
                    sorted(x for x in ancestors if x.startswith(("AD-", "DD-", "MD-")))
                ),
                "impl_files": ",".join(impl_files),
                "unit_tests": ",".join(t.nodeid for t in related_tests if t.category == "unit"),
                "integration_tests": ",".join(
                    t.nodeid for t in related_tests if t.category == "integration"
                ),
                "e2e_tests": ",".join(t.nodeid for t in related_tests if t.category == "e2e"),
                "verify_status": status,
                "evidence_commit": str(manifest.get("target_commit", "")) if manifest else "",
            }
        )
    if write:
        _write(root, rows)
    return rows


def _write(root: Path, rows: list[dict[str, str]]) -> None:
    """Serialize `rows` to `docs/trace/rtm.csv` and `docs/trace/rtm.md`.

    Side Effects:
        Creates `docs/trace/` if missing; overwrites both output files.
    """
    out = root / "docs/trace"
    out.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (out / "rtm.csv").write_text(buffer.getvalue(), encoding="utf-8")
    md = [
        "# Requirements Traceability Matrix",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(COLUMNS)) + " |",
    ]
    md.extend("| " + " | ".join(row[c].replace("|", "\\|") for c in COLUMNS) + " |" for row in rows)
    (out / "rtm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
