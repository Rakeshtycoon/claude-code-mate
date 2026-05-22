"""Reconstruction orchestrator.

Turns the raw float arrays recovered by :mod:`advrecover.recon.scan` into a
:class:`ReconResult` — point cloud, contour polylines and reconstructed
surface meshes — ready for the viewer and exporter.
"""
from __future__ import annotations

import numpy as np

from ..format.constants import MICRONS_PER_MM
from ..format.model import AdvDocument
from .mesh import Mesh, PolyLine, ReconResult, convex_hull, marching_cubes_surface
from .scan import GeometryArray, filter_coherent, scan_geometry

#: Supported surface reconstruction strategies.
METHODS = ("pointcloud", "hull", "clustered_hull", "marching_cubes")


def reconstruct(
    data: bytes,
    doc: AdvDocument,
    *,
    method: str = "marching_cubes",
    scale_to_mm: bool = True,
    min_points: int = 32,
    keep_contours: bool = True,
) -> ReconResult:
    """Reconstruct geometry from a parsed ``.ADV`` document.

    ``method`` selects the surface strategy; ``pointcloud`` skips meshing.
    Coordinates are converted from microns to millimetres when
    ``scale_to_mm`` is set.
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {METHODS}")

    section = doc.section(1)
    if section is None:
        result = ReconResult()
        result.notes.append("no main-model section; nothing to reconstruct")
        return result

    raw_arrays = scan_geometry(data, section.offset, section.end, min_points=min_points)
    arrays = filter_coherent(raw_arrays)
    factor = 1.0 / MICRONS_PER_MM if scale_to_mm else 1.0

    result = ReconResult()
    if not arrays:
        result.notes.append("no float32 XYZ runs found in the main-model section")
        return result
    dropped = len(raw_arrays) - len(arrays)
    if dropped:
        result.notes.append(
            f"dropped {dropped} spatially incoherent array(s) before reconstruction"
        )

    all_points = np.vstack([a.points for a in arrays]).astype(np.float32) * factor
    result.point_cloud = all_points
    unit = "mm" if scale_to_mm else "micron"
    result.notes.append(
        f"recovered {len(arrays)} planar contour records, "
        f"{len(all_points):,} points (units: {unit})"
    )
    result.notes.append(
        "note: these contours are a 2-D auxiliary dataset; the true 3-D model "
        "lives in the opaque packed block (see docs/ADV_FORMAT.md sec 6)"
    )

    if keep_contours:
        for i, arr in enumerate(arrays):
            result.contours.append(
                PolyLine(points=arr.points.astype(np.float32) * factor,
                         name=f"contour_{i:04d}")
            )

    if method == "pointcloud":
        return result

    if method == "hull":
        result.meshes.append(convex_hull(all_points, name="contour_hull"))
    elif method == "marching_cubes":
        result.meshes.append(
            marching_cubes_surface(all_points, name="contour_surface")
        )
    elif method == "clustered_hull":
        result.meshes.extend(_clustered_hulls(arrays, factor))

    result.notes.append(f"surface method: {method}")
    return result


def _clustered_hulls(arrays: list[GeometryArray], factor: float) -> list[Mesh]:
    """Group arrays by spatial proximity and hull each group separately.

    This separates spatially distinct elements (eg the rough envelope vs.
    inner planned stones) without inventing geometry — every hull wraps real
    recovered points.
    """
    from scipy.spatial import cKDTree

    centroids = np.array([a.centroid for a in arrays])
    overall = centroids.max(axis=0) - centroids.min(axis=0)
    link = float(np.linalg.norm(overall)) * 0.08 + 1e-6

    parent = list(range(len(arrays)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in cKDTree(centroids).query_pairs(link):
        parent[find(i)] = find(j)

    groups: dict[int, list[GeometryArray]] = {}
    for i in range(len(arrays)):
        groups.setdefault(find(i), []).append(arrays[i])

    meshes: list[Mesh] = []
    for k, members in enumerate(sorted(groups.values(), key=len, reverse=True)):
        pts = np.vstack([m.points for m in members]).astype(np.float32) * factor
        mesh = convex_hull(pts, name=f"cluster_{k:02d}")
        if not mesh.is_empty:
            meshes.append(mesh)
    return meshes
