"""Geometry discovery inside the ``.adv`` body block.

The ~15-32 MB block between the header and the X-ray slice run is a
serialized 3D scene. Diffing five sample files showed it carries the
laser-scanned **outer surface mesh** of the rough diamond:

* **vertex buffers** - long contiguous arrays of ``float64`` XYZ
  coordinates (values within roughly +/-30000, mixed sign => a centred
  model).
* **face buffers** - ``uint32`` triangle lists framed as
  ``[3][i0][i1][i2]`` (16 bytes/triangle; the constant ``3`` is the
  per-face vertex count).
* index/connectivity and ~1024-wide 16-bit raster regions also occur.

The exact per-object framing (counts, vertex/face pairing) is not yet
fully locked, so this module *discovers and reports candidate buffers*
rather than asserting a single definitive mesh. It is deliberately a
scanner, not a guesser - every buffer it returns is backed by a measured,
self-consistent byte pattern.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from advkit.core.log import get_logger

_log = get_logger("bodyscan")

# Plausible diamond vertex magnitude (microns). The lower bound rejects
# tiny denormals - crucially, packed uint32 index data reads as ~1e-320
# doubles, so without this bound a vertex scan would bleed into face
# buffers. A real coordinate is either exactly 0.0 or comfortably > 1e-3.
_COORD_MIN = 1.0e-3
_COORD_LIMIT = 3.0e4
_FACE_STRIDE = 16          # bytes per triangle: [3][i0][i1][i2]
_TRIANGLE_TAG = 3


def _is_coordinate(v: float) -> bool:
    return v == 0.0 or (math.isfinite(v) and _COORD_MIN <= abs(v) < _COORD_LIMIT)


@dataclass
class VertexBuffer:
    """A contiguous run of float64 XYZ coordinates."""

    offset: int
    end: int
    vertex_count: int

    @property
    def byte_size(self) -> int:
        return self.end - self.offset

    def read(self, buf) -> list[tuple[float, float, float]]:
        raw = bytes(buf[self.offset:self.offset + self.vertex_count * 24])
        flat = struct.unpack(f"<{self.vertex_count * 3}d", raw)
        return [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]

    def as_dict(self) -> dict:
        return {"offset": self.offset, "end": self.end,
                "vertex_count": self.vertex_count, "byte_size": self.byte_size}


@dataclass
class FaceBuffer:
    """A contiguous run of ``[3][i0][i1][i2]`` uint32 triangles."""

    offset: int
    end: int
    triangle_count: int
    max_index: int

    @property
    def byte_size(self) -> int:
        return self.end - self.offset

    def read(self, buf) -> list[tuple[int, int, int]]:
        faces = []
        for o in range(self.offset, self.end, _FACE_STRIDE):
            i0, i1, i2 = struct.unpack_from("<3I", bytes(buf[o + 4:o + 16]))
            faces.append((i0, i1, i2))
        return faces

    def as_dict(self) -> dict:
        return {"offset": self.offset, "end": self.end,
                "triangle_count": self.triangle_count,
                "max_index": self.max_index, "byte_size": self.byte_size}


def _u32(buf, o: int) -> int:
    return struct.unpack_from("<I", buf, o)[0]


def scan_face_buffers(buf, start: int, end: int, max_index: int = 4_000_000,
                      min_triangles: int = 64) -> list[FaceBuffer]:
    """Locate triangle-index buffers in ``buf[start:end]``.

    A face buffer is a maximal run of 16-byte records whose first u32 is the
    triangle tag ``3`` and whose three index u32s stay below ``max_index``
    (the bound rejects coincidental ``3`` bytes inside unrelated data).
    """
    out: list[FaceBuffer] = []
    i = start
    limit = end - _FACE_STRIDE
    while i <= limit:
        if _u32(buf, i) != _TRIANGLE_TAG:
            i += 4
            continue
        j = i
        run_max = 0
        while j <= limit and _u32(buf, j) == _TRIANGLE_TAG:
            a, b, c = _u32(buf, j + 4), _u32(buf, j + 8), _u32(buf, j + 12)
            if a > max_index or b > max_index or c > max_index:
                break
            run_max = max(run_max, a, b, c)
            j += _FACE_STRIDE
        tris = (j - i) // _FACE_STRIDE
        if tris >= min_triangles:
            out.append(FaceBuffer(i, j, tris, run_max))
            i = j
        else:
            i += 4
    _log.info("found %d face buffer(s) in [%d,%d]", len(out), start, end)
    return out


def scan_vertex_buffers(buf, start: int, end: int,
                        min_vertices: int = 256) -> list[VertexBuffer]:
    """Locate float64 XYZ coordinate arrays in ``buf[start:end]``.

    A vertex buffer is a maximal 8-byte-aligned run of finite doubles whose
    magnitude is a plausible coordinate (``< 3e4``). Runs are reported with
    a vertex count of ``len // 24`` (three doubles per vertex).
    """
    out: list[VertexBuffer] = []
    region = bytes(buf[start:end])
    n = len(region) // 8
    doubles = struct.unpack_from(f"<{n}d", region, 0)
    run_start = None
    for k in range(n + 1):
        ok = k < n and _is_coordinate(doubles[k])
        if ok and run_start is None:
            run_start = k
        elif not ok and run_start is not None:
            verts = (k - run_start) // 3
            if verts >= min_vertices:
                out.append(VertexBuffer(start + run_start * 8,
                                        start + (run_start + verts * 3) * 8,
                                        verts))
            run_start = None
    _log.info("found %d vertex buffer(s) in [%d,%d]", len(out), start, end)
    return out


@dataclass
class BodyGeometry:
    """Summary of geometry discovered in a body block."""

    vertex_buffers: list[VertexBuffer]
    face_buffers: list[FaceBuffer]

    @property
    def total_vertices(self) -> int:
        return sum(v.vertex_count for v in self.vertex_buffers)

    @property
    def total_triangles(self) -> int:
        return sum(f.triangle_count for f in self.face_buffers)

    def largest_vertex_buffer(self) -> VertexBuffer | None:
        return max(self.vertex_buffers, key=lambda v: v.vertex_count,
                   default=None)

    def largest_face_buffer(self) -> FaceBuffer | None:
        return max(self.face_buffers, key=lambda f: f.triangle_count,
                   default=None)

    def as_dict(self) -> dict:
        return {
            "vertex_buffer_count": len(self.vertex_buffers),
            "face_buffer_count": len(self.face_buffers),
            "total_vertices": self.total_vertices,
            "total_triangles": self.total_triangles,
            "vertex_buffers": [v.as_dict() for v in self.vertex_buffers],
            "face_buffers": [f.as_dict() for f in self.face_buffers],
        }


def scan_body_geometry(buf, start: int, end: int,
                       min_vertices: int = 256,
                       min_triangles: int = 64) -> BodyGeometry:
    """Run both scanners over a body block and return a combined report."""
    return BodyGeometry(
        vertex_buffers=scan_vertex_buffers(buf, start, end, min_vertices),
        face_buffers=scan_face_buffers(buf, start, end,
                                       min_triangles=min_triangles),
    )


def extract_point_cloud(buf, start: int, end: int,
                        min_vertices: int = 1000,
                        dedup: bool = True):
    """Extract every body-block vertex buffer as a single ``(N, 3)`` array.

    This is the most reliable geometry the body block yields: the laser
    scan's surface vertices as float64 XYZ. The container often stores the
    geometry twice, so ``dedup`` drops exact duplicate points.

    Returns a numpy ``float64`` array (requires numpy).
    """
    import numpy as np

    buffers = scan_vertex_buffers(buf, start, end, min_vertices)
    chunks = []
    for vb in buffers:
        raw = bytes(buf[vb.offset:vb.offset + vb.vertex_count * 24])
        chunks.append(np.frombuffer(raw, dtype="<f8").reshape(-1, 3))
    if not chunks:
        return np.empty((0, 3), dtype=np.float64)
    cloud = np.vstack(chunks)
    if dedup:
        cloud = np.unique(cloud, axis=0)
    _log.info("extracted point cloud: %d vertices from %d buffer(s)",
              len(cloud), len(buffers))
    return cloud


def export_point_cloud(cloud, path: str) -> None:
    """Write an ``(N, 3)`` point cloud to PLY / OBJ / XYZ."""
    import numpy as np
    import trimesh

    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "xyz":
        np.savetxt(path, cloud, fmt="%.6f")
    elif ext == "obj":
        with open(path, "w", encoding="ascii") as fh:
            fh.write("# advkit body-block vertex cloud\n")
            for v in cloud:
                fh.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    elif ext == "ply":
        trimesh.PointCloud(cloud).export(path)
    else:
        raise ValueError(f"unsupported point-cloud format: .{ext} "
                         f"(use ply, obj, xyz)")
    _log.info("exported point cloud -> %s", path)
