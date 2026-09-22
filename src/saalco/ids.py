from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .errors import SaalcoError

WIDTH = {"F": 3, "REQ": 4, "AD": 4, "DD": 4, "MD": 4, "UT": 4, "IT": 4, "ST": 4, "DEV": 4}


def read_ledger(root: Path) -> list[tuple[str, str, str, str]]:
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
        result.append((parts[0], parts[1], parts[2], parts[3]))
    return result


@contextmanager
def lock(root: Path):
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
