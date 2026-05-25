"""PyVista-based 3D viewport widget."""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
import pyvista as pv
import vtk
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from pyvistaqt import QtInteractor

from .scene import LoadedMesh


class Viewport(QWidget):
    """Wraps a PyVista QtInteractor and exposes mesh-management helpers."""

    point_picked = Signal(tuple)  # (x, y, z) world-space pick

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#1e1e22", top="#2a2a30")
        self.plotter.show_axes()
        self.plotter.enable_anti_aliasing("msaa")

        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter.interactor)

        self._render_mode = "surface"  # surface | wireframe | points
        self._pick_callback: Optional[Callable[[tuple], None]] = None
        self._press_pos: Optional[tuple[int, int]] = None
        self._press_observer_id: Optional[int] = None
        self._release_observer_id: Optional[int] = None
        self._raw_iren = None

    # ------------------------------------------------------------------
    # Mesh management
    # ------------------------------------------------------------------

    def add_loaded_mesh(self, item: LoadedMesh) -> None:
        style = {"surface": "surface", "wireframe": "wireframe", "points": "points"}[
            self._render_mode
        ]
        actor = self.plotter.add_mesh(
            item.mesh,
            color=item.color,
            opacity=item.opacity,
            style=style,
            smooth_shading=True,
            name=str(id(item)),
            show_scalar_bar=False,
            lighting=True,
        )
        item.actor = actor

    def remove_loaded_mesh(self, item: LoadedMesh) -> None:
        if item.actor is not None:
            self.plotter.remove_actor(item.actor)
            item.actor = None

    def update_visibility(self, item: LoadedMesh) -> None:
        if item.actor is None and item.visible:
            self.add_loaded_mesh(item)
        elif item.actor is not None:
            item.actor.SetVisibility(bool(item.visible))
            self.plotter.render()

    def update_appearance(self, item: LoadedMesh) -> None:
        """Re-add the mesh so color/opacity/style changes take effect."""
        was_visible = item.visible
        self.remove_loaded_mesh(item)
        if was_visible:
            self.add_loaded_mesh(item)
        self.plotter.render()

    # ------------------------------------------------------------------
    # Camera helpers
    # ------------------------------------------------------------------

    def reset_view(self) -> None:
        self.plotter.reset_camera()
        self.plotter.view_isometric()
        self.plotter.render()

    def fit_view(self) -> None:
        self.plotter.reset_camera()
        self.plotter.render()

    def set_render_mode(self, mode: str) -> None:
        if mode not in ("surface", "wireframe", "points"):
            return
        self._render_mode = mode

    def take_screenshot(self, path: str) -> None:
        self.plotter.screenshot(path)

    # ------------------------------------------------------------------
    # Measurement overlay
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback: Callable[[tuple], None]) -> None:
        """Enable left-click surface picking.

        Uses direct VTK observers instead of PyVista's enable_*_picking
        helpers, which proved unreliable: they could leave behind a red
        rubber-band rectangle and their callback signature changed
        between versions. With this approach the interaction is exactly:

        * Left-click without movement = pick a surface point (callback).
        * Left-click and drag         = rotate the camera (untouched).
        """
        self._pick_callback = callback
        self._press_pos = None

        raw_iren = self.plotter.iren
        if hasattr(raw_iren, "interactor"):
            raw_iren = raw_iren.interactor
        self._raw_iren = raw_iren

        def _on_press(obj, _event):
            try:
                self._press_pos = obj.GetEventPosition()
            except Exception:
                self._press_pos = None

        def _on_release(obj, _event):
            press = self._press_pos
            self._press_pos = None
            if press is None or self._pick_callback is None:
                return
            try:
                x, y = obj.GetEventPosition()
            except Exception:
                return
            # Treat any movement > 4 px as a drag (rotation), not a click.
            if abs(x - press[0]) > 4 or abs(y - press[1]) > 4:
                return

            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.005)
            renderer = self.plotter.renderer
            if picker.Pick(x, y, 0, renderer):
                world = picker.GetPickPosition()
                self._pick_callback(
                    (float(world[0]), float(world[1]), float(world[2]))
                )

        self._press_observer_id = raw_iren.AddObserver(
            "LeftButtonPressEvent", _on_press
        )
        self._release_observer_id = raw_iren.AddObserver(
            "LeftButtonReleaseEvent", _on_release
        )

    def disable_point_picking(self) -> None:
        if self._raw_iren is not None:
            if self._press_observer_id is not None:
                self._raw_iren.RemoveObserver(self._press_observer_id)
            if self._release_observer_id is not None:
                self._raw_iren.RemoveObserver(self._release_observer_id)
        self._press_observer_id = None
        self._release_observer_id = None
        self._pick_callback = None
        self._press_pos = None

    def add_marker(self, point: tuple, name: str) -> None:
        sphere = pv.Sphere(radius=self._marker_radius(), center=point)
        self.plotter.add_mesh(
            sphere, color="#FFD24A", name=name, lighting=False
        )

    def add_line(self, a: tuple, b: tuple, name: str, label: str) -> None:
        line = pv.Line(a, b)
        self.plotter.add_mesh(line, color="#FFD24A", line_width=3, name=name)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
        self.plotter.add_point_labels(
            [mid],
            [label],
            name=f"{name}-label",
            font_size=14,
            point_size=1,
            text_color="#FFD24A",
            shape=None,
            always_visible=True,
        )

    def add_angle(
        self, a: tuple, vertex: tuple, c: tuple, name: str, label: str
    ) -> None:
        self.add_line(a, vertex, f"{name}-arm1", "")
        self.add_line(vertex, c, f"{name}-arm2", "")
        self.plotter.add_point_labels(
            [vertex],
            [label],
            name=f"{name}-label",
            font_size=14,
            text_color="#FFD24A",
            shape=None,
            always_visible=True,
        )

    def clear_overlays(self, prefix: str = "measure-") -> None:
        # PyVista stores actors by name; remove anything matching the prefix.
        for actor_name in list(self.plotter.actors.keys()):
            if actor_name.startswith(prefix):
                self.plotter.remove_actor(actor_name)
        self.plotter.render()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _marker_radius(self) -> float:
        """Pick a marker size relative to the current scene bounds."""
        bounds = self.plotter.bounds
        if bounds is None:
            return 0.05
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        return max(diag * 0.005, 1e-4)

    def closeEvent(self, event):  # noqa: N802 (Qt naming)
        self.plotter.close()
        super().closeEvent(event)


def distance(a: tuple, b: tuple) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def angle_degrees(a: tuple, vertex: tuple, c: tuple) -> float:
    va = np.array(a) - np.array(vertex)
    vc = np.array(c) - np.array(vertex)
    na = np.linalg.norm(va)
    nc = np.linalg.norm(vc)
    if na == 0 or nc == 0:
        return 0.0
    cos_t = float(np.clip(np.dot(va, vc) / (na * nc), -1.0, 1.0))
    return math.degrees(math.acos(cos_t))
