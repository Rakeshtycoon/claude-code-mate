# Project Conversation History — STL TO STN

> **Purpose of this file**: A complete reference of the conversation and
> work done between the user and Claude Code on the STL/STN viewer
> projects. The user is transferring this project to a new PC and will
> give this file to a fresh Claude session so it can continue the work
> with full context. Folder path will be kept identical on the new PC.

---

## 0. QUICK PRIMER FOR THE NEW CLAUDE — READ THIS FIRST

You are picking up an in-flight project. The user has been working with
Claude Code in Gujarati written in Roman script (English letters). The
project is on Windows 11. Everything below is the cumulative state.

**Do not start from scratch.** The repo is already pushed to GitHub and
the user already has a working `.exe`. Most of this document is
*reference* so you know what's already in place — the user will tell you
what they want to do next.

---

## 1. USER PROFILE & COMMUNICATION

- **Language**: User communicates in **Gujarati written with English
  letters** (e.g., "EXE OPEN KARI TO AA ERROR AAVE CHHE" = "When I open
  the EXE, this error appears"). Reply to the user in the same style.
  Keep technical terms (Python, PowerShell, build, etc.) in English.
- **Tech comfort**: Comfortable opening File Explorer, running batch
  files, and following step-by-step instructions. Less comfortable with
  command-line tools, debugging stack traces, or editing code directly.
  Always break instructions into small numbered steps with explicit
  click-by-click guidance.
- **Patience**: Very patient. Will send screenshots of every error.
  Always wait for their feedback after each step rather than batching
  many changes.
- **Email**: rcmakani@gmail.com
- **GitHub**: Rakeshtycoon

## 2. ENVIRONMENT (Windows 11 PC)

| Thing | Value |
|---|---|
| OS | Windows 11 |
| Shell | Windows PowerShell (Administrator) |
| Python | **3.11.9** (primary, on PATH) and 3.14.5 installed |
| Python Launcher (`py`) | Installed |
| Git | Installed (v2.54.0) — but user downloads ZIPs, doesn't `git clone` |
| WinRAR | Installed (used to unzip GitHub ZIPs) |
| Editors | None mentioned — uses Notepad when needed |
| GPU | NVIDIA (drivers + GeForce Experience installed) |
| Drive | F:\ used for projects |

### Folder paths in F:\CONVERTOR PROJECT\

```
F:\CONVERTOR PROJECT\
├── claude-code-mate-claude-amazing-brown-OpOnv\  ← THE MAIN PROJECT (this doc)
├── stn-reader\                                    ← Separate STN viewer (built by other Claude)
└── claude-code-mate-OLD-*\                        ← Backup folders from earlier builds
```

The user **renames the old project folder to `claude-code-mate-OLD-N`**
each time they re-download a fresh ZIP from GitHub. The active folder is
always named `claude-code-mate-claude-amazing-brown-OpOnv`.

## 3. REPOSITORY INFORMATION

- **GitHub**: https://github.com/Rakeshtycoon/claude-code-mate
- **Working branch**: `claude/amazing-brown-OpOnv`
- **ZIP download URL** the user uses:
  ```
  https://github.com/Rakeshtycoon/claude-code-mate/archive/refs/heads/claude/amazing-brown-OpOnv.zip
  ```
- **All development pushes go to** `claude/amazing-brown-OpOnv`.
- **Last commit at time of writing**: `8e46a18` (Batch 1 features).
  Subsequent commits may exist for this conversation summary.

## 4. WHAT HAS BEEN BUILT — current state

The repo contains **two independent components** that share nothing
except being in the same repo:

### 4A. `stl_to_stn/` Python package — STL ↔ STN converter library

| File | Purpose |
|---|---|
| `stl_to_stn/__init__.py` | Re-exports `convert`, `read_stl`, `write_stn`, `Mesh` |
| `stl_to_stn/__main__.py` | CLI: `python -m stl_to_stn in.stl out.stn [--pretty]` |
| `stl_to_stn/converter.py` | Parser (ASCII + binary STL) + STN JSON writer. **Pure stdlib, no dependencies.** |
| `stl_to_stn/types.py` | `Mesh` dataclass with `vertices`, `normals`, `triangles` (indexed mesh) |
| `tests/test_converter.py` | 8 unit tests covering both parsers, edge cases, round-trip |

**STN format** (defined by `write_stn()`):

```json
{
  "format": "STN",
  "version": 1,
  "source": "original.stl",
  "units": "mm",
  "triangle_count": <int>,
  "vertices":  [[x, y, z], ...],   // deduplicated
  "normals":   [[nx, ny, nz], ...], // one per triangle
  "triangles": [[i, j, k], ...]    // indices into vertices
}
```

**Note**: Only STL → STN exists. STN → STL is **not implemented yet**.

### 4B. `viewer/` Python package — Desktop 3D STL viewer

Built with PySide6 (Qt6) + PyVista + VTK. Packaged to standalone `.exe`
via PyInstaller. **THIS IS WORKING ON THE USER'S MACHINE.**

| File | Purpose |
|---|---|
| `viewer/__init__.py` | Trivial package marker |
| `viewer/__main__.py` | `python -m viewer` entry. Uses absolute imports + `sys.path` insertion so it also works as a PyInstaller entry. |
| `viewer/scene.py` | `LoadedMesh` dataclass, `color_for_index()` palette helper |
| `viewer/viewport.py` | PyVista `QtInteractor` wrapper. Mesh add/remove, camera presets, bbox toggle, smooth-shading toggle, lighting presets, **Qt-event-filter-based picking** |
| `viewer/side_panel.py` | Left dock: loaded-files list, color/opacity controls, stats group, measurement buttons |
| `viewer/main_window.py` | `QMainWindow`. Menus, recent files (QSettings), drag-drop, measurement workflow |
| `run_viewer.py` (at project root) | PyInstaller entry script using absolute imports |
| `viewer.spec` | PyInstaller spec — onedir layout, collects pyvista/pyvistaqt/vtkmodules |
| `build_exe.bat` | One-click Windows builder |
| `requirements-viewer.txt` | PySide6 ≥ 6.6, pyvista ≥ 0.43, pyvistaqt ≥ 0.11, numpy ≥ 1.24 |

### Working features of the viewer (verified by user)

- Drag-drop multiple `.stl` files
- Left-click rotates, scroll zooms, right-click pans
- Per-mesh color picker, opacity slider, hide/show, remove
- Mesh stats: triangles, vertices, bounding box (W×D×H), surface area, volume
- All values displayed in mm
- **Measure distance** (`D` key or button): click 2 points → yellow line + distance label
- **Measure angle** (`A` key or button): click 3 points → arms + angle label
- **Clear measurements** (`C` key or button)
- **Camera presets**: `Ctrl+1` Front, `Ctrl+2` Back, `Ctrl+3` Top, `Ctrl+4` Bottom, `Ctrl+5` Left, `Ctrl+6` Right, `Ctrl+7` Isometric
- **Show bounding box** toggle (`B`)
- **Smooth shading** toggle (`Shift+S`)
- **Lighting presets**: Default / Bright / Dim / Headlight
- **Recent files** menu (last 10, persisted via QSettings)
- **Save screenshot** (`Ctrl+S`)
- Render modes: solid / wireframe / points (`1` / `2` / `3`)

## 5. PLANNED BUT NOT YET BUILT (Batch 2 and 3)

The user agreed to a 3-batch rollout. Batch 1 is shipped. Batches 2 and
3 are **NOT YET IMPLEMENTED**.

### Batch 2 (next)

- **Measurement history panel** — list of all distance/angle measurements
  with rename, hide/show, delete per-item, plus **CSV export** for
  reports.
- **Surface color maps** — color the mesh by curvature, height, or wall
  thickness; show a scalar bar.

### Batch 3 (after Batch 2)

- **Cross-section / slicing** — interactive cutting plane to see inside
  the model.
- **Mesh comparison overlay** — load 2 STLs, color-code surface
  deviation (red = farther, green = matching, blue = closer), report
  mean/max deviation.

## 6. CRITICAL TECHNICAL DECISIONS — lessons learned the hard way

These are things that broke during development. Don't re-trip on them.

### 6.1. Picking — use a Qt event filter, NOT PyVista's `enable_*_picking`

`plotter.enable_surface_point_picking` left a red rubber-band rectangle
in the scene that never cleaned up, and its callback signature changed
between PyVista versions so picks weren't always firing. The user saw
"click karu chu pan kai nathi thatu" (clicking does nothing) AND a
stray red box.

**Working solution** (in `viewer/viewport.py`): install a `QObject`
event filter on the `QVTKRenderWindowInteractor` widget. Track
`MouseButtonPress` position; on `MouseButtonRelease`, if Manhattan
distance ≤ 4 px treat as a click; run a `vtkCellPicker` manually,
converting Qt logical pixels to VTK physical pixels via
`devicePixelRatioF()`. **Always return `False`** from `eventFilter` so
the default trackball style still rotates on drag.

### 6.2. PyInstaller entry script must live OUTSIDE the package

The first `viewer.spec` pointed at `viewer/__main__.py`. PyInstaller
runs entry scripts as `__main__`, so the relative import
`from .main_window import ...` raised
`ImportError: attempted relative import with no known parent package`
at `.exe` launch.

**Working solution**: `run_viewer.py` at the project root, using
absolute imports (`from viewer.main_window import MainWindow`), spec
points at this script. `viewer/__main__.py` was also converted to
absolute imports with a `sys.path` insertion so `python -m viewer` still
works.

### 6.3. PyInstaller — use onedir + `collect_all`, NOT onefile

VTK + Qt have many lazy/dynamic imports and ship many data files. The
spec uses:

```python
pv_data, pv_bins, pv_hidden = collect_all("pyvista")
pvqt_data, pvqt_bins, pvqt_hidden = collect_all("pyvistaqt")
vtk_data, vtk_bins, vtk_hidden = collect_all("vtkmodules")

hidden = pv_hidden + pvqt_hidden + vtk_hidden + collect_submodules("vtkmodules") + collect_submodules("viewer") + ["pkg_resources.py2_warn"]
```

onedir layout (NOT onefile) gives much faster startup and better
compatibility with VTK. Final bundle is ~400-600 MB.

### 6.4. Make overlay actors non-pickable

Measurement markers (spheres) and lines must be
`actor.SetPickable(False)` after adding, otherwise the next pick lands
on a previous yellow dot instead of the mesh.

### 6.5. Smooth shading — re-add, don't patch property

Just flipping `actor.GetProperty().SetInterpolationToFlat/Phong()`
doesn't always pick up vertex normals. Toggle a `self._smooth_shading`
bool and **remove + re-add** every loaded mesh with the new
`smooth_shading=` flag.

### 6.6. Camera presets — use PyVista helpers with `negative=True`

```python
plotter.view_xz()                # Front
plotter.view_xz(negative=True)   # Back
plotter.view_xy()                # Top
plotter.view_xy(negative=True)   # Bottom
plotter.view_yz()                # Left
plotter.view_yz(negative=True)   # Right
plotter.view_isometric()         # Isometric
```

Always follow with `plotter.reset_camera()` + `plotter.render()`.

### 6.7. `QSettings` returns weird shapes

`QSettings.value("recent_files", [])` may return a single string instead
of a list when only one entry is saved. Normalise:

```python
raw = self._settings.value("recent_files", [])
if isinstance(raw, str): raw = [raw]
if not isinstance(raw, list): raw = []
# Also filter out paths that no longer exist
```

### 6.8. PowerShell quirks the user hit

- **`.\` prefix required**: `build_exe.bat` won't run; the user must
  type `.\build_exe.bat`. PowerShell doesn't load from the current
  directory by default.
- **Select Mode pauses the process**: clicking inside the PowerShell
  window during a build puts it into "Select" mode (the title bar shows
  `Select Administrator: ...`). The build appears stuck. Press **Esc**
  to resume. Tell the user explicitly not to click inside the window
  while builds run.
- **Microsoft Store Python alias hijacks `python`**: Windows 11 has an
  App Execution Alias for `python.exe` that opens the MS Store instead.
  Disable in Settings → Apps → Advanced app settings → App execution
  aliases → toggle off "python.exe" and "python3.exe". The user already
  did this.
- **Python on PATH**: After disabling MS Store alias, `python` may not
  resolve at all if the real Python install didn't add itself to PATH.
  Either re-run the Python 3.11 installer with "Modify" → tick "Add
  Python to environment variables", OR use `py -3.11` instead of
  `python`. The user re-ran the installer with PATH ticked and `python
  --version` now works.

### 6.9. STL files the user has been testing with

Located at `/root/.claude/uploads/1ed69704-315e-4632-a237-1d9dd0c059e8/`
(historical, won't be on the new PC) — but the user uses these three
files for testing on Windows:

- `Merge0001a.STL` — 2.0 MB, 42,200 triangles, 21,114 vertices, bbox
  ~2.5×4.7×3.1 mm
- `Merge0001c.STL` — 13.4 MB, 281,344 triangles, 140,713 vertices,
  same bbox as 0001a (higher-detail version of same object)
- `Merge0000__Copy.STL` — 12.5 MB, 260,992 triangles, 130,498
  vertices, bbox ~7.3×7.7×7.0 mm (different, larger object)

Light-scanning origin — probably dental or jewellery scans. Units are
millimetres.

## 7. THE SEPARATE STN VIEWER PROJECT (`F:\CONVERTOR PROJECT\stn-reader\`)

The user spawned a **separate Claude session** to build a parallel
viewer for `.stn` files (the JSON format `stl_to_stn` emits). We gave
that other Claude a comprehensive prompt containing all the lessons
from this project (Qt event filter for picking, PyInstaller entry
outside package, onedir, etc.).

**That project is unrelated to this repo** — it lives in
`F:\CONVERTOR PROJECT\stn-reader\` and has its own `build_exe.bat`.
At time of writing the user successfully ran its `build_exe.bat` after
fixing the Python-PATH issue.

If the user asks about the STN viewer, refer to that other folder.
The STL viewer (this repo) is unchanged by that work.

## 8. HOW TO RESUME WORK ON THE NEW PC

The folder path will be the same: `F:\CONVERTOR PROJECT\claude-code-mate-claude-amazing-brown-OpOnv\`.

### To get the latest code on the new PC

The user prefers ZIP downloads over `git clone`. Tell them:

1. Open browser, go to:
   ```
   https://github.com/Rakeshtycoon/claude-code-mate/archive/refs/heads/claude/amazing-brown-OpOnv.zip
   ```
2. Extract into `F:\CONVERTOR PROJECT\` so the folder
   `claude-code-mate-claude-amazing-brown-OpOnv` exists.

### To run the viewer (already-built `.exe`)

If they transferred `dist\STL-TO-STN-Viewer\` from the old PC, they can
double-click `STL-TO-STN-Viewer.exe` directly — no Python needed.

### To rebuild the `.exe` on the new PC

Prerequisites:
- Python 3.11 installed with "Add to PATH" ticked
- MS Store python alias disabled

Then in PowerShell (Administrator):

```powershell
cd "F:\CONVERTOR PROJECT\claude-code-mate-claude-amazing-brown-OpOnv"
.\build_exe.bat
```

Wait 5-10 minutes (DON'T click inside the window — Select Mode will
pause it). Output: `dist\STL-TO-STN-Viewer\STL-TO-STN-Viewer.exe`.

### To continue development

Push to `claude/amazing-brown-OpOnv` branch. The user's pattern is:
**old folder rename to `claude-code-mate-OLD-N`** → **fresh ZIP
download** → **rebuild**.

---

## 9. FULL CONVERSATION TIMELINE

This section is the conversation in chronological order, summarised by
phase. Verbatim user messages are in **bold**; Claude responses are
summarised.

### Phase 1 — Project naming & initial scaffold

**User**: "project name:- STL TO STN" (after the repo was empty with
just a placeholder README about a "medicine management app").

Claude built a Python package `stl_to_stn` with binary + ASCII STL
parser and JSON-based STN writer. Added `pyproject.toml`, 8 unit
tests. All tests passing. Commit `f58f4b7`.

### Phase 2 — Desktop viewer (initial)

**User** sent 3 STL files (`Merge0001a/c.STL`, `Merge0000__Copy.STL`)
and asked, in Gujarati Roman, for a 3D viewer to open them.

After clarifying questions (platform, features, users, file source),
Claude built `viewer/` package with PySide6 + PyVista. Features: drag-
drop, rotate/zoom/pan, multi-file with per-mesh color/opacity, mesh
stats (triangles, vertices, bbox, surface area, volume in mm), distance
& angle measurements. Commit `58cd39a`.

### Phase 3 — PyInstaller `.exe` packaging

**User**: ".EXE BANAVVI CHHE" (want to build the .exe).

Claude added `viewer.spec` (onedir layout, collect_all for VTK/Qt) and
`build_exe.bat`. Commit `3013ab7`.

### Phase 4 — Debugging the `.exe`

Multiple round-trips:

1. User ran `build_exe.bat` from PowerShell → "command not recognized".
   **Fix**: PowerShell needs `.\build_exe.bat` (with `.\` prefix).
2. User ran the EXE from `build\` folder → Python DLL error.
   **Fix**: Run from `dist\STL-TO-STN-Viewer\` instead.
3. User ran the right `.exe` → `ImportError: attempted relative import
   with no known parent package` in `viewer/__main__.py` line 9.
   **Fix**: Added `run_viewer.py` at repo root with absolute imports,
   updated spec to point at it. Commit `a3dd2a2`.
4. Same error after rebuild — `viewer/__main__.py` was still being
   used. **Fix**: Converted `viewer/__main__.py` itself to absolute
   imports with `sys.path` insertion. Commit `89d9583`.
5. Build looked "stuck" at "1/6 [setuptools]" → user had clicked inside
   PowerShell window, triggering Select Mode. **Fix**: Press Esc.

Eventually viewer launched successfully and rendered
`Merge0000.STL` as a purple polyhedron. The user said "OPEN THAI GYU
CHHE" (it opened).

### Phase 5 — Measurement debugging

The first attempt at measurements (left-click on model) did nothing
because PyVista's `enable_surface_point_picking` uses the `P` key by
default, not left-click. Multiple iterations:

1. Tried `enable_surface_point_picking(left_clicking=True, ...)`.
   Commit `7b56f3f`. → Still didn't pick; instead drew a stray red
   rubber-band rectangle.
2. Switched to direct VTK observers
   (`AddObserver("LeftButtonPressEvent", ...)`). Commit `f3c8290`. →
   Qt was consuming events before VTK saw them.
3. **Final fix**: Qt event filter on
   `self.plotter.interactor`. Press/release pair, ≤ 4 px = click,
   run `vtkCellPicker` manually with `devicePixelRatioF()` scaling.
   Commit `3ff8db3`.

After the rebuild, the user confirmed: "Measurements (distance, angle)
properly chālī rahī chh" (working properly).

### Phase 6 — User asked how to actually USE measurements

The user didn't know HOW to operate distance/angle. Claude gave a
visual step-by-step in Gujarati Roman. The user successfully measured.

### Phase 7 — Advanced features (Batch 1)

**User**: asked for advanced feature suggestions and selected ALL the
options Claude offered.

Claude proposed a 3-batch rollout to limit rebuild count. Batch 1
shipped (commit `8e46a18`):

- Camera presets (Ctrl+1..Ctrl+7) — `viewport.set_camera_view()`
- Recent files menu (QSettings, last 10, prune missing)
- Bounding box toggle (`B`)
- Smooth shading toggle (`Shift+S`)
- Lighting presets (Default/Bright/Dim/Headlight)
- README updated with shortcuts

### Phase 8 — Separate STN viewer project

**User**: wanted a similar viewer for `.stn` files, said they'd build
it in another Claude session. Asked for a comprehensive prompt.

Claude wrote a full self-contained prompt embedding all lessons from
the STL viewer (Qt event filter, PyInstaller entry outside package,
onedir layout, `collect_all` for vtkmodules, non-pickable overlays,
QSettings normalisation, PowerShell `.\` prefix, Select Mode pause,
camera preset API, smooth-shading re-add pattern).

User pasted that prompt into another Claude, which built the
`stn-reader` project. User ran into Python-on-PATH issues, fixed by
running the Python 3.11 installer with "Modify" and ticking "Add to
PATH". Build then succeeded.

### Phase 9 — Technical reference report

User asked for a complete technical report of the STL parser to carry
into a separate STL ↔ STN bidirectional converter project.

Claude produced a comprehensive markdown report with: format details
(both ASCII & binary), exact byte layout, endianness, full verbatim
source of `converter.py` and `types.py`, in-memory data structure
(indexed mesh, no dedup tolerance), rendering pipeline (viewer uses
`pv.read()` independently, not our `Mesh`), project tree,
dependencies, known limitations (no STN reader, no STL writer, no
tolerance dedup, no NaN/Inf rejection, no color/material support, no
multi-solid ASCII, no streaming).

### Phase 10 — This conversation summary

User asked for the entire chat in markdown form to transfer to a new
PC. This file is the answer.

---

## 10. KEY FILES — VERBATIM SOURCE LOCATIONS

If the new Claude needs to read code, here's where things live (all
paths relative to `F:\CONVERTOR PROJECT\claude-code-mate-claude-amazing-brown-OpOnv\`):

```
README.md                        # Project docs + shortcuts table
pyproject.toml                   # stl-to-stn package metadata
requirements-viewer.txt          # PySide6, pyvista, pyvistaqt, numpy
build_exe.bat                    # Windows one-click .exe builder
viewer.spec                      # PyInstaller spec (onedir + collect_all)
run_viewer.py                    # PyInstaller entry script (absolute imports)

stl_to_stn/                      # STL → STN converter library
├── __init__.py
├── __main__.py                  # CLI: python -m stl_to_stn
├── converter.py                 # Parser (ASCII + binary) + STN writer
└── types.py                     # Mesh dataclass

viewer/                          # Desktop 3D viewer
├── __init__.py
├── __main__.py                  # python -m viewer entry
├── scene.py                     # LoadedMesh, color palette
├── viewport.py                  # PyVista wrapper + Qt event filter picking
├── side_panel.py                # Left dock UI
└── main_window.py               # QMainWindow, menus, recent files

tests/
├── __init__.py
└── test_converter.py            # 8 unit tests (binary + ASCII parsers)
```

---

## 11. IF THE USER ASKS YOU TO IMPLEMENT BATCH 2 OR 3

### Batch 2 (measurement history + CSV, surface color maps)

The measurement history needs:
- A `Measurement` dataclass with kind (distance/angle), points, value,
  unit, optional note
- A new section in `side_panel.py` with a `QListWidget` of measurements
- Per-item: rename action, toggle visibility (hide the line/label in
  scene), delete
- `Tools → Export measurements to CSV…` writing
  `id, kind, point_a_x, point_a_y, point_a_z, ..., value, unit, note`
- Persist to `QSettings` per file path so they survive viewer restart

Surface color maps need:
- New `viewer/analysis.py` with `compute_curvature(mesh) -> np.ndarray`,
  `compute_height(mesh, axis='z') -> np.ndarray`, etc.
- `View → Surface map → None / Curvature / Height / Wall thickness`
- `plotter.add_mesh(..., scalars=values, cmap='coolwarm',
  scalar_bar_args=...)` — switch render path so colors come from the
  scalar field instead of the fixed `LoadedMesh.color`

### Batch 3 (cross-section, mesh comparison)

Cross-section:
- `Tools → Cross-section` activates a `pv.PlaneWidget` (PyVista has
  `plotter.add_plane_widget`) with origin and normal controls
- Use `mesh.clip(...)` on the fly as the plane moves
- Show the cut profile in a small 2D inset

Mesh comparison:
- When ≥ 2 meshes are loaded, `Tools → Compare meshes` opens a dialog
  to pick reference and target
- Use `vtkDistancePolyDataFilter` (available via VTK) or per-vertex
  nearest-neighbour distance via `scipy.spatial.cKDTree` (would add
  scipy dependency — confirm with user first)
- Color the target by signed distance with a diverging colormap; show
  mean/max in the stats panel

Always confirm dependencies with the user before adding scipy or any
non-trivial new package.

---

## 12. THINGS THE USER MIGHT ASK NEXT — likely follow-ups

Based on the conversation trajectory:

1. **"Code transfer karyu, mā navi PC par chu, viewer rebuild karvo
   chhe"** → Walk them through fresh Python 3.11 install (with PATH),
   ZIP download, `.\build_exe.bat`.
2. **"Batch 2 banāvo"** → Implement measurement history + CSV + surface
   color maps as described above. One commit, one rebuild.
3. **"STN reader pan banāvo"** (in this repo) → Add `read_stn()` to
   `stl_to_stn/converter.py`, plus `write_stl_binary()`, then a CLI
   verb. Reference the limitations section.
4. **"Different file mā problem āve chhe"** → Always ask for the
   screenshot, then walk through specific fix.

---

## 13. END OF REFERENCE

If you (the new Claude) read this whole file, you know everything I
(the previous Claude) know about this project. Pick up wherever the
user takes you.

Be patient, reply in Gujarati Roman script with technical terms in
English, break instructions into small numbered steps with explicit
click-by-click guidance, and always wait for the user's screenshot
feedback before pushing more changes.

— End of CONVERSATION_HISTORY.md
