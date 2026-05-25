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


def _build_heightfield_mesh(
    raw_bytes: bytes, offset: int, size: int
) -> Optional[pv.StructuredGrid]:
    if size < 64:
        return None
    samples = decode_heightfield(raw_bytes, offset, size)
    if samples.size < 16:
        return None

    # Reshape to a clean (height, width) grid by trimming trailing
    # samples down to a near-square factorisation.
    n = samples.size
    side = int(np.sqrt(n))
    width = max(side, 1)
    while width > 1 and n % width != 0:
        width -= 1
    if width <= 1:
        width = side
        n = width * width
        samples = samples[:n]
    height = n // width
    grid = samples.reshape(height, width)

    valid = grid[~np.isnan(grid)]
    if valid.size < 4:
        return None
    lo, hi = float(valid.min()), float(valid.max())
    rng = hi - lo if hi > lo else 1.0
    target_z = 0.25 * max(width, height)
    z = (grid - lo) / rng * target_z

    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)

    structured = pv.StructuredGrid(xx, yy, z.astype(np.float32))
    structured.point_data["height"] = z.ravel(order="F").astype(np.float32)
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
        hf_mesh = _build_heightfield_mesh(
            raw, model.heightfield_offset, model.heightfield_size
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
