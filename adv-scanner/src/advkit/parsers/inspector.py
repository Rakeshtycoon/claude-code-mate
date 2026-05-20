"""Low-level binary inspection: entropy, histograms, signatures, patterns.

These utilities are format-agnostic. They are what you reach for first when
a new/unknown .adv revision shows up and the structured parser cannot make
sense of a region: an entropy profile instantly separates compressed blobs
from raw voxel arrays from JPEG runs.
"""
from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass, field

# Magic numbers for compression/container codecs the .adv pipeline may embed.
SIGNATURES: dict[bytes, str] = {
    b"\x1f\x8b": "gzip",
    b"\x78\x01": "zlib (no/low compression)",
    b"\x78\x9c": "zlib (default)",
    b"\x78\xda": "zlib (best)",
    b"\x04\x22\x4d\x18": "lz4 frame",
    b"\x28\xb5\x2f\xfd": "zstd",
    b"\x42\x5a\x68": "bzip2",
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"II*\x00": "tiff (little-endian)",
    b"MM\x00*": "tiff (big-endian)",
    b"PK\x03\x04": "zip",
}


def shannon_entropy(buf) -> float:
    """Shannon entropy of a byte buffer in bits/byte (0..8)."""
    if len(buf) == 0:
        return 0.0
    counts = Counter(buf)
    total = len(buf)
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


@dataclass
class EntropyWindow:
    offset: int
    size: int
    entropy: float

    @property
    def classification(self) -> str:
        """Coarse content guess from entropy alone."""
        if self.entropy < 1.0:
            return "padding/constant"
        if self.entropy < 4.0:
            return "structured (records/headers)"
        if self.entropy < 7.0:
            return "mixed (raw imagery/voxels)"
        if self.entropy < 7.9:
            return "high (lightly compressed)"
        return "very high (compressed/encrypted/jpeg)"


def entropy_profile(buf, window: int = 65536, limit: int | None = None) -> list[EntropyWindow]:
    """Sliding (non-overlapping) entropy profile across ``buf``.

    ``window`` of 64 KiB gives a good structure/compression contrast without
    being noisy. ``limit`` caps how many bytes are scanned (None = all).
    """
    total = len(buf) if limit is None else min(len(buf), limit)
    out: list[EntropyWindow] = []
    off = 0
    while off < total:
        chunk = bytes(buf[off:off + window])
        out.append(EntropyWindow(off, len(chunk), shannon_entropy(chunk)))
        off += window
    return out


def detect_signatures(buf, start: int = 0, end: int | None = None,
                       max_hits: int = 256) -> list[tuple[int, str]]:
    """Locate known codec/container magic numbers in ``buf[start:end]``."""
    if end is None:
        end = len(buf)
    hits: list[tuple[int, str]] = []
    for magic, name in SIGNATURES.items():
        cursor = start
        while len(hits) < max_hits:
            pos = buf.find(magic, cursor)
            if pos < 0 or pos >= end:
                break
            hits.append((pos, name))
            cursor = pos + len(magic)
    hits.sort()
    return hits


@dataclass
class NumericGuess:
    """Result of probing a region for a homogeneous numeric encoding."""

    dtype: str
    item_size: int
    count: int
    finite_ratio: float
    in_range_ratio: float
    sample: list = field(default_factory=list)

    @property
    def plausible(self) -> bool:
        return self.finite_ratio > 0.98 and self.in_range_ratio > 0.90


def probe_numeric(buf, start: int, end: int, lo: float = -1e6, hi: float = 1e6,
                  sample_items: int = 4096) -> dict[str, NumericGuess]:
    """Test whether ``buf[start:end]`` is an array of float32/float64/int.

    For each candidate dtype it samples the leading items and reports the
    fraction that are finite and within a plausible coordinate range. The
    geometry/voxel sections of an .adv file are identified this way.
    """
    region = bytes(buf[start:end])
    out: dict[str, NumericGuess] = {}
    specs = [("float64", "<d", 8), ("float32", "<f", 4),
             ("int32", "<i", 4), ("uint16", "<H", 2)]
    for name, fmt, size in specs:
        n = min(len(region) // size, sample_items)
        if n == 0:
            continue
        vals = struct.unpack_from(f"<{n}{fmt[-1]}", region, 0)
        finite = [v for v in vals if isinstance(v, int) or math.isfinite(v)]
        in_range = sum(1 for v in finite if lo <= v <= hi)
        out[name] = NumericGuess(
            dtype=name,
            item_size=size,
            count=len(region) // size,
            finite_ratio=len(finite) / n,
            in_range_ratio=in_range / n,
            sample=[round(v, 4) if isinstance(v, float) else v for v in vals[:8]],
        )
    return out


def find_repeats(buf, start: int, end: int, unit: int = 2,
                 min_run: int = 8) -> list[tuple[int, int, bytes]]:
    """Find runs where the same ``unit``-byte value repeats >= ``min_run``.

    Long runs of a constant 16-bit value are a strong tell for an
    uninitialised/sentinel-filled raw image or voxel buffer.
    """
    region = bytes(buf[start:end])
    runs: list[tuple[int, int, bytes]] = []
    i = 0
    limit = len(region) - unit
    while i <= limit:
        token = region[i:i + unit]
        j = i + unit
        while j <= limit and region[j:j + unit] == token:
            j += unit
        run_units = (j - i) // unit
        if run_units >= min_run:
            runs.append((start + i, run_units, token))
        i = j if j > i else i + unit
    return runs


def hexdump(buf, offset: int, length: int = 256, width: int = 16) -> str:
    """Classic ``offset | hex | ascii`` hexdump of a region."""
    data = bytes(buf[offset:offset + length])
    lines = []
    for row in range(0, len(data), width):
        chunk = data[row:row + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk).ljust(width * 3 - 1)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset + row:08x}  {hex_part}  |{ascii_part}|")
    return "\n".join(lines)
