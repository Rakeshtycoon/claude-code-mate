# ADV Planning Data Recovery

A reverse-engineering converter and 3D viewer for **OctoNus Advisor `.ADV`
diamond planning files**. It parses the proprietary `.ADV` container,
extracts geometry, metadata and embedded previews, reconstructs a 3D model
and exports it to **OBJ** and **STL**.

> Project codename: *Planning Data Recovery*. The repository name
> (`claude-code-mate`) predates the project.

## Status — v0.1

This is an **honest, evidence-based** reverse-engineering effort. Nothing is
faked: every extracted value traces to bytes in the file, and the format
specification (`docs/ADV_FORMAT.md`) marks each field `VERIFIED` or
`HYPOTHESIS`.

| Capability | State |
|------------|-------|
| Container header / end directory / sections | **Verified** on real samples |
| Metadata (stone id, plan code, scan mode, timestamp, UUID) | **Verified** |
| Planning tree (`Saw*` / `Pie*` element names) | **Verified** |
| Embedded JPEG preview extraction | **Verified** (200+ images/file) |
| Float32 XYZ geometry recovery | **Working** — real coordinate arrays |
| Surface reconstruction (hull / marching cubes) | **Working** |
| OBJ / STL / MTL export | **Working** |
| Qt + PyVista desktop viewer | **Built** (needs a GPU/display to run) |
| Exact match to the original visualisation | **In progress** — see below |

The geometry recovered so far is real, but the *semantics* (which arrays are
the rough body vs. planned stones vs. saw planes, and any per-element
transforms) are still being reverse-engineered. The two highest-value next
targets are documented in `docs/ADV_FORMAT.md` §6–7.

## Install

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Command-line usage

```bash
python -m advrecover info     stone.adv          # parsed container structure
python -m advrecover tree     stone.adv          # structure as a tree
python -m advrecover probe    stone.adv          # reverse-engineering diagnostics
python -m advrecover segment  stone.adv --ranked # entropy block map, geometry-ranked
python -m advrecover chunks   stone.adv          # per-element chunk table
python -m advrecover survey   ./samples          # structural comparison of many files
python -m advrecover diff     a.adv b.adv        # binary diff of two files
python -m advrecover extract  stone.adv --out extracted     # previews + metadata
python -m advrecover export   stone.adv --out out --method marching_cubes
python -m advrecover batch    ./samples --out out           # batch conversion
python -m advrecover gui      stone.adv          # desktop viewer
```

Surface methods: `pointcloud`, `hull`, `clustered_hull`, `marching_cubes`.

## Desktop application

```bash
python -m advrecover gui
```

Features: parsed-structure tree, PyVista 3D viewport (orbit / zoom / pan),
layer toggles (rough / planned stones / saw planes / contours / point cloud /
axes), wireframe mode, reconstruction-method selector, RE diagnostics panel,
logging console and OBJ/STL export.

## Building the Windows `.exe`

See `docs/BUILD.md`. In short:

```bash
pip install -r requirements-dev.txt
pyinstaller packaging/advrecover.spec
```

## Architecture

```
advrecover/
  binio/      structured binary reader, GUID, hexdump      (format-agnostic)
  format/     .ADV container: header, directory, sections, main-model header
  recon/      geometry scanner, contour handling, mesh reconstruction
  export/     OBJ / STL / MTL writers with object grouping
  re_tools/   reverse-engineering diagnostics: probe, binary diff
  viewer/     PySide6 + PyVista desktop application
  cli.py      command-line entry point (also drives batch mode)
```

See `docs/ARCHITECTURE.md` for the full design and `docs/ADV_FORMAT.md` for
the reverse-engineered file-format specification.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run on synthetic fixtures — no proprietary `.ADV` samples are committed.
