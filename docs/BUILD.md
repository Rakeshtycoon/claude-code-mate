# Build & Packaging

## Development environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
```

Python 3.10+ is required.

## Run from source

```bash
python -m advrecover gui            # desktop viewer
python -m advrecover info file.adv  # CLI
pytest                              # test suite
```

## Building the Windows `.exe`

The desktop application is packaged with **PyInstaller**:

```bash
pip install -r requirements-dev.txt
cd packaging
pyinstaller advrecover.spec
```

The result is a one-folder distribution:

```
packaging/dist/ADVPlanningDataRecovery/
  ADVPlanningDataRecovery.exe
  ... (Qt, VTK and Python runtime)
```

Ship the whole folder. Double-clicking the `.exe` opens the viewer; a
`.adv` path may also be passed as an argument or via a file association.

### Notes on VTK / PyVista packaging

* VTK ships many data files and binary modules; `advrecover.spec` uses
  `collect_all` for `pyvista`, `pyvistaqt`, `vtk`/`vtkmodules`, `skimage`
  and `trimesh` so nothing is missed.
* A first build can be large (300–500 MB) because of Qt + VTK. Enabling UPX
  (`upx=True` in the spec, with UPX installed) reduces it noticeably.
* Build the Windows executable **on Windows** — PyInstaller does not
  cross-compile.

## Continuous reverse-engineering

`docs/ADV_FORMAT.md` is the living format specification. When `advrecover
probe` / `advrecover diff` reveal a new field, add it there with a
`VERIFIED` or `HYPOTHESIS` tag and, where relevant, a parser/section handler
in `advrecover/format/`.
