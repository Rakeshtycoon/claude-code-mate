"""Parametric brilliant-cut gemstone generator.

Turns planned-diamond proportion records into realistic faceted solids,
returned as :class:`advrecover.recon.mesh.Mesh` instances ready for
OBJ/STL export.
"""
from __future__ import annotations

from advrecover.gem.brilliant import round_brilliant
from advrecover.gem.cuts import (
    CUT_REGISTRY,
    STANDARD_ROUND_BRILLIANT,
    CutSpec,
)

__all__ = [
    "CutSpec",
    "STANDARD_ROUND_BRILLIANT",
    "CUT_REGISTRY",
    "round_brilliant",
]
