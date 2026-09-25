"""Static and verification checks (`saalco check` / `saalco check --verification`).

Responsibilities:
    - Implement spec §12 static checks: document headers/Tier, ID ledger consistency,
      `covers:`/`verify:` reference validity and cycle-freedom, approval-hash consistency,
      test-marker cross-references, DEV `status` validity and closed-record completeness (§8.6).
    - Implement spec §13 verification-only checks (added when `verification=True`):
      current-Evidence presence, `verifies` test PASS status, coverage status, the §13-14
      unapproved-design check (via coverage contexts), RTM `verified` status, DEV-recorded
      deviations (§8.6/12.3) downgrading specific ERRORs to WARNING, and NOT_CONFIGURED gate
      warnings.

Non-responsibilities:
    - Does not run tests, gates, or coverage; only reads the current evidence manifest
      (`saalco.evidence.current_manifest`) and coverage JSON (`saalco.coverage_contexts`).
    - Does not write any files or mutate the working tree — `saalco check` is read-only
      (contract 4: it calls `trace.generate(root, write=False)`).

DEV behavior (§8.6): `status` must be `open` or `closed`. Closed DEVs must have non-empty
`closed_at` and `closed_condition`. Only `open` DEVs may downgrade ERRORs to WARNINGs; `closed`
and invalid-status DEVs never downgrade.

DEV downgrade rule numbers implemented (see `_dev_downgrade`): 4.6, 6.4, 6.8, 7.1, 7.3.
"""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .coverage_contexts import load as load_contexts
from .documents import Document, Item, content_hash, items, parse_document
from .errors import SaalcoError
from .evidence import current_manifest
from .ids import LedgerRow, read_ledger
from .markers import scan_tests
from .project import config
from .templates import TIER_FILES
from .trace import generate as generate_trace

ALLOWED = {
    "REQ": set(),
    "AD": {"REQ"},
    "DD": {"AD", "REQ"},
    "MD": {"DD", "AD", "REQ"},
    "UT": {"DD", "MD"},
    "IT": {"AD"},
    "ST": {"REQ"},
}

#: Header keys that only make sense once a document is approved (§6.5/§12-10).
_APPROVAL_KEYS = ("approved_by", "approved_at", "approved_hash")

#: verifies() category -> expected referenced item kind (spec §8.4).
_CATEGORY_EXPECTED_KIND = {"unit": {"DD", "MD"}, "integration": {"AD"}, "e2e": {"REQ"}}

#: verify: static-only category the RTM/coverage-diff DEV exceptions apply to.
_DEV_RULE_COVERAGE = "7.3"
_DEV_RULE_GATE = "7.1"
_DEV_RULE_RTM = "6.8"
#: Substantive rule this check enforces ("implement according to the approved design");
#: 13.5 is only the tool-spec list item number, not a rule number.
_DEV_RULE_UNAPPROVED_DESIGN = "4.6"
_DEV_RULE_VERIFIES_NOT_PASS = "6.4"


@dataclass
class Report:
    """Accumulated check findings.

    Attributes:
        errors: Blocking findings; a non-empty list means `saalco check` exits non-zero.
        warnings: Non-blocking findings (e.g. ERRORs downgraded by an open DEV record).
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when there are no errors (warnings alone do not fail the check)."""
        return not self.errors

    def output(self, as_json: bool = False) -> str:
        """Render the report as plain text (`ERROR ...` / `WARNING ...` lines) or JSON."""
        if as_json:
            return json.dumps(
                {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}, indent=2
            )
        lines = [*(f"ERROR {x}" for x in self.errors), *(f"WARNING {x}" for x in self.warnings)]
        lines.append(f"{len(self.errors)} errors, {len(self.warnings)} warnings")
        return "\n".join(lines)


def _documents(root: Path, report: Report) -> list[Document]:
    """Parse every feature document and check header consistency (§12 items 1, 6, 10).

    Checks: required header keys present; `status` is a valid value; when `approved`, all
    approval fields are present and `approved_hash` matches current content; when `draft` or
    `superseded`, approval-only fields (`approved_by`/`approved_at`/`approved_hash`) must be
    absent — carrying them is an inconsistent approval record (§12-10). `version` is exempt:
    keeping it after moving off `approved` is fine (a document may retain its last-approved
    version number for reference).

    Side Effects:
        Reads every `docs/features/F-*/*.md` file.
    """
    docs = []
    for path in sorted((root / "docs" / "features").glob("F-*/*.md")):
        try:
            doc = parse_document(path)
            docs.append(doc)
            missing = {"kind", "feature", "status"} - doc.header.keys()
            if missing:
                report.errors.append(
                    f"{path.relative_to(root)}: missing header keys {sorted(missing)}"
                )
            status = doc.header.get("status")
            if status not in {"draft", "approved", "superseded"}:
                report.errors.append(f"{path.relative_to(root)}: invalid status")
            if status == "approved":
                expected = doc.header.get("approved_hash")
                if not all(
                    doc.header.get(k)
                    for k in ("version", "approved_by", "approved_at", "approved_hash")
                ):
                    report.errors.append(f"{path.relative_to(root)}: incomplete approval metadata")
                elif expected != content_hash(doc):
                    report.errors.append(
                        f"{path.relative_to(root)}: approved_hash does not match current content; ask a human to re-approve"
                    )
            elif status in {"draft", "superseded"}:
                stale = [k for k in _APPROVAL_KEYS if doc.header.get(k)]
                if stale:
                    report.errors.append(
                        f"{path.relative_to(root)}: status is {status!r} but still carries "
                        f"approval fields {sorted(stale)} (inconsistent approval record)"
                    )
        except (OSError, ValueError, SaalcoError) as exc:
            report.errors.append(str(exc).removeprefix("ERROR "))
    return docs


def _find_cycles(edges: dict[str, list[str]], report: Report) -> None:
    """Detect `covers:` cycles with a visited set, reporting each distinct cycle once.

    Standard white/gray/black DFS: `visited` marks nodes whose subtree is fully explored
    (never re-entered), `on_stack` marks nodes on the current DFS path (a cycle is found
    when we reach a node already `on_stack`). Cycles are deduped by their frozenset of
    member IDs so the same cycle discovered from different start nodes reports only once.
    """
    visited: set[str] = set()
    on_stack: set[str] = set()
    reported: set[frozenset[str]] = set()

    def visit(node: str, path: list[str]) -> None:
        """Recursively traverse the graph and detect cycles via DFS."""
        if node in on_stack:
            idx = path.index(node)
            cycle = frozenset(path[idx:])
            if cycle not in reported:
                reported.add(cycle)
                report.errors.append(
                    f"{min(cycle)}: cyclic covers reference ({' -> '.join([*path[idx:], node])})"
                )
            return
        if node in visited:
            return
        visited.add(node)
        on_stack.add(node)
        path.append(node)
        for neighbor in edges.get(node, []):
            visit(neighbor, path)
        path.pop()
        on_stack.discard(node)

    for start in edges:
        if start not in visited:
            visit(start, [])


def _dev_downgrade(
    devs: list[Item],
    rule: str,
    *,
    feature: str | None = None,
    item_id: str | None = None,
    file: str | None = None,
) -> bool:
    """Decide whether an open DEV record downgrades an ERROR to WARNING (§8.6).

    A DEV matches when all of: `status: open`, its `rule` (comma-separated rule-number
    tokens, per §8.6's multi-rule extension — e.g. `rule: 4.6, 6.8, 10.5`) contains `rule`
    as one of those tokens by exact match, and its `scope` (comma-separated tokens) matches
    the violation — a token equals `feature`, equals `item_id`, or is a path prefix of `file`
    (`file.startswith(token)`). Both `rule` and `scope` tokens are compared exactly, never as
    substrings (`F-001` must not match `F-0012`; rule `6.8` must not match `6.81`).

    When `feature`, `item_id`, and `file` are all None (used for project-wide findings with
    no single owning item, e.g. overall coverage status or "coverage contexts unavailable"),
    any open DEV with a matching `rule` applies regardless of its `scope` — there is no
    specific candidate to check the scope against.

    `closed` DEVs and DEVs with invalid `status` values never downgrade, even if they match
    on rule and scope. Only DEVs with `status: open` may downgrade ERRORs to WARNINGs (§8.6).

    Used for rules: 4.6 (unapproved design / contexts unavailable), 6.4 (verifies test not
    PASS), 6.8 (RTM not-verified), 7.1 (gate FAIL/ERROR), 7.3 (coverage).

    Args:
        devs: all DEV items (not pre-filtered by status).
        rule: the violated rule number, matched exactly against `DEV.rule`.
        feature: the feature ID the violation belongs to, if any.
        item_id: the item/REQ ID the violation belongs to, if any.
        file: the repo-relative file path the violation belongs to, if any.

    Returns:
        True if a matching open DEV was found.
    """
    global_check = feature is None and item_id is None and file is None
    for dev in devs:
        if dev.kind != "DEV" or dev.meta.get("status") != "open":
            continue
        rule_tokens = [t.strip() for t in dev.meta.get("rule", "").split(",") if t.strip()]
        if rule not in rule_tokens:
            continue
        if global_check:
            return True
        tokens = [t.strip() for t in dev.meta.get("scope", "").split(",") if t.strip()]
        if feature is not None and feature in tokens:
            return True
        if item_id is not None and item_id in tokens:
            return True
        if file is not None and any(file.startswith(token) for token in tokens):
            return True
    return False


def _as_dicts(value: object) -> list[dict[str, Any]]:
    """Coerce a manifest field expected to be a list of dicts, tolerating malformed input."""
    return value if isinstance(value, list) else []


def _retired_reference_message(where: str, ident: str, retired: dict[str, LedgerRow]) -> str:
    """Format the standard "<where>: references retired ID <ID>" ERROR (spec §9, item 3).

    Appends " (superseded by <X>)" when the retired row records a `superseded_by` ID.
    """
    message = f"{where}: references retired ID {ident}"
    superseded_by = retired[ident].superseded_by
    if superseded_by:
        message += f" (superseded by {superseded_by})"
    return message


def _check_retired_ledger(
    root: Path, report: Report, ledger_rows: list[LedgerRow], by_id: dict[str, Item]
) -> tuple[set[str], dict[str, LedgerRow]]:
    """Validate ledger-level retirement invariants (spec §9, items 2 and 4).

    Checks: (2a) a retired ID must not appear on more than one ledger row; (2b) a retired ID
    must not still be declared as a document item heading, or (for a retired `F-nnn`) have a
    matching `docs/features/<F-nnn>_*` directory; (4) `superseded_by`, when set, must name an
    ID present in the ledger that is not itself retired. Non-retired duplicate ledger IDs are
    still reported, with the generic "duplicate ID" message.

    Returns:
        `(retired_ids, retired_by_id)`: the set of retired IDs and a map from a retired ID to
        its (last-seen) ledger row, for reuse by the reference checks that follow.
    """
    retired_by_id = {row.id: row for row in ledger_rows if row.status == "retired"}
    retired_ids = set(retired_by_id)

    rows_by_id: dict[str, list[LedgerRow]] = {}
    for row in ledger_rows:
        rows_by_id.setdefault(row.id, []).append(row)
    for ident, rows in sorted(rows_by_id.items()):
        if len(rows) <= 1:
            continue
        if ident in retired_ids:
            report.errors.append(f"docs/ids.ledger: retired ID {ident} reused")
        else:
            report.errors.append(f"docs/ids.ledger: duplicate ID {ident}")

    for ident in sorted(retired_ids):
        if ident in by_id:
            report.errors.append(f"docs/ids.ledger: retired ID {ident} reused")
        if ident.startswith("F-") and list((root / "docs/features").glob(f"{ident}_*")):
            report.errors.append(f"docs/ids.ledger: retired ID {ident} reused")

    ledger_id_set = set(rows_by_id)
    for row in ledger_rows:
        if not row.superseded_by:
            continue
        if row.superseded_by not in ledger_id_set:
            report.errors.append(
                f"docs/ids.ledger:{row.line}: superseded_by {row.superseded_by} is not "
                "present in the ledger"
            )
        elif row.superseded_by in retired_ids:
            report.errors.append(
                f"docs/ids.ledger:{row.line}: superseded_by {row.superseded_by} is itself retired"
            )
    return retired_ids, retired_by_id


def _check_committed_rtm_retired_refs(
    root: Path, report: Report, retired_ids: set[str], retired_by_id: dict[str, LedgerRow]
) -> None:
    """Flag references to retired IDs in the committed `docs/trace/rtm.csv` (spec §9, item 3).

    Reads the file as checked in (not a freshly regenerated RTM): both `req_id` and any ID
    listed in `design_ids` are checked.

    Side Effects:
        Reads docs/trace/rtm.csv, if present.
    """
    path = root / "docs/trace/rtm.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            req_id = row.get("req_id", "")
            where = f"{path.relative_to(root)} (row {req_id})"
            if req_id in retired_ids:
                report.errors.append(_retired_reference_message(where, req_id, retired_by_id))
            design_ids = [x.strip() for x in (row.get("design_ids") or "").split(",") if x.strip()]
            for ident in design_ids:
                if ident in retired_ids:
                    report.errors.append(_retired_reference_message(where, ident, retired_by_id))


def _tracked_src_files(root: Path) -> set[str]:
    """List git-tracked Python files under `src/`, as repo-relative POSIX paths.

    Only `.py` files are implementation files that coverage.py can attribute to tests;
    data files such as JSON schemas are excluded.

    Side Effects:
        Invokes `git ls-files src` (read-only). Returns an empty set if git is unavailable
        or the command fails, so callers degrade to "nothing to warn about" rather than
        crashing.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "src"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return set()
    if proc.returncode:
        return set()
    return {line for line in proc.stdout.splitlines() if line.strip().endswith(".py")}


def _check_unapproved_design(
    root: Path,
    report: Report,
    *,
    manifest: dict,
    by_id: dict[str, Item],
    dev_items: list[Item],
    item_feature: dict[str, str],
) -> None:
    """§13-14 / Rule 4.6: implementation reached only by unapproved or stale design.

    Walks impl file -> verifies tests reaching it (via coverage contexts) -> referenced
    DD/MD item -> that item's owning document. If the document is not `status: approved` or
    its hash no longer matches `approved_hash`, that is an ERROR (subject to DEV downgrade).
    A tracked `src/` file reached by no verifies test at all is a WARNING (not downgradable —
    the spec lists it as a plain WARNING, not an ERROR needing an exception record).

    When coverage contexts are unavailable (`coverage_contexts.load` returns None — e.g. an
    older manifest without `coverage.json_path`, or the JSON is missing/unreadable), this
    check cannot be evaluated at all; that is itself an ERROR ("NOT_EVALUATED"), since silently
    skipping the check would let unapproved implementations pass unnoticed.

    Side Effects:
        Reads the coverage JSON (via `coverage_contexts.load`) and invokes `git ls-files`
        (via `_tracked_src_files`).
    """
    contexts = load_contexts(root, manifest)
    if contexts is None:
        message = "unapproved-design check NOT_EVALUATED: coverage contexts unavailable"
        if _dev_downgrade(dev_items, _DEV_RULE_UNAPPROVED_DESIGN):
            report.warnings.append(message + "; covered by an open DEV")
        else:
            report.errors.append(message)
        return

    markers = scan_tests(root)
    verifies_by_nodeid = {
        m.nodeid: m.referenced_id for m in markers if m.marker == "verifies" and m.referenced_id
    }
    checked_docs: dict[str, Document] = {}
    for impl_file, nodeids in sorted(contexts.items()):
        verifies_here = {verifies_by_nodeid[n] for n in nodeids if n in verifies_by_nodeid}
        design_ids = {i for i in verifies_here if by_id.get(i) and by_id[i].kind in {"DD", "MD"}}
        for design_id in sorted(design_ids):
            item = by_id[design_id]
            doc_key = str(item.path)
            if doc_key not in checked_docs:
                try:
                    checked_docs[doc_key] = parse_document(item.path)
                except (OSError, ValueError, SaalcoError):
                    continue
            doc = checked_docs[doc_key]
            approved = doc.header.get("status") == "approved" and doc.header.get(
                "approved_hash"
            ) == content_hash(doc)
            if not approved:
                message = f"{impl_file}: reached by verifies test for unapproved/stale {design_id}"
                if _dev_downgrade(
                    dev_items,
                    _DEV_RULE_UNAPPROVED_DESIGN,
                    feature=item_feature.get(design_id),
                    item_id=design_id,
                    file=impl_file,
                ):
                    report.warnings.append(message + "; covered by an open DEV")
                else:
                    report.errors.append(message)

    reached = set(contexts)
    for src_file in sorted(_tracked_src_files(root)):
        if src_file not in reached or not (
            {verifies_by_nodeid.get(n) for n in contexts.get(src_file, set())} - {None}
        ):
            report.warnings.append(f"{src_file}: reached by no verifies test")


def run(root: Path, verification: bool = False) -> Report:
    """Run `saalco check` (static) or `saalco check --verification` (static + verification).

    Args:
        root: project root.
        verification: when True, also run the §13 verification-only checks, which require
            a current evidence manifest (`saalco.evidence.current_manifest`).

    Returns:
        A `Report`; `report.ok` is False if any ERROR was recorded.

    Side Effects:
        Read-only: parses documents/tests/ledger, reads the current evidence manifest and
        (when verification is True) the coverage JSON it references, and invokes
        `git ls-files` and `trace.generate(root, write=False)`. Never writes files.
    """
    report = Report()
    cfg = config(root)
    docs = _documents(root, report)
    by_id: dict[str, Item] = {}
    item_list: list[Item] = []
    item_feature: dict[str, str] = {}
    for doc in docs:
        for item in items(doc):
            if item.id in by_id:
                report.errors.append(f"{item.path.relative_to(root)}: duplicate ID {item.id}")
            by_id[item.id] = item
            item_list.append(item)
            item_feature[item.id] = doc.header.get("feature", "")
    ledger_rows = read_ledger(root)
    ledger_ids = [row.id for row in ledger_rows]
    retired_ids, retired_by_id = _check_retired_ledger(root, report, ledger_rows, by_id)
    documented = set(by_id)
    documented.update(
        doc.header.get("feature", "") for doc in docs if doc.path.name == "00-meta.md"
    )
    for ident in documented - set(ledger_ids):
        report.errors.append(f"{ident}: documented ID is missing from docs/ids.ledger")
    for ident in set(ledger_ids) - documented - retired_ids:
        # §9: a retired ID is excluded from this mismatch check (item 1) — it is expected to
        # remain in the ledger without a live document item.
        report.errors.append(f"docs/ids.ledger: {ident} has no corresponding document item")
    _check_committed_rtm_retired_refs(root, report, retired_ids, retired_by_id)

    for meta in (d for d in docs if d.path.name == "00-meta.md"):
        tier = meta.header.get("tier")
        if tier not in TIER_FILES:
            report.errors.append(f"{meta.path.relative_to(root)}: tier must be S, M, or L")
            continue
        present = {p.name for p in meta.path.parent.glob("*.md")}
        for missing in set(TIER_FILES[tier]) - present:
            report.errors.append(
                f"{meta.path.parent.relative_to(root)}/{missing}: required for Tier {tier}"
            )

    edges: dict[str, list[str]] = {}
    for item in item_list:
        if item.kind == "DEV":
            scope = item.meta.get("scope")
            if not scope:
                report.errors.append(f"{item.path.relative_to(root)} {item.id}: scope is required")
            else:
                where = f"{item.path.relative_to(root)} {item.id}"
                for token in (t.strip() for t in scope.split(",")):
                    if token in retired_ids:
                        report.errors.append(
                            _retired_reference_message(where, token, retired_by_id)
                        )
            # Validate DEV status and closed records (§8.6).
            status = item.meta.get("status")
            where = f"{item.path.relative_to(root)} {item.id}"
            if status is None:
                report.errors.append(
                    f"{where}: invalid DEV status '<missing>'; set it to `open` or `closed`."
                )
            elif status not in {"open", "closed"}:
                report.errors.append(
                    f"{where}: invalid DEV status '{status}'; set it to `open` or `closed`."
                )
            elif status == "closed":
                closed_at = item.meta.get("closed_at")
                closed_condition = item.meta.get("closed_condition")
                if not closed_at or not closed_at.strip():
                    report.errors.append(
                        f"{where}: closed DEV is missing `closed_at` or its value is empty; a human must fill this field."
                    )
                if not closed_condition or not closed_condition.strip():
                    report.errors.append(
                        f"{where}: closed DEV is missing `closed_condition` or its value is empty; a human must fill this field."
                    )
            continue
        raw = item.meta.get("covers")
        if raw is None or (not raw and item.kind != "REQ"):
            report.errors.append(f"{item.path.relative_to(root)} {item.id}: covers is empty")
            continue
        refs = [] if raw == "-" else [x.strip() for x in raw.split(",") if x.strip()]
        if item.kind == "REQ" and raw != "-":
            report.errors.append(f"{item.path.relative_to(root)} {item.id}: REQ covers must be '-'")
        edges[item.id] = refs
        for ref in refs:
            if ref in retired_ids:
                report.errors.append(
                    _retired_reference_message(
                        f"{item.path.relative_to(root)} {item.id}", ref, retired_by_id
                    )
                )
            elif ref not in by_id:
                report.errors.append(
                    f"{item.path.relative_to(root)} {item.id}: unknown covers ID {ref}"
                )
            elif by_id[ref].kind not in ALLOWED.get(item.kind, set()):
                report.errors.append(f"{item.path.relative_to(root)} {item.id}: cannot cover {ref}")
        verify = item.meta.get("verify", "test")
        if verify not in {"test", "review", "static"}:
            report.errors.append(
                f"{item.path.relative_to(root)} {item.id}: invalid verify {verify!r}"
            )
        if verify == "static":
            gate = item.meta.get("static")
            gates = {k.split(".")[-1] for k in cfg if k.startswith("gate.")}
            if not gate or gate not in gates:
                report.errors.append(
                    f"{item.path.relative_to(root)} {item.id}: unknown static gate"
                )
    _find_cycles(edges, report)

    markers = scan_tests(root)
    verified_ids = {m.referenced_id for m in markers if m.marker == "verifies" and m.referenced_id}
    spec_ids = {i.id for i in item_list if i.kind in {"UT", "IT", "ST"}}
    for marker in markers:
        if marker.referenced_id and marker.referenced_id in retired_ids:
            report.errors.append(
                _retired_reference_message(marker.nodeid, marker.referenced_id, retired_by_id)
            )
        elif marker.referenced_id and marker.referenced_id not in by_id:
            report.errors.append(f"{marker.nodeid}: verifies unknown ID {marker.referenced_id}")
        if marker.spec and marker.spec in retired_ids:
            report.errors.append(
                _retired_reference_message(marker.nodeid, marker.spec, retired_by_id)
            )
        elif marker.spec and marker.spec not in spec_ids:
            report.errors.append(
                f"{marker.nodeid}: verifies spec references unknown ID {marker.spec}"
            )
        expected = _CATEGORY_EXPECTED_KIND.get(marker.category, set())
        if marker.referenced_id in by_id and by_id[marker.referenced_id].kind not in expected:
            report.warnings.append(
                f"{marker.nodeid}: {marker.category} test references {marker.referenced_id}"
            )
    for item in item_list:
        if (
            item.meta.get("verify", "test") == "test"
            and item.kind in {"REQ", "AD", "DD", "MD"}
            and item.id not in verified_ids
        ):
            report.errors.append(f"{item.id}: no Specification-derived verifies test")
        if (
            item.kind in {"DD", "MD"}
            and item.meta.get("verify", "test") == "test"
            and not any(x.kind == "UT" and item.id in edges.get(x.id, []) for x in item_list)
        ):
            report.errors.append(f"{item.id}: no UT specification covers this item")
    referenced = {ref for refs in edges.values() for ref in refs}
    for item in item_list:
        if item.kind in {"REQ", "AD", "DD", "MD"} and item.id not in referenced:
            report.warnings.append(f"{item.id}: not covered by a downstream item")

    if verification:
        dev_items = [i for i in item_list if i.kind == "DEV"]
        manifest = current_manifest(root)
        if manifest is None:
            report.errors.append("no current Evidence; run `saalco evidence` and commit it")
        else:
            for test in _as_dicts(manifest.get("tests")):
                if test.get("marker") == "verifies" and test.get("result") != "PASS":
                    message = f"{test.get('nodeid')}: verifies test did not PASS"
                    referenced_id = test.get("referenced_id")
                    referenced_id = referenced_id if isinstance(referenced_id, str) else None
                    if _dev_downgrade(
                        dev_items,
                        _DEV_RULE_VERIFIES_NOT_PASS,
                        feature=item_feature.get(referenced_id) if referenced_id else None,
                        item_id=referenced_id,
                    ):
                        report.warnings.append(message + "; covered by an open DEV")
                    else:
                        report.errors.append(message)
            for gate_entry in _as_dicts(manifest.get("gates")):
                if gate_entry.get("result") in {"FAIL", "ERROR"}:
                    message = f"gate {gate_entry.get('name')}: result is {gate_entry.get('result')}"
                    if _dev_downgrade(dev_items, _DEV_RULE_GATE):
                        report.warnings.append(message + "; covered by an open DEV")
                    else:
                        report.errors.append(message)
            cov = manifest.get("coverage")
            cov = cov if isinstance(cov, dict) else {}
            if cov.get("status") not in {"PASS"}:
                message = f"coverage is {cov.get('status', 'NOT_EVALUATED')}"
                if _dev_downgrade(dev_items, _DEV_RULE_COVERAGE):
                    report.warnings.append(message + "; covered by an open DEV")
                else:
                    report.errors.append(message)

            _check_unapproved_design(
                root,
                report,
                manifest=manifest,
                by_id=by_id,
                dev_items=dev_items,
                item_feature=item_feature,
            )

            for row in generate_trace(root, write=False):
                if row["verify_status"] != "verified":
                    message = f"{row['req_id']}: RTM status is {row['verify_status']}, not verified"
                    if _dev_downgrade(
                        dev_items,
                        _DEV_RULE_RTM,
                        feature=row["feature"] or None,
                        item_id=row["req_id"],
                    ):
                        report.warnings.append(message + "; covered by an open DEV")
                    else:
                        report.errors.append(message)
        for key in ("gate.04.secret_scan", "gate.05.dependency_audit"):
            if not cfg.get(key):
                report.warnings.append(f"{key}: NOT_CONFIGURED")
    return report
