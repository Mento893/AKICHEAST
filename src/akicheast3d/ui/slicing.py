"""Schnittebenen durch das Volumen in radiologischer Darstellung.

Das Volumen liegt nach dem Laden immer gleich im Speicher: i nach links (+x),
j nach hinten (+y), k zum Kopf (+z). Die Darstellung folgt der Radiologie
und 3D Slicer:

- axial:    von den Füssen her gesehen, rechts im Bild ist links im Patienten, vorne oben
- koronal:  von vorne gesehen, rechts im Bild ist links im Patienten, Kopf oben
- sagittal: von links gesehen, vorne links im Bild, Kopf oben

Bildkoordinaten sind (Spalte, Zeile), Zeile 0 ist oben.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from akicheast3d.core import Volume


class Orientation(Enum):
    AXIAL = "Axial"
    CORONAL = "Koronal"
    SAGITTAL = "Sagittal"


@dataclass(frozen=True)
class EdgeLabels:
    """Beschriftung der Bildränder: R/L, V/H (vorne/hinten), K/F (Kopf/Fuss)."""

    left: str
    right: str
    top: str
    bottom: str


AXIS = {Orientation.AXIAL: 2, Orientation.CORONAL: 1, Orientation.SAGITTAL: 0}
"""Index-Achse (0 = i, 1 = j, 2 = k), entlang der geblättert wird."""

LABELS = {
    Orientation.AXIAL: EdgeLabels("R", "L", "V", "H"),
    Orientation.CORONAL: EdgeLabels("R", "L", "K", "F"),
    Orientation.SAGITTAL: EdgeLabels("V", "H", "K", "F"),
}


def slice_count(volume: Volume, orientation: Orientation) -> int:
    return volume.size[AXIS[orientation]]


def extract_slice(volume: Volume, orientation: Orientation, index: int) -> np.ndarray:
    """Dichtewerte einer Schicht in Darstellungsrichtung, Form (Zeilen, Spalten)."""
    hu = volume.hu
    if orientation is Orientation.AXIAL:
        return hu[index]
    if orientation is Orientation.CORONAL:
        return hu[::-1, index, :]
    return hu[::-1, :, index]


def pixel_size_mm(volume: Volume, orientation: Orientation) -> tuple[float, float]:
    """Grösse eines Bildpunkts (Breite, Höhe) in mm."""
    dx, dy, dz = volume.spacing
    if orientation is Orientation.AXIAL:
        return dx, dy
    if orientation is Orientation.CORONAL:
        return dx, dz
    return dy, dz


def display_to_index(
    volume: Volume, orientation: Orientation, slice_index: int, column: int, row: int
) -> tuple[int, int, int]:
    """Bildpunkt (Spalte, Zeile) einer Schicht als Voxelindex (i, j, k)."""
    top_k = volume.size[2] - 1
    if orientation is Orientation.AXIAL:
        return column, row, slice_index
    if orientation is Orientation.CORONAL:
        return column, slice_index, top_k - row
    return slice_index, column, top_k - row


def index_to_display(
    volume: Volume, orientation: Orientation, index: tuple[int, int, int]
) -> tuple[int, int, int]:
    """Voxelindex (i, j, k) als (Schicht, Spalte, Zeile) dieser Ansicht."""
    i, j, k = index
    top_k = volume.size[2] - 1
    if orientation is Orientation.AXIAL:
        return k, i, j
    if orientation is Orientation.CORONAL:
        return j, i, top_k - k
    return i, j, top_k - k


def format_position(world: np.ndarray) -> str:
    """Weltpunkt mit Richtungsbuchstaben, zum Beispiel 'L 12.3  H 4.0  K 100.5 mm'.

    Entspricht der Anzeige in 3D Slicer: L/R, H/V statt P/A, K/F statt S/I.
    """
    x, y, z = (float(v) for v in world)
    parts = [
        f"{'L' if x >= 0 else 'R'} {abs(x):.1f}",
        f"{'H' if y >= 0 else 'V'} {abs(y):.1f}",
        f"{'K' if z >= 0 else 'F'} {abs(z):.1f}",
    ]
    return "  ".join(parts) + " mm"
