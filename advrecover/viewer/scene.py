"""Scene model for the viewer.

A :class:`SceneModel` is a layered, render-agnostic description of an opened
``.ADV`` document — built from the parser + reconstruction engines, then
handed to the Qt/PyVista window. Keeping it Qt-free means it can be unit
tested headlessly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..format.model import AdvDocument
from ..recon import reconstruct
from ..recon.mesh import Mesh, PolyLine
from ..recon.planning import reconstruct_planning

# Layer keys, in display order.
LAYER_ORDER = (
    "rough_body", "cutting_planes", "planned_stones",
    "inclusions", "surface_points", "bounding_box", "contours", "axes",
)


@dataclass
class SceneLayer:
    """One toggleable layer of renderable items."""

    key: str
    label: str
    color: tuple[float, float, float]
    opacity: float
    visible: bool
    meshes: list[Mesh] = field(default_factory=list)
    lines: list[PolyLine] = field(default_factory=list)
    points: np.ndarray | None = None
    inferred: bool = False           # True => a proxy, not decoded geometry
    kind: str = "surface"            # surface | wireframe | points

    @property
    def is_empty(self) -> bool:
        return (not self.meshes and not self.lines
                and (self.points is None or len(self.points) == 0))


@dataclass
class SceneModel:
    """A fully built, layered scene for one document."""

    layers: list[SceneLayer] = field(default_factory=list)
    bounds_min: np.ndarray | None = None
    bounds_max: np.ndarray | None = None
    notes: list[str] = field(default_factory=list)

    def layer(self, key: str) -> SceneLayer | None:
        for layer in self.layers:
            if layer.key == key:
                return layer
        return None

    @property
    def dimensions(self) -> np.ndarray | None:
        if self.bounds_min is None or self.bounds_max is None:
            return None
        return self.bounds_max - self.bounds_min


def _bbox_lines(lo: np.ndarray, hi: np.ndarray) -> list[PolyLine]:
    """Twelve edges of an axis-aligned bounding box, as polylines."""
    c = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]],
                  [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                  [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]],
                  [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]], dtype=np.float32)
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
             (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    return [PolyLine(points=c[list(e)], name=f"bbox_{i}", closed=False)
            for i, e in enumerate(edges)]


def _build_real_meshes(doc: AdvDocument):
    """Build a rough-body mesh and inclusion point set from the decoded clouds.

    Returns ``(rough_meshes, inclusion_points_mm, surface_points_mm, used_real)``.
    Falls back to ``([], None, None, False)`` if no usable clouds are present.
    """
    if not doc.clouds:
        return [], None, None, False
    from ..format.constants import MICRONS_PER_MM

    cloud_verts = [c.vertices for c in doc.clouds
                   if c.kind == "cloud" and len(c.vertices)]
    inclusion_verts = [c.vertices for c in doc.clouds
                       if c.kind == "inclusion" and len(c.vertices)]

    rough_meshes: list[Mesh] = []
    surface_pts_mm = None
    if cloud_verts:
        surface_pts_um = np.vstack(cloud_verts)
        surface_pts_mm = (surface_pts_um / MICRONS_PER_MM).astype(np.float32)
        if surface_pts_mm.shape[0] >= 4:
            try:
                from scipy.spatial import ConvexHull
                hull = ConvexHull(surface_pts_mm.astype(np.float64))
                verts = surface_pts_mm[hull.vertices].astype(np.float32)
                remap = {old: new for new, old in enumerate(hull.vertices)}
                faces = np.array([[remap[i] for i in s] for s in hull.simplices],
                                 dtype=np.int32)
                rough_meshes = [Mesh(verts, faces, name="rough_body")
                                .compute_normals()]
            except Exception:                                 # noqa: BLE001
                rough_meshes = []

    inclusion_pts_mm = None
    if inclusion_verts:
        inclusion_pts_mm = (np.vstack(inclusion_verts) / MICRONS_PER_MM
                            ).astype(np.float32)

    used_real = bool(rough_meshes) or inclusion_pts_mm is not None
    return rough_meshes, inclusion_pts_mm, surface_pts_mm, used_real


def build_scene(
    data: bytes,
    doc: AdvDocument,
    *,
    solution: str | None = None,
    geometry_method: str = "hull",
    plane_size_mm: float | None = None,
) -> SceneModel:
    """Assemble a :class:`SceneModel` from a parsed document."""
    from ..recon.planning import hull_proxy

    model = SceneModel()

    # -- planning reconstruction (decoded, real geometry) ------------------
    planning = reconstruct_planning(data, doc, solution=solution,
                                    plane_size_mm=plane_size_mm)
    model.notes += planning.notes
    saw = [m for m in planning.meshes if m.name.startswith("Saw")]
    pie = [m for m in planning.meshes if m.name.startswith("Pie")]
    saw_lines = [c for c in planning.contours if c.name.startswith("Saw")]
    pie_lines = [c for c in planning.contours if c.name.startswith("Pie")]

    # -- real rough body and inclusions, decoded from the section[1] clouds
    rough_meshes, inclusion_points, surface_points, used_real = (
        _build_real_meshes(doc))
    if used_real:
        model.notes.append(
            f"rough body: convex hull of {surface_points.shape[0]:,} decoded "
            f"surface points from {len([c for c in doc.clouds if c.kind == 'cloud'])} "
            f"labeled cloud patches (REAL scanned geometry)")
        if inclusion_points is not None and len(inclusion_points):
            model.notes.append(
                f"inclusions: {inclusion_points.shape[0]:,} decoded "
                f"interior points from {len([c for c in doc.clouds if c.kind == 'inclusion'])} "
                f"inclusion meshes (REAL scanner data)")
    else:
        # Fall back to convex hull of planning elements if no clouds decoded
        geometry = reconstruct(data, doc, method=geometry_method)
        hull = hull_proxy(data, doc, solution=solution) if solution else None
        if hull is not None and not hull.is_empty:
            rough_meshes = [hull]
            model.notes.append(
                "rough body: convex hull of planning-element positions "
                "(approximate envelope; no clouds decoded from section[1])")
        else:
            rough_meshes = geometry.meshes
            model.notes += geometry.notes
        inclusion_points = None
        surface_points = None
    contour_lines = reconstruct(data, doc, method=geometry_method).contours

    # -- layers ------------------------------------------------------------
    model.layers = [
        SceneLayer("rough_body", "Rough body" + ("" if used_real else " (proxy)"),
                   (0.80, 0.64, 0.68), 0.30, True, meshes=rough_meshes,
                   inferred=not used_real),
        SceneLayer("cutting_planes", "Cutting planes", (0.25, 0.78, 0.45),
                   0.55, True, meshes=saw, lines=saw_lines),
        SceneLayer("planned_stones", "Planned stones", (0.95, 0.83, 0.28),
                   0.80, True, meshes=pie, lines=pie_lines),
        SceneLayer("inclusions", "Inclusions" + ("" if used_real else " (markers)"),
                   (0.85, 0.20, 0.20), 1.0, True,
                   points=inclusion_points if inclusion_points is not None else None,
                   kind="points" if inclusion_points is not None else "surface"),
        SceneLayer("surface_points", "Surface scan points", (0.40, 0.55, 0.80),
                   1.0, False,
                   points=surface_points if surface_points is not None else None,
                   kind="points"),
        SceneLayer("bounding_box", "Bounding box", (0.45, 0.45, 0.50),
                   1.0, False, kind="wireframe"),
        SceneLayer("contours", "Contour template", (0.20, 0.45, 0.85),
                   1.0, False, lines=contour_lines, inferred=True,
                   kind="wireframe"),
        SceneLayer("axes", "Coordinate axes", (0.3, 0.3, 0.3), 1.0, True),
    ]

    # -- overall bounds + bounding-box layer -------------------------------
    pts: list[np.ndarray] = []
    for layer in model.layers:
        for mesh in layer.meshes:
            if not mesh.is_empty:
                pts.append(mesh.vertices)
        for line in layer.lines:
            pts.append(line.points)
        if layer.points is not None and len(layer.points):
            pts.append(layer.points)
    if pts:
        allv = np.vstack(pts)
        model.bounds_min = allv.min(axis=0)
        model.bounds_max = allv.max(axis=0)
        bbox = model.layer("bounding_box")
        if bbox is not None:
            bbox.lines = _bbox_lines(model.bounds_min, model.bounds_max)
    return model


# -- PyVista conversion (imported lazily by the Qt window) ------------------
def mesh_to_polydata(mesh: Mesh):
    import pyvista as pv

    if mesh.is_empty:
        return pv.PolyData()
    faces = np.hstack(
        [np.full((len(mesh.faces), 1), 3, dtype=np.int64), mesh.faces.astype(np.int64)]
    ).ravel()
    return pv.PolyData(mesh.vertices.astype(np.float64), faces)


def polyline_to_polydata(poly: PolyLine):
    import pyvista as pv

    pts = poly.points.astype(np.float64)
    if len(pts) < 2:
        return pv.PolyData()
    if poly.closed:
        pts = np.vstack([pts, pts[0]])
    cells = np.hstack([[len(pts)], np.arange(len(pts))])
    pd = pv.PolyData()
    pd.points = pts
    pd.lines = cells
    return pd


def points_to_polydata(points: np.ndarray):
    import pyvista as pv

    return pv.PolyData(points.astype(np.float64))
