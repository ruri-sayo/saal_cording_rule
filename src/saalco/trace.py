from __future__ import annotations

import csv
import io
from pathlib import Path

from .documents import content_hash, items, parse_document
from .evidence import current_manifest
from .markers import scan_tests
from .project import config


def generate(root: Path) -> list[dict[str, str]]:
    all_items = []
    for path in sorted((root / "docs/features").glob("F-*/*.md")):
        all_items.extend(items(parse_document(path)))
    tests = scan_tests(root)
    manifest = current_manifest(root)
    language = config(root).get("language")
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
            results = {x.get("nodeid"): x.get("result") for x in manifest.get("tests", [])}
            gates = {x.get("name"): x.get("result") for x in manifest.get("gates", [])}

            def satisfied(
                item_id: str,
                related=related_tests,
                gate_results=gates,
                test_results=results,
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
                    and x.meta.get("commit") == manifest.get("target_commit")
                    for x in all_items
                )

            required = [x for x in ancestors if x.startswith(("REQ-", "AD-", "DD-", "MD-"))]
            if required and all(satisfied(item_id) for item_id in required):
                status = "verified"
        rows.append(
            {
                "req_id": req.id,
                "requirement": req.title,
                "feature": parse_document(req.path).header.get("feature", ""),
                "design_ids": ",".join(
                    sorted(x for x in ancestors if x.startswith(("AD-", "DD-", "MD-")))
                ),
                "impl_files": "",
                "unit_tests": ",".join(t.nodeid for t in related_tests if t.category == "unit"),
                "integration_tests": ",".join(
                    t.nodeid for t in related_tests if t.category == "integration"
                ),
                "e2e_tests": ",".join(t.nodeid for t in related_tests if t.category == "e2e"),
                "verify_status": status,
                "evidence_commit": manifest.get("target_commit", "") if manifest else "",
            }
        )
    out = root / "docs/trace"
    out.mkdir(parents=True, exist_ok=True)
    columns = [
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
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (out / "rtm.csv").write_text(buffer.getvalue(), encoding="utf-8")
    md = [
        "# Requirements Traceability Matrix",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    md.extend("| " + " | ".join(row[c].replace("|", "\\|") for c in columns) + " |" for row in rows)
    (out / "rtm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows
