"""Convert reconstruction results into PyVista renderables.

Kept free of Qt so it can be unit-tested headless (off-screen rendering).
"""
from __future__ import annotations

import numpy as np

from ..export.materials import material_for
from ..recon.mesh import Mesh, PolyLine


def mesh_to_polydata(mesh: Mesh):
    """Convert a :class:`Mesh` to a ``pyvista.PolyData`` triangle surface."""
    import pyvista as pv

    if mesh.is_empty:
        return pv.PolyData()
    faces = np.hstack(
        [np.full((len(mesh.faces), 1), 3, dtype=np.int64), mesh.faces.astype(np.int64)]
    ).ravel()
    return pv.PolyData(mesh.vertices.astype(np.float64), faces)


def polyline_to_polydata(poly: PolyLine):
    """Convert a :class:`PolyLine` contour to ``pyvista.PolyData`` lines."""
    import pyvista as pv

    pts = poly.points.astype(np.float64)
    if len(pts) < 2:
        return pv.PolyData()
    if poly.closed:
        pts = np.vstack([pts, pts[0]])
    count = len(pts)
    cells = np.hstack([[count], np.arange(count)])
    pd = pv.PolyData()
    pd.points = pts
    pd.lines = cells
    return pd


def points_to_polydata(points: np.ndarray):
    import pyvista as pv

    return pv.PolyData(points.astype(np.float64))


#: Layer keys recognised by the viewer.
LAYERS = ("rough", "polished", "saw_planes", "contours", "point_cloud", "axes")


def classify_layer(name: str) -> str:
    """Map an object name to a viewer layer key."""
    mat = material_for(name).name
    if mat == "rough":
        return "rough"
    if mat == "polished":
        return "polished"
    if mat == "saw_plane":
        return "saw_planes"
    if mat == "contour":
        return "contours"
    return "rough"
