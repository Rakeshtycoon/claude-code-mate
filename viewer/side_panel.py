"""Side panel: file list, mesh properties, measurement controls."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .scene import LoadedMesh


class SidePanel(QWidget):
    """Left dock: shows loaded meshes, their stats, and measurement actions."""

    visibility_toggled = Signal(object)  # LoadedMesh
    color_changed = Signal(object)
    opacity_changed = Signal(object)
    mesh_removed = Signal(object)
    measure_distance_clicked = Signal()
    measure_angle_clicked = Signal()
    clear_measurements_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(280)
        self._build_ui()
        self._current: Optional[LoadedMesh] = None

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        root.addWidget(QLabel("<b>Loaded files</b>"))
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        root.addWidget(self.list_widget, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_color = QPushButton("Color…")
        self.btn_color.clicked.connect(self._pick_color)
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self._remove_current)
        btn_row.addWidget(self.btn_color)
        btn_row.addWidget(self.btn_remove)
        root.addLayout(btn_row)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(10, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.slider_opacity)
        root.addLayout(opacity_row)

        # Stats group ----------------------------------------------------
        self.stats_box = QGroupBox("Mesh stats")
        form = QFormLayout(self.stats_box)
        self.lbl_tri = QLabel("—")
        self.lbl_vert = QLabel("—")
        self.lbl_bbox = QLabel("—")
        self.lbl_area = QLabel("—")
        self.lbl_volume = QLabel("—")
        form.addRow("Triangles:", self.lbl_tri)
        form.addRow("Vertices:", self.lbl_vert)
        form.addRow("Bounding box:", self.lbl_bbox)
        form.addRow("Surface area:", self.lbl_area)
        form.addRow("Volume:", self.lbl_volume)
        root.addWidget(self.stats_box)

        # Measurement group ---------------------------------------------
        measure_box = QGroupBox("Measurements")
        ml = QVBoxLayout(measure_box)
        self.btn_distance = QPushButton("Measure distance (2 points)")
        self.btn_distance.clicked.connect(self.measure_distance_clicked.emit)
        self.btn_angle = QPushButton("Measure angle (3 points)")
        self.btn_angle.clicked.connect(self.measure_angle_clicked.emit)
        self.btn_clear = QPushButton("Clear measurements")
        self.btn_clear.clicked.connect(self.clear_measurements_clicked.emit)
        ml.addWidget(self.btn_distance)
        ml.addWidget(self.btn_angle)
        ml.addWidget(self.btn_clear)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        ml.addWidget(sep)

        self.lbl_measure_status = QLabel(
            "Click 'Measure distance' or 'Measure angle' to start."
        )
        self.lbl_measure_status.setWordWrap(True)
        ml.addWidget(self.lbl_measure_status)
        root.addWidget(measure_box)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_mesh_item(self, item: LoadedMesh) -> None:
        widget_item = QListWidgetItem(item.name)
        widget_item.setFlags(widget_item.flags() | Qt.ItemIsUserCheckable)
        widget_item.setCheckState(Qt.Checked if item.visible else Qt.Unchecked)
        widget_item.setData(Qt.UserRole, item)
        widget_item.setBackground(QColor(item.color))
        widget_item.setForeground(QColor("#101014"))
        self.list_widget.addItem(widget_item)
        self.list_widget.setCurrentItem(widget_item)

    def update_status(self, text: str) -> None:
        self.lbl_measure_status.setText(text)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _on_item_changed(self, widget_item: QListWidgetItem) -> None:
        item: LoadedMesh = widget_item.data(Qt.UserRole)
        new_visible = widget_item.checkState() == Qt.Checked
        if new_visible != item.visible:
            item.visible = new_visible
            self.visibility_toggled.emit(item)

    def _on_selection_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            self._current = None
            self._clear_stats()
            return
        item: LoadedMesh = current.data(Qt.UserRole)
        self._current = item
        self._populate_stats(item)
        self.slider_opacity.blockSignals(True)
        self.slider_opacity.setValue(int(item.opacity * 100))
        self.slider_opacity.blockSignals(False)

    def _populate_stats(self, item: LoadedMesh) -> None:
        self.lbl_tri.setText(f"{item.triangle_count:,}")
        self.lbl_vert.setText(f"{item.vertex_count:,}")
        w, d, h = item.bounds_xyz
        self.lbl_bbox.setText(f"{w:.2f} × {d:.2f} × {h:.2f} mm")
        self.lbl_area.setText(f"{item.surface_area:.2f} mm²")
        vol = item.volume
        if vol is None:
            self.lbl_volume.setText("— (not closed)")
        else:
            self.lbl_volume.setText(f"{vol:.2f} mm³")

    def _clear_stats(self) -> None:
        for lbl in (
            self.lbl_tri,
            self.lbl_vert,
            self.lbl_bbox,
            self.lbl_area,
            self.lbl_volume,
        ):
            lbl.setText("—")

    def _pick_color(self) -> None:
        if self._current is None:
            return
        initial = QColor(self._current.color)
        chosen = QColorDialog.getColor(initial, self, "Pick mesh color")
        if not chosen.isValid():
            return
        self._current.color = chosen.name()
        widget_item = self.list_widget.currentItem()
        if widget_item is not None:
            widget_item.setBackground(chosen)
        self.color_changed.emit(self._current)

    def _on_opacity_changed(self, value: int) -> None:
        if self._current is None:
            return
        self._current.opacity = value / 100.0
        self.opacity_changed.emit(self._current)

    def _remove_current(self) -> None:
        if self._current is None:
            return
        item = self._current
        row = self.list_widget.currentRow()
        self.list_widget.takeItem(row)
        self.mesh_removed.emit(item)
