"""Per-file state container for the STN viewer.

A LoadedStn wraps the parsed :class:`StnModel` together with a PyVista
mesh reconstructed from the file's quantised heightfield body, so the
viewport can treat each file uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pyvista as pv

from stn_reader.parser import (
    NO_DATA_SENTINEL_U16,
    StnModel,
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


def _reconstruct_heightfield(
    raw_bytes: bytes, body_offset: int
) -> Optional[pv.StructuredGrid]:
    """Best-effort heightmap from the .stn body.

    The exact 2-D layout of the body is still being reverse-engineered, so
    we decode every u16 sample, mask the no-data sentinel, then reshape
    into the closest-to-square grid that exactly fits. This produces a
    visually meaningful preview even before the true grid dimensions are
    pinned down.
    """
    body = raw_bytes[body_offset:]
    if len(body) < 64:
        return None

    samples = np.frombuffer(body[: len(body) // 2 * 2], dtype="<u2").astype(
        np.float32
    )
    if samples.size == 0:
        return None

    # Cap to keep the viewport responsive on large scans.
    cap = 1_500_000
    if samples.size > cap:
        samples = samples[:cap]

    # Reshape: pick the divisor of N closest to sqrt(N) for a square-ish grid.
    n = samples.size
    side = int(np.sqrt(n))
    width = side
    while width > 1 and n % width != 0:
        width -= 1
    if width <= 1:
        # Force a clean shape by trimming trailing samples.
        width = side
        n = width * width
        samples = samples[:n]
    height = n // width

    grid = samples.reshape(height, width)

    # Mask the no-data sentinel, then normalise so the height range is
    # ~order of the XY extent (otherwise the surface is razor-thin).
    mask = grid == NO_DATA_SENTINEL_U16
    valid = grid[~mask]
    if valid.size < 4:
        return None
    lo, hi = float(valid.min()), float(valid.max())
    rng = hi - lo if hi > lo else 1.0
    target_z = 0.25 * max(width, height)
    z = (grid - lo) / rng * target_z
    z[mask] = np.nan

    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)

    structured = pv.StructuredGrid(xx, yy, z)
    structured.point_data["height"] = z.ravel(order="F")
    return structured


@dataclass
class LoadedStn:
    """A single .stn file loaded into the scene."""

    name: str
    path: Path
    model: StnModel
    mesh: Optional[pv.StructuredGrid]
    color: str
    opacity: float = 1.0
    visible: bool = True
    actor: object = None  # set by viewport after add_mesh

    @classmethod
    def from_path(cls, path: Path, index: int) -> "LoadedStn":
        model = parse_stn_file(path)
        raw = path.read_bytes()
        mesh = _reconstruct_heightfield(raw, model.body_offset)
        return cls(
            name=path.name,
            path=path,
            model=model,
            mesh=mesh,
            color=color_for_index(index),
        )

    @property
    def has_mesh(self) -> bool:
        return self.mesh is not None and self.mesh.n_points > 0

    @property
    def grid_shape(self) -> tuple[int, int]:
        if self.mesh is None:
            return (0, 0)
        dims = self.mesh.dimensions  # (i, j, k)
        return (int(dims[0]), int(dims[1]))

    @property
    def sample_count(self) -> int:
        return 0 if self.mesh is None else int(self.mesh.n_points)
