"""Tests for the parametric brilliant-cut gemstone generator."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pytest

from advrecover.gem import CUT_REGISTRY, STANDARD_ROUND_BRILLIANT, round_brilliant
from advrecover.gem.cuts import CutSpec
from advrecover.recon.mesh import Mesh


def _edge_use_counts(faces: np.ndarray) -> dict[tuple[int, int], int]:
    """Return how many triangles use each undirected edge."""
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            counts[(int(min(u, v)), int(max(u, v)))] += 1
    return counts


def test_returns_non_empty_triangle_mesh():
    mesh = round_brilliant(6.5)
    assert isinstance(mesh, Mesh)
    assert not mesh.is_empty
    assert mesh.faces.ndim == 2 and mesh.faces.shape[1] == 3
    assert mesh.vertices.shape[1] == 3
    assert len(mesh.faces) > 0


def test_mesh_is_manifold():
    """Every undirected edge must be shared by exactly two triangles."""
    mesh = round_brilliant(5.0)
    counts = _edge_use_counts(mesh.faces)
    bad = {e: c for e, c in counts.items() if c != 2}
    assert not bad, f"non-manifold edges (use-count != 2): {bad}"


def test_mesh_is_watertight_closed():
    """A closed solid has Euler characteristic V - E + F == 2."""
    mesh = round_brilliant(7.2)
    v = len(mesh.vertices)
    e = len(_edge_use_counts(mesh.faces))
    f = len(mesh.faces)
    assert v - e + f == 2, f"Euler characteristic V-E+F = {v - e + f}, expected 2"


def test_winding_is_consistent():
    """Each directed edge appears once -> consistent outward winding."""
    directed: dict[tuple[int, int], int] = defaultdict(int)
    mesh = round_brilliant(4.0)
    for a, b, c in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            directed[(int(u), int(v))] += 1
    assert all(n == 1 for n in directed.values())
    assert all(directed.get((v, u), 0) == 1 for (u, v) in directed)


@pytest.mark.parametrize("diameter", [2.0, 6.5, 12.3])
def test_scales_to_requested_diameter(diameter):
    mesh = round_brilliant(diameter)
    lo = mesh.vertices.min(axis=0)
    hi = mesh.vertices.max(axis=0)
    span_x = hi[0] - lo[0]
    span_y = hi[1] - lo[1]
    assert span_x == pytest.approx(diameter, rel=1e-3)
    assert span_y == pytest.approx(diameter, rel=1e-3)


def test_centred_with_table_up_and_culet_down():
    mesh = round_brilliant(6.0)
    lo = mesh.vertices.min(axis=0)
    hi = mesh.vertices.max(axis=0)
    # Centred on the origin in x/y.
    assert abs(lo[0] + hi[0]) < 1e-3
    assert abs(lo[1] + hi[1]) < 1e-3
    # Table above the girdle plane, culet below it.
    assert hi[2] > 0.0 > lo[2]


def test_default_spec_matches_registry():
    mesh = round_brilliant(5.0)
    assert mesh.name == "brilliant"
    assert CUT_REGISTRY["round_brilliant"] is STANDARD_ROUND_BRILLIANT


def test_cut_registry_contains_round_brilliant():
    assert "round_brilliant" in CUT_REGISTRY
    spec = CUT_REGISTRY["round_brilliant"]
    assert isinstance(spec, CutSpec)
    # Sane Tolkowsky-style proportions.
    assert 53.0 <= spec.table_pct <= 57.0
    assert 33.0 <= spec.crown_angle_deg <= 36.0
    assert 40.0 <= spec.pavilion_angle_deg <= 41.5
    assert spec.total_depth_pct > 0.0


def test_rejects_non_positive_diameter():
    with pytest.raises(ValueError):
        round_brilliant(0.0)
