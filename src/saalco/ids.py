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
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .errors import SaalcoError

WIDTH = {"F": 3, "REQ": 4, "AD": 4, "DD": 4, "MD": 4, "UT": 4, "IT": 4, "ST": 4, "DEV": 4}
ID_PATTERN = re.compile(r"^[A-Z]+-\d+$")


def read_ledger(root: Path) -> list[tuple[str, str, str, str]]:
    """Read the ID ledger from docs/ids.ledger.

    Args:
        root: Project root directory.

    Returns:
        List of (id, feature, timestamp, title) tuples; empty list if ledger doesn't exist.

    Raises:
        SaalcoError: If ledger format is invalid (field count, ID format).

    Side Effects:
        Reads docs/ids.ledger file.
    """
    result: list[tuple[str, str, str, str]] = []
    path = root / "docs" / "ids.ledger"
    if not path.exists():
        return result
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t", 3)
        if len(parts) != 4:
            raise SaalcoError(
                f"ERROR {path}:{number}: ledger row must have four tab-separated fields."
            )
        ident = parts[0]
        if not ID_PATTERN.match(ident):
            raise SaalcoError(
                f"ERROR {path}:{number}: invalid ID format '{ident}'; expected [A-Z]+-\\d+."
            )
        result.append((ident, parts[1], parts[2], parts[3]))
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

    Reads the current maximum ID of the given kind, increments it, and appends to ledger.

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
    with lock(root):
        rows = read_ledger(root)
        values = [int(row[0].split("-")[1]) for row in rows if row[0].split("-")[0] == kind]
        ident = f"{kind}-{max(values, default=0) + 1:0{WIDTH[kind]}d}"
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with (root / "docs" / "ids.ledger").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{ident}\t{feature}\t{stamp}\t{title}\n")
    return ident
