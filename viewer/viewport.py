"""PyVista-based 3D viewport widget."""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
import pyvista as pv
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
        self._pick_callback = callback

        def _on_pick(point, picker):
            if point is None:
                return
            self._pick_callback((float(point[0]), float(point[1]), float(point[2])))

        self.plotter.enable_surface_point_picking(
            callback=_on_pick,
            show_message=False,
            show_point=False,
        )

    def disable_point_picking(self) -> None:
        self._pick_callback = None
        self.plotter.disable_picking()

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
