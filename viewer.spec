# PyInstaller spec for the STL TO STN desktop 3D viewer.
#
# Build (from project root, on Windows):
#     pyinstaller --clean --noconfirm viewer.spec
#
# Output: dist\STL-TO-STN-Viewer\STL-TO-STN-Viewer.exe
#
# We use the "onedir" layout (not "onefile") because VTK/PyVista ship many
# DLLs and data files that load much faster from a plain folder. Distribute
# the whole `dist\STL-TO-STN-Viewer` folder (or zip it).

from PyInstaller.utils.hooks import collect_all, collect_submodules

# pyvista, pyvistaqt and vtk have lots of lazy/dynamic imports — pull them
# all in so the bundle is self-contained.
pv_data, pv_bins, pv_hidden = collect_all("pyvista")
pvqt_data, pvqt_bins, pvqt_hidden = collect_all("pyvistaqt")
vtk_data, vtk_bins, vtk_hidden = collect_all("vtkmodules")

hidden = (
    pv_hidden
    + pvqt_hidden
    + vtk_hidden
    + collect_submodules("vtkmodules")
    + ["pkg_resources.py2_warn"]
)

a = Analysis(
    ["viewer/__main__.py"],
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
    name="STL-TO-STN-Viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # add an .ico path here later if you want a custom icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="STL-TO-STN-Viewer",
)
