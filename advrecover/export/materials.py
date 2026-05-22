"""Material presets for exported geometry groups.

Colours mirror the original Advisor visualisation: a translucent rough body,
yellow planned stones and saw planes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Material:
    name: str
    diffuse: tuple[float, float, float]
    alpha: float = 1.0


ROUGH = Material("rough", (0.78, 0.62, 0.66), alpha=0.35)
POLISHED = Material("polished", (0.95, 0.85, 0.30), alpha=0.85)
SAW_PLANE = Material("saw_plane", (0.30, 0.80, 0.45), alpha=0.55)
INCLUSION = Material("inclusion", (0.85, 0.20, 0.20), alpha=1.0)
CONTOUR = Material("contour", (0.20, 0.45, 0.85), alpha=1.0)
DEFAULT = Material("default", (0.70, 0.70, 0.72), alpha=1.0)

ALL = [ROUGH, POLISHED, SAW_PLANE, INCLUSION, CONTOUR, DEFAULT]


def material_for(name: str) -> Material:
    """Pick a material from an object name (best-effort until classified)."""
    lowered = name.lower()
    if "rough" in lowered or "envelope" in lowered or lowered.startswith("cluster_00"):
        return ROUGH
    if "pie" in lowered or "polish" in lowered or "cluster_" in lowered:
        return POLISHED
    if "saw" in lowered or "plane" in lowered:
        return SAW_PLANE
    if "inclusion" in lowered or "crack" in lowered:
        return INCLUSION
    if "contour" in lowered:
        return CONTOUR
    return DEFAULT


def write_mtl(path: str) -> None:
    """Write a Wavefront ``.mtl`` library with every preset material."""
    lines: list[str] = ["# ADV Planning Data Recovery - material library", ""]
    for mat in ALL:
        r, g, b = mat.diffuse
        lines += [
            f"newmtl {mat.name}",
            f"Kd {r:.4f} {g:.4f} {b:.4f}",
            f"Ka {r * 0.2:.4f} {g * 0.2:.4f} {b * 0.2:.4f}",
            "Ks 0.30 0.30 0.30",
            "Ns 32.0",
            f"d {mat.alpha:.3f}",
            "",
        ]
    with open(path, "w", encoding="ascii") as fh:
        fh.write("\n".join(lines))
