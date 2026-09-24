"""Document parsing, serialization, and content hashing.

Responsibilities:
- Parse SAAL document format (YAML-like flat header + Markdown body).
- Serialize documents preserving structure.
- Compute SHA256 hashes for approval tracking.
- Atomically write documents (temp file + rename).
- Extract item definitions and metadata.

Non-responsibilities:
- Document validation (done by checks module).
- Item content analysis (only structural extraction).

External dependencies:
- Filesystem: reads/writes document files.
- tempfile: for atomic writes.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import SaalcoError

ITEM_RE = re.compile(r"^###\s+((?:REQ|AD|DD|MD|UT|IT|ST|DEV)-\d{4}):\s*(.+?)\s*$", re.MULTILINE)
META_RE = re.compile(r"^([a-z_]+):\s*(.*?)\s*$")


@dataclass
class Document:
    """In-memory representation of a SAAL document.

    Attributes:
        path: File path (not necessarily absolute).
        header: Parsed header as flat dict of strings.
        body: Markdown body text (post-header, including opening --).
    """

    path: Path
    header: dict[str, str]
    body: str


@dataclass
class Item:
    """Extracted item (REQ, DD, UT, etc.) from a document.

    Attributes:
        id: Item identifier (REQ-0001, DD-0042, etc.).
        kind: Item kind prefix (REQ, AD, DD, MD, UT, IT, ST, DEV).
        title: Item title from heading.
        path: Path of document containing this item.
        meta: Extracted metadata lines (covers:, verify:, etc.) as dict.
    """

    id: str
    kind: str
    title: str
    path: Path
    meta: dict[str, str]


def parse_document(path: Path) -> Document:
    """Parse a SAAL document from file.

    Document format: --- header lines --- body

    Args:
        path: Path to document file.

    Returns:
        Parsed Document with header dict and body string.

    Raises:
        SaalcoError: If file not found, missing delimiters, or invalid header format.

    Side Effects:
        Reads file from disk.
    """
    try:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except OSError as exc:
        raise SaalcoError(f"ERROR {path}: {exc}") from exc
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SaalcoError(f"ERROR {path}: missing opening '---' header delimiter.")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise SaalcoError(f"ERROR {path}: missing closing '---' header delimiter.")
    header: dict[str, str] = {}
    for lineno, line in enumerate(lines[1:end], 2):
        raw = line.rstrip("\n")
        if not raw or ":" not in raw:
            raise SaalcoError(f"ERROR {path}:{lineno}: header must be flat `key: value`.")
        key, value = raw.split(":", 1)
        if not key.strip() or key.strip() in header:
            raise SaalcoError(f"ERROR {path}:{lineno}: invalid or duplicate header key.")
        header[key.strip()] = value.strip()
    return Document(path, header, "".join(lines[end + 1 :]))


def serialize(doc: Document) -> str:
    """Serialize a document to text.

    Args:
        doc: Document to serialize.

    Returns:
        Text representation: --- header --- body.
    """
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in doc.header.items()) + "---\n" + doc.body


def atomic_write(doc: Document) -> None:
    """Write a document to disk atomically.

    Creates a temp file, writes, verifies by re-parsing, then renames to destination.

    Args:
        doc: Document to write.

    Raises:
        SaalcoError: If serialized document fails to re-parse (data corruption).

    Side Effects:
        Writes to temporary file, then replaces doc.path.
    """
    text = serialize(doc)
    doc.path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{doc.path.name}.", dir=doc.path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        parse_document(Path(name))
        os.replace(name, doc.path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def content_hash(doc: Document) -> str:
    """Compute SHA256 hash of document content for approval tracking.

    Excludes approval-related header keys: status, version, approved_by, approved_at, approved_hash.
    Normalizes line endings to LF before hashing.

    Args:
        doc: Document to hash.

    Returns:
        40-character hex SHA256 hash.
    """
    ignored = {"status", "version", "approved_by", "approved_at", "approved_hash"}
    header = "".join(f"{k}: {v}\n" for k, v in doc.header.items() if k not in ignored)
    payload = (header + "---\n" + doc.body).replace("\r\n", "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def items(doc: Document) -> list[Item]:
    """Extract all items (REQ, DD, UT, etc.) from a document body.

    Parses `### ID: Title` headings and following metadata lines (key: value).

    Args:
        doc: Document to extract from.

    Returns:
        List of Item objects; empty if no items found.
    """
    matches = list(ITEM_RE.finditer(doc.body))
    result: list[Item] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(doc.body)
        block = doc.body[match.end() : end]
        meta: dict[str, str] = {}
        for line in block.splitlines():
            found = META_RE.match(line)
            if found:
                meta[found.group(1)] = found.group(2)
            elif line.startswith("#"):
                break
        ident = match.group(1)
        result.append(Item(ident, ident.split("-")[0], match.group(2), doc.path, meta))
    return result


def set_header(doc: Document, values: dict[str, str]) -> None:
    """Update multiple header fields in a document.

    Args:
        doc: Document to modify.
        values: Dict of key-value pairs to set in header.

    Side Effects:
        Modifies doc.header in place (does not write to disk).
    """
    for key, value in values.items():
        doc.header[key] = value
