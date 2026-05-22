"""Length-prefixed string harvesting.

``.ADV`` stores text as ``u32 length`` + ASCII bytes. This module scans a
byte range for every plausible string, which is how metadata and the
planning tree (``Saw*`` / ``Pie*``) are recovered.
"""
from __future__ import annotations

import re
import struct

_PRINTABLE = bytes(range(32, 127))
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                     r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
PLANNING_RE = re.compile(r"^(Saw|Pie|Mea)\b|^(Saw|Pie)\d", re.IGNORECASE)


def harvest_strings(data: bytes, base: int = 0, min_len: int = 2,
                    max_len: int = 256) -> list[tuple[int, str]]:
    """Find every ``u32``-length-prefixed printable ASCII string.

    Returns ``(absolute_offset, text)`` pairs. ``base`` is added so callers
    working on a slice still get file-absolute offsets.
    """
    found: list[tuple[int, str]] = []
    n = len(data)
    i = 0
    while i < n - 4:
        length = struct.unpack_from("<I", data, i)[0]
        if min_len <= length <= max_len and i + 4 + length <= n:
            chunk = data[i + 4:i + 4 + length]
            if all(c in _PRINTABLE for c in chunk):
                found.append((base + i, chunk.decode("ascii")))
                i += 4 + length
                continue
        i += 1
    return found


def planning_tree(strings: list[tuple[int, str]]) -> list[str]:
    """Filter harvested strings down to planning-tree element names."""
    seen: set[str] = set()
    tree: list[str] = []
    for _off, text in strings:
        if PLANNING_RE.match(text) and text not in seen:
            seen.add(text)
            tree.append(text)
    return tree
