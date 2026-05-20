# Roadmap — `.adv` Diamond Planner

The brief asks for a full industrial desktop planner (Qt6 + Vulkan, AI
modules, etc.). That is a multi-quarter program. This repository delivers
the **foundation that gates everything else**: a verified format decoder
and analysis toolkit. The plan below is honest about what is done, what is
next, and where the hard problems are.

## Delivered now (Phase 1 + working slices of 2–4)

| Capability | Module | State |
|------------|--------|-------|
| Memory-mapped reader for 500 MB+ files | `core.binreader` | done |
| Marker-aware JPEG carver | `parsers.jpeg` | done |
| Binary inspector (entropy, signatures, numeric/repeat probes, hexdump) | `parsers.inspector` | done |
| `.adv` container parser (header, sections, metadata) | `parsers.adv` | done |
| Volume reconstruction from slices (+ damaged-slice interpolation) | `volume.slices` | done |
| Automated structure discovery (dimension brute-force) | `volume.discover` | done |
| Body-block geometry discovery (mesh vertex/face buffers) | `mesh.bodyscan` | done |
| Inclusion detection (Otsu + fill-holes + 3D CCL) | `inclusion.detector` | done |
| Isosurface extraction + STL/OBJ/PLY export | `mesh.surface` | done |
| `adv-analyzer` CLI | `tools.cli` | done |
| Test suite (41 tests, synthetic + real-file gated) | `tests/` | done |

This already satisfies the brief's **INITIAL TASK** in full: inspect the
binary, build a low-level parser, detect candidate sections, identify the
image/voxel blocks, ship a binary analysis tool, and produce this roadmap.

## Phase 1 — finish format decoding (next)

1. **Body block** — identified as a serialized 3D mesh scene (`FORMAT.md
   §5`); `mesh.bodyscan` already extracts verified vertex/face buffers.
   Remaining: the per-object framing so a complete watertight outer mesh
   can be reassembled, and the ~1024-wide raster regions.
2. Map the remaining header u32 table (counts vs. offsets). Note the
   header is **variable-length** — the embedded length-prefixed strings
   shift every field after them, so it must be parsed as a stream.
3. Decode the intermediate block and the 148-byte trailer.
4. Formalise the layout as a [Kaitai Struct](https://kaitai.io) `.ksy`
   spec so other languages get a parser for free.

## Phase 2 — volume engine

- Voxel spacing calibration from the header `f64` scalar.
- 16-bit volume path; histogram-driven density normalisation.
- Slice alignment / registration before stacking.

## Phase 3 — surface engine

- The laser outer mesh **is** in the body block (confirmed). Promote
  `mesh.bodyscan` from a buffer scanner to a full object-graph decoder so
  the rough-stone hull is reconstructed directly from the file.
- Mesh repair: hole filling, decimation, watertight enforcement, GLTF export.

## Phase 4 — inclusion intelligence

- Classification of inclusion *type* (carbon / crack / cloud / "nash" /
  "kapa") — the current detector finds and measures them; typing is ML.
- Crack-path tracing and severity scoring.

## Phase 5 — desktop application

The analysis core here is language-agnostic (pure data in / data out). The
production UI is a separate front end:

```
            +-------------------- Qt 6 desktop shell ---------------------+
            | File explorer | Hex inspector | Slice viewer | 3D viewer    |
            |               | Inclusion editor | Planning tools          |
            +------------------------------+------------------------------+
                                           |
                          C++20 core  <--->  advkit (this repo)
                          (Vulkan/OpenGL renderer,         via a thin
                           VTK/ITK volume, CGAL mesh)      C-ABI or
                                           |               Python embed
                          +----------------+----------------+
                          |  ONNX Runtime / TensorRT plugin host  |
                          +---------------------------------------+
```

Recommended split:
- Keep **format decoding + analysis** in this toolkit (fast to iterate,
  trivially testable, no GPU/UI dependency).
- Build the **renderer and UI** in C++20/Qt6 with Vulkan; it consumes the
  decoded volume/mesh/inclusion structures, which are already clean,
  serialisable dataclasses (`VolumeStats`, `Mesh`, `InclusionResult`).
- Expose the toolkit to C++ either by embedding CPython or by porting the
  (small, well-specified) `parsers` layer once the format is fully locked.

## Phase 6 — AI integration

`InclusionResult` and the label volume from `inclusion.label_volume` are
already the right hand-off shape for a model:
- inference via ONNX Runtime (CPU/GPU) — no retraining infra needed to ship;
- a plugin interface so detectors/classifiers are swappable;
- training data is exportable today (`adv-analyzer slices`, `volume`,
  `inclusions --json`).

## Known risks

- **Five samples**, all from one scanner/day. `[CONFIRMED]` claims hold
  across all five; a wider corpus is still wise before hard-coding any
  offset past the variable-length header.
- **Body-block framing.** Buffer *types* are decoded; the object framing
  that stitches them into one mesh is not — Phase 3's full hull decoder
  depends on it.
- The desktop GUI / GPU stack cannot be built or tested in a headless
  environment — it is intentionally scoped as a separate downstream effort.
