# PyInstaller spec for building the STN READER Windows executable.
# Run from the repo root on a Windows host:
#   pyinstaller packaging/stn_reader.spec

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = []
datas += collect_data_files("matplotlib", include_py_files=False)

a = Analysis(
    ["../src/stn_reader/__main__.py"],
    pathex=["../src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "matplotlib.backends.backend_tkagg",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="STN-Reader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="STN-Reader",
)
