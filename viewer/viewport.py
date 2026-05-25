"""PyVista-based 3D viewport widget for STN scans."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from .scene import LoadedStn


class Viewport(QWidget):
    """Wraps a PyVista QtInteractor and exposes per-file management helpers."""

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

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def add_loaded_file(self, item: LoadedStn) -> None:
        self._add_point_cloud_actor(item)
        self._add_heightmap_actor(item)

    def remove_loaded_file(self, item: LoadedStn) -> None:
        for attr in ("actor_points", "actor_surface"):
            actor = getattr(item, attr)
            if actor is not None:
                self.plotter.remove_actor(actor)
                setattr(item, attr, None)

    def update_visibility(self, item: LoadedStn) -> None:
        if item.visible:
            if item.actor_points is None and item.show_points:
                self._add_point_cloud_actor(item)
            if item.actor_surface is None and item.show_surface:
                self._add_heightmap_actor(item)
            for actor in (item.actor_points, item.actor_surface):
                if actor is not None:
                    actor.SetVisibility(True)
        else:
            for actor in (item.actor_points, item.actor_surface):
                if actor is not None:
                    actor.SetVisibility(False)
        self.plotter.render()

    def update_appearance(self, item: LoadedStn) -> None:
        """Re-add actors so color / opacity / style changes take effect."""
        was_visible = item.visible
        self.remove_loaded_file(item)
        if was_visible:
            self.add_loaded_file(item)
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

    def closeEvent(self, event):  # noqa: N802 (Qt naming)
        self.plotter.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_point_cloud_actor(self, item: LoadedStn) -> None:
        if item.point_cloud is None or not item.show_points:
            return
        item.actor_points = self.plotter.add_mesh(
            item.point_cloud,
            color=item.color,
            opacity=min(1.0, item.opacity + 0.1),
            point_size=4.0,
            render_points_as_spheres=True,
            name=f"{id(item)}-points",
            show_scalar_bar=False,
            lighting=False,
        )

    def _add_heightmap_actor(self, item: LoadedStn) -> None:
        if item.heightmap is None or not item.show_surface:
            return
        style = {
            "surface": "surface",
            "wireframe": "wireframe",
            "points": "points",
        }[self._render_mode]
        item.actor_surface = self.plotter.add_mesh(
            item.heightmap,
            color=item.color,
            opacity=item.opacity * 0.55,
            style=style,
            smooth_shading=True,
            name=f"{id(item)}-surface",
            show_scalar_bar=False,
            lighting=True,
        )
