"""Per-mesh state container for the viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pyvista as pv


_PALETTE = [
    "#4F8EF7",  # blue
    "#F76C5E",  # coral
    "#46C387",  # green
    "#E6B800",  # amber
    "#9D7CD8",  # violet
    "#FF8FB1",  # pink
    "#54C5C5",  # teal
]


@dataclass
class LoadedMesh:
    """A single STL loaded into the scene."""

    name: str
    path: Path
    mesh: pv.PolyData
    color: str
    opacity: float = 1.0
    visible: bool = True
    actor: object = None  # set by viewport after add_mesh

    @property
    def triangle_count(self) -> int:
        return int(self.mesh.n_cells)

    @property
    def vertex_count(self) -> int:
        return int(self.mesh.n_points)

    @property
    def bounds_xyz(self) -> tuple[float, float, float]:
        """Width, depth, height in source units."""
        xmin, xmax, ymin, ymax, zmin, zmax = self.mesh.bounds
        return (xmax - xmin, ymax - ymin, zmax - zmin)

    @property
    def surface_area(self) -> float:
        return float(self.mesh.area)

    @property
    def volume(self) -> Optional[float]:
        """Volume in source-unit^3, or None if mesh isn't closed."""
        try:
            vol = float(self.mesh.volume)
        except Exception:
            return None
        # PyVista returns 0 (or near-zero) for non-watertight meshes.
        if abs(vol) < 1e-9:
            return None
        return abs(vol)


def color_for_index(index: int) -> str:
    return _PALETTE[index % len(_PALETTE)]
