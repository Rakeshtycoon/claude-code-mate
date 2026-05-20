"""Volumetric inclusion detection.

In an X-ray scan of a rough diamond the clean crystal is comparatively
bright/uniform while inclusions (carbon, cracks, clouds, "nash"/"jiram"/
"kapa" in trade terms) are darker, denser regions. The trade convention -
and this detector - treats *dark voxels enclosed by the stone* as defects.

Algorithm (classical, deterministic, no ML):
  1. Otsu threshold separates air (dark background) from stone (bright).
  2. The stone mask's holes are filled, giving the solid hull.
  3. ``hull AND NOT stone`` = dark voxels surrounded by stone = inclusions.
  4. 3D connected-component labelling groups them into discrete defects.

This neatly avoids the trap of a plain threshold, which cannot tell a dark
inclusion from the equally dark air outside the stone - the spatial
"enclosed by stone" test is what disambiguates them.

The result (:class:`InclusionResult`) is a clean serialisable hand-off to
the UI / future ML classifier (see ``docs/ROADMAP.md``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from advkit.core.log import get_logger

_log = get_logger("inclusion")


@dataclass
class Inclusion:
    """A single detected internal defect."""

    label: int
    voxel_count: int
    centroid: tuple[float, float, float]      # (z, y, x)
    bbox: tuple[int, int, int, int, int, int]  # (z0, y0, x0, z1, y1, x1)
    mean_intensity: float
    severity: str

    @property
    def extent(self) -> tuple[int, int, int]:
        z0, y0, x0, z1, y1, x1 = self.bbox
        return (z1 - z0, y1 - y0, x1 - x0)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "voxel_count": self.voxel_count,
            "centroid": [round(c, 2) for c in self.centroid],
            "bbox": list(self.bbox),
            "extent": list(self.extent),
            "mean_intensity": round(self.mean_intensity, 2),
            "severity": self.severity,
        }


@dataclass
class InclusionResult:
    """Full detection output - the hand-off contract to UI / AI layers."""

    body_threshold: int
    min_voxels: int
    inclusions: list[Inclusion] = field(default_factory=list)
    total_defect_voxels: int = 0
    body_voxels: int = 0

    @property
    def count(self) -> int:
        return len(self.inclusions)

    @property
    def defect_fraction(self) -> float:
        return self.total_defect_voxels / self.body_voxels if self.body_voxels else 0.0

    def as_dict(self) -> dict:
        return {
            "body_threshold": self.body_threshold,
            "min_voxels": self.min_voxels,
            "count": self.count,
            "body_voxels": self.body_voxels,
            "total_defect_voxels": self.total_defect_voxels,
            "defect_fraction": round(self.defect_fraction, 6),
            "inclusions": [i.as_dict() for i in self.inclusions],
        }


def _severity(voxel_count: int, body: int) -> str:
    frac = voxel_count / body if body else 0.0
    if frac > 1e-3:
        return "critical"
    if frac > 1e-4:
        return "major"
    if frac > 1e-5:
        return "minor"
    return "trace"


def otsu_threshold(volume: np.ndarray) -> int:
    """Otsu threshold separating background air from stone material.

    Runs on the full volume so the dark-background peak and the bright-stone
    peak are both present - that bimodality is exactly what Otsu needs.
    """
    from skimage.filters import threshold_otsu

    vmin, vmax = int(volume.min()), int(volume.max())
    if vmin == vmax:
        return vmin
    return int(threshold_otsu(volume.reshape(-1)))


def stone_mask(volume: np.ndarray, body_threshold: int) -> np.ndarray:
    """Boolean mask of bright stone material (before hole filling)."""
    return volume > body_threshold


def detect(volume: np.ndarray, body_threshold: int | None = None,
           min_voxels: int = 8, connectivity: int = 1,
           max_darkness: int | None = None) -> InclusionResult:
    """Detect inclusions in a ``(Z, Y, X)`` uint8 volume.

    ``body_threshold`` - air/stone split; ``None`` => Otsu.
    ``min_voxels``      - components smaller than this are discarded as noise.
    ``connectivity``    - 1 = 6-neighbour, 3 = 26-neighbour labelling.
    ``max_darkness``    - optional extra cut: only count enclosed voxels at or
                          below this intensity (rejects faint density noise).
    """
    if volume.ndim != 3:
        raise ValueError("inclusion detection expects a 3D volume")
    if body_threshold is None:
        body_threshold = otsu_threshold(volume)

    stone = stone_mask(volume, body_threshold)
    hull = ndimage.binary_fill_holes(stone)
    defect = hull & ~stone
    if max_darkness is not None:
        defect &= volume <= max_darkness

    structure = ndimage.generate_binary_structure(3, connectivity)
    labels, n = ndimage.label(defect, structure=structure)
    _log.info("body_threshold=%d -> hull=%d voxels, %d raw defect components",
              body_threshold, int(hull.sum()), n)

    result = InclusionResult(body_threshold=body_threshold,
                             min_voxels=min_voxels,
                             body_voxels=int(hull.sum()))
    if n == 0:
        return result

    sizes = ndimage.sum(np.ones_like(labels, dtype=np.int64), labels,
                        index=range(1, n + 1))
    objects = ndimage.find_objects(labels)
    centroids = ndimage.center_of_mass(defect, labels, index=range(1, n + 1))
    means = ndimage.mean(volume, labels, index=range(1, n + 1))

    for lbl in range(1, n + 1):
        count = int(sizes[lbl - 1])
        if count < min_voxels:
            continue
        sl = objects[lbl - 1]
        bbox = (sl[0].start, sl[1].start, sl[2].start,
                sl[0].stop, sl[1].stop, sl[2].stop)
        cz, cy, cx = centroids[lbl - 1]
        result.inclusions.append(
            Inclusion(
                label=lbl,
                voxel_count=count,
                centroid=(float(cz), float(cy), float(cx)),
                bbox=tuple(int(b) for b in bbox),
                mean_intensity=float(means[lbl - 1]),
                severity=_severity(count, result.body_voxels),
            )
        )
        result.total_defect_voxels += count

    result.inclusions.sort(key=lambda i: i.voxel_count, reverse=True)
    _log.info("kept %d inclusions (>= %d voxels)",
              result.count, min_voxels)
    return result


def label_volume(volume: np.ndarray, result: InclusionResult) -> np.ndarray:
    """Build a uint16 label volume for visualisation/overlay.

    Each kept inclusion keeps its detection id; 0 is background. This is the
    array a 3D viewer colour-maps on top of the transparent diamond body.
    """
    stone = stone_mask(volume, result.body_threshold)
    hull = ndimage.binary_fill_holes(stone)
    defect = hull & ~stone
    structure = ndimage.generate_binary_structure(3, 1)
    labels, _ = ndimage.label(defect, structure=structure)
    keep = [i.label for i in result.inclusions]
    mask = np.isin(labels, keep) if keep else np.zeros_like(labels, bool)
    return np.where(mask, labels, 0).astype(np.uint16)
