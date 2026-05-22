# Architecture

`ADV Planning Data Recovery` is a modular reverse-engineering + 3D
reconstruction pipeline. Each stage is independent and testable in
isolation; the GUI and CLI are thin drivers over the same core.

```
                 +-------------------+
   .ADV  ---->    |   binio           |  structured binary cursor, GUIDs, hex
                  +---------+---------+
                            |
                  +---------v---------+
                  |   format          |  container, directory, sections,
                  |                   |  main-model header + string table
                  +---------+---------+
                            |
              +-------------+-------------+
              |                           |
   +----------v---------+      +----------v----------+
   |   re_tools         |      |   recon             |
   |  probe / diff /    |      |  geometry scanner,  |
   |  chunk inspector   |      |  contour lofting,   |
   |  (RE diagnostics)  |      |  mesh reconstruction|
   +--------------------+      +----------+----------+
                                          |
                            +-------------+-------------+
                            |                           |
                  +---------v---------+      +----------v----------+
                  |   export          |      |   viewer            |
                  |  OBJ / STL / MTL  |      |  PySide6 + PyVista  |
                  +-------------------+      +---------------------+
```

## Packages

| Package | Responsibility |
|---------|----------------|
| `advrecover.binio`   | `BinaryReader` cursor, `Guid`, hexdump utilities. No format knowledge. |
| `advrecover.format`  | `.ADV` container model: header, end directory, sections, main-model header + string harvesting. |
| `advrecover.recon`   | Geometry extraction: float-array scanner, contour grouping, mesh reconstruction (lofting / marching cubes). |
| `advrecover.export`  | Mesh/point/polyline writers for OBJ, STL, MTL with object grouping. |
| `advrecover.re_tools`| Reverse-engineering diagnostics: entropy/GUID/string/float probe, binary diff, unknown-chunk inspector. |
| `advrecover.viewer`  | Qt desktop application + PyVista 3D scene (orbit camera, layer toggles, wireframe, slicing). |
| `advrecover.cli`     | Command-line entry point driving every stage; supports batch mode. |

## Design rules

1. **Never fabricate geometry.** Every exported vertex traces to bytes in the
   `.ADV` file. Reconstruction (lofting, marching cubes) is allowed and
   labelled as such; invented shapes are not.
2. **Layered dependencies only.** `binio` knows nothing about `.ADV`;
   `format` knows nothing about meshes; `recon` knows nothing about Qt.
3. **Everything is inspectable.** Any byte range the parser does not
   understand is preserved as a raw `UnknownBlock` and surfaced in the
   diagnostics panel.
4. **Plugin-ready.** New section/chunk handlers register against a class
   GUID, so future RE findings extend the parser without edits to the core.

## Data model (core objects)

* `AdvContainer` — file header, directory, list of `Section`.
* `Section` — id, class GUID, byte range, decoded payload or raw bytes.
* `MainModel` — header fields, metadata, string table, planning tree.
* `GeometryArray` — a contiguous float32 XYZ run (offset, points).
* `Contour` — an ordered polyline of points.
* `ReconObject` — a named, classified element (rough / plane / polished /
  inclusion) carrying contours and/or a reconstructed `Mesh`.
* `Mesh` — vertices + triangle faces + normals.

## Build / packaging

Development: `pip install -r requirements-dev.txt`.
Windows EXE: `pyinstaller packaging/advrecover.spec` (see `docs/BUILD.md`).
