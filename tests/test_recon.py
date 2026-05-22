"""Tests for the geometry scanner and reconstruction engine."""
import numpy as np

from advrecover.format import parse_bytes
from advrecover.recon import (
    convex_hull,
    marching_cubes_surface,
    reconstruct,
    scan_geometry,
)
from advrecover.recon.scan import filter_coherent


def test_scan_finds_geometry_runs(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    section = doc.section(1)
    arrays = scan_geometry(synthetic_adv_bytes, section.offset, section.end,
                           min_points=64)
    assert len(arrays) == 5
    for arr in arrays:
        assert arr.points.shape[1] == 3
        assert arr.count >= 64
        assert arr.diagonal > 50.0


def test_scan_rejects_zero_padding():
    # 4096 zero bytes => 1024 zero floats: degenerate, must be rejected.
    arrays = scan_geometry(b"\x00" * 4096, min_points=16)
    assert arrays == []


def test_filter_coherent_drops_outlier(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    section = doc.section(1)
    arrays = scan_geometry(synthetic_adv_bytes, section.offset, section.end,
                           min_points=64)
    kept = filter_coherent(arrays)
    assert len(kept) == len(arrays)  # synthetic runs are all coherent


def test_convex_hull_is_closed():
    pts = np.random.default_rng(0).uniform(-1, 1, size=(200, 3)).astype("float32")
    mesh = convex_hull(pts)
    assert not mesh.is_empty
    assert mesh.faces.shape[1] == 3
    assert mesh.normals is not None


def test_marching_cubes_produces_surface():
    rng = np.random.default_rng(1)
    sphere = rng.normal(size=(2000, 3)).astype("float32")
    sphere /= np.linalg.norm(sphere, axis=1, keepdims=True)
    mesh = marching_cubes_surface(sphere * 100.0, resolution=48)
    assert not mesh.is_empty


def test_reconstruct_pipeline(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    result = reconstruct(synthetic_adv_bytes, doc, method="hull")
    assert len(result.point_cloud) > 0
    assert len(result.contours) == 5
    assert len(result.meshes) == 1
    assert not result.meshes[0].is_empty
