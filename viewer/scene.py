"""Per-file state container for the STN viewer.

A :class:`LoadedStn` wraps the parsed model plus PyVista geometry built
from two parts of the .stn body:

* the float32 point-cloud chunks decoded directly from real coordinates,
* the quantised u16 heightfield, reshaped into a square-ish grid for a
  surface preview (until the exact 2-D layout is fully pinned down).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pyvista as pv

from stn_reader.parser import (
    StnModel,
    decode_heightfield,
    parse_stn_file,
)


_PALETTE = [
    "#4F8EF7",
    "#F76C5E",
    "#46C387",
    "#E6B800",
    "#9D7CD8",
    "#FF8FB1",
    "#54C5C5",
]


def color_for_index(index: int) -> str:
    return _PALETTE[index % len(_PALETTE)]


def _build_point_cloud_mesh(points: np.ndarray) -> Optional[pv.PolyData]:
    if points.size == 0:
        return None
    cloud = pv.PolyData(points.astype(np.float32, copy=False))
    cloud.point_data["z"] = points[:, 2].astype(np.float32, copy=False)
    return cloud


def _factor_close_to_square(n: int) -> tuple[int, int]:
    """Return (width, height) factors of n closest to a square shape."""
    side = max(int(np.sqrt(n)), 1)
    for w in range(side, 0, -1):
        if n % w == 0:
            return w, n // w
    return n, 1


def _build_heightfield_mesh(
    raw_bytes: bytes,
    offset: int,
    size: int,
    point_bounds: Optional[tuple[float, float, float, float, float, float]] = None,
) -> Optional[pv.StructuredGrid]:
    """Reconstruct the quantised u16 region as a heightmap surface.

    The grid dimensions are chosen as the most square-ish exact
    factorisation of the u16 sample count. Z is rescaled so the height
    range matches the point-cloud Z extent (when available) and X / Y
    are positioned over the point cloud's footprint, so the dense
    surface and the float edge points line up in the viewport.
    """
    if size < 64:
        return None
    samples = decode_heightfield(raw_bytes, offset, size)
    if samples.size < 16:
        return None

    width, height = _factor_close_to_square(int(samples.size))
    grid = samples.reshape(height, width)

    valid_mask = ~np.isnan(grid)
    valid_values = grid[valid_mask]
    if valid_values.size < 16:
        return None

    # Percentile-clip so a handful of extreme outliers don't squash the
    # whole range when normalising.
    lo, hi = np.percentile(valid_values, [1.0, 99.0])
    if hi <= lo:
        lo, hi = float(valid_values.min()), float(valid_values.max() + 1.0)

    # Position / scale to match the point-cloud bounds, falling back to
    # pixel-space when no chunks were decoded.
    if point_bounds is not None and any(point_bounds):
        xmin, xmax, ymin, ymax, zmin, zmax = point_bounds
        span_x = max(xmax - xmin, 1.0)
        span_y = max(ymax - ymin, 1.0)
        span_z = max(zmax - zmin, 1.0)
    else:
        xmin, ymin, zmin = 0.0, 0.0, 0.0
        span_x = float(width)
        span_y = float(height)
        span_z = 0.25 * max(width, height)

    z_norm = (np.clip(grid, lo, hi) - lo) / (hi - lo)
    z_norm[~valid_mask] = np.nan
    z = (zmin + z_norm * span_z).astype(np.float32)

    xs = np.linspace(xmin, xmin + span_x, width, dtype=np.float32)
    ys = np.linspace(ymin, ymin + span_y, height, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)

    # Replace NaN with the floor Z so the mesh has finite coordinates,
    # then mark those vertices so we can hide their cells.
    z_finite = np.where(np.isnan(z), zmin, z).astype(np.float32)
    structured = pv.StructuredGrid(xx, yy, z_finite)
    structured.point_data["height"] = z_finite.ravel(order="F")

    # Hide any cell whose any vertex was no-data, leaving a surface that
    # only covers the actual scanned area.
    valid_pts = (~np.isnan(z)).astype(np.uint8)
    structured.point_data["__valid"] = valid_pts.ravel(order="F")
    return structured


@dataclass
class LoadedStn:
    """A single .stn file loaded into the scene."""

    name: str
    path: Path
    model: StnModel
    point_cloud: Optional[pv.PolyData]
    heightmap: Optional[pv.StructuredGrid]
    color: str
    opacity: float = 1.0
    visible: bool = True
    show_points: bool = True
    show_surface: bool = True
    actor_points: object = None
    actor_surface: object = None

    @classmethod
    def from_path(cls, path: Path, index: int) -> "LoadedStn":
        model = parse_stn_file(path)
        raw = path.read_bytes()
        pc_mesh = _build_point_cloud_mesh(model.point_cloud.points)
        pc_bounds = (
            model.point_cloud.bounds if model.point_cloud.point_count > 0 else None
        )
        hf_mesh = _build_heightfield_mesh(
            raw,
            model.heightfield_offset,
            model.heightfield_size,
            point_bounds=pc_bounds,
        )
        return cls(
            name=path.name,
            path=path,
            model=model,
            point_cloud=pc_mesh,
            heightmap=hf_mesh,
            color=color_for_index(index),
        )

    @property
    def point_count(self) -> int:
        return self.model.point_cloud.point_count

    @property
    def chunk_count(self) -> int:
        return self.model.point_cloud.chunk_count

    @property
    def heightmap_dims(self) -> tuple[int, int]:
        if self.heightmap is None:
            return (0, 0)
        dims = self.heightmap.dimensions
        return (int(dims[0]), int(dims[1]))

    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]:
        return self.model.point_cloud.bounds
