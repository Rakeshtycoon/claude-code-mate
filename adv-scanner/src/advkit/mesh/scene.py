"""Reconstruct a complete diamond model and export it to standard formats.

This assembles the deliverable the planning software visualises: the rough
diamond's outer surface plus its internal inclusions (rendered green by the
planner). Both are reconstructed from the container's 300 internal X-ray
slices:

* **body**       - isosurface of the segmented, hole-filled stone hull.
* **inclusions** - isosurface of the enclosed dark regions found by
  :mod:`advkit.inclusion.detector`.

The result is exported via :mod:`trimesh` to OBJ / PLY / STL / GLB, with
the body shown translucent white and the inclusions green so the output
matches what the planner shows on screen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh
from scipy import ndimage

from advkit.core.log import get_logger
from advkit.inclusion.detector import detect
from advkit.mesh.surface import Mesh
from advkit.parsers.adv import AdvFile
from advkit.volume.slices import SliceStack

_log = get_logger("scene")

_BODY_COLOR = [205, 215, 235, 110]   # translucent white-blue
_INCLUSION_COLOR = [40, 200, 60, 255]  # planner green


def _marching_cubes(mask: np.ndarray, smooth: float, step: int) -> Mesh | None:
    """Isosurface of a boolean mask, optionally Gaussian-pre-smoothed."""
    from skimage import measure

    if mask.sum() == 0:
        return None
    field = mask.astype(np.float32)
    if smooth > 0:
        field = ndimage.gaussian_filter(field, sigma=smooth)
    try:
        verts, faces, normals, _ = measure.marching_cubes(
            field, level=0.5, step_size=step)
    except (ValueError, RuntimeError):
        return None
    return Mesh(vertices=verts.astype(np.float32),
                faces=faces.astype(np.int64),
                normals=normals.astype(np.float32))


def _to_trimesh(mesh: Mesh, color) -> trimesh.Trimesh:
    tm = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces,
                          process=False)
    tm.visual.face_colors = color
    return tm


@dataclass
class DiamondModel:
    """A reconstructed rough diamond: outer hull + inclusion geometry."""

    body: Mesh
    inclusions: Mesh | None
    inclusion_count: int
    voxel_size: float
    source: str
    metadata: dict = field(default_factory=dict)

    @property
    def body_volume_voxels(self) -> int:
        return self.metadata.get("body_voxels", 0)

    def summary(self) -> dict:
        return {
            "source": self.source,
            "voxel_size": self.voxel_size,
            "body_vertices": self.body.vertex_count,
            "body_faces": self.body.face_count,
            "inclusion_count": self.inclusion_count,
            "inclusion_vertices": self.inclusions.vertex_count if self.inclusions else 0,
            "inclusion_faces": self.inclusions.face_count if self.inclusions else 0,
            **self.metadata,
        }

    def to_scene(self) -> trimesh.Scene:
        """Build a trimesh Scene (body translucent, inclusions green)."""
        geom = {"diamond_body": _scaled(self.body, self.voxel_size, _BODY_COLOR)}
        if self.inclusions is not None:
            geom["inclusions"] = _scaled(self.inclusions, self.voxel_size,
                                         _INCLUSION_COLOR)
        return trimesh.Scene(geom)


def _scaled(mesh: Mesh, voxel_size: float, color) -> trimesh.Trimesh:
    tm = _to_trimesh(mesh, color)
    if voxel_size != 1.0:
        tm.apply_scale(voxel_size)
    return tm


def build_diamond_model(adv: AdvFile, downsample: int = 2,
                        smooth: float = 1.0, step: int = 1,
                        min_inclusion_voxels: int = 8) -> DiamondModel:
    """Reconstruct the full diamond model from an open :class:`AdvFile`."""
    stack = SliceStack(adv)
    volume = stack.build_volume(downsample=downsample)
    _log.info("reconstructed volume %s for model build", volume.shape)

    result = detect(volume, min_voxels=min_inclusion_voxels)

    stone = volume > result.body_threshold
    hull = ndimage.binary_fill_holes(stone)
    body_mesh = _marching_cubes(hull, smooth, step)
    if body_mesh is None:
        raise ValueError("could not reconstruct an outer surface")

    defect = hull & ~stone
    structure = ndimage.generate_binary_structure(3, 1)
    labels, _ = ndimage.label(defect, structure=structure)
    keep = np.isin(labels, [i.label for i in result.inclusions])
    inclusion_mesh = _marching_cubes(keep, smooth * 0.6, step) if keep.any() else None

    return DiamondModel(
        body=body_mesh,
        inclusions=inclusion_mesh,
        inclusion_count=result.count,
        voxel_size=float(downsample),
        source=adv.path,
        metadata={
            "downsample": downsample,
            "body_threshold": result.body_threshold,
            "body_voxels": result.body_voxels,
            "defect_voxels": result.total_defect_voxels,
            "defect_fraction": round(result.defect_fraction, 6),
        },
    )


def export_model(model: DiamondModel, path: str) -> None:
    """Write the model to ``path``; format inferred from the extension.

    OBJ / PLY / GLB keep body and inclusions as separate coloured objects;
    STL is geometry-only so the two are merged.
    """
    ext = path.rsplit(".", 1)[-1].lower()
    scene = model.to_scene()
    if ext in ("glb", "gltf", "obj"):
        scene.export(path)
    elif ext == "ply":
        # PLY has no scene graph: concatenate with per-vertex colours.
        scene.dump(concatenate=True).export(path)
    elif ext == "stl":
        scene.dump(concatenate=True).export(path)
    else:
        raise ValueError(f"unsupported model format: .{ext} "
                         f"(use obj, ply, stl, glb)")
    _log.info("exported model -> %s", path)
