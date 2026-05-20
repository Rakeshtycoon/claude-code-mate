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


def scan_vertex_segments(buf, start: int, end: int,
                         min_vertices: int = 256) -> list[VertexBuffer]:
    """Locate float64 XYZ coordinate runs at *any* byte alignment.

    The rough-stone vertex pool is split into several contiguous f64-XYZ
    segments joined by 6-byte separators, so successive segments sit at
    different byte alignments (see ``docs/FORMAT.md`` §5). A purely
    8-byte-aligned scan (:func:`scan_vertex_buffers`) only catches the
    segments that happen to land on the grid. This scans all eight phase
    offsets and merges the result, recovering the whole pool.
    """
    import numpy as np

    raw = bytes(buf[start:end])
    found: list[tuple[int, int]] = []
    for phase in range(8):
        n = (len(raw) - phase) // 8
        if n < min_vertices * 3:
            continue
        d = np.frombuffer(raw[phase:phase + n * 8], dtype="<f8")
        valid = np.isfinite(d) & (np.abs(d) < _COORD_LIMIT)
        flags = np.concatenate(([0], valid.view(np.int8), [0]))
        diff = np.diff(flags)
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        for rs, re in zip(starts, ends):
            verts = int(re - rs) // 3
            if verts >= min_vertices:
                found.append((start + phase + int(rs) * 8, verts))
    # keep the longest non-overlapping set (drops spurious cross-phase runs)
    found.sort(key=lambda s: -s[1])
    accepted: list[tuple[int, int]] = []
    for off, verts in found:
        seg_end = off + verts * 24
        if any(off < ae and seg_end > ao for ao, ae in accepted):
            continue
        accepted.append((off, seg_end))
    accepted.sort()
    out = [VertexBuffer(o, e, (e - o) // 24) for o, e in accepted]
    _log.info("found %d vertex segment(s) in [%d,%d] (any alignment)",
              len(out), start, end)
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


def _remove_outliers(cloud, k: int = 16, z: float = 3.0):
    """Statistical outlier removal: drop points whose mean distance to their
    ``k`` nearest neighbours is more than ``z`` MADs above the median.

    This strips the thin auxiliary geometry (measurement gizmos, axes) that
    is mixed into the body block, leaving the compact stone surface.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    if len(cloud) <= k:
        return cloud
    tree = cKDTree(cloud)
    dist, _ = tree.query(cloud, k=k + 1)
    mean_d = dist[:, 1:].mean(axis=1)
    med = np.median(mean_d)
    mad = np.median(np.abs(mean_d - med)) or 1.0
    keep = mean_d <= med + z * 1.4826 * mad
    return cloud[keep]


def extract_point_cloud(buf, start: int, end: int,
                        min_vertices: int = 256,
                        dedup: bool = True,
                        denoise: bool = False):
    """Extract every body-block vertex buffer as a single ``(N, 3)`` array.

    This is the most reliable geometry the body block yields: the laser
    scan's surface vertices as float64 XYZ. The container often stores the
    geometry twice, so ``dedup`` drops exact duplicate points; ``denoise``
    additionally removes statistical outliers (stray auxiliary geometry).

    Returns a numpy ``float64`` array (requires numpy).
    """
    import numpy as np

    buffers = scan_vertex_segments(buf, start, end, min_vertices)
    chunks = []
    for vb in buffers:
        raw = bytes(buf[vb.offset:vb.offset + vb.vertex_count * 24])
        chunks.append(np.frombuffer(raw, dtype="<f8").reshape(-1, 3))
    if not chunks:
        return np.empty((0, 3), dtype=np.float64)
    cloud = np.vstack(chunks)
    if dedup:
        cloud = np.unique(cloud, axis=0)
    if denoise:
        cloud = _remove_outliers(cloud)
    _log.info("extracted point cloud: %d vertices from %d buffer(s)",
              len(cloud), len(buffers))
    return cloud


def _walk_faces(buf, start: int, end: int, max_index: int = 200000):
    """Walk every 16-byte ``[3][i0][i1][i2]`` triangle; return (faces, first
    face offset). Tolerates the 14-byte chunk separators by re-syncing."""
    import numpy as np

    faces = []
    first = None
    o = start
    while o + 16 <= end:
        if (_u32(buf, o) == _TRIANGLE_TAG and _u32(buf, o + 4) < max_index
                and _u32(buf, o + 8) < max_index
                and _u32(buf, o + 12) < max_index):
            s = o
            chunk = []
            while o + 16 <= end and _u32(buf, o) == _TRIANGLE_TAG:
                a, b, c = _u32(buf, o + 4), _u32(buf, o + 8), _u32(buf, o + 12)
                if max(a, b, c) >= max_index:
                    break
                chunk.append((a, b, c))
                o += 16
            if len(chunk) >= 1500:
                if first is None:
                    first = s
                faces.extend(chunk)
            else:
                o = s + 4
        else:
            o += 4
    return np.array(faces, dtype=np.int64), first


def assemble_surface_mesh(buf, start: int, end: int,
                          vertex_window: int = 2_600_000):
    """Reconstruct the rough-diamond surface mesh from the body block.

    Strategy (see ``docs/FORMAT.md`` §5): the body block stores the mesh as
    a global ``float64`` XYZ vertex pool followed by ``uint32`` triangle
    chunks. The pool is interrupted by short separators that drift byte
    alignment, so it is recovered as the concatenation of every f64
    coordinate run (each trimmed to whole vertices) in the
    ``vertex_window`` bytes preceding the first triangle chunk. The pool
    ends immediately before the faces, so the *last* ``N`` vertices (with
    ``N`` = max triangle index + 1) are the ones the faces reference.

    Returns ``(vertices, faces)`` as numpy arrays. Best-effort: the result
    may contain triangulation artefacts where a separator could not be
    located exactly.
    """
    import numpy as np

    faces, first_face = _walk_faces(buf, start, end)
    if first_face is None or len(faces) == 0:
        return np.empty((0, 3)), np.empty((0, 3), dtype=np.int64)

    order = np.sort(faces.ravel())
    nverts = int(order[int(len(order) * 0.999)]) + 1  # robust to separator junk

    # Collect every f64 coordinate run in the window before the faces, at
    # ANY byte alignment (separators drift the alignment off the 8-byte
    # grid). Each run is trimmed to a whole number of vertices.
    region = bytes(buf[max(start, first_face - vertex_window):first_face])
    base = max(start, first_face - vertex_window)
    coords: list[float] = []
    pos = 0
    limit = len(region)
    while pos < limit - 8:
        n = 0
        while pos + n * 8 + 8 <= limit and _is_coordinate(
                struct.unpack_from("<d", region, pos + n * 8)[0]):
            n += 1
        if n >= 60:
            m = (n // 3) * 3
            coords.extend(struct.unpack_from(f"<{m}d", region, pos))
            pos += n * 8
        else:
            pos += 1
    pool = np.array(coords[:len(coords) // 3 * 3]).reshape(-1, 3)
    _ = base  # window base retained for clarity / future absolute offsets
    if len(pool) < nverts:
        return pool, faces[(faces < len(pool)).all(axis=1)]

    vertices = pool[-nverts:]
    faces = faces[(faces < nverts).all(axis=1)]
    _log.info("assembled surface mesh: %d vertices, %d faces",
              len(vertices), len(faces))
    return vertices, faces


def export_surface_mesh(buf, start: int, end: int, path: str) -> dict:
    """Assemble the body-block surface mesh and export it (PLY/OBJ/STL/GLB)."""
    import trimesh

    vertices, faces = assemble_surface_mesh(buf, start, end)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.export(path)
    _log.info("exported surface mesh -> %s", path)
    return {"vertices": len(mesh.vertices), "faces": len(mesh.faces),
            "watertight": bool(mesh.is_watertight)}


def export_hull_mesh(cloud, path: str, denoise: bool = True) -> dict:
    """Export the convex hull of the surface point cloud as a mesh.

    The exact triangle mesh stored in the body block could not be
    reconstructed - the face buffers do not pair cleanly with the vertex
    pool under any tested layout (see ``docs/FORMAT.md`` §5). The convex
    hull of the surface vertices is a clean, watertight **approximate**
    solid model of the rough stone; for a near-convex rough crystal it is
    a usable stand-in. Returns basic mesh statistics.
    """
    import trimesh

    pts = _remove_outliers(cloud) if denoise and len(cloud) > 32 else cloud
    hull = trimesh.Trimesh(vertices=pts).convex_hull
    hull.export(path)
    _log.info("exported convex-hull model -> %s", path)
    return {"vertices": int(len(hull.vertices)),
            "faces": int(len(hull.faces)),
            "volume": float(hull.volume),
            "area": float(hull.area),
            "watertight": bool(hull.is_watertight)}


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
