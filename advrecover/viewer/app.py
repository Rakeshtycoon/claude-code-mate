"""PySide6 + PyVista desktop application.

The window is built lazily (``_build_window_class``) so importing this
module never requires PySide6/pyvistaqt — only :func:`launch` does.

Features: solution browser, layer toggles, orbit/pan/zoom camera with
fit-to-scene and orthographic mode, point picking with a coordinate
read-out, a transparency slider, plane-normal visualisation, a
reconstructed-vs-inferred debug mode, OBJ/STL export and batch conversion.
"""
from __future__ import annotations

import os
import sys
import traceback

import numpy as np

from ..export import write_obj, write_stl
from ..format import parse_file
from ..format.constants import guid_name
from ..recon import METHODS
from ..recon.mesh import ReconResult
from ..recon.planning import best_solution, list_solutions, reconstruct_planning
from .scene import (
    build_scene,
    mesh_to_polydata,
    points_to_polydata,
    polyline_to_polydata,
)


def launch(path: str | None = None) -> int:
    """Create the Qt application, show the window and run the event loop."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = _build_window_class()()
    window.show()
    if path:
        window.load_file(path)
    return app.exec()


def _build_window_class():
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon, QImage, QPixmap
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDockWidget,
        QDoubleSpinBox,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSlider,
        QTabWidget,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    from pyvistaqt import QtInteractor

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("ADV Planning Data Recovery")
            self.resize(1500, 940)

            self.document = None
            self.raw_data = b""
            self.scene = None
            self.current_solution: str | None = None
            self._actors: dict[str, list] = {}
            self._wireframe = False
            self._ortho = False

            self.plotter = QtInteractor(self)
            self.setCentralWidget(self.plotter)
            self.plotter.set_background("white")
            self.plotter.add_axes()

            self._build_menu()
            self._build_left_dock()
            self._build_right_dock()
            self._build_log_dock()
            self.log("Ready — File ▸ Open a .ADV file to begin.")

        # -- construction --------------------------------------------------
        def _build_menu(self) -> None:
            file_menu = self.menuBar().addMenu("&File")
            file_menu.addAction("&Open .ADV…", self._on_open)
            file_menu.addSeparator()
            file_menu.addAction("Export &OBJ…", lambda: self._export("obj"))
            file_menu.addAction("Export &STL…", lambda: self._export("stl"))
            file_menu.addAction("&Batch convert folder…", self._batch)
            file_menu.addSeparator()
            file_menu.addAction("Export all &previews…", self._export_previews)
            file_menu.addSeparator()
            file_menu.addAction("E&xit", self.close)

            view_menu = self.menuBar().addMenu("&View")
            view_menu.addAction("Fit to scene", self._fit)
            view_menu.addAction("Toggle orthographic", self._toggle_ortho)
            view_menu.addAction("Toggle wireframe", self._toggle_wireframe)
            view_menu.addAction("Reset camera", lambda: self.plotter.reset_camera())

        def _build_left_dock(self) -> None:
            tabs = QTabWidget()

            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Structure", "Detail"])
            tabs.addTab(self.tree, "Structure")

            self.solution_list = QListWidget()
            self.solution_list.itemSelectionChanged.connect(self._on_solution_changed)
            tabs.addTab(self.solution_list, "Solutions")

            self.preview_list = QListWidget()
            self.preview_list.setViewMode(QListWidget.IconMode)
            self.preview_list.setIconSize(QSize(140, 140))
            self.preview_list.setResizeMode(QListWidget.Adjust)
            self.preview_list.setMovement(QListWidget.Static)
            self.preview_list.setSpacing(4)
            self.preview_list.setUniformItemSizes(True)
            self.preview_list.itemDoubleClicked.connect(self._show_preview)
            tabs.addTab(self.preview_list, "Previews")

            dock = QDockWidget("Document", self)
            dock.setWidget(tabs)
            dock.setMinimumWidth(340)
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        def _build_right_dock(self) -> None:
            panel = QWidget()
            layout = QVBoxLayout(panel)

            # Layers
            box = QGroupBox("Layers")
            box_layout = QVBoxLayout(box)
            self.layer_checks: dict[str, QCheckBox] = {}
            for key, label in (
                ("rough_body", "Rough body (proxy)"),
                ("cutting_planes", "Cutting planes"),
                ("planned_stones", "Planned stones"),
                ("inclusions", "Inclusion markers"),
                ("bounding_box", "Bounding box"),
                ("contours", "Contour template"),
                ("point_cloud", "Point cloud"),
                ("axes", "Coordinate axes"),
            ):
                check = QCheckBox(label)
                # rough_body is on (it's now the hull proxy when a single
                # solution is selected — much more useful than stacked 2-D
                # contours were). Inclusions stay on but typically empty.
                check.setChecked(key not in ("bounding_box", "contours",
                                              "point_cloud"))
                check.stateChanged.connect(self._apply_visibility)
                box_layout.addWidget(check)
                self.layer_checks[key] = check
            layout.addWidget(box)

            # Appearance
            box = QGroupBox("Appearance")
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(QLabel("Transparency"))
            self.transparency = QSlider(Qt.Horizontal)
            self.transparency.setRange(0, 100)
            self.transparency.setValue(40)
            self.transparency.valueChanged.connect(self._apply_appearance)
            box_layout.addWidget(self.transparency)
            self.show_normals = QCheckBox("Show plane normals")
            self.show_normals.stateChanged.connect(self._render)
            box_layout.addWidget(self.show_normals)
            self.debug_mode = QCheckBox("Debug: highlight inferred geometry")
            self.debug_mode.stateChanged.connect(self._render)
            box_layout.addWidget(self.debug_mode)
            layout.addWidget(box)

            # Reconstruction
            box = QGroupBox("Reconstruction")
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(QLabel("Rough-proxy method"))
            self.method_combo = QComboBox()
            self.method_combo.addItems([m for m in METHODS if m != "pointcloud"])
            box_layout.addWidget(self.method_combo)
            box_layout.addWidget(QLabel("Plane size (mm, 0 = auto)"))
            self.plane_size = QDoubleSpinBox()
            self.plane_size.setRange(0.0, 30.0)
            self.plane_size.setValue(0.0)
            self.plane_size.setSpecialValueText("auto")
            box_layout.addWidget(self.plane_size)
            rebuild = QPushButton("Rebuild scene")
            rebuild.clicked.connect(self._rebuild)
            box_layout.addWidget(rebuild)
            layout.addWidget(box)

            # Inspector
            box = QGroupBox("Inspector")
            box_layout = QVBoxLayout(box)
            self.inspector = QPlainTextEdit()
            self.inspector.setReadOnly(True)
            self.inspector.setMaximumHeight(150)
            self.inspector.setPlainText("Click geometry to inspect.")
            box_layout.addWidget(self.inspector)
            layout.addWidget(box)
            layout.addStretch(1)

            dock = QDockWidget("Controls", self)
            dock.setWidget(panel)
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        def _build_log_dock(self) -> None:
            self.console = QPlainTextEdit()
            self.console.setReadOnly(True)
            self.console.setMaximumBlockCount(4000)
            dock = QDockWidget("Log", self)
            dock.setWidget(self.console)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        # -- helpers -------------------------------------------------------
        def log(self, message: str) -> None:
            self.console.appendPlainText(message)

        def _on_open(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open .ADV file", "",
                "Advisor files (*.adv *.ADV);;All files (*)")
            if path:
                self.load_file(path)

        def load_file(self, path: str) -> None:
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(self._wait_cursor())
            try:
                self.log(f"Parsing {path} …")
                self.document = parse_file(path)
                with open(path, "rb") as fh:
                    self.raw_data = fh.read()
                self._populate_tree()
                self._populate_solutions()
                self._populate_previews()
                # Auto-pick the most-elements solution so the default view
                # is a single clean cut plan rather than 100+ overlapping ones.
                pick = best_solution(self.raw_data, self.document)
                self.current_solution = pick
                if pick is not None:
                    self._select_solution_in_list(pick)
                    self.log(f"Auto-selected solution {pick} (most elements). "
                             f"Pick another from the Solutions tab to compare.")
                self._rebuild()
                self.setWindowTitle(
                    f"ADV Planning Data Recovery — {os.path.basename(path)}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR: {exc}")
                self.log(traceback.format_exc())
            finally:
                QApplication.restoreOverrideCursor()

        @staticmethod
        def _wait_cursor():
            from PySide6.QtCore import Qt as _Qt
            return _Qt.WaitCursor

        def _populate_tree(self) -> None:
            self.tree.clear()
            doc = self.document
            if doc is None:
                return
            root = QTreeWidgetItem([os.path.basename(doc.path), f"v{doc.version}"])
            self.tree.addTopLevelItem(root)
            for sec in doc.sections:
                node = QTreeWidgetItem(
                    [f"section[{sec.section_id}] {sec.role}", f"{sec.size:,} B"])
                node.addChild(QTreeWidgetItem(["guid", guid_name(sec.guid)]))
                if sec.section_id == 1 and doc.main_model:
                    mm = doc.main_model
                    for label, value in (("stone id", mm.stone_id),
                                          ("plan code", mm.plan_code),
                                          ("scan mode", mm.scan_mode),
                                          ("created", str(mm.created))):
                        node.addChild(QTreeWidgetItem([label, value]))
                root.addChild(node)
            root.setExpanded(True)

        def _populate_solutions(self) -> None:
            self.solution_list.clear()
            self.solution_list.addItem("(all solutions)")
            if self.document is None:
                return
            solutions = list_solutions(self.raw_data, self.document)
            for sid, count in sorted(solutions.items(),
                                     key=lambda kv: (-kv[1], kv[0])):
                self.solution_list.addItem(f"solution {sid}  ({count} elements)")

        def _on_solution_changed(self) -> None:
            items = self.solution_list.selectedItems()
            if not items:
                return
            text = items[0].text()
            self.current_solution = (None if text.startswith("(all")
                                     else text.split()[1])
            self._rebuild()

        def _select_solution_in_list(self, sid: str) -> None:
            """Programmatically select a solution by id, without firing rebuild."""
            self.solution_list.blockSignals(True)
            try:
                for i in range(self.solution_list.count()):
                    text = self.solution_list.item(i).text()
                    if not text.startswith("(all") and text.split()[1] == sid:
                        self.solution_list.setCurrentRow(i)
                        return
            finally:
                self.solution_list.blockSignals(False)

        # -- embedded JPEG previews (real Advisor renders) ----------------
        def _populate_previews(self) -> None:
            self.preview_list.clear()
            if self.document is None or not self.document.previews:
                return
            loaded = 0
            for idx, preview in enumerate(self.document.previews):
                img = QImage.fromData(preview.data)
                if img.isNull():
                    continue
                pix = QPixmap.fromImage(img).scaled(
                    140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(QIcon(pix), f"#{idx + 1:03d}")
                item.setData(Qt.UserRole, idx)
                item.setToolTip(f"Preview {idx + 1}/{len(self.document.previews)} "
                                f"— {len(preview.data):,} bytes\nDouble-click to enlarge")
                self.preview_list.addItem(item)
                loaded += 1
            self.log(f"Loaded {loaded} embedded preview image(s) — "
                     f"double-click any thumbnail to see the original Advisor render.")

        def _show_preview(self, item) -> None:
            if self.document is None:
                return
            idx = item.data(Qt.UserRole)
            if idx is None or idx >= len(self.document.previews):
                return
            preview = self.document.previews[idx]
            img = QImage.fromData(preview.data)
            if img.isNull():
                self.log(f"Preview #{idx + 1} could not be decoded.")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(
                f"Preview #{idx + 1} of {len(self.document.previews)} — "
                f"original Advisor render ({img.width()}×{img.height()})")
            dlg.resize(min(img.width() + 60, 1200),
                       min(img.height() + 100, 900))

            v = QVBoxLayout(dlg)
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setPixmap(QPixmap.fromImage(img))
            scroll = QScrollArea()
            scroll.setWidget(label)
            scroll.setWidgetResizable(False)
            scroll.setAlignment(Qt.AlignCenter)
            v.addWidget(scroll, 1)

            buttons = QWidget()
            h = QHBoxLayout(buttons)
            h.setContentsMargins(0, 0, 0, 0)
            h.addStretch(1)
            save_btn = QPushButton("Save as…")
            save_btn.clicked.connect(lambda: self._save_preview(idx))
            h.addWidget(save_btn)
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dlg.accept)
            h.addWidget(close_btn)
            v.addWidget(buttons)
            dlg.exec()

        def _save_preview(self, idx: int) -> None:
            if (self.document is None
                    or idx >= len(self.document.previews)):
                return
            preview = self.document.previews[idx]
            stem = os.path.splitext(os.path.basename(self.document.path))[0]
            default = f"{stem}_preview_{idx + 1:03d}.jpg"
            path, _ = QFileDialog.getSaveFileName(
                self, "Save preview as JPEG", default, "JPEG (*.jpg *.jpeg)")
            if not path:
                return
            try:
                with open(path, "wb") as fh:
                    fh.write(preview.data)
                self.log(f"Saved preview #{idx + 1} to {path}")
            except OSError as exc:
                self.log(f"ERROR saving preview: {exc}")

        def _export_previews(self) -> None:
            if self.document is None or not self.document.previews:
                self.log("No previews to export — open a .ADV file first.")
                return
            directory = QFileDialog.getExistingDirectory(
                self, "Choose folder to save all previews")
            if not directory:
                return
            stem = os.path.splitext(os.path.basename(self.document.path))[0]
            saved = 0
            for idx, preview in enumerate(self.document.previews):
                out = os.path.join(directory, f"{stem}_preview_{idx + 1:03d}.jpg")
                try:
                    with open(out, "wb") as fh:
                        fh.write(preview.data)
                    saved += 1
                except OSError as exc:
                    self.log(f"  failed {out}: {exc}")
            self.log(f"Exported {saved}/{len(self.document.previews)} "
                     f"preview(s) to {directory}")

        # -- scene build / render -----------------------------------------
        def _rebuild(self) -> None:
            if self.document is None:
                return
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(self._wait_cursor())
            try:
                self.log(f"Building scene (solution: "
                         f"{self.current_solution or 'all'}) …")
                size_value = self.plane_size.value()
                self.scene = build_scene(
                    self.raw_data, self.document,
                    solution=self.current_solution,
                    geometry_method=self.method_combo.currentText(),
                    plane_size_mm=size_value if size_value > 0 else None)
                for note in self.scene.notes:
                    self.log(f"  {note}")
                self._render()
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR building scene: {exc}")
                self.log(traceback.format_exc())
            finally:
                QApplication.restoreOverrideCursor()

        def _render(self) -> None:
            self.plotter.clear()
            self.plotter.add_axes()
            self._actors = {}
            if self.scene is None:
                return
            opacity = 1.0 - self.transparency.value() / 100.0
            debug = self.debug_mode.isChecked()

            for layer in self.scene.layers:
                if layer.key == "axes" or layer.is_empty:
                    continue
                actors: list = []
                color = (1.0, 0.0, 1.0) if (debug and layer.inferred) else layer.color
                layer_opacity = opacity if layer.kind == "surface" else 1.0

                for mesh in layer.meshes:
                    if mesh.is_empty:
                        continue
                    actors.append(self.plotter.add_mesh(
                        mesh_to_polydata(mesh), color=color,
                        opacity=layer_opacity if layer.key != "rough_body" else opacity,
                        style="wireframe" if self._wireframe else "surface",
                        show_edges=layer.kind == "surface", name=mesh.name))
                for line in layer.lines:
                    pd = polyline_to_polydata(line)
                    if pd.n_points:
                        actors.append(self.plotter.add_mesh(
                            pd, color=color, line_width=2, name=line.name))
                if layer.points is not None and len(layer.points):
                    actors.append(self.plotter.add_mesh(
                        points_to_polydata(layer.points), color=color,
                        point_size=2, name=f"{layer.key}_pts"))
                self._actors[layer.key] = actors

            if self.show_normals.isChecked():
                self._add_plane_normals()
            self._enable_picking()
            self.plotter.reset_camera()
            self._apply_visibility()
            self.log("Render complete.")

        def _add_plane_normals(self) -> None:
            """Draw an arrow at each cutting-plane centre along its normal."""
            layer = self.scene.layer("cutting_planes") if self.scene else None
            if layer is None:
                return
            centres, directions = [], []
            for mesh in layer.meshes:
                if mesh.is_empty:
                    continue
                tri = mesh.vertices[mesh.faces[0]]
                n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                norm = np.linalg.norm(n)
                if norm > 0:
                    centres.append(mesh.vertices.mean(axis=0))
                    directions.append(n / norm)
            if centres:
                try:
                    self.plotter.add_arrows(np.array(centres), np.array(directions),
                                            mag=2.0, color="red", name="normals")
                except Exception:  # noqa: BLE001
                    pass

        def _enable_picking(self) -> None:
            try:
                self.plotter.enable_point_picking(
                    callback=self._on_pick, show_message=False,
                    show_point=True, use_picker=True)
            except Exception:  # noqa: BLE001
                pass

        def _on_pick(self, point, *args) -> None:
            if point is None or self.scene is None:
                return
            p = np.asarray(point)
            lines = [f"Picked point: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}) mm"]
            dims = self.scene.dimensions
            if dims is not None:
                lines.append(f"Scene size: {dims[0]:.2f} × {dims[1]:.2f} "
                             f"× {dims[2]:.2f} mm")
            self.inspector.setPlainText("\n".join(lines))

        # -- toggles -------------------------------------------------------
        def _apply_visibility(self) -> None:
            for key, check in self.layer_checks.items():
                visible = check.isChecked()
                for actor in self._actors.get(key, []):
                    actor.SetVisibility(visible)
            self.plotter.render()

        def _apply_appearance(self) -> None:
            opacity = 1.0 - self.transparency.value() / 100.0
            for key in ("rough_body", "cutting_planes", "planned_stones"):
                for actor in self._actors.get(key, []):
                    try:
                        actor.GetProperty().SetOpacity(opacity)
                    except AttributeError:
                        pass
            self.plotter.render()

        def _toggle_wireframe(self) -> None:
            self._wireframe = not self._wireframe
            for actors in self._actors.values():
                for actor in actors:
                    try:
                        prop = actor.GetProperty()
                        (prop.SetRepresentationToWireframe if self._wireframe
                         else prop.SetRepresentationToSurface)()
                    except AttributeError:
                        pass
            self.plotter.render()
            self.log(f"Wireframe {'on' if self._wireframe else 'off'}.")

        def _toggle_ortho(self) -> None:
            self._ortho = not self._ortho
            try:
                if self._ortho:
                    self.plotter.enable_parallel_projection()
                else:
                    self.plotter.disable_parallel_projection()
            except Exception:  # noqa: BLE001
                pass
            self.log(f"Projection: {'orthographic' if self._ortho else 'perspective'}.")

        def _fit(self) -> None:
            self.plotter.reset_camera()
            self.plotter.render()

        # -- export --------------------------------------------------------
        def _scene_result(self) -> ReconResult:
            """Collect the visible scene into a single ReconResult for export."""
            result = ReconResult()
            if self.scene is None:
                return result
            for layer in self.scene.layers:
                if not self.layer_checks[layer.key].isChecked():
                    continue
                result.meshes.extend(m for m in layer.meshes if not m.is_empty)
                result.contours.extend(layer.lines)
            return result

        def _export(self, fmt: str) -> None:
            if self.scene is None:
                self.log("Nothing to export — open a file first.")
                return
            ext = "obj" if fmt == "obj" else "stl"
            path, _ = QFileDialog.getSaveFileName(
                self, f"Export {ext.upper()}", "", f"{ext.upper()} (*.{ext})")
            if not path:
                return
            try:
                result = self._scene_result()
                if fmt == "obj":
                    write_obj(result, path)
                else:
                    write_stl(result, path)
                self.log(f"Exported {path}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR exporting: {exc}")

        def _batch(self) -> None:
            directory = QFileDialog.getExistingDirectory(
                self, "Select folder of .ADV files")
            if not directory:
                return
            out = os.path.join(directory, "advrecover_out")
            os.makedirs(out, exist_ok=True)
            files = [f for f in sorted(os.listdir(directory))
                     if f.lower().endswith(".adv")]
            self.log(f"Batch: {len(files)} file(s) → {out}")
            ok = 0
            for name in files:
                try:
                    doc = parse_file(os.path.join(directory, name))
                    with open(os.path.join(directory, name), "rb") as fh:
                        data = fh.read()
                    result = reconstruct_planning(data, doc)
                    stem = os.path.splitext(name)[0]
                    write_obj(result, os.path.join(out, stem + ".obj"))
                    write_stl(result, os.path.join(out, stem + ".stl"))
                    self.log(f"  ✓ {name}")
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    self.log(f"  ✗ {name}: {exc}")
            self.log(f"Batch complete: {ok}/{len(files)} succeeded. Report in {out}")
            with open(os.path.join(out, "report.txt"), "w", encoding="utf-8") as fh:
                fh.write(f"advrecover batch report\n{ok}/{len(files)} succeeded\n")

    return MainWindow
