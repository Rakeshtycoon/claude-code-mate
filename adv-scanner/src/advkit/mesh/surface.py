"""Isosurface extraction and mesh export.

Given a reconstructed voxel volume (from :mod:`advkit.volume.slices`), this
module extracts a triangulated surface with marching cubes and writes it to
the common interchange formats. It serves both the rough-stone outer hull
and inclusion surfaces - the caller just supplies the volume and iso level.

Mesh writers are dependency-free; only the marching-cubes step uses
scikit-image.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np

from advkit.core.log import get_logger

_log = get_logger("mesh")


@dataclass
class Mesh:
    """A triangle mesh: ``vertices`` (V,3) float32, ``faces`` (F,3) int."""

    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray | None = None

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def face_count(self) -> int:
        return len(self.faces)

    def is_watertight(self) -> bool:
        """True if every edge is shared by exactly two triangles."""
        from collections import Counter
        edges: Counter = Counter()
        for a, b, c in self.faces:
            for u, v in ((a, b), (b, c), (c, a)):
                edges[(min(u, v), max(u, v))] += 1
        return bool(edges) and all(v == 2 for v in edges.values())


def extract_surface(volume: np.ndarray, iso_level: float | None = None,
                    step: int = 1) -> Mesh:
    """Marching-cubes isosurface of ``volume`` at ``iso_level``.

    ``iso_level`` defaults to the midpoint between the volume's min and max.
    ``step`` decimates the marching-cubes grid for a lighter mesh.
    """
    from skimage import measure

    if iso_level is None:
        iso_level = float(volume.min() + volume.max()) / 2.0
    verts, faces, normals, _ = measure.marching_cubes(
        volume.astype(np.float32), level=iso_level, step_size=step
    )
    _log.info("isosurface @%.1f: %d verts, %d faces",
              iso_level, len(verts), len(faces))
    return Mesh(vertices=verts.astype(np.float32),
                faces=faces.astype(np.int64),
                normals=normals.astype(np.float32))


# -- exporters ------------------------------------------------------------
def write_obj(mesh: Mesh, path: str) -> None:
    with open(path, "w", encoding="ascii") as fh:
        fh.write("# advkit OBJ export\n")
        for v in mesh.vertices:
            fh.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        if mesh.normals is not None:
            for nrm in mesh.normals:
                fh.write(f"vn {nrm[0]:.6f} {nrm[1]:.6f} {nrm[2]:.6f}\n")
        for f in mesh.faces:  # OBJ is 1-indexed
            fh.write(f"f {f[0] + 1} {f[1] + 1} {f[2] + 1}\n")


def write_ply(mesh: Mesh, path: str) -> None:
    with open(path, "wb") as fh:
        header = (
            "ply\nformat binary_little_endian 1.0\n"
            f"element vertex {mesh.vertex_count}\n"
            "property float x\nproperty float y\nproperty float z\n"
            f"element face {mesh.face_count}\n"
            "property list uchar int vertex_indices\n"
            "end_header\n"
        )
        fh.write(header.encode("ascii"))
        fh.write(mesh.vertices.astype("<f4").tobytes())
        for f in mesh.faces:
            fh.write(struct.pack("<B3i", 3, int(f[0]), int(f[1]), int(f[2])))


def write_stl(mesh: Mesh, path: str) -> None:
    """Write a binary STL (per-facet normals computed from the geometry)."""
    v = mesh.vertices
    with open(path, "wb") as fh:
        fh.write(b"advkit binary STL".ljust(80, b"\x00"))
        fh.write(struct.pack("<I", mesh.face_count))
        for f in mesh.faces:
            p0, p1, p2 = v[f[0]], v[f[1]], v[f[2]]
            nrm = np.cross(p1 - p0, p2 - p0)
            norm = np.linalg.norm(nrm)
            nrm = nrm / norm if norm else nrm
            fh.write(struct.pack("<3f", *nrm))
            fh.write(struct.pack("<3f", *p0))
            fh.write(struct.pack("<3f", *p1))
            fh.write(struct.pack("<3f", *p2))
            fh.write(b"\x00\x00")


_WRITERS = {"obj": write_obj, "ply": write_ply, "stl": write_stl}


def export_mesh(mesh: Mesh, path: str) -> None:
    """Dispatch to the writer matching ``path``'s extension."""
    ext = path.rsplit(".", 1)[-1].lower()
    writer = _WRITERS.get(ext)
    if writer is None:
        raise ValueError(f"unsupported mesh format: .{ext} "
                          f"(supported: {', '.join(sorted(_WRITERS))})")
    writer(mesh, path)
    _log.info("wrote %s", path)
