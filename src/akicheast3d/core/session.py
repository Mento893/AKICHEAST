"""Sitzung: eine geöffnete Serie mit Strukturen, Markierungen und Ansichten.

Jedes Öffnen einer Serie erzeugt eine neue Sitzung. Die Sitzung enthält
keine Patientendaten wie Name, Geburtsdatum oder Patienten-ID.
"""

from __future__ import annotations

from dataclasses import dataclass

from akicheast3d.core.structure import Structure
from akicheast3d.core.volume import Vector3, Volume


@dataclass
class Marker:
    """Markierung an einem Weltpunkt in mm."""

    position_mm: Vector3
    text: str = ""


@dataclass
class SavedView:
    """Gespeicherte Kameraeinstellung der 3D-Ansicht, alles in mm."""

    name: str
    camera_position: Vector3
    focal_point: Vector3
    view_up: Vector3


class Session:
    def __init__(
        self,
        volume: Volume,
        series_description: str = "",
        warnings: list[str] | None = None,
    ) -> None:
        self.volume = volume
        self.series_description = series_description
        self.warnings: list[str] = list(warnings or [])
        self.markers: list[Marker] = []
        self.views: dict[str, SavedView] = {}
        self._structures: dict[str, Structure] = {}

    @property
    def structures(self) -> list[Structure]:
        """Alle Strukturen in der Reihenfolge, in der sie hinzugefügt wurden."""
        return list(self._structures.values())

    def structure(self, name: str) -> Structure:
        try:
            return self._structures[name]
        except KeyError:
            raise KeyError(f"Keine Struktur mit dem Namen '{name}'.") from None

    def add_structure(self, structure: Structure) -> None:
        if structure.mask.shape != self.volume.hu.shape:
            raise ValueError(
                f"Die Maske von '{structure.name}' passt nicht zur Grösse des Volumens."
            )
        if structure.name in self._structures:
            raise ValueError(f"Die Struktur '{structure.name}' gibt es bereits.")
        self._structures[structure.name] = structure

    def remove_structure(self, name: str) -> None:
        self.structure(name)
        del self._structures[name]

    def clear_structures(self) -> None:
        self._structures.clear()

    def add_marker(self, marker: Marker) -> None:
        self.markers.append(marker)

    def save_view(self, view: SavedView) -> None:
        """Speichert eine Ansicht. Eine Ansicht mit gleichem Namen wird ersetzt."""
        self.views[view.name] = view
