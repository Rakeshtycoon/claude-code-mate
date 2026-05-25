"""PyVista-based 3D viewport widget for STN heightfields."""

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
        if not item.has_mesh:
            return
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

    def remove_loaded_file(self, item: LoadedStn) -> None:
        if item.actor is not None:
            self.plotter.remove_actor(item.actor)
            item.actor = None

    def update_visibility(self, item: LoadedStn) -> None:
        if item.actor is None and item.visible:
            self.add_loaded_file(item)
        elif item.actor is not None:
            item.actor.SetVisibility(bool(item.visible))
            self.plotter.render()

    def update_appearance(self, item: LoadedStn) -> None:
        """Re-add the mesh so color/opacity/style changes take effect."""
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
