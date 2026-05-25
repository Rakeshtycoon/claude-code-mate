"""Main window: ties together the viewport, side panel, and menu."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
)

from stn_reader.parser import StnParseError

from .scene import LoadedStn
from .side_panel import SidePanel
from .viewport import Viewport


class MainWindow(QMainWindow):
    """Top-level window for the STN viewer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STN READER — 3D Viewer")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._files: List[LoadedStn] = []

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
        splitter.setSizes([360, 920])
        self.setCentralWidget(splitter)

        self.status: QStatusBar = self.statusBar()
        self.status.showMessage("Drag-drop .stn files, or use File > Open.")

        self.side_panel.visibility_toggled.connect(self.viewport.update_visibility)
        self.side_panel.color_changed.connect(self.viewport.update_appearance)
        self.side_panel.opacity_changed.connect(self.viewport.update_appearance)
        self.side_panel.file_removed.connect(self._on_file_removed)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        act_open = QAction("&Open .stn…", self)
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

        help_menu = mb.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open .stn files",
            "",
            "STN files (*.stn *.STN);;All files (*)",
        )
        for p in paths:
            self.load_file(p)

    def load_file(self, path: str | Path) -> None:
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, "File not found", f"Could not open {p}.")
            return
        try:
            item = LoadedStn.from_path(p, index=len(self._files))
        except StnParseError as exc:
            QMessageBox.critical(self, "Failed to read .stn", f"{p.name}: {exc}")
            return
        except Exception as exc:  # pragma: no cover - depends on bad files
            QMessageBox.critical(self, "Failed to read .stn", f"{p.name}: {exc}")
            return

        self._files.append(item)
        self.viewport.add_loaded_file(item)
        self.side_panel.add_file_item(item)
        if len(self._files) == 1:
            self.viewport.reset_view()

        meta = item.model.metadata
        self.status.showMessage(
            f"Loaded {p.name}: part={meta.part_number or '—'}, "
            f"{item.sample_count:,} samples, Stone v{meta.producer_version or '?'}"
        )

    def _on_file_removed(self, item: LoadedStn) -> None:
        self.viewport.remove_loaded_file(item)
        if item in self._files:
            self._files.remove(item)
        self.viewport.plotter.render()

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".stn") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".stn"):
                self.load_file(path)
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # View modes / screenshot / about
    # ------------------------------------------------------------------

    def _set_mode(self, mode: str) -> None:
        self.viewport.set_render_mode(mode)
        for item in self._files:
            self.viewport.update_appearance(item)
        self.status.showMessage(f"Render mode: {mode}")

    def _save_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save screenshot",
            "stn-screenshot.png",
            "PNG image (*.png)",
        )
        if not path:
            return
        self.viewport.take_screenshot(path)
        self.status.showMessage(f"Screenshot saved to {path}")

    def _show_about(self) -> None:
        from viewer import __version__

        QMessageBox.information(
            self,
            "About STN READER",
            f"STN READER v{__version__}\n\n"
            "Desktop 3D viewer for Stone .stn scan files.\n"
            "Magic 0x00000937 — companion to STL TO STN.",
        )
