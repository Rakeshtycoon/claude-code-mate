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
