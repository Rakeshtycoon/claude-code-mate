"""Reconstruct a 3D voxel volume by stacking the internal X-ray slices.

The .adv container stores ~300 grayscale JPEG slices. Stacking them along
Z yields a volume suitable for inclusion detection and isosurface
extraction. Because a full-resolution stack (300 x 1280 x 1024) is large,
:meth:`SliceStack.build_volume` supports integer downsampling so callers
can work at an interactive resolution and only pay for full detail when
exporting.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from advkit.core.log import get_logger
from advkit.parsers.adv import AdvFile

_log = get_logger("volume")


@dataclass
class VolumeStats:
    shape: tuple[int, int, int]
    dtype: str
    voxel_count: int
    min: int
    max: int
    mean: float
    histogram: list[int]

    def as_dict(self) -> dict:
        return {
            "shape": list(self.shape),
            "dtype": self.dtype,
            "voxel_count": self.voxel_count,
            "min": self.min,
            "max": self.max,
            "mean": round(self.mean, 3),
        }


class SliceStack:
    """A lazily-decoded stack of X-ray slices from an :class:`AdvFile`."""

    def __init__(self, adv: AdvFile):
        self.adv = adv
        self.count = adv.slice_count
        # All slices share one geometry; take it from the first declared one.
        self.width = adv.slices[0].width if self.count else 0
        self.height = adv.slices[0].height if self.count else 0

    def decode_slice(self, index: int) -> np.ndarray:
        """Return slice ``index`` as a 2D ``uint8`` array (grayscale)."""
        img = self.adv.slice_image(index).convert("L")
        return np.asarray(img, dtype=np.uint8)

    def build_volume(self, downsample: int = 1,
                     z_range: tuple[int, int] | None = None) -> np.ndarray:
        """Assemble a ``(Z, Y, X)`` uint8 volume.

        ``downsample`` decimates every axis by that integer factor. Damaged
        slices (those that fail to decode) are interpolated from their
        neighbours so the volume stays geometrically consistent.
        """
        if self.count == 0:
            raise ValueError("no slices to stack")
        z0, z1 = z_range or (0, self.count)
        z_indices = list(range(z0, z1, downsample))
        out_h = self.height // downsample
        out_w = self.width // downsample
        volume = np.zeros((len(z_indices), out_h, out_w), dtype=np.uint8)

        missing: list[int] = []
        for out_z, z in enumerate(z_indices):
            try:
                plane = self.decode_slice(z)
            except Exception as exc:  # noqa: BLE001 - corruption handled below
                _log.warning("slice %d failed to decode (%s); will interpolate", z, exc)
                missing.append(out_z)
                continue
            if downsample > 1:
                plane = plane[::downsample, ::downsample]
            volume[out_z] = plane[:out_h, :out_w]

        self._fill_missing(volume, missing)
        _log.info("built volume %s (downsample=%d, %d interpolated)",
                  volume.shape, downsample, len(missing))
        return volume

    @staticmethod
    def _fill_missing(volume: np.ndarray, missing: list[int]) -> None:
        """Replace failed planes with the mean of nearest good neighbours."""
        n = volume.shape[0]
        for z in missing:
            lo = next((k for k in range(z - 1, -1, -1) if k not in missing), None)
            hi = next((k for k in range(z + 1, n) if k not in missing), None)
            if lo is not None and hi is not None:
                volume[z] = ((volume[lo].astype(np.uint16)
                              + volume[hi].astype(np.uint16)) // 2).astype(np.uint8)
            elif lo is not None:
                volume[z] = volume[lo]
            elif hi is not None:
                volume[z] = volume[hi]

    @staticmethod
    def stats(volume: np.ndarray) -> VolumeStats:
        hist = np.bincount(volume.reshape(-1), minlength=256)[:256]
        return VolumeStats(
            shape=tuple(int(d) for d in volume.shape),
            dtype=str(volume.dtype),
            voxel_count=int(volume.size),
            min=int(volume.min()),
            max=int(volume.max()),
            mean=float(volume.mean()),
            histogram=[int(h) for h in hist],
        )

    @staticmethod
    def normalize(volume: np.ndarray) -> np.ndarray:
        """Contrast-stretch a volume to the full 0..255 range."""
        lo, hi = int(volume.min()), int(volume.max())
        if hi <= lo:
            return volume.copy()
        scaled = (volume.astype(np.float64) - lo) * (255.0 / (hi - lo))
        return np.rint(scaled).clip(0, 255).astype(np.uint8)

    @staticmethod
    def save_raw(volume: np.ndarray, path: str) -> None:
        """Dump the volume as a headerless RAW file (uint8, Z-major)."""
        volume.tofile(path)

    @staticmethod
    def save_npy(volume: np.ndarray, path: str) -> None:
        np.save(path, volume)
