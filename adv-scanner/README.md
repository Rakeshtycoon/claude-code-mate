# advkit — `.adv` Diamond Galaxy-Scanner Toolkit

A reverse-engineering and analysis toolkit for the proprietary `.adv` files
produced by diamond "galaxy" scanning systems. It decodes the container,
extracts the internal X-ray slice imagery, reconstructs a 3D voxel volume,
detects internal inclusions and exports surface meshes — all offline, all
from the command line or as a Python library.

> **Scope.** This repo delivers the **format decoder + analysis core** —
> the foundation a full Qt6/Vulkan industrial planner would build on. See
> [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is done vs. planned and
> [`docs/FORMAT.md`](docs/FORMAT.md) for the reverse-engineering findings.

## What it does (verified across 5 real `.adv` samples, 25–48 MB)

- Parses the header: GUIDs, version, Windows FILETIME scan time,
  calibration scalar, job id / scan mode / UUID strings.
- Carves the embedded JPEG streams with a **marker-aware** parser that
  rejects false-positive `FF D8` markers inside binary data.
- Identifies the **300 grayscale 1024×1280 X-ray slices** and the RGB
  preview thumbnails, and flags corrupt/truncated streams.
- Discovers the **3D mesh geometry** in the body block — `float64` XYZ
  vertex buffers and `uint32` triangle-index buffers (the laser-scanned
  outer surface).
- Reconstructs a 3D voxel volume (with downsampling and damaged-slice
  interpolation).
- Detects internal inclusions (Otsu body segmentation → hull fill →
  enclosed-dark-region labelling → 3D connected components).
- Extracts isosurfaces (marching cubes) and exports STL / OBJ / PLY.
- Provides binary-inspection tooling (entropy profiling, signature
  scanning, dimension brute-forcing) to keep decoding unknown regions.

See [`docs/FORMAT.md`](docs/FORMAT.md) for the full, evidence-graded
reverse-engineering write-up.

## Install

```bash
cd adv-scanner
pip install -e .          # installs advkit + the adv-analyzer CLI
```

Dependencies: numpy, pillow, scipy, scikit-image.

## CLI usage

```bash
adv-analyzer inspect      sample.adv                 # structure + header report
adv-analyzer report       sample.adv                 # same, as JSON
adv-analyzer entropy      sample.adv                 # entropy profile
adv-analyzer hexdump      sample.adv --offset 0 --length 512
adv-analyzer geometry     sample.adv --json mesh.json # mesh vertex/face buffers
adv-analyzer discover     sample.adv                 # structure discovery
adv-analyzer slices       sample.adv -o out/slices   # export X-ray slices as PNG
adv-analyzer thumbnails   sample.adv -o out/thumbs
adv-analyzer volume       sample.adv -o vol.npy --downsample 4
adv-analyzer inclusions   sample.adv --downsample 4 --json inclusions.json
adv-analyzer surface      sample.adv -o hull.stl --downsample 4
```

## Library usage

```python
from advkit import AdvFile
from advkit.volume.slices import SliceStack
from advkit.inclusion.detector import detect

with AdvFile.open("sample.adv") as adv:
    print(adv.header.scan_time, adv.slice_count)
    volume = SliceStack(adv).build_volume(downsample=4)
    result = detect(volume)
    print(result.count, "inclusions,", result.defect_fraction, "of body")
```

## Architecture

Layered, low → high; each layer depends only on those above it:

```
core        memory-mapped IO, logging
parsers     JPEG carving, binary inspection, the .adv container model
volume      voxel-volume reconstruction, automated structure discovery
mesh        body-block geometry discovery, isosurface extraction, export
inclusion   volumetric defect detection
tools       the adv-analyzer command-line front end
```

## Tests

```bash
pip install -e ".[dev]"
pytest                                   # 46 tests, runs fully offline
ADV_SAMPLE=/path/to/real.adv pytest       # also exercises a genuine file
```

The suite builds a byte-accurate **synthetic** `.adv` fixture, so it needs
no proprietary data to run.
