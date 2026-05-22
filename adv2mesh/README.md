# adv2mesh

Production-grade converter for proprietary **`.ADV`** diamond-planning
files (Sarine *Advisor* / *Galaxy* rough-planning projects) into open
3D formats: **OBJ · MTL · STL · glTF**.

Pure Python 3, **no third-party dependencies** (stdlib only).

## Usage

```bash
python -m adv2mesh INPUT.adv -o OUTDIR
```

Options:

| Flag | Effect |
|------|--------|
| `-o, --out DIR` | output directory (default `<input>_adv2mesh`) |
| `--no-loft` | export the rough as contour polylines instead of a lofted mesh |
| `--no-debug` | skip the orthographic debug PNG |
| `-v, --verbose` | DEBUG-level logging |

As a library:

```python
from adv2mesh import convert
report = convert("stone.adv", "out/")
```

## Outputs

```
<stem>.obj / .mtl     scene geometry + materials (world space)
<stem>.stl            binary STL, all triangles, world space
<stem>.gltf           glTF 2.0 — full node hierarchy + transforms
<stem>_metadata.json  container info, stone metadata, units, bboxes,
                      transforms, per-plane / per-polished tables
<stem>_debug.png      orthographic wireframe of the assembled scene
extraction.log        full per-run extraction log
```

## What gets extracted

| Object | Status |
|--------|--------|
| Rough diamond | ✅ float32 contour chain → lofted mesh |
| Cutting / saw planes | ✅ reference format; ⚠️ a known variant is unmatched |
| Planned polished diamonds | ✅ metadata + saw planes + bounding cage |
| Inclusions | ❌ inside a proprietary-compressed blob — only located |

## Architecture

```
container.py  file header + footer chunk table
chunks.py     typed chunk decoders (metadata, object directory)
geometry.py   contour harvesting + pluggable MeshBuilder
planes.py     cutting-plane extraction + frame solving
polished.py   planned polished diamond records
units.py      physical unit estimation
scene.py      scene-graph model + 4x4 transform helpers
exporters.py  OBJ / MTL / STL / glTF writers
debug.py      stdlib PNG visualiser
pipeline.py   orchestration + logging
cli.py        command-line interface
```

The pipeline is linear and stage-isolated; each extractor returns plain
data, so new chunk types, mesh builders, or exporters can be added in
isolation. See **`RE_NOTES.md`** for the recovered format specification.

## Limitations

- The format is undocumented; parsing is heuristic and calibrated
  against the reference file. A second sample exposed a cutting-plane
  layout variant that is not yet decoded (extractor degrades gracefully).
- Lofting per-angle silhouette contours twists the rough surface; a
  visual-hull builder is the correct fix (interface is in place).
- Inclusion geometry requires cracking the proprietary compression.
- Absolute scale is a ±30 % carat-based estimate.
