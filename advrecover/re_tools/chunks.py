"""Per-element chunk parser for the ``0xCA0000``-onwards region.

The ``.ADV`` main-model section ends with a long run of per-element records
(~430 of them, one per ``Saw``/``Pie`` planning element). Each record is a
small low-entropy **header** followed by a high-entropy **compressed body**.

This module locates the chunks and decodes everything readable in their
headers. The compressed bodies cannot be decoded from the current samples,
but :func:`compare_chunk_tables` is built so that, once more ``.ADV`` files
are available, differential analysis of the headers can proceed immediately.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np


@dataclass
class ElementChunk:
    """One per-element record: a readable header + a compressed body."""

    index: int
    start: int
    end: int
    header_id: int
    header_floats: list[float] = field(default_factory=list)
    body_entropy: float = 0.0

    @property
    def size(self) -> int:
        return self.end - self.start


def _entropy(block: bytes) -> float:
    if not block:
        return 0.0
    hist = np.bincount(np.frombuffer(block, np.uint8), minlength=256).astype(np.float64)
    p = hist[hist > 0] / len(block)
    return float(-(p * np.log2(p)).sum())


def _is_header(data: bytes, offset: int, probe: int = 512) -> bool:
    """A chunk header window has markedly lower entropy than a compressed body."""
    if offset + probe > len(data):
        return False
    return _entropy(data[offset:offset + probe]) < 6.8


def _header_floats(data: bytes, offset: int, span: int = 2048) -> list[float]:
    """Clean float64 values found in a chunk header (plausible magnitudes)."""
    out: list[float] = []
    end = min(offset + span, len(data) - 8)
    for pos in range(offset, end, 8):
        value = struct.unpack_from("<d", data, pos)[0]
        if np.isfinite(value) and 1e-6 <= abs(value) <= 1e9:
            out.append(round(value, 6))
    return out


def find_chunks(data: bytes, region_start: int, region_end: int,
                window: int = 2048) -> list[ElementChunk]:
    """Locate per-element chunks via low-entropy header detection.

    Each chunk begins where a low-entropy header window starts (after a
    high-entropy body), so chunk boundaries are entropy transitions.
    """
    boundaries: list[int] = []
    prev_low = False
    for off in range(region_start, region_end, window):
        low = _is_header(data, off, probe=window)
        if low and not prev_low:
            boundaries.append(off)
        prev_low = low

    chunks: list[ElementChunk] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else region_end
        body = data[start + window:end]
        chunks.append(ElementChunk(
            index=i,
            start=start,
            end=end,
            header_id=struct.unpack_from("<I", data, start)[0],
            header_floats=_header_floats(data, start),
            body_entropy=_entropy(body),
        ))
    return chunks


def chunk_table(data: bytes, region_start: int = 0xCA0000,
                region_end: int | None = None) -> list[ElementChunk]:
    """Parse the per-element chunk table from a full ``.ADV`` buffer."""
    region_end = len(data) if region_end is None else region_end
    return find_chunks(data, region_start, region_end)


def compare_chunk_tables(a: list[ElementChunk],
                         b: list[ElementChunk]) -> list[str]:
    """Differential report between two files' chunk tables.

    Built for the next RE stage: with several ``.ADV`` samples, fields that
    stay constant are structural and fields that vary are per-stone data.
    """
    report = [f"chunk count: A={len(a)}  B={len(b)}"]
    for ca, cb in zip(a, b):
        diffs = []
        if ca.header_id != cb.header_id:
            diffs.append(f"id {ca.header_id}!={cb.header_id}")
        if len(ca.header_floats) != len(cb.header_floats):
            diffs.append(
                f"float-count {len(ca.header_floats)}!={len(cb.header_floats)}")
        if abs(ca.size - cb.size) > 0:
            diffs.append(f"size {ca.size}!={cb.size}")
        if diffs:
            report.append(f"  chunk[{ca.index}]: " + ", ".join(diffs))
    return report


def render_chunk_table(chunks: list[ElementChunk], limit: int = 40) -> str:
    """Human-readable rendering of a chunk table."""
    lines = [f"PER-ELEMENT CHUNK TABLE ({len(chunks)} chunks)",
             f"{'idx':>4} {'offset':>10} {'size':>9} {'id':>8} "
             f"{'body-ent':>9}  header floats"]
    for c in chunks[:limit]:
        floats = ", ".join(f"{v:g}" for v in c.header_floats[:6])
        lines.append(f"{c.index:4d} 0x{c.start:08x} {c.size:9,} {c.header_id:8d} "
                      f"{c.body_entropy:9.3f}  {floats}")
    if len(chunks) > limit:
        lines.append(f"  ... {len(chunks) - limit} more")
    return "\n".join(lines)
