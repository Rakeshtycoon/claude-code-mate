# PyInstaller spec for ADV Planning Data Recovery.
#   build:  pyinstaller packaging/advrecover.spec
# Produces a one-folder Windows application in dist/ADVPlanningDataRecovery/.
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("pyvista", "pyvistaqt", "vtkmodules", "vtk", "skimage", "trimesh"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += ["advrecover.viewer.app", "scipy.spatial", "scipy.ndimage"]

a = Analysis(
    ["launch_gui.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ADVPlanningDataRecovery",
    console=False,
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="ADVPlanningDataRecovery",
)
