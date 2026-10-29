"""Die drei 2D-Ansichten mit Schiebereglern, Fenster-Voreinstellungen und Dichteanzeige.

Ein Klick in eine Ansicht stellt die beiden anderen auf diesen Punkt ein.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from akicheast3d.core import Volume
from akicheast3d.ui.slice_view import SliceView
from akicheast3d.ui.slicing import Orientation, format_position, index_to_display
from akicheast3d.ui.windowing import DEFAULT_PRESET, PRESETS, WindowPreset


class SlicePanel(QWidget):
    """Eine Ansicht mit Schieberegler darunter."""

    def __init__(self, orientation: Orientation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view = SliceView(orientation)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.view, stretch=1)
        layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self.view.set_slice)
        self.view.slice_changed.connect(self._sync_slider)

    def set_volume(self, volume: Volume | None) -> None:
        self.view.set_volume(volume)
        self.slider.setEnabled(volume is not None)
        self.slider.setRange(0, max(self.view.slice_count - 1, 0))
        self._sync_slider(self.view.slice_index)

    def _sync_slider(self, index: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(index)
        self.slider.blockSignals(False)


class Viewer2D(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.panels = {o: SlicePanel(o) for o in Orientation}
        self._volume: Volume | None = None

        self.window_buttons = QButtonGroup(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Fenster:"))
        for preset in PRESETS.values():
            button = QToolButton()
            button.setText(preset.name)
            button.setCheckable(True)
            button.setChecked(preset == DEFAULT_PRESET)
            button.clicked.connect(lambda _=False, p=preset: self.set_window(p))
            self.window_buttons.addButton(button)
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.status = QLabel()
        toolbar.addWidget(self.status)

        views = QHBoxLayout()
        for panel in self.panels.values():
            views.addWidget(panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addLayout(views, stretch=1)

        for panel in self.panels.values():
            panel.view.hovered.connect(self._show_value)
            panel.view.clicked.connect(self.go_to)

    @property
    def views(self) -> dict[Orientation, SliceView]:
        return {o: panel.view for o, panel in self.panels.items()}

    def set_volume(self, volume: Volume | None) -> None:
        self._volume = volume
        for panel in self.panels.values():
            panel.set_volume(volume)
        self.status.clear()

    def set_window(self, preset: WindowPreset) -> None:
        for view in self.views.values():
            view.set_window(preset)
        for button in self.window_buttons.buttons():
            button.setChecked(button.text() == preset.name)

    def go_to(self, index: tuple[int, int, int]) -> None:
        """Stellt alle Ansichten auf den Voxel (i, j, k) ein und zeigt das Fadenkreuz."""
        for orientation, view in self.views.items():
            slice_index, _, _ = index_to_display(self._volume, orientation, index)
            view.set_slice(slice_index)
            view.set_cursor(index)

    def _show_value(self, index: tuple[int, int, int] | None) -> None:
        if index is None or self._volume is None:
            self.status.clear()
            return
        i, j, k = index
        world = self._volume.index_to_world(index)
        hu = int(self._volume.hu[k, j, i])
        self.status.setText(f"{format_position(world)}    {hu} HU")
