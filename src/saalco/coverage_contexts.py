"""Load coverage.py test-context data produced during `saalco evidence`.

Responsibilities:
    - Locate the coverage JSON referenced by an evidence manifest (`coverage.json_path`,
      per contract 1/5 in the shared brief) and parse its per-line test contexts.
    - Reduce coverage.py's `files[path]["contexts"]` (line -> [context, ...]) into a
      impl-file -> {test nodeid, ...} mapping, in the nodeid format used across the
      manifest/markers/trace contracts (contract 1), by stripping the `|run` /
      `|setup` / `|teardown` suffix coverage.py appends and any `[param]` parametrize
      suffix.
    - Normalize impl file paths to repo-relative POSIX paths under `src/`.

Non-responsibilities:
    - Does not run coverage.py or pytest; `saalco.evidence.create` produces the JSON this
      module reads.
    - Does not interpret coverage percentages/totals; see `saalco.evidence._coverage_result`.

Used by checks.py (§13-14 unapproved-design check) and trace.py (`impl_files` column).
"""

from __future__ import annotations

import json
from pathlib import Path

#: Suffixes coverage.py appends to a dynamic context; stripped to recover the test nodeid.
_CONTEXT_SUFFIXES = ("|run", "|setup", "|teardown")


def _normalize_nodeid(context: str) -> str | None:
    """Strip coverage.py's `|run`/`|setup`/`|teardown` and any `[param]` suffix.

    Args:
        context: a raw coverage.py dynamic context string, e.g.
            `tests/unit/test_x.py::test_name[param]|run`.

    Returns:
        The bare nodeid (`tests/unit/test_x.py::test_name`), or None for the empty
        "no context" string coverage.py records for lines outside any test.
    """
    if not context:
        return None
    for suffix in _CONTEXT_SUFFIXES:
        if context.endswith(suffix):
            context = context[: -len(suffix)]
            break
    bracket = context.find("[")
    if bracket != -1 and context.endswith("]"):
        context = context[:bracket]
    return context or None


def load(root: Path, manifest: dict) -> dict[str, set[str]] | None:
    """Map repo-relative `src/` files to the set of test nodeids that covered them.

    Args:
        root: project root.
        manifest: an evidence manifest dict (contract 1); only `coverage.json_path` is read.

    Returns:
        `{impl_file: {nodeid, ...}}` for every file under `files` in the coverage JSON that
        has at least one test context, keyed by repo-relative POSIX path. `None` when
        `manifest["coverage"]["json_path"]` is absent (older manifests predating this
        field), null, the file does not exist on disk, or the file fails to parse as JSON —
        callers must treat `None` as "coverage contexts unavailable", not "no files covered".

    Side Effects:
        Reads the coverage JSON file at `root / manifest["coverage"]["json_path"]`; performs
        no writes.
    """
    json_path = manifest.get("coverage", {}).get("json_path")
    if not json_path:
        return None
    path = root / json_path
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    result: dict[str, set[str]] = {}
    for raw_name, file_data in files.items():
        contexts = file_data.get("contexts") if isinstance(file_data, dict) else None
        if not isinstance(contexts, dict):
            continue
        nodeids: set[str] = set()
        for ctx_list in contexts.values():
            for ctx in ctx_list:
                nodeid = _normalize_nodeid(ctx)
                if nodeid:
                    nodeids.add(nodeid)
        if not nodeids:
            continue
        candidate = Path(raw_name)
        rel = candidate if not candidate.is_absolute() else _relative_to_root(candidate, root)
        if rel is None:
            continue
        result.setdefault(rel.as_posix(), set()).update(nodeids)
    return result


def _relative_to_root(path: Path, root: Path) -> Path | None:
    """Best-effort resolve an absolute coverage.py file path to a repo-relative path."""
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
