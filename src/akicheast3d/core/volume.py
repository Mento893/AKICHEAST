"""Volumen: Dichtewerte in Hounsfield-Einheiten mit Geometrie in Millimetern.

Konventionen:
- Das Array `hu` hat die Form (k, j, i) = (Schicht, Zeile, Spalte), wie bei SimpleITK.
- Indizes, `spacing` und `origin` stehen in der Reihenfolge (i, j, k) bzw. (x, y, z).
- Weltkoordinaten sind DICOM-Patientenkoordinaten (LPS):
  +x zeigt nach links, +y nach hinten, +z zum Kopf.
- `direction` ist eine orthonormale 3x3-Matrix. Ihre Spalten sind die Richtungen
  der Achsen i, j und k in Weltkoordinaten.
- `origin` ist der Mittelpunkt des Voxels (0, 0, 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

Vector3 = tuple[float, float, float]


@dataclass(frozen=True, eq=False)
class Volume:
    hu: np.ndarray
    spacing: Vector3
    origin: Vector3 = (0.0, 0.0, 0.0)
    direction: np.ndarray = field(default_factory=lambda: np.eye(3))

    def __post_init__(self) -> None:
        hu = np.asarray(self.hu)
        if hu.ndim != 3:
            raise ValueError("Das Volumen muss dreidimensional sein.")
        # Die Dichtewerte werden nach dem Laden nicht mehr verändert.
        hu.flags.writeable = False

        spacing = _vector3(self.spacing, "spacing")
        if min(spacing) <= 0:
            raise ValueError("Die Voxelabstände müssen grösser als 0 sein.")
        origin = _vector3(self.origin, "origin")

        direction = np.array(self.direction, dtype=float)
        if direction.shape != (3, 3):
            raise ValueError("direction muss eine 3x3-Matrix sein.")
        if not np.allclose(direction.T @ direction, np.eye(3), atol=1e-4):
            raise ValueError("direction muss orthonormal sein.")
        direction.flags.writeable = False

        object.__setattr__(self, "hu", hu)
        object.__setattr__(self, "spacing", spacing)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "direction", direction)

    @property
    def size(self) -> tuple[int, int, int]:
        """Anzahl Voxel in der Reihenfolge (i, j, k)."""
        nk, nj, ni = self.hu.shape
        return (ni, nj, nk)

    @property
    def extent_mm(self) -> Vector3:
        """Ausdehnung des Voxelgitters entlang (i, j, k) in mm."""
        return tuple(n * s for n, s in zip(self.size, self.spacing))

    @property
    def voxel_volume_mm3(self) -> float:
        sx, sy, sz = self.spacing
        return sx * sy * sz

    def index_to_world(self, index: np.ndarray | tuple) -> np.ndarray:
        """Wandelt Indizes (i, j, k) in Weltkoordinaten in mm um.

        Nimmt einen einzelnen Index der Form (3,) oder viele der Form (N, 3).
        """
        index = np.asarray(index, dtype=float)
        scaled = index * np.asarray(self.spacing)
        return np.asarray(self.origin) + scaled @ self.direction.T

    def world_to_index(self, point: np.ndarray | tuple) -> np.ndarray:
        """Wandelt Weltkoordinaten in mm in kontinuierliche Indizes (i, j, k) um."""
        point = np.asarray(point, dtype=float)
        local = (point - np.asarray(self.origin)) @ self.direction
        return local / np.asarray(self.spacing)

    def contains_index(self, index: np.ndarray | tuple) -> bool:
        """Prüft, ob ein ganzzahliger Index (i, j, k) im Volumen liegt."""
        index = np.asarray(index)
        return bool(np.all(index >= 0) and np.all(index < np.asarray(self.size)))

    def hu_at_world(self, point: np.ndarray | tuple) -> float:
        """Dichtewert des nächstgelegenen Voxels an einem Weltpunkt."""
        index = np.rint(self.world_to_index(point)).astype(int)
        if not self.contains_index(index):
            raise IndexError("Der Punkt liegt ausserhalb des Volumens.")
        i, j, k = index
        return float(self.hu[k, j, i])


def _vector3(values: tuple, label: str) -> Vector3:
    result = tuple(float(v) for v in values)
    if len(result) != 3:
        raise ValueError(f"{label} braucht genau drei Werte.")
    return result
