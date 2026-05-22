"""Parametric ("Path B") reconstruction from decoded planning elements.

Each ``Saw`` element is rendered as its cutting plane and each ``Pie``
element as its planned-stone orientation plane. Geometry comes straight from
the decoded records (normal + offset) — nothing is invented.
"""
from __future__ import annotations

import numpy as np

from ..format.constants import MICRONS_PER_MM
from ..format.elements import PlanningElement, parse_elements
from ..format.model import AdvDocument
from .mesh import Mesh, PolyLine, ReconResult


def _plane_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two orthonormal in-plane vectors for a given unit normal."""
    ref = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(normal, ref)
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    return u, v


def plane_mesh(element: PlanningElement, size: float, factor: float) -> Mesh:
    """Build a square quad mesh for one planning element's plane."""
    n = np.array(element.normal, dtype=np.float64)
    center = n * element.offset * factor
    u, v = _plane_basis(n)
    half = size / 2.0
    verts = np.array([
        center + half * (u + v),
        center + half * (-u + v),
        center + half * (-u - v),
        center + half * (u - v),
    ], dtype=np.float32)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    return Mesh(verts, faces, name=element.name).compute_normals()


def plane_outline(element: PlanningElement, size: float, factor: float) -> PolyLine:
    """Build the square outline polyline for one planning element's plane."""
    n = np.array(element.normal, dtype=np.float64)
    center = n * element.offset * factor
    u, v = _plane_basis(n)
    half = size / 2.0
    pts = np.array([
        center + half * (u + v),
        center + half * (-u + v),
        center + half * (-u - v),
        center + half * (u - v),
    ], dtype=np.float32)
    return PolyLine(points=pts, name=element.name, closed=True)


def reconstruct_planning(
    data: bytes,
    doc: AdvDocument,
    *,
    scale_to_mm: bool = True,
    plane_size_mm: float = 7.0,
    kinds: tuple[str, ...] = ("saw", "pie"),
    solution: str | None = None,
) -> ReconResult:
    """Reconstruct the planning model (cutting planes + planned stones).

    This is the parametric reconstruction: it does not need the encoded
    geometry blocks — only the decoded per-element records. Pass
    ``solution`` (e.g. ``"133"``) to render a single planning solution.
    """
    factor = 1.0 / MICRONS_PER_MM if scale_to_mm else 1.0
    size = plane_size_mm if scale_to_mm else plane_size_mm * MICRONS_PER_MM

    elements = [e for e in parse_elements(data, doc) if e.kind in kinds]
    if solution is not None:
        elements = [e for e in elements if e.solution == solution]
    result = ReconResult()
    if not elements:
        result.notes.append("no decodable Saw/Pie planning elements found")
        return result

    saws = sum(1 for e in elements if e.kind == "saw")
    pies = sum(1 for e in elements if e.kind == "pie")
    scope = f"solution {solution}" if solution else "all solutions"
    result.notes.append(
        f"parametric reconstruction ({scope}): {len(elements)} planning "
        f"elements ({saws} saw planes, {pies} planned stones)"
    )
    result.notes.append(f"units: {'mm' if scale_to_mm else 'micron'}; "
                        f"plane size {plane_size_mm} mm")

    for element in elements:
        result.meshes.append(plane_mesh(element, size, factor))
        result.contours.append(plane_outline(element, size, factor))
    return result


def list_solutions(data: bytes, doc: AdvDocument) -> dict[str, int]:
    """Return a mapping of planning-solution id -> element count."""
    counts: dict[str, int] = {}
    for element in parse_elements(data, doc):
        counts[element.solution] = counts.get(element.solution, 0) + 1
    return counts
