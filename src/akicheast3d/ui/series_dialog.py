"""Dialog zur Auswahl einer Serie. Zeigt keine Patientendaten."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from akicheast3d.loading import SeriesInfo

COLUMNS = ["Nr.", "Beschreibung", "Schichten", "Schichtdicke", "Hinweis"]
RECOMMENDED = "Empfohlen (dünnste Schichten)"
DISABLED_COLOR = QColor(140, 140, 140)


def recommended_series(series: list[SeriesInfo]) -> SeriesInfo | None:
    """Ladbare Serie mit den dünnsten Schichten, bei Gleichstand die mit den meisten Schichten."""
    loadable = [s for s in series if s.loadable]
    if not loadable:
        return None
    return min(
        loadable,
        key=lambda s: (s.slice_thickness if s.slice_thickness else float("inf"), -s.slice_count),
    )


class SeriesDialog(QDialog):
    def __init__(self, series: list[SeriesInfo], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Serie wählen")
        self.resize(760, 380)
        self._series = series
        recommended = recommended_series(series)

        self.table = QTableWidget(len(series), len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row, info in enumerate(series):
            note = RECOMMENDED if info is recommended else info.note
            thickness = f"{info.slice_thickness:.2f} mm" if info.slice_thickness else ""
            values = [
                "" if info.number is None else str(info.number),
                info.description,
                str(info.slice_count),
                thickness,
                note,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if not info.loadable:
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item.setForeground(QBrush(DISABLED_COLOR))
                self.table.setItem(row, column, item)
        if recommended is not None:
            self.table.selectRow(series.index(recommended))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Öffnen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.table.itemSelectionChanged.connect(self._update_ok)
        self.table.cellDoubleClicked.connect(lambda *_: self._ok.isEnabled() and self.accept())
        self._update_ok()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Empfohlen ist eine Dünnschicht-Serie mit ca. 1 mm."))
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def selected_series(self) -> SeriesInfo | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        info = self._series[rows[0].row()]
        return info if info.loadable else None

    def _update_ok(self) -> None:
        self._ok.setEnabled(self.selected_series() is not None)
