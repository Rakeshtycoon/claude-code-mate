"""adv2mesh - production-grade converter for proprietary .ADV diamond
planning files (Sarine Advisor / Galaxy rough-planning projects).

The package is organised as an extensible pipeline:

    container  -> low-level file/footer/chunk parsing
    chunks     -> typed chunk decoders (metadata, object directory)
    geometry   -> contour harvesting + mesh builders
    planes     -> cutting / saw plane extraction
    polished   -> planned polished diamond records
    units      -> physical unit estimation
    scene      -> scene-graph assembly
    exporters  -> OBJ / MTL / STL / glTF writers
    debug      -> pure-stdlib PNG debug visualisations
    pipeline   -> orchestration + logging

The format is undocumented; everything here was recovered by heuristic
reverse engineering. See RE_NOTES.md for the recovered specification.
"""

__version__ = "1.0.0"

from .pipeline import convert  # noqa: F401
