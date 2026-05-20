"""Automated structure discovery for undecoded raw regions.

The .adv container's leading ~32 MB block is uncompressed, high-entropy and
not yet positively typed. This module provides the brute-force tooling to
narrow it down: it tests candidate image/voxel dimensions by exploiting the
fact that real imagery has strong correlation between adjacent rows, while
a wrong stride destroys that correlation.

Nothing here asserts a definitive answer - it produces ranked, scored
hypotheses for an analyst (or a future automated stage) to confirm.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from advkit.core.log import get_logger

_log = get_logger("discover")


@dataclass
class DimensionGuess:
    width: int
    bytes_per_pixel: int
    row_correlation: float
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "width": self.width,
            "bytes_per_pixel": self.bytes_per_pixel,
            "row_correlation": round(self.row_correlation, 4),
            "note": self.note,
        }


def _row_correlation(rows: np.ndarray) -> float:
    """Mean Pearson correlation between consecutive rows of a 2D array."""
    if rows.shape[0] < 2:
        return 0.0
    a = rows[:-1].astype(np.float64)
    b = rows[1:].astype(np.float64)
    a -= a.mean(axis=1, keepdims=True)
    b -= b.mean(axis=1, keepdims=True)
    num = (a * b).sum(axis=1)
    den = np.sqrt((a * a).sum(axis=1) * (b * b).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.where(den > 0, num / den, 0.0)
    return float(np.nanmean(np.abs(corr)))


def brute_force_dimensions(block: bytes, min_width: int = 64,
                           max_width: int = 4096,
                           bytes_per_pixel: tuple[int, ...] = (1, 2),
                           sample_rows: int = 512,
                           top: int = 8) -> list[DimensionGuess]:
    """Rank candidate image widths for a raw ``block``.

    For each (width, bpp) the leading bytes are reshaped into rows and the
    adjacent-row correlation is measured. A correct width produces a sharp
    correlation peak; wrong widths look like noise. Returns the ``top``
    highest-scoring hypotheses.
    """
    guesses: list[DimensionGuess] = []
    for bpp in bytes_per_pixel:
        dtype = np.uint8 if bpp == 1 else np.uint16
        arr = np.frombuffer(block, dtype=dtype)
        for width in range(min_width, max_width + 1):
            need = width * sample_rows
            if need > arr.size:
                rows_avail = arr.size // width
                if rows_avail < 8:
                    continue
                need = width * rows_avail
            rows = arr[:need].reshape(-1, width)
            corr = _row_correlation(rows)
            guesses.append(DimensionGuess(width, bpp, corr))
    guesses.sort(key=lambda g: g.row_correlation, reverse=True)
    for g in guesses[:top]:
        g.note = "strong adjacent-row correlation -> likely image stride"
    _log.info("dimension brute-force: best width=%d corr=%.3f",
              guesses[0].width if guesses else 0,
              guesses[0].row_correlation if guesses else 0.0)
    return guesses[:top]


@dataclass
class BlockProfile:
    """Coarse content classification of a raw region."""

    offset: int
    size: int
    entropy: float
    zero_fraction: float
    printable_fraction: float
    verdict: str

    def as_dict(self) -> dict:
        return {
            "offset": self.offset,
            "size": self.size,
            "entropy": round(self.entropy, 3),
            "zero_fraction": round(self.zero_fraction, 4),
            "printable_fraction": round(self.printable_fraction, 4),
            "verdict": self.verdict,
        }


def profile_block(block: bytes, offset: int = 0) -> BlockProfile:
    """Classify a raw block (padding / text / structured / raw / compressed)."""
    from advkit.parsers.inspector import shannon_entropy

    arr = np.frombuffer(block, dtype=np.uint8)
    entropy = shannon_entropy(block)
    zero_frac = float((arr == 0).mean()) if arr.size else 1.0
    printable = float(((arr >= 32) & (arr < 127)).mean()) if arr.size else 0.0

    if zero_frac > 0.9:
        verdict = "padding / sparse"
    elif printable > 0.85:
        verdict = "text / ascii records"
    elif entropy < 4.0:
        verdict = "structured binary (records/headers)"
    elif entropy < 7.5:
        verdict = "raw imagery or voxel data"
    else:
        verdict = "compressed/encoded or JPEG payload"
    return BlockProfile(offset, len(block), entropy, zero_frac, printable, verdict)
