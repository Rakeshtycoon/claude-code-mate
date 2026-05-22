"""Mesh container plus surface-reconstruction algorithms.

Reconstruction here is *honest*: every vertex originates from float data in
the ``.ADV`` file. Convex-hull and marching-cubes surfaces are clearly
labelled as reconstructions of the recovered point set, never invented.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Mesh:
    """A triangle mesh: vertices + faces, with optional per-vertex normals."""

    vertices: np.ndarray                                  # (V, 3) float32
    faces: np.ndarray                                     # (F, 3) int32
    normals: np.ndarray | None = None                     # (V, 3) float32
    name: str = "mesh"

    @property
    def is_empty(self) -> bool:
        return len(self.vertices) == 0 or len(self.faces) == 0

    def compute_normals(self) -> "Mesh":
        """Compute area-weighted per-vertex normals."""
        v, f = self.vertices, self.faces
        normals = np.zeros_like(v, dtype=np.float64)
        tris = v[f]
        face_n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        for i in range(3):
            np.add.at(normals, f[:, i], face_n)
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        self.normals = (normals / lengths).astype(np.float32)
        return self

    def scaled(self, factor: float) -> "Mesh":
        """Return a copy with vertices multiplied by ``factor`` (eg µm -> mm)."""
        return Mesh(
            vertices=(self.vertices * factor).astype(np.float32),
            faces=self.faces.copy(),
            normals=self.normals,
            name=self.name,
        )


@dataclass
class PolyLine:
    """An ordered polyline — used for raw contour geometry."""

    points: np.ndarray            # (N, 3) float32
    name: str = "contour"
    closed: bool = True


@dataclass
class ReconResult:
    """Everything the reconstruction engine produced for one document."""

    point_cloud: np.ndarray = field(default_factory=lambda: np.empty((0, 3), np.float32))
    contours: list[PolyLine] = field(default_factory=list)
    meshes: list[Mesh] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def convex_hull(points: np.ndarray, name: str = "hull") -> Mesh:
    """Convex-hull surface of a point set (a valid envelope of real data)."""
    from scipy.spatial import ConvexHull

    if len(points) < 4:
        return Mesh(np.empty((0, 3), np.float32), np.empty((0, 3), np.int32), name=name)
    hull = ConvexHull(points.astype(np.float64))
    return Mesh(
        vertices=points.astype(np.float32),
        faces=hull.simplices.astype(np.int32),
        name=name,
    ).compute_normals()


def marching_cubes_surface(
    points: np.ndarray, resolution: int = 96, name: str = "isosurface"
) -> Mesh:
    """Voxelise a point cloud and extract an isosurface with marching cubes.

    This reconstructs a closed surface from slice/contour point data — the
    approach the format requires, since the rough diamond is stored as
    cross-section contours rather than an explicit mesh.
    """
    from scipy.ndimage import distance_transform_edt, gaussian_filter
    from skimage.measure import marching_cubes

    if len(points) < 8:
        return Mesh(np.empty((0, 3), np.float32), np.empty((0, 3), np.int32), name=name)

    lo = points.min(axis=0)
    hi = points.max(axis=0)
    span = np.maximum(hi - lo, 1e-6)
    pad = span * 0.05
    lo -= pad
    hi += pad
    span = hi - lo

    grid = np.zeros((resolution, resolution, resolution), dtype=bool)
    idx = np.floor((points - lo) / span * (resolution - 1)).astype(int)
    idx = np.clip(idx, 0, resolution - 1)
    grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True

    # Solidify: distance field, smoothed, then iso-extract the shell.
    field = distance_transform_edt(~grid)
    field = gaussian_filter(field.astype(np.float32), sigma=1.0)
    iso = float(np.percentile(field[field > 0], 6)) if np.any(field > 0) else 1.0

    try:
        verts, faces, normals, _ = marching_cubes(field, level=iso)
    except (ValueError, RuntimeError):
        return Mesh(np.empty((0, 3), np.float32), np.empty((0, 3), np.int32), name=name)

    verts = verts / (resolution - 1) * span + lo
    return Mesh(
        vertices=verts.astype(np.float32),
        faces=faces.astype(np.int32),
        normals=normals.astype(np.float32),
        name=name,
    )
