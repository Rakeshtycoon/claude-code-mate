"""PySide6 desktop application — the ``.ADV`` planning viewer.

Layout:
  * left dock   — parsed structure tree
  * centre      — PyVista 3D viewport (orbit / zoom / pan)
  * right dock  — layer toggles, render options, reverse-engineering panel
  * bottom dock — logging console

The heavy lifting (parse + reconstruct) is delegated to the same core
modules the CLI uses; this file is purely presentation + wiring.
"""
from __future__ import annotations

import os
import sys
import traceback

from ..export import write_obj, write_stl
from ..format import parse_file
from ..format.constants import guid_name
from ..recon import METHODS, reconstruct
from .scene import classify_layer, mesh_to_polydata, points_to_polydata, polyline_to_polydata

_LAYER_LABELS = {
    "rough": "Rough diamond",
    "polished": "Planned polished stones",
    "saw_planes": "Saw / cutting planes",
    "contours": "Raw contours",
    "point_cloud": "Point cloud",
    "axes": "Coordinate axes",
}
_LAYER_COLOURS = {
    "rough": (0.78, 0.62, 0.66),
    "polished": (0.95, 0.85, 0.30),
    "saw_planes": (0.30, 0.80, 0.45),
    "contours": (0.20, 0.45, 0.85),
    "point_cloud": (0.55, 0.55, 0.60),
}


def launch(path: str | None = None) -> int:
    """Create the Qt application, show the main window and run the loop."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window_cls = _build_window_class()
    window = window_cls()
    window.show()
    if path:
        window.load_file(path)
    return app.exec()


def _build_window_class():
    """Build the MainWindow class lazily so importing this module is cheap."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDockWidget,
        QFileDialog,
        QGroupBox,
        QLabel,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
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
            self.resize(1400, 900)

            self.document = None
            self.recon = None
            self.raw_data = b""
            self._actors: dict[str, list] = {}
            self._wireframe = False

            self.plotter = QtInteractor(self)
            self.setCentralWidget(self.plotter.interactor)
            self.plotter.set_background("white")
            self.plotter.add_axes()

            self._build_menu()
            self._build_tree_dock()
            self._build_control_dock()
            self._build_log_dock()
            self.log("Ready. Open a .ADV file to begin.")

        # -- UI construction ------------------------------------------------
        def _build_menu(self) -> None:
            file_menu = self.menuBar().addMenu("&File")
            file_menu.addAction("&Open .ADV...", self._on_open)
            file_menu.addSeparator()
            file_menu.addAction("Export &OBJ...", lambda: self._on_export("obj"))
            file_menu.addAction("Export &STL...", lambda: self._on_export("stl"))
            file_menu.addSeparator()
            file_menu.addAction("E&xit", self.close)

            view_menu = self.menuBar().addMenu("&View")
            view_menu.addAction("Reset camera", lambda: self.plotter.reset_camera())
            view_menu.addAction("Toggle wireframe", self._toggle_wireframe)

        def _build_tree_dock(self) -> None:
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Structure", "Detail"])
            dock = QDockWidget("Parsed structure", self)
            dock.setWidget(self.tree)
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        def _build_control_dock(self) -> None:
            panel = QWidget()
            layout = QVBoxLayout(panel)

            layers_box = QGroupBox("Layers")
            layers_layout = QVBoxLayout(layers_box)
            self.layer_checks: dict[str, QCheckBox] = {}
            for key, label in _LAYER_LABELS.items():
                check = QCheckBox(label)
                check.setChecked(key != "point_cloud")
                check.stateChanged.connect(self._apply_layer_visibility)
                layers_layout.addWidget(check)
                self.layer_checks[key] = check
            layout.addWidget(layers_box)

            recon_box = QGroupBox("Reconstruction")
            recon_layout = QVBoxLayout(recon_box)
            self.method_combo = QComboBox()
            self.method_combo.addItems(list(METHODS))
            self.method_combo.setCurrentText("marching_cubes")
            recon_layout.addWidget(QLabel("Surface method:"))
            recon_layout.addWidget(self.method_combo)
            rebuild = QPushButton("Rebuild geometry")
            rebuild.clicked.connect(self._rebuild)
            recon_layout.addWidget(rebuild)
            wire = QPushButton("Toggle wireframe")
            wire.clicked.connect(self._toggle_wireframe)
            recon_layout.addWidget(wire)
            layout.addWidget(recon_box)

            diag_box = QGroupBox("RE diagnostics")
            diag_layout = QVBoxLayout(diag_box)
            self.diag_text = QPlainTextEdit()
            self.diag_text.setReadOnly(True)
            diag_layout.addWidget(self.diag_text)
            layout.addWidget(diag_box)

            dock = QDockWidget("Controls", self)
            dock.setWidget(panel)
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        def _build_log_dock(self) -> None:
            self.console = QPlainTextEdit()
            self.console.setReadOnly(True)
            self.console.setMaximumBlockCount(2000)
            dock = QDockWidget("Log", self)
            dock.setWidget(self.console)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        # -- helpers --------------------------------------------------------
        def log(self, message: str) -> None:
            self.console.appendPlainText(message)

        def _on_open(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open .ADV file", "", "Advisor files (*.adv *.ADV);;All files (*)"
            )
            if path:
                self.load_file(path)

        def load_file(self, path: str) -> None:
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.log(f"Parsing {path} ...")
                self.document = parse_file(path)
                with open(path, "rb") as fh:
                    self.raw_data = fh.read()
                self._populate_tree()
                self._populate_diagnostics()
                self._rebuild()
                self.setWindowTitle(f"ADV Planning Data Recovery - {os.path.basename(path)}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR: {exc}")
                self.log(traceback.format_exc())
            finally:
                QApplication.restoreOverrideCursor()

        def _populate_tree(self) -> None:
            self.tree.clear()
            doc = self.document
            if doc is None:
                return
            root = QTreeWidgetItem([os.path.basename(doc.path), f"v{doc.version}"])
            self.tree.addTopLevelItem(root)
            for sec in doc.sections:
                node = QTreeWidgetItem(
                    [f"section[{sec.section_id}] {sec.role}", f"{sec.size:,} B"]
                )
                node.addChild(QTreeWidgetItem(["guid", guid_name(sec.guid)]))
                if sec.section_id == 1 and doc.main_model:
                    mm = doc.main_model
                    meta = QTreeWidgetItem(["metadata", mm.stone_id])
                    for label, value in (
                        ("plan code", mm.plan_code), ("scan mode", mm.scan_mode),
                        ("created", str(mm.created)), ("uuid", mm.document_uuid),
                    ):
                        meta.addChild(QTreeWidgetItem([label, value]))
                    node.addChild(meta)
                    tree_node = QTreeWidgetItem(
                        ["planning tree", f"{len(mm.planning_tree)} elements"]
                    )
                    for elem in mm.planning_tree:
                        tree_node.addChild(QTreeWidgetItem([elem, ""]))
                    node.addChild(tree_node)
                if sec.section_id == 4:
                    node.addChild(QTreeWidgetItem(
                        ["previews", f"{len(doc.previews)} JPEG(s)"]))
                root.addChild(node)
            root.setExpanded(True)

        def _populate_diagnostics(self) -> None:
            doc = self.document
            if doc is None:
                return
            lines = [
                f"file size : {doc.file_size:,} bytes",
                f"sections  : {len(doc.sections)}",
                f"previews  : {len(doc.previews)}",
                f"warnings  : {len(doc.warnings)}",
            ]
            lines += [f"  ! {w}" for w in doc.warnings]
            for block in doc.unknown_blocks:
                lines.append(f"unknown @0x{block.offset:x} ({block.size} B) {block.note}")
            self.diag_text.setPlainText("\n".join(lines))

        def _rebuild(self) -> None:
            if self.document is None:
                return
            method = self.method_combo.currentText()
            self.log(f"Reconstructing geometry (method: {method}) ...")
            try:
                self.recon = reconstruct(self.raw_data, self.document, method=method)
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR during reconstruction: {exc}")
                return
            for note in self.recon.notes:
                self.log(f"  {note}")
            self._render()

        def _render(self) -> None:
            self.plotter.clear()
            self.plotter.add_axes()
            self._actors = {key: [] for key in _LAYER_LABELS}
            if self.recon is None:
                return

            for mesh in self.recon.meshes:
                if mesh.is_empty:
                    continue
                layer = classify_layer(mesh.name)
                actor = self.plotter.add_mesh(
                    mesh_to_polydata(mesh),
                    color=_LAYER_COLOURS.get(layer, (0.7, 0.7, 0.7)),
                    opacity=0.4 if layer == "rough" else 0.85,
                    show_edges=True,
                    name=mesh.name,
                )
                self._actors[layer].append(actor)

            for poly in self.recon.contours:
                pd = polyline_to_polydata(poly)
                if pd.n_points == 0:
                    continue
                actor = self.plotter.add_mesh(
                    pd, color=_LAYER_COLOURS["contours"], line_width=1, name=poly.name
                )
                self._actors["contours"].append(actor)

            if len(self.recon.point_cloud):
                actor = self.plotter.add_mesh(
                    points_to_polydata(self.recon.point_cloud),
                    color=_LAYER_COLOURS["point_cloud"], point_size=2,
                    render_points_as_spheres=False, name="point_cloud",
                )
                self._actors["point_cloud"].append(actor)

            self.plotter.reset_camera()
            self._apply_layer_visibility()
            self.log("Render complete.")

        def _apply_layer_visibility(self) -> None:
            for key, check in self.layer_checks.items():
                if key == "axes":
                    continue
                visible = check.isChecked()
                for actor in self._actors.get(key, []):
                    actor.SetVisibility(visible)
            self.plotter.render()

        def _toggle_wireframe(self) -> None:
            self._wireframe = not self._wireframe
            for actors in self._actors.values():
                for actor in actors:
                    try:
                        prop = actor.GetProperty()
                        prop.SetRepresentationToWireframe() if self._wireframe \
                            else prop.SetRepresentationToSurface()
                    except AttributeError:
                        pass
            self.plotter.render()
            self.log(f"Wireframe {'on' if self._wireframe else 'off'}.")

        def _on_export(self, fmt: str) -> None:
            if self.recon is None:
                self.log("Nothing to export — open a file first.")
                return
            ext = "obj" if fmt == "obj" else "stl"
            path, _ = QFileDialog.getSaveFileName(
                self, f"Export {ext.upper()}", "", f"{ext.upper()} (*.{ext})"
            )
            if not path:
                return
            try:
                if fmt == "obj":
                    write_obj(self.recon, path)
                else:
                    write_stl(self.recon, path)
                self.log(f"Exported {path}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR exporting: {exc}")

    return MainWindow
