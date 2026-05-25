# PyInstaller spec for the STN READER desktop 3D viewer.
#
# Build (from project root, on Windows):
#     pyinstaller --clean --noconfirm viewer.spec
#
# Output: dist\STN-Reader\STN-Reader.exe
#
# We use the "onedir" layout (not "onefile") because VTK/PyVista ship many
# DLLs and data files that load much faster from a plain folder. Distribute
# the whole `dist\STN-Reader` folder (or zip it).

from PyInstaller.utils.hooks import collect_all, collect_submodules

# pyvista, pyvistaqt and vtk have lots of lazy/dynamic imports - pull them
# all in so the bundle is self-contained.
pv_data, pv_bins, pv_hidden = collect_all("pyvista")
pvqt_data, pvqt_bins, pvqt_hidden = collect_all("pyvistaqt")
vtk_data, vtk_bins, vtk_hidden = collect_all("vtkmodules")

hidden = (
    pv_hidden
    + pvqt_hidden
    + vtk_hidden
    + collect_submodules("vtkmodules")
    + collect_submodules("viewer")
    + collect_submodules("stn_reader")
    + ["pkg_resources.py2_warn"]
)

a = Analysis(
    ["run_viewer.py"],
    pathex=["."],
    binaries=pv_bins + pvqt_bins + vtk_bins,
    datas=pv_data + pvqt_data + vtk_data,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib.tests",
        "numpy.tests",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtQuick",
        "PySide6.QtQml",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="STN-Reader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="STN-Reader",
)
