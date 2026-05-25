"""Side panel: file list, parsed STN metadata, view controls."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFormLayout,
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

from .scene import LoadedStn


class SidePanel(QWidget):
    """Left dock: shows loaded .stn files and the selected one's metadata."""

    visibility_toggled = Signal(object)
    color_changed = Signal(object)
    opacity_changed = Signal(object)
    file_removed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(320)
        self._current: Optional[LoadedStn] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        root.addWidget(QLabel("<b>Loaded .stn files</b>"))
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

        # Header / file metadata --------------------------------------------
        self.header_box = QGroupBox("File header")
        hf = QFormLayout(self.header_box)
        self.lbl_magic = QLabel("—")
        self.lbl_size = QLabel("—")
        self.lbl_part = QLabel("—")
        self.lbl_quality = QLabel("—")
        self.lbl_scale = QLabel("—")
        self.lbl_dims = QLabel("—")
        hf.addRow("Magic:", self.lbl_magic)
        hf.addRow("File size:", self.lbl_size)
        hf.addRow("Part number:", self.lbl_part)
        hf.addRow("Quality tag:", self.lbl_quality)
        hf.addRow("Scale factor:", self.lbl_scale)
        hf.addRow("Header dims:", self.lbl_dims)
        root.addWidget(self.header_box)

        # Producer ----------------------------------------------------------
        self.producer_box = QGroupBox("Producer (Stone)")
        pf = QFormLayout(self.producer_box)
        self.lbl_version = QLabel("—")
        self.lbl_builds = QLabel("—")
        pf.addRow("Version:", self.lbl_version)
        pf.addRow("Build dates:", self.lbl_builds)
        root.addWidget(self.producer_box)

        # Point cloud -------------------------------------------------------
        self.points_box = QGroupBox("Point cloud (float32 chunks)")
        pcf = QFormLayout(self.points_box)
        self.lbl_chunks = QLabel("—")
        self.lbl_points = QLabel("—")
        self.lbl_xrange = QLabel("—")
        self.lbl_yrange = QLabel("—")
        self.lbl_zrange = QLabel("—")
        pcf.addRow("Chunks:", self.lbl_chunks)
        pcf.addRow("Points:", self.lbl_points)
        pcf.addRow("X range:", self.lbl_xrange)
        pcf.addRow("Y range:", self.lbl_yrange)
        pcf.addRow("Z range:", self.lbl_zrange)
        root.addWidget(self.points_box)

        # Heightfield -------------------------------------------------------
        self.mesh_box = QGroupBox("Heightfield preview")
        mf = QFormLayout(self.mesh_box)
        self.lbl_grid = QLabel("—")
        mf.addRow("Grid shape:", self.lbl_grid)
        root.addWidget(self.mesh_box)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_file_item(self, item: LoadedStn) -> None:
        widget_item = QListWidgetItem(item.name)
        widget_item.setFlags(widget_item.flags() | Qt.ItemIsUserCheckable)
        widget_item.setCheckState(Qt.Checked if item.visible else Qt.Unchecked)
        widget_item.setData(Qt.UserRole, item)
        widget_item.setBackground(QColor(item.color))
        widget_item.setForeground(QColor("#101014"))
        self.list_widget.addItem(widget_item)
        self.list_widget.setCurrentItem(widget_item)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _on_item_changed(self, widget_item: QListWidgetItem) -> None:
        item: LoadedStn = widget_item.data(Qt.UserRole)
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
            self._clear_metadata()
            return
        item: LoadedStn = current.data(Qt.UserRole)
        self._current = item
        self._populate_metadata(item)
        self.slider_opacity.blockSignals(True)
        self.slider_opacity.setValue(int(item.opacity * 100))
        self.slider_opacity.blockSignals(False)

    def _populate_metadata(self, item: LoadedStn) -> None:
        h = item.model.header
        m = item.model.metadata

        ok = "OK" if item.model.is_valid else "BAD"
        self.lbl_magic.setText(f"0x{h.magic:08x} ({ok})")
        self.lbl_size.setText(f"{item.model.byte_size:,} bytes")
        self.lbl_part.setText(m.part_number or "—")
        self.lbl_quality.setText(m.quality_tag or "—")
        self.lbl_scale.setText(f"{h.scale_factor:.6g}")
        self.lbl_dims.setText(f"{h.width_count} × {h.height_count}")

        self.lbl_version.setText(m.producer_version or "—")
        if m.producer_dates:
            preview = ", ".join(m.producer_dates[:3])
            extra = f" (+{len(m.producer_dates) - 3} more)" if len(m.producer_dates) > 3 else ""
            self.lbl_builds.setText(preview + extra)
        else:
            self.lbl_builds.setText("—")

        self.lbl_chunks.setText(f"{item.chunk_count}")
        self.lbl_points.setText(f"{item.point_count:,}")
        xmin, xmax, ymin, ymax, zmin, zmax = item.bounds
        if item.point_count > 0:
            self.lbl_xrange.setText(f"{xmin:.2f} … {xmax:.2f}")
            self.lbl_yrange.setText(f"{ymin:.2f} … {ymax:.2f}")
            self.lbl_zrange.setText(f"{zmin:.2f} … {zmax:.2f}")
        else:
            for lbl in (self.lbl_xrange, self.lbl_yrange, self.lbl_zrange):
                lbl.setText("—")
        gw, gh = item.heightmap_dims
        self.lbl_grid.setText(f"{gw} × {gh}" if gw else "—")

    def _clear_metadata(self) -> None:
        for lbl in (
            self.lbl_magic,
            self.lbl_size,
            self.lbl_part,
            self.lbl_quality,
            self.lbl_scale,
            self.lbl_dims,
            self.lbl_version,
            self.lbl_builds,
            self.lbl_chunks,
            self.lbl_points,
            self.lbl_xrange,
            self.lbl_yrange,
            self.lbl_zrange,
            self.lbl_grid,
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
        self.file_removed.emit(item)
