"""Entropy segmentation and a confidence-ranked block map.

This is the core reverse-engineering instrument for the ``.ADV`` format: it
splits a file into homogeneous regions, classifies each one, and ranks every
region by how likely it is to contain extractable 3-D geometry.

The block map is the artefact to consult first when new samples or the
Advisor DLLs become available — it says exactly where to dig.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..recon.scan import filter_coherent, scan_geometry

# Entropy-class thresholds (bits/byte).
_LOW = 5.0
_MID = 7.30
_HIGH = 7.85


@dataclass
class Segment:
    """One homogeneous region of a file."""

    start: int
    end: int
    entropy: float
    kind: str
    geometry_confidence: float          # 0.0 .. 1.0
    float_points: int
    note: str

    @property
    def size(self) -> int:
        return self.end - self.start


def _window_entropy(data: bytes, window: int) -> np.ndarray:
    """Shannon entropy (bits/byte) for each ``window``-sized block."""
    arr = np.frombuffer(data, dtype=np.uint8)
    count = len(arr) // window
    out = np.zeros(count)
    for i in range(count):
        block = arr[i * window:(i + 1) * window]
        hist = np.bincount(block, minlength=256).astype(np.float64)
        p = hist[hist > 0] / window
        out[i] = -(p * np.log2(p)).sum()
    return out


def _entropy_class(value: float) -> str:
    if value < _LOW:
        return "low"
    if value < _MID:
        return "mid"
    if value < _HIGH:
        return "high"
    return "max"


def _raw_segments(data: bytes, window: int) -> list[tuple[int, int, float]]:
    """Merge adjacent windows of the same entropy class into segments."""
    ent = _window_entropy(data, window)
    if len(ent) == 0:
        return [(0, len(data), 0.0)]
    segments: list[tuple[int, int, float]] = []
    start = 0
    cls = _entropy_class(ent[0])
    for i in range(1, len(ent)):
        if _entropy_class(ent[i]) != cls:
            segments.append((start * window, i * window, float(ent[start:i].mean())))
            start, cls = i, _entropy_class(ent[i])
    segments.append((start * window, len(data), float(ent[start:].mean())))
    return segments


def _classify(data: bytes, start: int, end: int, entropy: float) -> Segment:
    """Classify a segment and score its geometry likelihood."""
    chunk = data[start:end]
    zero_fraction = chunk.count(0) / max(len(chunk), 1)

    arrays = filter_coherent(scan_geometry(chunk, min_points=48))
    float_points = sum(a.count for a in arrays)

    if zero_fraction > 0.85:
        return Segment(start, end, entropy, "padding", 0.0, 0,
                       "mostly zero bytes")
    if entropy < _LOW:
        return Segment(start, end, entropy, "structured", 0.15, float_points,
                       "low entropy: headers / tables / strings")
    if entropy < _MID:
        if float_points > 600:
            return Segment(start, end, entropy, "float-geometry", 0.90,
                           float_points,
                           f"mid entropy: plain float geometry ({float_points} pts)")
        if float_points > 0:
            return Segment(start, end, entropy, "float-geometry", 0.50,
                           float_points,
                           f"mid entropy: sparse float runs ({float_points} pts)")
        return Segment(start, end, entropy, "structured", 0.25, 0,
                       "mid entropy: structured data, no coherent float runs")
    if entropy < _HIGH:
        return Segment(start, end, entropy, "dense", 0.30, float_points,
                       "high entropy: dense or lightly-compressed data")
    return Segment(start, end, entropy, "compressed", 0.08, float_points,
                   "near-maximum entropy: compressed or encrypted")


def segment_file(data: bytes, window: int = 8192,
                 min_size: int = 0) -> list[Segment]:
    """Return classified segments of ``data`` in file order."""
    segments = [
        _classify(data, s, e, ent)
        for s, e, ent in _raw_segments(data, window)
    ]
    if min_size:
        segments = [s for s in segments if s.size >= min_size]
    return segments


def block_map(data: bytes, window: int = 8192) -> list[Segment]:
    """Return segments ranked by geometry confidence (then by size)."""
    segments = segment_file(data, window, min_size=window * 2)
    return sorted(segments, key=lambda s: (s.geometry_confidence, s.size),
                  reverse=True)


def render_segments(segments: list[Segment], ranked: bool = False) -> str:
    """Human-readable rendering of a segment list."""
    title = "CONFIDENCE-RANKED BLOCK MAP" if ranked else "FILE SEGMENTS (in order)"
    lines = [title, "-" * len(title)]
    for seg in segments:
        bar = "#" * int(seg.geometry_confidence * 20)
        lines.append(
            f"  0x{seg.start:08x}..0x{seg.end:08x}  {seg.size:>11,}B  "
            f"ent={seg.entropy:5.2f}  conf={seg.geometry_confidence:4.2f} {bar:<20} "
            f"{seg.kind:<14} {seg.note}"
        )
    return "\n".join(lines)
