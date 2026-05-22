"""Binary STL exporter."""
from __future__ import annotations

import struct

import numpy as np

from ..recon.mesh import Mesh, ReconResult


def _triangles(mesh: Mesh) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(facet_normals, triangle_vertices)`` for a mesh."""
    tris = mesh.vertices[mesh.faces].astype(np.float64)        # (F, 3, 3)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    return (normals / lengths), tris


def write_stl(result: ReconResult, path: str) -> str:
    """Write every mesh in ``result`` into a single binary STL file.

    STL has no object grouping; use :func:`write_stl_per_object` to keep the
    rough body and planned stones in separate files.
    """
    meshes = [m for m in result.meshes if not m.is_empty]
    _write_meshes(meshes, path)
    return path


def write_stl_per_object(result: ReconResult, directory: str, stem: str) -> list[str]:
    """Write one binary STL file per mesh; returns the written paths."""
    import os

    written: list[str] = []
    for mesh in result.meshes:
        if mesh.is_empty:
            continue
        out = os.path.join(directory, f"{stem}_{mesh.name}.stl")
        _write_meshes([mesh], out)
        written.append(out)
    return written


def _write_meshes(meshes: list[Mesh], path: str) -> None:
    facet_count = sum(len(m.faces) for m in meshes)
    with open(path, "wb") as fh:
        fh.write(b"ADV Planning Data Recovery STL export".ljust(80, b"\0"))
        fh.write(struct.pack("<I", facet_count))
        for mesh in meshes:
            if mesh.is_empty:
                continue
            normals, tris = _triangles(mesh)
            for n, tri in zip(normals, tris):
                fh.write(struct.pack("<3f", *n))
                fh.write(struct.pack("<3f", *tri[0]))
                fh.write(struct.pack("<3f", *tri[1]))
                fh.write(struct.pack("<3f", *tri[2]))
                fh.write(b"\0\0")
