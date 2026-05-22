"""Wavefront OBJ exporter with per-object groups and an MTL library."""
from __future__ import annotations

import os

import numpy as np

from ..recon.mesh import ReconResult
from .materials import material_for, write_mtl


def write_obj(
    result: ReconResult,
    path: str,
    *,
    write_materials: bool = True,
    include_contours: bool = True,
    include_point_cloud: bool = False,
) -> str:
    """Write a :class:`ReconResult` to an OBJ file.

    Each mesh and contour becomes its own ``o`` group so the rough body,
    planned stones and saw planes stay separable in any CAD tool.
    """
    lines: list[str] = ["# ADV Planning Data Recovery - OBJ export"]
    mtl_path = os.path.splitext(path)[0] + ".mtl"
    if write_materials:
        write_mtl(mtl_path)
        lines.append(f"mtllib {os.path.basename(mtl_path)}")
    lines.append("")

    vertex_base = 1  # OBJ indices are 1-based

    for mesh in result.meshes:
        if mesh.is_empty:
            continue
        lines.append(f"o {mesh.name}")
        lines.append(f"usemtl {material_for(mesh.name).name}")
        for vx, vy, vz in mesh.vertices:
            lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
        if mesh.normals is not None:
            for nx, ny, nz in mesh.normals:
                lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
            for a, b, c in mesh.faces:
                ia, ib, ic = a + vertex_base, b + vertex_base, c + vertex_base
                lines.append(f"f {ia}//{ia} {ib}//{ib} {ic}//{ic}")
        else:
            for a, b, c in mesh.faces:
                lines.append(f"f {a + vertex_base} {b + vertex_base} {c + vertex_base}")
        vertex_base += len(mesh.vertices)
        lines.append("")

    if include_contours:
        for poly in result.contours:
            if len(poly.points) < 2:
                continue
            lines.append(f"o {poly.name}")
            lines.append(f"usemtl {material_for(poly.name).name}")
            for px, py, pz in poly.points:
                lines.append(f"v {px:.6f} {py:.6f} {pz:.6f}")
            count = len(poly.points)
            idx = [str(vertex_base + k) for k in range(count)]
            if poly.closed:
                idx.append(idx[0])
            lines.append("l " + " ".join(idx))
            vertex_base += count
            lines.append("")

    if include_point_cloud and len(result.point_cloud):
        lines.append("o point_cloud")
        for px, py, pz in result.point_cloud:
            lines.append(f"v {px:.6f} {py:.6f} {pz:.6f}")
        vertex_base += len(result.point_cloud)
        lines.append("")

    with open(path, "w", encoding="ascii") as fh:
        fh.write("\n".join(lines))
    return path
