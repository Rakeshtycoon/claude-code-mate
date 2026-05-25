# STN READER

A desktop 3D viewer (Windows / macOS / Linux) for **`.stn`** scan files
produced by the "Stone" CMM/inspection toolchain. Companion to the
**STL TO STN** project: where that one writes `.stn`, this one reads it.

## Features

- Drag-and-drop one or more `.stn` files into the window
- Rotate / zoom / pan with the mouse (left-drag, right-drag, scroll)
- Per-file colour, opacity, and visibility from the side panel
- Header / metadata view: magic, part number, quality tag, scale factor,
  Stone producer version and build dates
- Heightfield preview rendered as a 3-D surface (`pyvista`)
- Render modes: solid / wireframe / point cloud
- Screenshot to PNG

## What is `.stn`?

`.stn` is a proprietary binary scan format. Reverse-engineered from
sample files:

| Offset    | Type       | Meaning                                                    |
|-----------|------------|------------------------------------------------------------|
| 0         | u32 LE     | Magic = `0x00000937`                                       |
| 4         | u32 LE     | File ID / hash                                             |
| 8         | u32 LE     | Creation marker                                            |
| 16        | f64        | Scale factor                                               |
| 48        | u32 LE     | Width count                                                |
| 52        | u32 LE     | Format constant = `61200`                                  |
| 56        | u32 LE     | Height count                                               |
| 213       | u32 + str  | Part number (length-prefixed ASCII)                        |
| 237       | u32 + str  | Quality tag, e.g. `"Most Accurate"`                        |
| 256..end  | u16 LE[]   | Quantised height samples; `0x6F7D` = no-data sentinel      |
| tail      | ASCII      | `(StoneTextualData: PrivateBuild N Date d.m.y h:m:s Version:x.y.z.b)` |

Sample files in this repo were produced by **Stone v5.3.0.165**. The
exact 2-D layout of the body is still being confirmed; the viewer
currently reconstructs a square-ish heightmap from the decoded samples
to give a meaningful preview.

## Project layout

```
.
├── run_viewer.py            # PyInstaller entry script
├── viewer.spec              # PyInstaller spec
├── build_exe.bat            # Windows .exe builder
├── requirements-viewer.txt  # Runtime dependencies
├── pyproject.toml
├── README.md
├── stn_reader/              # File format parser
│   ├── __init__.py
│   └── parser.py
├── viewer/                  # PySide6 + PyVista desktop viewer
│   ├── __init__.py
│   ├── __main__.py
│   ├── main_window.py
│   ├── scene.py
│   ├── side_panel.py
│   └── viewport.py
└── tests/
    ├── fixtures/sample.stn
    └── test_parser.py
```

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
python -m viewer path\to\part-700-1201.stn path\to\part-173.84-34.stn
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open `.stn` file(s) |
| `Ctrl+S` | Save screenshot |
| `R` | Reset view (isometric) |
| `F` | Fit to screen |
| `1` / `2` / `3` | Surface / wireframe / points |

## Run tests

```cmd
pip install pytest
pytest
```

## Build a standalone Windows `.exe`

The viewer can be packaged as a self-contained Windows executable using
PyInstaller. The packaged app does **not** need Python or any of the
listed dependencies installed on the target machine.

> The build itself has to run on Windows — PyInstaller cannot
> cross-compile a working Windows `.exe` from Linux/macOS.

From the project root in a Windows Command Prompt:

```cmd
build_exe.bat
```

The script will:

1. Create a `.venv` if one doesn't exist
2. Install the runtime requirements + PyInstaller
3. Run `pyinstaller --clean --noconfirm viewer.spec`
4. Print the path to the built `.exe`

The final layout is:

```
dist\STN-Reader\
    STN-Reader.exe          <- launch this
    _internal\              <- DLLs, VTK data, PySide plugins
```

Distribute the **whole `STN-Reader` folder** (or zip it). The `.exe`
needs the sibling `_internal` folder to run.

Expected build time: 2-5 minutes. Expected folder size: ~400-600 MB
(VTK + PySide6 are large; this is normal for a Qt/VTK app).
