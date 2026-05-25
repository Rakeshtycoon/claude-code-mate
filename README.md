# STN READER

A Windows desktop application for reading and inspecting `.stn` (CAD/3D) files.

> Status: project scaffolding only. The file parser and 3D viewer are stubs;
> wire them up as the next step.

## Project layout

```
.
├── src/stn_reader/        # Application source
│   ├── __init__.py
│   ├── __main__.py        # `python -m stn_reader`
│   ├── app.py             # Tkinter GUI entry point
│   └── parser.py          # .stn file parser (stub)
├── tests/                 # pytest tests
│   └── test_parser.py
├── packaging/
│   └── stn_reader.spec    # PyInstaller spec for the Windows .exe
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Requirements

- Python 3.11+ on Windows (the GUI uses Tkinter, which ships with the standard
  Python installer from python.org).

## Setup (development)

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

## Run tests

```powershell
pytest
```

## Build a Windows .exe

PyInstaller bundles the app and the Python runtime into a single executable.
Run on a Windows machine (cross-building from Linux is not supported):

```powershell
pip install -r requirements-dev.txt
pyinstaller packaging/stn_reader.spec
```

The resulting executable will be at `dist\STN-Reader\STN-Reader.exe`.
