"""Hex inspection utilities for reverse-engineering unknown byte ranges."""
from __future__ import annotations

import math
from collections import Counter


def hexdump(data: bytes, base: int = 0, width: int = 16, limit: int | None = 256) -> str:
    """Return a classic ``offset  hex  ascii`` dump."""
    out = []
    end = len(data) if limit is None else min(len(data), limit)
    for i in range(0, end, width):
        row = data[i:i + width]
        hex_part = " ".join(f"{b:02x}" for b in row)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        out.append(f"{base + i:08x}  {hex_part:<{width * 3}}  {ascii_part}")
    if limit is not None and len(data) > limit:
        out.append(f"... ({len(data) - limit} more bytes)")
    return "\n".join(out)


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits/byte (0 = uniform, ~8 = random/compressed)."""
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def entropy_profile(data: bytes, blocks: int = 32) -> list[tuple[int, float]]:
    """Sample entropy across the file; returns ``(offset, entropy)`` pairs."""
    if not data:
        return []
    step = max(1, len(data) // blocks)
    return [(off, shannon_entropy(data[off:off + step])) for off in range(0, len(data), step)]
