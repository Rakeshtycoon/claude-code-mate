"""Binary diff utility for comparing two ``.ADV`` files.

Comparing samples is how structural fields (constant across files) are told
apart from per-stone data (varies). Used heavily while extending the spec.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiffRegion:
    offset: int
    length: int


def diff_regions(a: bytes, b: bytes, min_run: int = 8) -> list[DiffRegion]:
    """Return byte ranges where ``a`` and ``b`` differ.

    Only differing runs of at least ``min_run`` bytes are reported, which
    suppresses the noise of scattered single-byte float differences.
    """
    n = min(len(a), len(b))
    regions: list[DiffRegion] = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            start = i
            while i < n and a[i] != b[i]:
                i += 1
            if i - start >= min_run:
                regions.append(DiffRegion(start, i - start))
        else:
            i += 1
    if len(a) != len(b):
        regions.append(DiffRegion(n, abs(len(a) - len(b))))
    return regions


def common_prefix(a: bytes, b: bytes) -> int:
    """Length of the identical leading byte run — the fixed header size."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i
