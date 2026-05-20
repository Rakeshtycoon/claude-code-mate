"""Tests for body-block geometry discovery."""
import struct

from advkit.mesh.bodyscan import (
    scan_body_geometry,
    scan_face_buffers,
    scan_vertex_buffers,
)


def _vertex_buffer(n):
    """n float64 XYZ vertices with plausible coordinates."""
    coords = []
    for i in range(n):
        coords += [float(i % 100) * 1.5, -float(i % 70), float(i % 40) + 0.25]
    return struct.pack(f"<{n * 3}d", *coords)


def _face_buffer(n, max_index=500):
    """n triangles framed as [3][i0][i1][i2]."""
    out = bytearray()
    for i in range(n):
        out += struct.pack("<4I", 3, i % max_index,
                            (i + 1) % max_index, (i + 2) % max_index)
    return bytes(out)


def test_scan_vertex_buffers_finds_run():
    pad = b"\xff" * 64                       # non-coordinate noise
    blob = pad + _vertex_buffer(800) + pad
    buffers = scan_vertex_buffers(blob, 0, len(blob), min_vertices=256)
    assert len(buffers) == 1
    assert buffers[0].vertex_count == 800
    verts = buffers[0].read(blob)
    assert len(verts) == 800
    assert verts[0] == (0.0, -0.0, 0.25)


def test_scan_face_buffers_finds_triangles():
    pad = b"\x99" * 48
    blob = pad + _face_buffer(300) + pad
    buffers = scan_face_buffers(blob, 0, len(blob), min_triangles=64)
    assert len(buffers) == 1
    assert buffers[0].triangle_count == 300
    faces = buffers[0].read(blob)
    assert faces[0] == (0, 1, 2)


def test_face_scanner_rejects_coincidental_tag():
    # An isolated value 3 must not be mistaken for a face buffer.
    blob = struct.pack("<8I", 3, 1, 2, 3, 99999, 7, 3, 8)
    assert scan_face_buffers(blob, 0, len(blob), min_triangles=64) == []


def test_face_scanner_stops_at_out_of_range_index():
    good = _face_buffer(200)
    bad = struct.pack("<4I", 3, 9_999_999, 1, 2)  # index over the bound
    blob = good + bad + good
    buffers = scan_face_buffers(blob, 0, len(blob),
                                max_index=4_000_000, min_triangles=64)
    assert len(buffers) == 2
    assert all(b.triangle_count == 200 for b in buffers)


def test_scan_body_geometry_combines_and_serialises():
    import json
    blob = (b"\xff" * 32 + _vertex_buffer(600)
            + b"\xff" * 32 + _face_buffer(150))
    geom = scan_body_geometry(blob, 0, len(blob))
    assert geom.total_vertices == 600
    assert geom.total_triangles == 150
    assert geom.largest_vertex_buffer().vertex_count == 600
    assert geom.largest_face_buffer().triangle_count == 150
    json.dumps(geom.as_dict())


def test_assemble_surface_mesh():
    from advkit.mesh.bodyscan import assemble_surface_mesh

    # vertex pool (2400 verts) followed by a 1600-triangle face chunk
    pool = _vertex_buffer(2400)
    faces = _face_buffer(1600, max_index=2400)
    blob = b"\xff" * 64 + pool + b"\xff" * 8 + faces
    verts, tris = assemble_surface_mesh(blob, 0, len(blob))
    assert verts.shape[1] == 3
    assert tris.shape[1] == 3
    assert len(tris) > 0
    # every face index must be valid for the returned vertex array
    assert tris.max() < len(verts)


def test_extract_and_export_point_cloud(tmp_path):
    from advkit.mesh.bodyscan import export_point_cloud, extract_point_cloud

    # two vertex buffers, the second a duplicate of the first
    vb = _vertex_buffer(1500)
    blob = b"\xff" * 16 + vb + b"\xff" * 16 + vb
    cloud = extract_point_cloud(blob, 0, len(blob), min_vertices=1000, dedup=True)
    # 1500 distinct vertices, duplicate copy removed
    assert cloud.shape[1] == 3
    assert len(cloud) == len(set(map(tuple, cloud)))

    for ext in ("ply", "obj", "xyz"):
        path = tmp_path / f"cloud.{ext}"
        export_point_cloud(cloud, str(path))
        assert path.is_file() and path.stat().st_size > 0
