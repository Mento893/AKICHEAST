"""3D-Ansicht: Oberflächen der Strukturen, drehen, zoomen, Standardansichten, automatische Rotation.

Die Kamera bewegt sich, die Daten bleiben unverändert.
"""

from __future__ import annotations

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from akicheast3d.core import Structure

BACKGROUND = (0.11, 0.12, 0.14)
ROTATION_DEG = 1.0
ROTATION_INTERVAL_MS = 30

# Blickrichtung von der Mitte zur Kamera (LPS: +x links, +y hinten, +z Kopf) und Oben-Richtung
VIEWS = {
    "Vorne": ((0, -1, 0), (0, 0, 1)),
    "Hinten": ((0, 1, 0), (0, 0, 1)),
    "Links": ((1, 0, 0), (0, 0, 1)),
    "Rechts": ((-1, 0, 0), (0, 0, 1)),
    "Oben": ((0, 0, 1), (0, -1, 0)),
}


class Viewer3D(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plotter = QtInteractor(self)
        self.plotter.set_background(BACKGROUND)
        self.plotter.enable_depth_peeling()
        self.plotter.add_axes(xlabel="L", ylabel="H", zlabel="K")
        self._actors: dict[str, object] = {}

        toolbar = QHBoxLayout()
        for name in VIEWS:
            button = QToolButton()
            button.setText(name)
            button.clicked.connect(lambda _=False, n=name: self.set_view(n))
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.rotate_button = QToolButton()
        self.rotate_button.setText("Drehen")
        self.rotate_button.setCheckable(True)
        self.rotate_button.toggled.connect(self.set_rotating)
        toolbar.addWidget(self.rotate_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addWidget(self.plotter.interactor, stretch=1)

        self._timer = QTimer(self)
        self._timer.setInterval(ROTATION_INTERVAL_MS)
        self._timer.timeout.connect(self._rotate_step)

    @property
    def is_rotating(self) -> bool:
        return self._timer.isActive()

    def set_surfaces(self, surfaces: list[tuple[Structure, pv.PolyData]]) -> None:
        """Zeigt neue Oberflächen an und richtet die Kamera von vorne aus."""
        self.clear()
        for structure, surface in surfaces:
            if surface.n_points == 0:
                continue
            actor = self.plotter.add_mesh(
                surface,
                color=structure.color,
                opacity=structure.opacity,
                smooth_shading=True,
                name=structure.name,
                reset_camera=False,
            )
            actor.SetVisibility(structure.visible)
            self._actors[structure.name] = actor
        self.set_view("Vorne")

    def update_structure(self, structure: Structure) -> None:
        actor = self._actors.get(structure.name)
        if actor is None:
            return
        actor.prop.color = structure.color
        actor.prop.opacity = structure.opacity
        actor.SetVisibility(structure.visible)
        self.plotter.render()

    def clear(self) -> None:
        self.set_rotating(False)
        for name in self._actors:
            self.plotter.remove_actor(name, render=False)
        self._actors.clear()
        self.plotter.render()

    def set_view(self, name: str) -> None:
        direction, view_up = VIEWS[name]
        bounds = np.array(self.plotter.bounds).reshape(3, 2)
        center = bounds.mean(axis=1)
        distance = max(float(np.ptp(bounds, axis=1).max()), 1.0) * 3
        position = center + np.asarray(direction, dtype=float) * distance
        self.plotter.camera_position = [tuple(position), tuple(center), view_up]
        self.plotter.reset_camera()
        self.plotter.render()

    def set_rotating(self, rotating: bool) -> None:
        if rotating:
            self._timer.start()
        else:
            self._timer.stop()
        self.rotate_button.blockSignals(True)
        self.rotate_button.setChecked(rotating)
        self.rotate_button.blockSignals(False)

    def render_image(self) -> np.ndarray:
        """Aktuelle Ansicht als RGB-Bild der Form (Höhe, Breite, 3), uint8."""
        return np.asarray(self.plotter.screenshot(return_img=True))[..., :3]

    def close_viewer(self) -> None:
        self._timer.stop()
        self.plotter.close()

    def _rotate_step(self) -> None:
        self.plotter.camera.Azimuth(ROTATION_DEG)
        self.plotter.render()
