"""Physical unit estimation.

The .ADV file stores geometry in raw scanner units with no explicit
scale. We estimate units/mm by matching the extracted silhouette extent
to the carat-implied physical size of the rough stone.

Diamond density = 3.52 g/cm^3 ; 1 carat = 0.2 g.

This is an ESTIMATE (+/-30%): the extracted rough mesh is a partial
surface, so the absolute scale cannot be pinned precisely. The result
is metric, micron-scale - never inches (an inch scale would contradict
the carat weight by ~2 orders of magnitude).
"""
import math

DIAMOND_DENSITY = 3.52   # g/cm^3
CT_TO_GRAM = 0.2


def estimate_units(silhouette_extent, rough_weight_ct, assumed_longest_mm=None):
    """Return a unit-estimation report.

    silhouette_extent : largest coordinate span of the extracted geometry
    rough_weight_ct   : rough diamond weight in carats (from metadata)
    assumed_longest_mm: optional override for the stone's longest dimension
    """
    report = {
        "system": "metric (micron-scale raw units) - NOT inches",
        "confidence": "low (+/-30%) - rough mesh is a partial surface",
    }
    if not rough_weight_ct:
        report["note"] = "no rough weight in metadata; scale undetermined"
        return report

    vol_mm3 = rough_weight_ct * CT_TO_GRAM / DIAMOND_DENSITY * 1000.0
    # crude longest-dimension model: treat the rough as ~2x an equal-sided
    # solid of the same volume (rough crystals are typically elongated).
    if assumed_longest_mm is None:
        assumed_longest_mm = 2.0 * (vol_mm3 ** (1.0 / 3.0))

    units_per_mm = (silhouette_extent / assumed_longest_mm
                    if assumed_longest_mm else 0.0)
    report.update({
        "rough_weight_ct": rough_weight_ct,
        "rough_volume_mm3": round(vol_mm3, 3),
        "silhouette_extent_units": round(silhouette_extent, 1),
        "assumed_longest_dim_mm": round(assumed_longest_mm, 3),
        "estimated_units_per_mm": round(units_per_mm, 1),
        "estimated_micron_per_unit": (round(1000.0 / units_per_mm, 4)
                                      if units_per_mm else None),
    })
    return report
