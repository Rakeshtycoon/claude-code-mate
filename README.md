# STN READER

Windows desktop reader for `.stn` (Stone-produced 3D scan / heightfield)
files. Inspired by the prior **STL TO STN Project** but reads `.stn`
instead of writing it.

## What `.stn` looks like

Reverse-engineered from sample files:

| Offset    | Type      | Meaning                                                  |
|-----------|-----------|----------------------------------------------------------|
| 0         | u32 LE    | Magic = `0x00000937`                                     |
| 4         | u32 LE    | File ID / hash                                           |
| 8         | u32 LE    | Creation marker                                          |
| 16        | f64       | Scale factor (per-file)                                  |
| 48        | u32 LE    | Width / column count                                     |
| 52        | u32 LE    | Format constant = `61200`                                |
| 56        | u32 LE    | Height / row count                                       |
| 213       | u32 + str | Part number (length-prefixed ASCII)                      |
| 237       | u32 + str | Quality tag, e.g. `"Most Accurate"`                      |
| 256..end  | u16 LE[]  | Quantised height samples; `0x6F7D` = no-data sentinel    |
| tail      | ASCII     | `(StoneTextualData: PrivateBuild N Date d.m.y h:m:s Version:x.y.z.b)` |

Producer in all sample files: **Stone v5.3.0.165**.

The grid dimensions and exact sample layout still need full
confirmation; the parser exposes everything currently understood and the
viewer plots the decoded samples as a 1-D signal until the 2-D grid
layout is pinned down.

## Project layout

```
.
├── src/stn_reader/        # Application source
│   ├── __init__.py
│   ├── __main__.py        # `python -m stn_reader`
│   ├── app.py             # Tkinter GUI with matplotlib preview
│   └── parser.py          # .stn header + metadata parser
├── tests/                 # pytest tests (synthetic + one real fixture)
│   ├── fixtures/sample.stn
│   └── test_parser.py
├── packaging/
│   └── stn_reader.spec    # PyInstaller spec for the Windows .exe
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

## Run from source

```powershell
python -m stn_reader
```

Use **File → Open .stn…** to load a file. The left pane shows header +
metadata, the right pane plots the quantised height samples.

## Run tests

```powershell
pytest
```

## Build the Windows `.exe`

PyInstaller bundles the app, the Python runtime and matplotlib into a
single distributable folder. Run on a Windows host (cross-building from
Linux is not supported by PyInstaller):

```powershell
pip install -r requirements-dev.txt
pyinstaller packaging/stn_reader.spec
```

Result: `dist\STN-Reader\STN-Reader.exe`.
