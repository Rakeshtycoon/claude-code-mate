"""PyVista-based 3D viewport widget."""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
import pyvista as pv
import vtk
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from .scene import LoadedMesh


class _PickEventFilter(QObject):
    """Qt event filter that turns left-click (not drag) into a pick.

    PyVista's built-in picking helpers and direct VTK observers both
    proved unreliable under pyvistaqt because Qt sometimes consumes
    mouse events before VTK ever sees them. Hooking at the Qt level
    is the most dependable: we always see the press/release pair.
    """

    def __init__(self, viewport: "Viewport") -> None:
        super().__init__()
        self._viewport = viewport
        self._press_pos: Optional[tuple[int, int]] = None

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt naming)
        viewport = self._viewport
        if viewport._pick_callback is None:
            return False

        try:
            et = event.type()
        except Exception:
            return False

        if et == QEvent.MouseButtonPress:
            try:
                if event.button() == Qt.LeftButton:
                    pos = event.position()
                    self._press_pos = (int(pos.x()), int(pos.y()))
            except Exception:
                self._press_pos = None
        elif et == QEvent.MouseButtonRelease:
            try:
                if event.button() != Qt.LeftButton:
                    return False
                press = self._press_pos
                self._press_pos = None
                if press is None:
                    return False
                pos = event.position()
                x_qt = int(pos.x())
                y_qt = int(pos.y())
                # > 4 px movement = drag (rotation), not a click.
                if abs(x_qt - press[0]) > 4 or abs(y_qt - press[1]) > 4:
                    return False
                viewport._do_vtk_pick(watched, x_qt, y_qt)
            except Exception:
                pass
        return False  # never consume — let the rotate/zoom style still work


class Viewport(QWidget):
    """Wraps a PyVista QtInteractor and exposes mesh-management helpers."""

    point_picked = Signal(tuple)  # (x, y, z) world-space pick

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#1e1e22", top="#2a2a30")
        self.plotter.show_axes()
        self.plotter.enable_anti_aliasing("msaa")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter.interactor)

        self._render_mode = "surface"  # surface | wireframe | points
        self._smooth_shading = True
        self._pick_callback: Optional[Callable[[tuple], None]] = None

        # Install a permanent click filter; it only acts while
        # `_pick_callback` is set.
        self._pick_filter = _PickEventFilter(self)
        try:
            self.plotter.interactor.installEventFilter(self._pick_filter)
        except Exception:
            pass

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
            smooth_shading=self._smooth_shading,
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

    def set_camera_view(self, view: str) -> None:
        """Snap the camera to a standard orthographic view."""
        p = self.plotter
        view = view.lower()
        # PyVista's view_* methods orient the camera along an axis.
        if view == "front":
            p.view_xz()
        elif view == "back":
            p.view_xz(negative=True)
        elif view == "top":
            p.view_xy()
        elif view == "bottom":
            p.view_xy(negative=True)
        elif view == "left":
            p.view_yz()
        elif view == "right":
            p.view_yz(negative=True)
        elif view == "isometric":
            p.view_isometric()
        else:
            return
        p.reset_camera()
        p.render()

    def take_screenshot(self, path: str) -> None:
        self.plotter.screenshot(path)

    # ------------------------------------------------------------------
    # Display toggles
    # ------------------------------------------------------------------

    _BBOX_NAME = "_viewer_bbox_outline"

    def set_bbox_visible(self, visible: bool) -> None:
        """Show or hide a grey wireframe around the loaded meshes' bounds."""
        if visible:
            if self._BBOX_NAME in self.plotter.actors:
                # Refresh in case bounds changed since last toggle.
                self.plotter.remove_actor(self._BBOX_NAME)
            bounds = self.plotter.bounds
            if bounds is None:
                self.plotter.render()
                return
            box = pv.Box(bounds=tuple(bounds), level=0)
            actor = self.plotter.add_mesh(
                box,
                style="wireframe",
                color="#888888",
                line_width=1,
                name=self._BBOX_NAME,
                lighting=False,
            )
            try:
                actor.SetPickable(False)
            except Exception:
                pass
        else:
            if self._BBOX_NAME in self.plotter.actors:
                self.plotter.remove_actor(self._BBOX_NAME)
        self.plotter.render()

    def set_smooth_shading(self, smooth: bool) -> None:
        """Toggle Gouraud-style smooth shading on all loaded meshes."""
        self._smooth_shading = bool(smooth)
        # Re-add every visible mesh so the new shading takes effect.
        # The caller is responsible for iterating; we expose the flag
        # via `_smooth_shading` and let the main window trigger refresh.

    def set_lighting(self, preset: str) -> None:
        """Switch to one of a few canned lighting setups."""
        p = self.plotter
        try:
            p.remove_all_lights()
        except Exception:
            pass

        preset = preset.lower()
        if preset == "bright":
            for pos, intensity in (
                ((1, 1, 1), 1.0),
                ((-1, 1, 0.5), 0.6),
                ((0, -1, 0.5), 0.5),
            ):
                p.add_light(
                    pv.Light(
                        position=pos, focal_point=(0, 0, 0), intensity=intensity
                    )
                )
        elif preset == "dim":
            p.add_light(
                pv.Light(
                    position=(1, 1, 1), focal_point=(0, 0, 0), intensity=0.5
                )
            )
        elif preset == "headlight":
            p.add_light(pv.Light(light_type="headlight", intensity=0.9))
        else:  # "default" / "studio"
            for pos, intensity in (
                ((1, 1, 1), 0.7),
                ((-1, 0, 0.5), 0.4),
                ((0, -1, 0.3), 0.3),
            ):
                p.add_light(
                    pv.Light(
                        position=pos, focal_point=(0, 0, 0), intensity=intensity
                    )
                )
        p.render()

    # ------------------------------------------------------------------
    # Measurement workflow
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback: Callable[[tuple], None]) -> None:
        """Arm the click filter to call `callback((x,y,z))` on left-click."""
        self._pick_callback = callback

    def disable_point_picking(self) -> None:
        self._pick_callback = None

    def _do_vtk_pick(self, watched, x_qt: int, y_qt: int) -> None:
        """Run a vtkCellPicker for the given Qt click position."""
        if self._pick_callback is None:
            return

        renderer = None
        for getter in (
            lambda: self.plotter.renderer,
            lambda: self.plotter.renderers[0],
        ):
            try:
                renderer = getter()
                if renderer is not None:
                    break
            except Exception:
                continue
        if renderer is None:
            return

        # VTK uses physical pixels with bottom-left origin; Qt gives us
        # logical pixels with top-left origin. Convert.
        try:
            dpr = float(watched.devicePixelRatioF())
        except Exception:
            dpr = 1.0
        try:
            ren_size = renderer.GetSize()  # (width, height) in physical px
            height_phys = int(ren_size[1])
        except Exception:
            height_phys = int(watched.height() * dpr)

        vtk_x = int(round(x_qt * dpr))
        vtk_y = height_phys - int(round(y_qt * dpr))

        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.01)
        if picker.Pick(vtk_x, vtk_y, 0, renderer):
            world = picker.GetPickPosition()
            self._pick_callback(
                (float(world[0]), float(world[1]), float(world[2]))
            )

    # ------------------------------------------------------------------
    # Overlay actors (markers, lines, labels)
    # ------------------------------------------------------------------

    def add_marker(self, point: tuple, name: str) -> None:
        sphere = pv.Sphere(radius=self._marker_radius(), center=point)
        actor = self.plotter.add_mesh(
            sphere, color="#FFD24A", name=name, lighting=False
        )
        # Don't let picker re-pick our own marker on the next click.
        try:
            actor.SetPickable(False)
        except Exception:
            pass

    def add_line(self, a: tuple, b: tuple, name: str, label: str) -> None:
        line = pv.Line(a, b)
        actor = self.plotter.add_mesh(
            line, color="#FFD24A", line_width=3, name=name
        )
        try:
            actor.SetPickable(False)
        except Exception:
            pass
        if label:
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
    # Internal helpers
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
