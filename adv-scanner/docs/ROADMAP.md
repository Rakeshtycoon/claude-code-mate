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
| Inclusion detection (Otsu + fill-holes + 3D CCL) | `inclusion.detector` | done |
| Isosurface extraction + STL/OBJ/PLY export | `mesh.surface` | done |
| `adv-analyzer` CLI | `tools.cli` | done |
| Test suite (41 tests, synthetic + real-file gated) | `tests/` | done |

This already satisfies the brief's **INITIAL TASK** in full: inspect the
binary, build a low-level parser, detect candidate sections, identify the
image/voxel blocks, ship a binary analysis tool, and produce this roadmap.

## Phase 1 — finish format decoding (next)

1. Decode the 30.5 MB body block (see `FORMAT.md §5`). Needs ≥3 more
   sample files to diff structurally. This is the **critical-path unknown**.
2. Map the remaining header u32 table (counts vs. offsets).
3. Decode the 1.6 MB intermediate block and the 148-byte trailer.
4. Formalise the layout as a [Kaitai Struct](https://kaitai.io) `.ksy`
   spec so other languages get a parser for free.

## Phase 2 — volume engine

- Voxel spacing calibration from the header `f64` scalar.
- 16-bit volume path; histogram-driven density normalisation.
- Slice alignment / registration before stacking.

## Phase 3 — surface engine

- Confirm whether the laser outer mesh lives in the body block; if so add a
  dedicated decoder. Otherwise treat the slice-stack isosurface as the hull.
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

- **Single sample.** Every `[CONFIRMED]` claim holds for one file. More
  samples are required before hard-coding any offset beyond the header.
- **Body block.** If it is the primary volumetric payload, Phase 2 cannot
  be fully realised until §5 is solved.
- The desktop GUI / GPU stack cannot be built or tested in a headless
  environment — it is intentionally scoped as a separate downstream effort.
