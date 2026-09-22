from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .documents import Document, content_hash, items, parse_document
from .errors import SaalcoError
from .ids import read_ledger
from .markers import scan_tests
from .project import config
from .templates import TIER_FILES

ALLOWED = {
    "REQ": set(),
    "AD": {"REQ"},
    "DD": {"AD", "REQ"},
    "MD": {"DD", "AD", "REQ"},
    "UT": {"DD", "MD"},
    "IT": {"AD"},
    "ST": {"REQ"},
}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def output(self, as_json: bool = False) -> str:
        if as_json:
            return json.dumps(
                {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}, indent=2
            )
        lines = [*(f"ERROR {x}" for x in self.errors), *(f"WARNING {x}" for x in self.warnings)]
        lines.append(f"{len(self.errors)} errors, {len(self.warnings)} warnings")
        return "\n".join(lines)


def _documents(root: Path, report: Report) -> list[Document]:
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
            if doc.header.get("status") not in {"draft", "approved", "superseded"}:
                report.errors.append(f"{path.relative_to(root)}: invalid status")
            if doc.header.get("status") == "approved":
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
        except (OSError, ValueError, SaalcoError) as exc:
            report.errors.append(str(exc).removeprefix("ERROR "))
    return docs


def run(root: Path, verification: bool = False) -> Report:
    report = Report()
    cfg = config(root)
    docs = _documents(root, report)
    by_id = {}
    item_list = []
    for doc in docs:
        for item in items(doc):
            if item.id in by_id:
                report.errors.append(f"{item.path.relative_to(root)}: duplicate ID {item.id}")
            by_id[item.id] = item
            item_list.append(item)
    ledger_rows = read_ledger(root)
    ledger_ids = [row[0] for row in ledger_rows]
    if len(ledger_ids) != len(set(ledger_ids)):
        report.errors.append("docs/ids.ledger: duplicate IDs")
    documented = set(by_id)
    documented.update(
        doc.header.get("feature", "") for doc in docs if doc.path.name == "00-meta.md"
    )
    for ident in documented - set(ledger_ids):
        report.errors.append(f"{ident}: documented ID is missing from docs/ids.ledger")
    for ident in set(ledger_ids) - documented:
        report.errors.append(f"docs/ids.ledger: {ident} has no corresponding document item")

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
            if not item.meta.get("scope"):
                report.errors.append(f"{item.path.relative_to(root)} {item.id}: scope is required")
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
            if ref not in by_id:
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
    for start in edges:
        stack: list[tuple[str, list[str]]] = [(start, [])]
        while stack:
            node, path = stack.pop()
            if node in path:
                report.errors.append(f"{start}: cyclic covers reference")
                break
            stack.extend((n, path + [node]) for n in edges.get(node, []))

    markers = scan_tests(root)
    verified_ids = {m.referenced_id for m in markers if m.marker == "verifies" and m.referenced_id}
    for marker in markers:
        if marker.referenced_id and marker.referenced_id not in by_id:
            report.errors.append(f"{marker.nodeid}: verifies unknown ID {marker.referenced_id}")
        expected = {"unit": {"DD", "MD"}, "integration": {"AD"}, "e2e": {"REQ"}}.get(
            marker.category, set()
        )
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
        from .evidence import current_manifest

        open_devs = [
            item
            for item in item_list
            if item.kind == "DEV" and item.meta.get("status") == "open" and item.meta.get("scope")
        ]
        manifest = current_manifest(root)
        if manifest is None:
            report.errors.append("no current Evidence; run `saalco evidence` and commit it")
        else:
            for test in manifest.get("tests", []):
                if test.get("marker") == "verifies" and test.get("result") != "PASS":
                    report.errors.append(f"{test.get('nodeid')}: verifies test did not PASS")
            cov = manifest.get("coverage", {})
            if cov.get("status") not in {"PASS"}:
                message = f"coverage is {cov.get('status', 'NOT_EVALUATED')}"
                if any(dev.meta.get("rule") in {"7.3", "10.5", "13.5"} for dev in open_devs):
                    report.warnings.append(message + "; covered by an open DEV")
                else:
                    report.errors.append(message)
            from .trace import generate

            for row in generate(root):
                if row["verify_status"] != "verified":
                    message = f"{row['req_id']}: RTM status is {row['verify_status']}, not verified"
                    if any(
                        row["req_id"] in dev.meta.get("scope", "")
                        or row["feature"] in dev.meta.get("scope", "")
                        for dev in open_devs
                    ):
                        report.warnings.append(message + "; covered by an open DEV")
                    else:
                        report.errors.append(message)
        for key in ("gate.04.secret_scan", "gate.05.dependency_audit"):
            if not cfg.get(key):
                report.warnings.append(f"{key}: NOT_CONFIGURED")
    return report
