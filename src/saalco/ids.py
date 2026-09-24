"""ID allocation and ledger management.

Responsibilities:
- Read and parse docs/ids.ledger.
- Allocate new IDs in sequence (F-001, REQ-0001, etc.).
- Enforce exclusive allocation via file-based lock.

Non-responsibilities:
- Document structure validation (done by checks module).
- Ledger backup or archival.

External dependencies:
- Filesystem: reads/writes .saal/ids.lock and docs/ids.ledger.
"""

from __future__ import annotations

import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .errors import SaalcoError

WIDTH = {"F": 3, "REQ": 4, "AD": 4, "DD": 4, "MD": 4, "UT": 4, "IT": 4, "ST": 4, "DEV": 4}
ID_PATTERN = re.compile(r"^[A-Z]+-\d+$")

#: Ledger row statuses recognized by spec §9 (revised).
_STATUSES = {"active", "retired"}


@dataclass
class LedgerRow:
    """One parsed row of `docs/ids.ledger` (spec §9).

    Attributes:
        id: Allocated ID (e.g. 'F-001', 'REQ-0042').
        feature: Feature ID the row belongs to ('-' for feature rows themselves).
        allocated_at: ISO timestamp recorded at allocation time.
        title: Human-readable title (never contains a tab; `allocate` sanitizes it).
        status: 'active' or 'retired'. A legacy 4-field row (or an empty 5th field) is
            'active'.
        reason: Optional retirement reason; '' when not set.
        superseded_by: Optional ID that supersedes this one; '' when not set.
        line: 1-based line number in the ledger file, for error messages.
    """

    id: str
    feature: str
    allocated_at: str
    title: str
    status: str = "active"
    reason: str = ""
    superseded_by: str = ""
    line: int = 0


def read_ledger(root: Path) -> list[LedgerRow]:
    r"""Read the ID ledger from docs/ids.ledger.

    Row format (tab-separated, backward compatible): `<ID>\t<feature>\t<allocated_at>\t
    <title>[\t<status>[\t<reason>[\t<superseded_by>]]]`. A legacy 4-field row, or one whose
    5th field is empty, is treated as `status: active`.

    Args:
        root: Project root directory.

    Returns:
        List of `LedgerRow`; empty list if ledger doesn't exist.

    Raises:
        SaalcoError: If ledger format is invalid (field count, ID format, status value).

    Side Effects:
        Reads docs/ids.ledger file.
    """
    path = root / "docs" / "ids.ledger"
    if not path.exists():
        return []
    return _parse_ledger_text(path, path.read_text(encoding="utf-8"))


def _parse_ledger_text(path: Path, text: str) -> list[LedgerRow]:
    """Parse ledger row text into `LedgerRow` objects.

    Shared by `read_ledger` (reads the real ledger) and `retire` (re-parses a temp file to
    verify a rewrite before the atomic replace).

    Args:
        path: Path used only for error messages.
        text: Raw ledger file content.

    Returns:
        List of `LedgerRow`; empty list for empty text.

    Raises:
        SaalcoError: If ledger format is invalid (field count, ID format, status value).
    """
    result: list[LedgerRow] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if not 4 <= len(parts) <= 7:
            raise SaalcoError(
                f"ERROR {path}:{number}: ledger row must have at least four (and at most "
                f"seven) tab-separated fields; got {len(parts)}."
            )
        ident = parts[0]
        if not ID_PATTERN.match(ident):
            raise SaalcoError(
                f"ERROR {path}:{number}: invalid ID format '{ident}'; expected [A-Z]+-\\d+."
            )
        status = parts[4] if len(parts) > 4 and parts[4] else "active"
        if status not in _STATUSES:
            raise SaalcoError(
                f"ERROR {path}:{number}: invalid ledger status {status!r}; expected "
                f"'active' or 'retired'."
            )
        result.append(
            LedgerRow(
                id=ident,
                feature=parts[1],
                allocated_at=parts[2],
                title=parts[3],
                status=status,
                reason=parts[5] if len(parts) > 5 else "",
                superseded_by=parts[6] if len(parts) > 6 else "",
                line=number,
            )
        )
    return result


@contextmanager
def lock(root: Path):
    """Exclusive lock for ID allocation.

    Uses O_EXCL to prevent concurrent ID allocation on the same machine.

    Args:
        root: Project root directory.

    Yields:
        None.

    Raises:
        SaalcoError: If lock cannot be acquired (another allocation in progress).

    Side Effects:
        Creates and removes .saal/ids.lock file.
    """
    lock_path = root / ".saal" / "ids.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SaalcoError(f"ERROR {lock_path}: another ID allocation is in progress.") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def allocate(root: Path, kind: str, feature: str, title: str) -> str:
    """Allocate a new unique ID.

    Reads the current maximum ID of the given kind (over ALL rows, including retired ones,
    so a retired number is never reused), increments it, and appends an active row to the
    ledger. Tabs in `title` are replaced with spaces first, since the ledger is tab-separated.

    Args:
        root: Project root directory.
        kind: ID kind (F, REQ, AD, DD, MD, UT, IT, ST, DEV).
        feature: Feature ID this item belongs to.
        title: Human-readable title.

    Returns:
        Newly allocated ID (e.g., 'F-001', 'REQ-0042').

    Raises:
        SaalcoError: If kind is unknown or ledger format is invalid.

    Side Effects:
        Acquires exclusive lock, reads docs/ids.ledger, appends new row, releases lock.
    """
    kind = kind.upper()
    if kind not in WIDTH:
        raise SaalcoError(f"ERROR unknown ID kind {kind!r}.")
    title = title.replace("\t", " ")
    with lock(root):
        rows = read_ledger(root)
        values = [int(row.id.split("-")[1]) for row in rows if row.id.split("-")[0] == kind]
        ident = f"{kind}-{max(values, default=0) + 1:0{WIDTH[kind]}d}"
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with (root / "docs" / "ids.ledger").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{ident}\t{feature}\t{stamp}\t{title}\n")
    return ident


def retire(
    root: Path, ident: str, reason: str | None = None, superseded_by: str | None = None
) -> LedgerRow:
    r"""Retire a ledger row so its ID is never reused (spec §9 revised; DD-0003).

    Rewrites only the `status`/`reason`/`superseded_by` columns of the target row, in place;
    every other row and every other column of the target row is left byte-for-byte identical.
    Never touches `docs/features/**` documents — removing the item heading and any references
    is left to the caller (see the guidance `saalco.commands.retire` returns).

    Args:
        root: Project root directory.
        ident: ID to retire (e.g., 'REQ-0013').
        reason: Optional free-text retirement reason. Must not contain a tab or newline
            (the ledger is tab-separated, one row per line).
        superseded_by: Optional replacement ID. If given, it must already exist in the
            ledger, in valid ID format, and not itself be retired.

    Returns:
        The updated `LedgerRow` for `ident`.

    Raises:
        SaalcoError: If `ident` is unknown or already retired; if `superseded_by` is
            malformed, unknown, or retired; or if `reason` contains a tab or newline.
            All are usage errors (exit code 2).

    Side Effects:
        Acquires the exclusive `.saal/ids.lock` (same lock as `allocate`). Reads and
        atomically rewrites `docs/ids.ledger` (temp file, re-parse verification, then
        `os.replace`). Never deletes a row and never writes to any other file.
    """
    reason = reason or ""
    if "\t" in reason or "\n" in reason:
        raise SaalcoError(
            f"ERROR retire {ident}: --reason must not contain a tab or newline (the ledger "
            "is tab-separated). Remove it from the reason text and retry."
        )
    if superseded_by is not None and not ID_PATTERN.match(superseded_by):
        raise SaalcoError(
            f"ERROR retire {ident}: --superseded-by '{superseded_by}' is not a valid ID "
            "(expected e.g. REQ-0001). Pass a valid ID or omit --superseded-by."
        )
    path = root / "docs" / "ids.ledger"
    with lock(root):
        rows = read_ledger(root)
        by_id = {row.id: row for row in rows}
        target = by_id.get(ident)
        if target is None:
            raise SaalcoError(
                f"ERROR retire {ident}: unknown ID; not found in docs/ids.ledger. Check the "
                "ID and retry, or allocate it first with `saalco new`."
            )
        if target.status == "retired":
            raise SaalcoError(
                f"ERROR retire {ident}: already retired. No action needed; if you meant a "
                "different ID, pass that ID instead."
            )
        if superseded_by is not None:
            replacement = by_id.get(superseded_by)
            if replacement is None:
                raise SaalcoError(
                    f"ERROR retire {ident}: --superseded-by {superseded_by} is not in "
                    "docs/ids.ledger. Allocate it first with `saalco new`, or pass an "
                    "existing active ID."
                )
            if replacement.status == "retired":
                raise SaalcoError(
                    f"ERROR retire {ident}: --superseded-by {superseded_by} is itself "
                    "retired. Pass a currently active ID."
                )
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        index = target.line - 1
        raw = lines[index]
        trailing_newline = "\n" if raw.endswith("\n") else ""
        parts = raw.rstrip("\n").split("\t")
        lines[index] = "\t".join(parts[:4] + ["retired", reason, superseded_by or ""]) + (
            trailing_newline or "\n"
        )
        new_text = "".join(lines)
        fd, name = tempfile.mkstemp(prefix=".ids.ledger.", dir=path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(new_text)
            verified = _parse_ledger_text(Path(name), new_text)
            if len(verified) != len(rows):
                raise SaalcoError(
                    f"ERROR retire {ident}: internal error; rewritten ledger row count "
                    "changed. Aborting without replacing docs/ids.ledger."
                )
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        updated = next(row for row in verified if row.id == ident)
    return updated
