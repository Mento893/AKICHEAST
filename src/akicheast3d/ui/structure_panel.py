"""Liste der Strukturen: ein- und ausblenden, Farbe und Transparenz."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QGridLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from akicheast3d.core import Structure


def _to_qcolor(color: tuple[float, float, float]) -> QColor:
    return QColor.fromRgbF(*color)


class StructureRow:
    """Bedienelemente für eine Struktur."""

    def __init__(self, structure: Structure, panel: StructurePanel) -> None:
        self.structure = structure
        self._panel = panel

        self.checkbox = QCheckBox(structure.name)
        self.checkbox.setChecked(structure.visible)
        self.checkbox.toggled.connect(self._set_visible)

        self.color_button = QToolButton()
        self.color_button.setToolTip("Farbe wählen")
        self.color_button.setFixedSize(22, 22)
        self.color_button.clicked.connect(self._choose_color)
        self._show_color()

        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(round(structure.opacity * 100))
        self.opacity.setToolTip("Deckkraft")
        self.opacity.valueChanged.connect(self._set_opacity)

        if structure.voxel_count == 0:
            for widget in (self.checkbox, self.color_button, self.opacity):
                widget.setEnabled(False)
                widget.setToolTip("In dieser Serie nicht gefunden")

    def set_color(self, color: QColor) -> None:
        self.structure.color = (color.redF(), color.greenF(), color.blueF())
        self._show_color()
        self._panel.changed.emit(self.structure)

    def _set_visible(self, visible: bool) -> None:
        self.structure.visible = visible
        self._panel.changed.emit(self.structure)

    def _set_opacity(self, value: int) -> None:
        self.structure.opacity = value / 100
        self._panel.changed.emit(self.structure)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(
            _to_qcolor(self.structure.color), self._panel, f"Farbe für {self.structure.name}"
        )
        if color.isValid():
            self.set_color(color)

    def _show_color(self) -> None:
        self.color_button.setStyleSheet(
            f"background-color: {_to_qcolor(self.structure.color).name()}; border: 1px solid #555;"
        )


class StructurePanel(QWidget):
    changed = Signal(object)
    """Eine Struktur wurde verändert (sichtbar, Farbe oder Deckkraft)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rows: list[StructureRow] = []
        self._grid = QGridLayout()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Strukturen</b>"))
        layout.addLayout(self._grid)
        layout.addStretch()

    def set_structures(self, structures: list[Structure]) -> None:
        while self._grid.count():
            self._grid.takeAt(0).widget().deleteLater()
        self.rows = [StructureRow(structure, self) for structure in structures]
        for line, row in enumerate(self.rows):
            self._grid.addWidget(row.checkbox, line, 0)
            self._grid.addWidget(row.color_button, line, 1)
            self._grid.addWidget(row.opacity, line, 2)
