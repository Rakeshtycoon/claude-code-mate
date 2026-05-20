"""Tests for isosurface extraction and mesh export."""
import struct

import numpy as np
import pytest

from advkit.mesh.surface import Mesh, export_mesh, extract_surface


def _cube_volume():
    vol = np.zeros((30, 30, 30), dtype=np.uint8)
    vol[8:22, 8:22, 8:22] = 255
    return vol


def test_extract_surface_produces_triangles():
    mesh = extract_surface(_cube_volume(), iso_level=128)
    assert mesh.vertex_count > 0
    assert mesh.face_count > 0
    assert mesh.faces.shape[1] == 3


def test_export_obj(tmp_path):
    mesh = extract_surface(_cube_volume(), iso_level=128)
    path = tmp_path / "m.obj"
    export_mesh(mesh, str(path))
    text = path.read_text()
    assert text.count("\nv ") + text.startswith("v ") >= 1
    assert "\nf " in text


def test_export_stl_binary_header_and_count(tmp_path):
    mesh = extract_surface(_cube_volume(), iso_level=128)
    path = tmp_path / "m.stl"
    export_mesh(mesh, str(path))
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    assert count == mesh.face_count
    assert len(raw) == 84 + count * 50


def test_export_ply_roundtrip_vertex_count(tmp_path):
    mesh = extract_surface(_cube_volume(), iso_level=128)
    path = tmp_path / "m.ply"
    export_mesh(mesh, str(path))
    head = path.read_bytes()[:256].decode("ascii", "replace")
    assert f"element vertex {mesh.vertex_count}" in head


def test_unsupported_format_raises(tmp_path):
    mesh = Mesh(vertices=np.zeros((3, 3), np.float32),
                faces=np.array([[0, 1, 2]]))
    with pytest.raises(ValueError):
        export_mesh(mesh, str(tmp_path / "m.xyz"))


def test_watertight_detection():
    # A single triangle cannot be watertight.
    mesh = Mesh(vertices=np.zeros((3, 3), np.float32),
                faces=np.array([[0, 1, 2]]))
    assert mesh.is_watertight() is False
