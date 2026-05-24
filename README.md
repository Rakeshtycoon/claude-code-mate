# STL TO STN

A small command-line tool that converts 3D mesh files in the **STL** format
(both ASCII and binary variants) into **STN** files.

## What is STN?

STL is a widely used but lossy and verbose 3D mesh format. It stores each
triangle as three vertices repeated independently, with no vertex sharing
and no metadata.

The **STN** ("Structured Triangle Network") format produced by this tool is
a simple JSON document that:

- de-duplicates vertices and stores triangles as indices into a vertex pool
- preserves per-face normals
- records the source filename, units (assumed millimetres), and triangle
  count in a small header

Example STN payload:

```json
{
  "format": "STN",
  "version": 1,
  "source": "cube.stl",
  "units": "mm",
  "triangle_count": 12,
  "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], ...],
  "normals":  [[0.0, 0.0, -1.0], ...],
  "triangles": [[0, 1, 2], [0, 2, 3], ...]
}
```

STN is intentionally simple and human-readable so downstream code can load
it with any JSON parser.

## Install

Requires Python 3.9+. There are no third-party dependencies.

```bash
git clone <this repo>
cd claude-code-mate
python -m stl_to_stn --help
```

## Usage

```bash
# Convert a single file
python -m stl_to_stn input.stl output.stn

# Pretty-print the JSON (default is compact)
python -m stl_to_stn input.stl output.stn --pretty

# Read from stdin, write to stdout
python -m stl_to_stn - - < input.stl > output.stn
```

## Running the tests

```bash
python -m unittest discover -s tests -v
```

---

# Desktop 3D Viewer

A Qt-based desktop app (Windows / macOS / Linux) for inspecting STL meshes
captured from light-scanning hardware. It does **not** require the `stn`
converter — it reads `.stl` directly.

## Features

- Drag-and-drop one or more `.stl` files into the window
- Rotate / zoom / pan with the mouse (left-drag, right-drag, scroll)
- Per-file color, opacity, and visibility from the side panel
- Mesh stats: triangle count, vertex count, bounding box, surface area,
  volume (for closed meshes), all in millimetres
- Measure **distance** between any two surface points
- Measure **angle** at any surface vertex (3-point pick)
- Render modes: solid / wireframe / point cloud
- Screenshot to PNG

## Install (Windows)

1. Install **Python 3.11** from <https://python.org> — tick "Add Python to PATH".
2. Open Command Prompt in this project folder, then:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-viewer.txt
```

(Same commands work on macOS / Linux with `source .venv/bin/activate`.)

## Run

```cmd
python -m viewer
```

Or open files directly from the command line:

```cmd
python -m viewer path\to\Merge0001a.STL path\to\Merge0001c.STL
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open STL file(s) |
| `Ctrl+S` | Save screenshot |
| `R` | Reset view (isometric) |
| `F` | Fit to screen |
| `1` / `2` / `3` | Solid / wireframe / points |
| `D` | Start distance measurement |
| `A` | Start angle measurement |
| `C` | Clear all measurements |
