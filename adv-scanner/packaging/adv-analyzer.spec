# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ``adv-analyzer`` - single-file console executable.

Build (from the adv-scanner project root)::

    pyinstaller --clean --noconfirm packaging/adv-analyzer.spec

Output: ``dist/adv-analyzer`` (``dist/adv-analyzer.exe`` on Windows).
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# SPECPATH is injected by PyInstaller: the directory holding this .spec.
ROOT = os.path.dirname(os.path.abspath(SPECPATH))      # noqa: F821
SRC = os.path.join(ROOT, "src")
ENTRY = os.path.join(ROOT, "packaging", "adv_analyzer_main.py")

# Make the in-repo `advkit` package importable while the spec is evaluated
# (collect_submodules below resolves it through the live import system).
if SRC not in sys.path:
    sys.path.insert(0, SRC)

datas, binaries, hiddenimports = [], [], []
# Heavy packages with data files / lazily-imported submodules: pull them
# in wholesale so the frozen build does not miss anything at runtime.
for pkg in ("trimesh", "skimage", "scipy"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules("numpy")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("advkit")

a = Analysis(
    [ENTRY],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "pytest", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="adv-analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
