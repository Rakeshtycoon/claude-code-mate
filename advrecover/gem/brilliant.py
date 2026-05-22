"""Standard round-brilliant cut generator.

Builds a watertight, manifold triangle mesh of a round-brilliant-cut
gemstone from a :class:`~advrecover.gem.cuts.CutSpec`.

Facet layout (8-fold symmetric)
-------------------------------
* **Crown** — a flat table (octagon), 8 bezel/kite facets, 8 star facets
  and 16 upper-girdle facets.
* **Girdle** — a faceted band of 16 segments between the crown and the
  pavilion.
* **Pavilion** — 8 pavilion main facets, 16 lower-girdle facets, and a
  small culet facet (octagon) at the bottom.

The mesh is centred on the origin: the girdle plane sits at ``z ~= 0``,
the table faces ``+Z`` and the culet points to ``-Z``. The girdle width
(diameter) equals the requested ``diameter_mm``.

Every undirected edge is shared by exactly two triangles and the closed
solid satisfies the Euler characteristic ``V - E + F == 2``.
"""
from __future__ import annotations

import math

import numpy as np

from advrecover.gem.cuts import STANDARD_ROUND_BRILLIANT, CutSpec
from advrecover.recon.mesh import Mesh

#: Number of main facets around the stone (8-fold symmetry).
_N = 8


def _ring(radius: float, z: float, count: int, phase: float) -> np.ndarray:
    """Return ``count`` points on a circle of ``radius`` at height ``z``.

    ``phase`` is an angular offset in radians.
    """
    ang = phase + np.arange(count) * (2.0 * math.pi / count)
    xy = np.stack([np.cos(ang), np.sin(ang)], axis=1) * radius
    return np.column_stack([xy, np.full(count, z, dtype=np.float64)])


def round_brilliant(
    diameter_mm: float,
    spec: CutSpec | None = None,
    name: str = "brilliant",
) -> Mesh:
    """Generate a standard round-brilliant-cut gemstone mesh.

    Parameters
    ----------
    diameter_mm:
        Girdle diameter of the stone, in millimetres.
    spec:
        Cut proportions. Defaults to :data:`STANDARD_ROUND_BRILLIANT`.
    name:
        Name assigned to the returned :class:`Mesh`.

    Returns
    -------
    Mesh
        A watertight, manifold triangle mesh with outward-facing normals.
    """
    if spec is None:
        spec = STANDARD_ROUND_BRILLIANT
    if diameter_mm <= 0:
        raise ValueError("diameter_mm must be positive")

    # All proportions are percentages of the girdle diameter -> mm.
    scale = diameter_mm / 100.0
    r_girdle = 50.0 * scale                       # girdle radius
    r_table = (spec.table_pct / 2.0) * scale      # table radius
    r_culet = (spec.culet_pct / 2.0) * scale      # culet radius

    crown_h = spec.crown_height_pct * scale
    girdle_h = spec.girdle_pct * scale
    pav_d = spec.pavilion_depth_pct * scale

    # Heights, with the girdle band straddling z = 0.
    z_girdle_top = 0.5 * girdle_h
    z_girdle_bot = -0.5 * girdle_h
    z_table = z_girdle_top + crown_h
    z_culet = z_girdle_bot - pav_d

    # Star tips reach from the table edge toward the girdle; param along
    # the crown height. Lower-girdle tips reach from the girdle toward the
    # culet along the pavilion depth.
    star_t = max(0.0, min(1.0, spec.star_pct / 100.0))
    lg_t = max(0.0, min(1.0, spec.lower_girdle_pct / 100.0))

    # Angular phases. Table corners and girdle "corners" share a phase;
    # girdle "valleys" sit half a step away.
    half = math.pi / _N

    verts: list[np.ndarray] = []

    def add(points: np.ndarray) -> int:
        """Append a ring of points; return the start index."""
        start = sum(len(p) for p in verts)
        verts.append(points)
        return start

    # ---- crown ----------------------------------------------------------
    i_table_center = add(np.array([[0.0, 0.0, z_table]]))
    # Table-edge corners (octagon corners of the table).
    i_table = add(_ring(r_table, z_table, _N, 0.0))
    # Star tips: on the crown surface, between a table corner pair, pulled
    # partway down the crown toward a girdle valley.
    r_star = r_table + star_t * (r_girdle - r_table)
    z_star = z_table + star_t * (z_girdle_top - z_table)
    i_star = add(_ring(r_star, z_star, _N, half))
    # Girdle-top ring: 16 vertices (8 corners aligned with table corners,
    # 8 valleys aligned with star tips), all at the girdle top plane.
    i_gtop = add(_ring(r_girdle, z_girdle_top, 2 * _N, 0.0))

    # ---- girdle band ----------------------------------------------------
    i_gbot = add(_ring(r_girdle, z_girdle_bot, 2 * _N, 0.0))

    # ---- pavilion -------------------------------------------------------
    # Lower-girdle tips: on the pavilion surface, below a girdle valley.
    r_lg = r_girdle + lg_t * (r_culet - r_girdle)
    z_lg = z_girdle_bot + lg_t * (z_culet - z_girdle_bot)
    i_lg = add(_ring(r_lg, z_lg, _N, half))
    # Culet ring + culet centre.
    i_culet = add(_ring(r_culet, z_culet, _N, 0.0))
    i_culet_center = add(np.array([[0.0, 0.0, z_culet]]))

    vertices = np.vstack(verts).astype(np.float32)
    faces: list[tuple[int, int, int]] = []

    def tri(a: int, b: int, c: int) -> None:
        faces.append((a, b, c))

    # ---- table (flat octagon, fan from centre, +Z outward) --------------
    for k in range(_N):
        a = i_table + k
        b = i_table + (k + 1) % _N
        tri(i_table_center, a, b)

    # ---- crown facets ---------------------------------------------------
    # For each sector k there is:
    #   * a bezel (kite) facet between table corner k, table corner k+1,
    #     girdle corner k and girdle corner k+1 -- split into triangles
    #     through the star tip k and girdle valley.
    # We build the crown from table corners, star tips, girdle corners and
    # girdle valleys so that every edge is shared by exactly two faces.
    for k in range(_N):
        tc0 = i_table + k                       # table corner k
        tc1 = i_table + (k + 1) % _N            # table corner k+1
        st = i_star + k                         # star tip k (between them)
        gc0 = i_gtop + (2 * k)                  # girdle corner k
        gv = i_gtop + (2 * k + 1)               # girdle valley k
        gc1 = i_gtop + (2 * ((k + 1) % _N))     # girdle corner k+1

        # Star facet: shares the table outer edge, so its winding on that
        # edge is the reverse of the table fan -> (tc1, tc0, st).
        tri(tc1, tc0, st)
        # Bezel half toward corner k: table corner k, star tip, girdle
        # corner k  -> plus upper-girdle facet to the valley.
        tri(tc0, gc0, st)
        tri(st, gc0, gv)
        # Bezel half toward corner k+1.
        tri(tc1, st, gc1)
        tri(st, gv, gc1)

    # ---- girdle band (16 quads -> 32 triangles) -------------------------
    # Wound so the shared top edge runs opposite to the crown facets and
    # the shared bottom edge opposite to the pavilion facets.
    for k in range(2 * _N):
        a = i_gtop + k
        b = i_gtop + (k + 1) % (2 * _N)
        c = i_gbot + (k + 1) % (2 * _N)
        d = i_gbot + k
        tri(a, c, b)
        tri(a, d, c)

    # ---- pavilion facets ------------------------------------------------
    # Mirror of the crown: pavilion mains run from girdle corners to the
    # culet ring; lower-girdle facets fill toward the girdle valleys.
    for k in range(_N):
        gc0 = i_gbot + (2 * k)                  # girdle corner k
        gv = i_gbot + (2 * k + 1)               # girdle valley k
        gc1 = i_gbot + (2 * ((k + 1) % _N))     # girdle corner k+1
        lg = i_lg + k                           # lower-girdle tip k
        cc0 = i_culet + k                       # culet corner k
        cc1 = i_culet + (k + 1) % _N            # culet corner k+1

        # Lower-girdle facets: girdle corner -> valley -> lower-girdle tip.
        tri(gc0, lg, gv)
        tri(gv, lg, gc1)
        # Pavilion main halves: girdle corner -> lower-girdle tip -> culet.
        tri(gc0, cc0, lg)
        tri(gc1, lg, cc1)
        tri(lg, cc0, cc1)

    # ---- culet (flat octagon, fan from centre, -Z outward) --------------
    for k in range(_N):
        a = i_culet + k
        b = i_culet + (k + 1) % _N
        tri(i_culet_center, b, a)

    faces_arr = np.array(faces, dtype=np.int32)
    mesh = Mesh(vertices=vertices, faces=faces_arr, name=name)
    mesh.compute_normals()
    return mesh
