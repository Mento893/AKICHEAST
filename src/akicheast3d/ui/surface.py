"""Oberflächen aus Masken für die 3D-Ansicht, in Weltkoordinaten (mm).

Die Maske wird auf ihren Bereich zugeschnitten, leicht geglättet und an der
Grenze 0.5 als Oberfläche berechnet. Grosse, kompakte Strukturen werden innerhalb
der Schicht auf halbe Auflösung gemittelt, damit die Ansicht flüssig dreht.
Feine, verzweigte Strukturen wie Gefässe behalten die volle Auflösung.
Die Daten selbst werden dabei nicht verändert.
"""

from __future__ import annotations

import numpy as np
import pyvista as pv
from scipy import ndimage

from akicheast3d.core import Volume

SMOOTHING_MM = 0.6
"""Stärker geglättet verschwinden dünne Knochenwände, zum Beispiel an den Rippen."""
LARGE_VOXELS = 8_000_000
"""Ab dieser Anzahl Voxel im zugeschnittenen Bereich wird die Auflösung halbiert."""
FINE_PIXEL_MM = 0.8
"""Halbiert wird nur, wenn die Pixel feiner als dieser Wert sind."""
SPARSE_FRACTION = 0.01
"""Füllt eine Struktur weniger als 1 % ihres Bereichs, ist sie fein verzweigt
(zum Beispiel Gefässe) und behält die volle Auflösung."""
MARGIN = 2


def mask_to_surface(mask: np.ndarray, volume: Volume) -> pv.PolyData:
    box = _bounding_box(mask)
    if box is None:
        return pv.PolyData()

    data = mask[box].astype(np.float32)
    spacing = np.array(volume.spacing)  # (x, y, z)
    factor = 1
    sparse = data.mean() < SPARSE_FRACTION
    if data.size > LARGE_VOXELS and spacing[:2].min() < FINE_PIXEL_MM and not sparse:
        factor = 2
        data = _halve_in_plane(data)
    effective = spacing * (factor, factor, 1)
    # Rundherum mit Nullen auffüllen, damit Strukturen, die am Rand des Volumens
    # abgeschnitten sind, eine geschlossene Oberfläche bekommen.
    data = np.pad(data, MARGIN)

    sigma = [max(SMOOTHING_MM / s, 0.5) for s in effective[::-1]]  # Reihenfolge (k, j, i)
    data = ndimage.gaussian_filter(data, sigma)

    nk, nj, ni = data.shape
    grid = pv.ImageData(dimensions=(ni, nj, nk), spacing=tuple(effective))
    grid.point_data["mask"] = data.ravel()
    surface = grid.contour([0.5], scalars="mask", method="flying_edges")
    surface.clear_data()

    # Lokale Koordinaten in Weltkoordinaten umrechnen. Beim Mitteln liegt der
    # neue Voxelmittelpunkt zwischen den gemittelten Voxeln.
    k0, j0, i0 = (s.start for s in box)
    shift = (factor - 1) / 2
    start = np.array([i0 + shift, j0 + shift, k0]) * spacing - MARGIN * effective
    surface.points = np.asarray(volume.origin) + (surface.points + start) @ volume.direction.T
    return surface


def _bounding_box(mask: np.ndarray) -> tuple[slice, ...] | None:
    box = []
    for axis in range(3):
        other = tuple(a for a in range(3) if a != axis)
        indices = np.flatnonzero(mask.any(axis=other))
        if len(indices) == 0:
            return None
        box.append(slice(indices[0], indices[-1] + 1))
    return tuple(box)


def _halve_in_plane(data: np.ndarray) -> np.ndarray:
    """Mittelt je 2 x 2 Pixel innerhalb jeder Schicht."""
    nk, nj, ni = data.shape
    data = data[:, : nj - nj % 2, : ni - ni % 2]
    return data.reshape(nk, nj // 2, 2, ni // 2, 2).mean(axis=(2, 4))
