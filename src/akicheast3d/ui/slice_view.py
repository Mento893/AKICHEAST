"""Eine 2D-Ansicht: zeigt eine Schicht in einer Richtung, mit Beschriftung und Fadenkreuz."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from akicheast3d.core import Volume
from akicheast3d.ui.slicing import (
    LABELS,
    Orientation,
    display_to_index,
    extract_slice,
    index_to_display,
    pixel_size_mm,
    slice_count,
)
from akicheast3d.ui.windowing import DEFAULT_PRESET, WindowPreset, apply_window

BACKGROUND = QColor(0, 0, 0)
LABEL_COLOR = QColor(255, 210, 90)
TEXT_COLOR = QColor(220, 220, 220)
CROSSHAIR_COLOR = QColor(80, 200, 255, 140)
MARGIN = 18
PAGE_STEP = 10


class SliceView(QWidget):
    hovered = Signal(object)
    """Voxelindex (i, j, k) unter dem Mauszeiger oder None."""
    clicked = Signal(object)
    """Voxelindex (i, j, k) des Mausklicks."""
    slice_changed = Signal(int)

    def __init__(self, orientation: Orientation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.orientation = orientation
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setMinimumSize(160, 160)
        self._volume: Volume | None = None
        self._index = 0
        self._window = DEFAULT_PRESET
        self._image: QImage | None = None
        self._cursor: tuple[int, int, int] | None = None

    # Zustand

    @property
    def volume(self) -> Volume | None:
        return self._volume

    @property
    def slice_index(self) -> int:
        return self._index

    @property
    def slice_count(self) -> int:
        return slice_count(self._volume, self.orientation) if self._volume else 0

    def set_volume(self, volume: Volume | None) -> None:
        self._volume = volume
        self._cursor = None
        self._index = self.slice_count // 2
        self._refresh()
        self.slice_changed.emit(self._index)

    def set_window(self, preset: WindowPreset) -> None:
        self._window = preset
        self._refresh()

    def set_slice(self, index: int) -> None:
        if self._volume is None:
            return
        index = int(np.clip(index, 0, self.slice_count - 1))
        if index != self._index:
            self._index = index
            self._refresh()
            self.slice_changed.emit(index)

    def set_cursor(self, index: tuple[int, int, int] | None) -> None:
        self._cursor = index
        self.update()

    # Geometrie

    def image_rect(self) -> QRectF:
        """Fläche, auf die das Bild in echten Seitenverhältnissen gezeichnet wird."""
        if self._image is None:
            return QRectF()
        width_mm, height_mm = self._image_size_mm()
        available = QRectF(self.rect()).adjusted(MARGIN, MARGIN, -MARGIN, -MARGIN)
        scale = min(available.width() / width_mm, available.height() / height_mm)
        width, height = width_mm * scale, height_mm * scale
        return QRectF(
            available.center().x() - width / 2, available.center().y() - height / 2, width, height
        )

    def index_at(self, pos: QPointF) -> tuple[int, int, int] | None:
        """Voxelindex (i, j, k) an einer Stelle im Widget oder None ausserhalb des Bildes."""
        rect = self.image_rect()
        if self._image is None or not rect.contains(pos):
            return None
        column = int((pos.x() - rect.left()) / rect.width() * self._image.width())
        row = int((pos.y() - rect.top()) / rect.height() * self._image.height())
        column = min(column, self._image.width() - 1)
        row = min(row, self._image.height() - 1)
        return display_to_index(self._volume, self.orientation, self._index, column, row)

    def _image_size_mm(self) -> tuple[float, float]:
        pixel_width, pixel_height = pixel_size_mm(self._volume, self.orientation)
        return self._image.width() * pixel_width, self._image.height() * pixel_height

    # Darstellung

    def _refresh(self) -> None:
        if self._volume is None:
            self._image = None
        else:
            plane = extract_slice(self._volume, self.orientation, self._index)
            data = np.ascontiguousarray(apply_window(plane, self._window))
            height, width = data.shape
            self._image = QImage(
                data.data, width, height, width, QImage.Format.Format_Grayscale8
            ).copy()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        painter.setPen(TEXT_COLOR)
        painter.drawText(8, 16, self.orientation.value)
        if self._image is None:
            painter.end()
            return

        rect = self.image_rect()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(rect, self._image)
        self._draw_crosshair(painter, rect)
        self._draw_labels(painter, rect)
        painter.setPen(TEXT_COLOR)
        painter.drawText(
            8, self.height() - 6, f"Schicht {self._index + 1} / {self.slice_count}"
        )
        painter.end()

    def _draw_crosshair(self, painter: QPainter, rect: QRectF) -> None:
        if self._cursor is None:
            return
        _, column, row = index_to_display(self._volume, self.orientation, self._cursor)
        x = rect.left() + (column + 0.5) / self._image.width() * rect.width()
        y = rect.top() + (row + 0.5) / self._image.height() * rect.height()
        painter.setPen(QPen(CROSSHAIR_COLOR, 1))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def _draw_labels(self, painter: QPainter, rect: QRectF) -> None:
        labels = LABELS[self.orientation]
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(LABEL_COLOR)
        half = MARGIN / 2
        center = rect.center()
        positions = {
            labels.left: QPointF(rect.left() - half, center.y()),
            labels.right: QPointF(rect.right() + half, center.y()),
            labels.top: QPointF(center.x(), rect.top() - half),
            labels.bottom: QPointF(center.x(), rect.bottom() + half),
        }
        for text, point in positions.items():
            box = QRectF(point.x() - 10, point.y() - 9, 20, 18)
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    # Bedienung

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() // 120
        if steps:
            self.set_slice(self._index + steps)
        event.accept()

    def keyPressEvent(self, event) -> None:
        step = {
            Qt.Key.Key_Up: 1,
            Qt.Key.Key_Down: -1,
            Qt.Key.Key_PageUp: PAGE_STEP,
            Qt.Key.Key_PageDown: -PAGE_STEP,
        }.get(event.key())
        if step is None:
            super().keyPressEvent(event)
        else:
            self.set_slice(self._index + step)

    def mouseMoveEvent(self, event) -> None:
        self.hovered.emit(self.index_at(event.position()))

    def leaveEvent(self, event) -> None:
        self.hovered.emit(None)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.index_at(event.position())
            if index is not None:
                self.clicked.emit(index)
