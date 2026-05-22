"""Cut specifications for parametric gemstone generation.

A :class:`CutSpec` holds the standard proportion set used to describe a
round-brilliant-style cut. All linear proportions are expressed as a
*percentage of the girdle diameter*; angles are in degrees.

The :data:`CUT_REGISTRY` maps cut-family names to presets so new cut
families can be added without touching generator code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CutSpec:
    """Proportions of a brilliant-style cut.

    Attributes
    ----------
    table_pct:
        Table-facet diameter as a percentage of the girdle diameter.
    crown_angle_deg:
        Angle of the crown main (bezel) facets from the girdle plane.
    pavilion_angle_deg:
        Angle of the pavilion main facets from the girdle plane.
    girdle_pct:
        Girdle-band thickness as a percentage of the girdle diameter.
    star_pct:
        Star-facet length: how far the star points reach from the table
        edge toward the girdle, as a percentage of the crown-height span.
    lower_girdle_pct:
        Lower-girdle-facet length: how far the lower-girdle facets reach
        from the girdle toward the culet, as a percentage of the
        pavilion-depth span.
    culet_pct:
        Culet diameter as a percentage of the girdle diameter
        (``0`` produces a single culet point).
    """

    table_pct: float
    crown_angle_deg: float
    pavilion_angle_deg: float
    girdle_pct: float
    star_pct: float
    lower_girdle_pct: float
    culet_pct: float

    # --- derived geometry ------------------------------------------------
    @property
    def crown_height_pct(self) -> float:
        """Crown height as a percentage of girdle diameter."""
        # The bezel facet rises from the girdle edge (radius 50%) to the
        # table edge (radius table_pct/2) at ``crown_angle_deg``.
        radial = (100.0 - self.table_pct) / 2.0
        return radial * math.tan(math.radians(self.crown_angle_deg))

    @property
    def pavilion_depth_pct(self) -> float:
        """Pavilion depth as a percentage of girdle diameter."""
        # The pavilion main drops from the girdle edge (radius 50%) to the
        # culet (radius culet_pct/2) at ``pavilion_angle_deg``.
        radial = (100.0 - self.culet_pct) / 2.0
        return radial * math.tan(math.radians(self.pavilion_angle_deg))

    @property
    def total_depth_pct(self) -> float:
        """Total stone depth (table to culet) as a percentage of diameter."""
        return self.crown_height_pct + self.girdle_pct + self.pavilion_depth_pct


#: Tolkowsky-style ideal round-brilliant proportions.
STANDARD_ROUND_BRILLIANT = CutSpec(
    table_pct=56.0,
    crown_angle_deg=34.5,
    pavilion_angle_deg=40.75,
    girdle_pct=3.0,
    star_pct=50.0,
    lower_girdle_pct=75.0,
    culet_pct=0.7,
)


#: Maps cut-family name -> :class:`CutSpec`. Extend with new families here.
CUT_REGISTRY: dict[str, CutSpec] = {
    "round_brilliant": STANDARD_ROUND_BRILLIANT,
}


def get_spec(name: str) -> CutSpec:
    """Look up a cut spec by family name.

    Raises
    ------
    KeyError
        If ``name`` is not a registered cut family.
    """
    try:
        return CUT_REGISTRY[name]
    except KeyError:  # pragma: no cover - defensive
        known = ", ".join(sorted(CUT_REGISTRY))
        raise KeyError(f"unknown cut family {name!r}; known: {known}") from None
