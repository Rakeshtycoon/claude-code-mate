"""Geometry scanner — locates float32 XYZ arrays inside ``.ADV`` bytes.

The ``.ADV`` format stores geometry as contiguous little-endian float32
triples (microns). This scanner finds those runs without hard-coded offsets.

Two filters keep the result honest:

* **degeneracy rejection** — runs that are mostly zeros or have no spatial
  extent are incidental float data, not geometry, and are dropped;
* **spatial coherence** — :func:`filter_coherent` keeps only the dominant
  spatial cluster, so a stray measurement array cannot distort the model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class GeometryArray:
    """A contiguous float32 XYZ run recovered from the file."""

    offset: int          # absolute byte offset of the first float
    points: np.ndarray   # (N, 3) float32, in microns

    @property
    def count(self) -> int:
        return len(self.points)

    @property
    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        return self.points.min(axis=0), self.points.max(axis=0)

    @property
    def centroid(self) -> np.ndarray:
        return self.points.mean(axis=0)

    @property
    def extent(self) -> np.ndarray:
        lo, hi = self.bbox
        return hi - lo

    @property
    def diagonal(self) -> float:
        return float(np.linalg.norm(self.extent))


def _plausible_mask(values: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Boolean mask of floats that could be a geometry coordinate."""
    mag = np.abs(values)
    return np.isfinite(values) & ((values == 0) | ((mag >= lo) & (mag <= hi)))


def scan_geometry(
    data: bytes,
    start: int = 0,
    end: int | None = None,
    min_points: int = 64,
    coord_lo: float = 1e-3,
    coord_hi: float = 1e6,
    min_diagonal: float = 50.0,
    max_zero_fraction: float = 0.5,
) -> list[GeometryArray]:
    """Scan ``data[start:end]`` for non-degenerate float32 XYZ runs.

    A run is accepted only when it is a contiguous block of plausible floats,
    a multiple of 3 in length, has at least ``min_points`` points, a bounding
    box diagonal above ``min_diagonal`` and fewer than ``max_zero_fraction``
    all-zero points.
    """
    end = len(data) if end is None else end
    span = data[start:end]
    aligned = (len(span) // 4) * 4
    floats = np.frombuffer(span[:aligned], dtype="<f4")

    good = _plausible_mask(floats, coord_lo, coord_hi)
    idx = np.flatnonzero(good)
    if idx.size == 0:
        return []

    breaks = np.flatnonzero(np.diff(idx) != 1)
    run_starts = np.r_[idx[0], idx[breaks + 1]]
    run_ends = np.r_[idx[breaks], idx[-1]]

    arrays: list[GeometryArray] = []
    for s, e in zip(run_starts, run_ends):
        length = e - s + 1
        usable = length - (length % 3)
        if usable // 3 < min_points:
            continue
        pts = floats[s:s + usable].reshape(-1, 3).astype(np.float32)

        zero_fraction = float(np.mean(np.all(pts == 0, axis=1)))
        if zero_fraction > max_zero_fraction:
            continue
        if float(np.linalg.norm(pts.max(0) - pts.min(0))) < min_diagonal:
            continue

        arrays.append(GeometryArray(offset=start + s * 4, points=pts))
    return arrays


def filter_coherent(arrays: list[GeometryArray], min_neighbours: int = 2):
    """Return only runs belonging to the dominant spatial cluster.

    A run is kept when at least ``min_neighbours`` other runs have a centroid
    within one median run-diagonal of it. This isolates the connected
    diamond geometry from stray, spatially-distant arrays.
    """
    if len(arrays) <= min_neighbours + 1:
        return list(arrays)

    from scipy.spatial import cKDTree

    centroids = np.array([a.centroid for a in arrays])
    radius = float(np.median([a.diagonal for a in arrays])) or 1.0
    tree = cKDTree(centroids)

    kept = [
        arr for i, arr in enumerate(arrays)
        if len(tree.query_ball_point(centroids[i], radius)) - 1 >= min_neighbours
    ]
    return kept or list(arrays)


def total_points(arrays: list[GeometryArray]) -> int:
    return sum(a.count for a in arrays)


def overall_bbox(arrays: list[GeometryArray]) -> tuple[np.ndarray, np.ndarray] | None:
    """Combined bounding box of every recovered array."""
    if not arrays:
        return None
    lows = np.vstack([a.bbox[0] for a in arrays])
    highs = np.vstack([a.bbox[1] for a in arrays])
    return lows.min(axis=0), highs.max(axis=0)
