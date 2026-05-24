"""Main window: ties together the viewport, side panel, and menu."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pyvista as pv
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
)

from .scene import LoadedMesh, color_for_index
from .side_panel import SidePanel
from .viewport import Viewport, angle_degrees, distance


class MainWindow(QMainWindow):
    """Top-level window for the STL viewer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STL TO STN — 3D Viewer")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._meshes: List[LoadedMesh] = []
        self._measure_mode: Optional[str] = None  # "distance" | "angle" | None
        self._pending_points: list[tuple] = []
        self._measurement_counter = 0

        self._build_ui()
        self._build_menu()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        self.side_panel = SidePanel()
        self.viewport = Viewport()
        splitter.addWidget(self.side_panel)
        splitter.addWidget(self.viewport)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 960])
        self.setCentralWidget(splitter)

        self.status: QStatusBar = self.statusBar()
        self.status.showMessage("Drag-drop STL files, or use File > Open.")

        # Side panel signals
        self.side_panel.visibility_toggled.connect(self.viewport.update_visibility)
        self.side_panel.color_changed.connect(self.viewport.update_appearance)
        self.side_panel.opacity_changed.connect(self.viewport.update_appearance)
        self.side_panel.mesh_removed.connect(self._on_mesh_removed)
        self.side_panel.measure_distance_clicked.connect(self._start_distance)
        self.side_panel.measure_angle_clicked.connect(self._start_angle)
        self.side_panel.clear_measurements_clicked.connect(self._clear_measurements)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        act_open = QAction("&Open STL…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._open_dialog)
        file_menu.addAction(act_open)

        act_screenshot = QAction("Save &screenshot…", self)
        act_screenshot.setShortcut("Ctrl+S")
        act_screenshot.triggered.connect(self._save_screenshot)
        file_menu.addAction(act_screenshot)

        file_menu.addSeparator()
        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = mb.addMenu("&View")
        act_reset = QAction("&Reset view (isometric)", self)
        act_reset.setShortcut("R")
        act_reset.triggered.connect(self.viewport.reset_view)
        view_menu.addAction(act_reset)

        act_fit = QAction("&Fit to screen", self)
        act_fit.setShortcut("F")
        act_fit.triggered.connect(self.viewport.fit_view)
        view_menu.addAction(act_fit)

        view_menu.addSeparator()
        for mode, label, shortcut in (
            ("surface", "&Surface", "1"),
            ("wireframe", "&Wireframe", "2"),
            ("points", "&Points", "3"),
        ):
            act = QAction(label, self)
            act.setShortcut(shortcut)
            act.triggered.connect(lambda _checked=False, m=mode: self._set_mode(m))
            view_menu.addAction(act)

        tools_menu = mb.addMenu("&Tools")
        act_dist = QAction("Measure &distance", self)
        act_dist.setShortcut("D")
        act_dist.triggered.connect(self._start_distance)
        tools_menu.addAction(act_dist)

        act_ang = QAction("Measure &angle", self)
        act_ang.setShortcut("A")
        act_ang.triggered.connect(self._start_angle)
        tools_menu.addAction(act_ang)

        act_clear = QAction("&Clear measurements", self)
        act_clear.setShortcut("C")
        act_clear.triggered.connect(self._clear_measurements)
        tools_menu.addAction(act_clear)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open STL files",
            "",
            "STL files (*.stl *.STL);;All files (*)",
        )
        for p in paths:
            self.load_file(p)

    def load_file(self, path: str | Path) -> None:
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, "File not found", f"Could not open {p}.")
            return
        try:
            mesh = pv.read(str(p))
            if not isinstance(mesh, pv.PolyData):
                mesh = mesh.extract_surface()
        except Exception as exc:  # pragma: no cover - depends on bad files
            QMessageBox.critical(
                self, "Failed to read STL", f"{p.name}: {exc}"
            )
            return

        item = LoadedMesh(
            name=p.name,
            path=p,
            mesh=mesh,
            color=color_for_index(len(self._meshes)),
        )
        self._meshes.append(item)
        self.viewport.add_loaded_mesh(item)
        self.side_panel.add_mesh_item(item)
        if len(self._meshes) == 1:
            self.viewport.reset_view()
        self.status.showMessage(
            f"Loaded {p.name}: {item.triangle_count:,} triangles, "
            f"{item.vertex_count:,} vertices"
        )

    def _on_mesh_removed(self, item: LoadedMesh) -> None:
        self.viewport.remove_loaded_mesh(item)
        if item in self._meshes:
            self._meshes.remove(item)
        self.viewport.plotter.render()

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".stl") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".stl"):
                self.load_file(path)
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Measurement workflow
    # ------------------------------------------------------------------

    def _start_distance(self) -> None:
        if not self._meshes:
            self.status.showMessage("Load an STL first.")
            return
        self._measure_mode = "distance"
        self._pending_points = []
        self.viewport.enable_point_picking(self._on_point_picked)
        self.side_panel.update_status(
            "Click the FIRST point on the model surface."
        )
        self.status.showMessage("Measuring distance — click 2 surface points.")

    def _start_angle(self) -> None:
        if not self._meshes:
            self.status.showMessage("Load an STL first.")
            return
        self._measure_mode = "angle"
        self._pending_points = []
        self.viewport.enable_point_picking(self._on_point_picked)
        self.side_panel.update_status(
            "Click point A (first arm), then the VERTEX, then point C (second arm)."
        )
        self.status.showMessage(
            "Measuring angle — click 3 surface points (A, vertex, C)."
        )

    def _on_point_picked(self, point: tuple) -> None:
        if self._measure_mode is None:
            return
        self._pending_points.append(point)

        marker_name = f"measure-point-{self._measurement_counter}-{len(self._pending_points)}"
        self.viewport.add_marker(point, marker_name)

        if self._measure_mode == "distance" and len(self._pending_points) == 2:
            a, b = self._pending_points
            d = distance(a, b)
            self._measurement_counter += 1
            tag = f"measure-distance-{self._measurement_counter}"
            label = f"{d:.3f} mm"
            self.viewport.add_line(a, b, tag, label)
            self.side_panel.update_status(f"Distance: {label}")
            self.status.showMessage(f"Distance: {label}")
            self._finish_measurement()
        elif self._measure_mode == "angle" and len(self._pending_points) == 3:
            a, v, c = self._pending_points
            theta = angle_degrees(a, v, c)
            self._measurement_counter += 1
            tag = f"measure-angle-{self._measurement_counter}"
            label = f"{theta:.2f}°"
            self.viewport.add_angle(a, v, c, tag, label)
            self.side_panel.update_status(f"Angle: {label}")
            self.status.showMessage(f"Angle: {label}")
            self._finish_measurement()
        elif self._measure_mode == "distance":
            self.side_panel.update_status("Click the SECOND point.")
        elif self._measure_mode == "angle":
            remaining = ["vertex", "second arm point"][len(self._pending_points) - 1]
            self.side_panel.update_status(f"Click the {remaining}.")

    def _finish_measurement(self) -> None:
        self._measure_mode = None
        self._pending_points = []
        self.viewport.disable_point_picking()

    def _clear_measurements(self) -> None:
        self.viewport.clear_overlays(prefix="measure-")
        self._measurement_counter = 0
        self.side_panel.update_status("Measurements cleared.")
        self.status.showMessage("Measurements cleared.")

    # ------------------------------------------------------------------
    # View modes / screenshot
    # ------------------------------------------------------------------

    def _set_mode(self, mode: str) -> None:
        self.viewport.set_render_mode(mode)
        for item in self._meshes:
            self.viewport.update_appearance(item)
        self.status.showMessage(f"Render mode: {mode}")

    def _save_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save screenshot",
            "viewer-screenshot.png",
            "PNG image (*.png)",
        )
        if not path:
            return
        self.viewport.take_screenshot(path)
        self.status.showMessage(f"Screenshot saved to {path}")
