"""Struktur: ein getrennter Teil des Volumens, zum Beispiel Lunge oder Knochen."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Color = tuple[float, float, float]


@dataclass(eq=False)
class Structure:
    """Maske mit Darstellungseigenschaften.

    Die Maske hat dieselbe Form (k, j, i) wie das zugehörige Volumen.
    Farbe als RGB mit Werten von 0 bis 1, Transparenz als Deckkraft von 0 bis 1.
    """

    name: str
    mask: np.ndarray
    color: Color
    opacity: float = 1.0
    visible: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Eine Struktur braucht einen Namen.")
        self.mask = np.asarray(self.mask, dtype=bool)
        if self.mask.ndim != 3:
            raise ValueError("Die Maske muss dreidimensional sein.")
        color = tuple(float(c) for c in self.color)
        if len(color) != 3 or not all(0.0 <= c <= 1.0 for c in color):
            raise ValueError("Die Farbe braucht drei Werte zwischen 0 und 1.")
        self.color = color
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("Die Deckkraft muss zwischen 0 und 1 liegen.")

    @property
    def voxel_count(self) -> int:
        return int(np.count_nonzero(self.mask))
