"""Round-trip and parser tests for the STL to STN converter."""

import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from stl_to_stn import convert, read_stl, write_stn
from stl_to_stn.converter import _is_binary_stl


def _build_binary_stl(triangles):
    """Build a binary STL byte string from (normal, v0, v1, v2) tuples."""
    header = b"binary-test".ljust(80, b"\x00")
    body = struct.pack("<I", len(triangles))
    for normal, v0, v1, v2 in triangles:
        body += struct.pack(
            "<12fH", *normal, *v0, *v1, *v2, 0
        )
    return header + body


ASCII_CUBE_FACE = """\
solid square
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 1 1 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 1 0
    vertex 0 1 0
  endloop
endfacet
endsolid square
"""


class DetectionTests(unittest.TestCase):
    def test_ascii_detection(self):
        self.assertFalse(_is_binary_stl(ASCII_CUBE_FACE.encode()))

    def test_binary_detection(self):
        data = _build_binary_stl(
            [
                ((0.0, 0.0, 1.0), (0, 0, 0), (1, 0, 0), (1, 1, 0)),
            ]
        )
        self.assertTrue(_is_binary_stl(data))


class AsciiParsingTests(unittest.TestCase):
    def test_two_triangles_share_vertices(self):
        mesh = read_stl(ASCII_CUBE_FACE.encode())
        self.assertEqual(mesh.triangle_count, 2)
        # Four unique vertices, not six (the two triangles share an edge).
        self.assertEqual(len(mesh.vertices), 4)
        for normal in mesh.normals:
            self.assertEqual(normal, (0.0, 0.0, 1.0))

    def test_malformed_ascii_raises(self):
        bad = "solid x\nfacet normal 0 0 1\nendsolid x\n"
        with self.assertRaises(ValueError):
            read_stl(bad.encode())


class BinaryParsingTests(unittest.TestCase):
    def test_round_trip(self):
        triangles = [
            (
                (0.0, 0.0, 1.0),
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
            ),
            (
                (0.0, 0.0, 1.0),
                (0.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 0.0),
            ),
        ]
        mesh = read_stl(_build_binary_stl(triangles))
        self.assertEqual(mesh.triangle_count, 2)
        self.assertEqual(len(mesh.vertices), 4)

    def test_truncated_binary_raises(self):
        data = _build_binary_stl(
            [
                (
                    (0.0, 0.0, 1.0),
                    (0.0, 0.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (1.0, 1.0, 0.0),
                ),
            ]
        )
        with self.assertRaises(ValueError):
            read_stl(data[:-10])


class StnOutputTests(unittest.TestCase):
    def test_write_to_stream_is_valid_json(self):
        mesh = read_stl(ASCII_CUBE_FACE.encode())
        buf = io.StringIO()
        write_stn(mesh, buf, source_name="square.stl", pretty=True)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["format"], "STN")
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["source"], "square.stl")
        self.assertEqual(payload["triangle_count"], 2)
        self.assertEqual(len(payload["vertices"]), 4)
        self.assertEqual(len(payload["triangles"]), 2)

    def test_convert_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            stl = tmp_path / "in.stl"
            stn = tmp_path / "out.stn"
            stl.write_bytes(ASCII_CUBE_FACE.encode())
            mesh = convert(stl, stn)
            self.assertTrue(stn.exists())
            payload = json.loads(stn.read_text())
            self.assertEqual(payload["triangle_count"], mesh.triangle_count)


if __name__ == "__main__":
    unittest.main()
