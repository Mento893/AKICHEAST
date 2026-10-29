"""Schwellenwert-Segmentierer: trennt Körperumriss, Lunge, Atemwege und Knochen über Dichtewerte.

Ablauf:
1. Körper: alles über -500 HU, grösstes zusammenhängendes Gebiet, Löcher pro Schicht gefüllt.
2. Luft im Körper: unter -400 HU. Die grossen Gebiete sind Lunge mit Atemwegen,
   kleine Gebiete wie Luft im Magen fallen weg.
3. Atemwege: Startpunkt in der Luftröhre zuoberst im Bild. Von dort wachsen sie
   über sehr dunkle Voxel. Die Schwelle wird schrittweise gelockert, solange das
   Gebiet nicht sprunghaft in die Lunge "ausläuft".
4. Lunge: Luft im Körper ohne Atemwege, Gefässe im Inneren aufgefüllt.
5. Knochen: über 200 HU im Körper, kleine Splitter entfernt.

Grenze: Gefässe mit Kontrastmittel können über 200 HU liegen und erscheinen dann als Knochen.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.segmentation import flood

from akicheast3d.core import ProgressCallback, Segmenter, Structure, Volume
from akicheast3d.core.registry import segmenters

BODY_MIN_HU = -500
AIR_MAX_HU = -400
LUNG_MIN_FRACTION = 0.2
"""Ein Luftgebiet zählt zur Lunge, wenn es mindestens 20 % des grössten Gebiets hat."""

AIRWAY_THRESHOLDS_HU = (-990, -970, -950, -930, -910)
AIRWAY_MAX_ML = 300.0
AIRWAY_MAX_GROWTH = 3.0
"""Wächst das Gebiet beim Lockern der Schwelle um mehr als das Dreifache, ist es ausgelaufen."""
AIRWAY_MIN_ML = 2.0
"""Erst ab dieser Grösse wird das Wachstum geprüft. Bei verrauschter Luft ist das
Gebiet bei strengen Schwellen sonst winzig und jeder Schritt wirkt wie ein Sprung."""
AIRWAY_WALL_HU = (-700, -400)
"""Mischvoxel am Rand der Atemwege. Lungengewebe liegt darunter und wird nicht angefügt."""
TRACHEA_AREA_MM2 = (30.0, 1000.0)
TRACHEA_MAX_OFFSET = 0.2
"""Die Luftröhre liegt höchstens 20 % der Körperbreite seitlich der Körpermitte."""
TRACHEA_SEARCH_MM = 60.0

BONE_MIN_HU = 200
BONE_MIN_ML = 0.5

LUNG = "Lunge"
AIRWAYS = "Atemwege"
BONE = "Knochen"
BODY = "Körperumriss"

COLORS = {
    LUNG: ((0.55, 0.75, 0.95), 0.6),
    AIRWAYS: ((0.35, 0.85, 0.55), 1.0),
    BONE: ((0.93, 0.90, 0.80), 1.0),
    BODY: ((0.95, 0.75, 0.65), 0.2),
}


@segmenters.register
class ThresholdSegmenter(Segmenter):
    name = "Schwellenwerte"

    def segment(
        self, volume: Volume, progress: ProgressCallback | None = None
    ) -> list[Structure]:
        report = progress or (lambda value: None)
        hu = volume.hu
        voxel_ml = volume.voxel_volume_mm3 / 1000.0

        body = _fill_slices(_largest_components(hu > BODY_MIN_HU, 1.0))
        report(0.3)

        air = body & (hu < AIR_MAX_HU)
        lung_air = _largest_components(air, LUNG_MIN_FRACTION)
        report(0.5)

        airways = _airways(hu, body, volume, voxel_ml)
        report(0.75)

        lung = _fill_slices(lung_air & ~airways) & ~airways
        bone = _remove_small(body & (hu > BONE_MIN_HU), BONE_MIN_ML / voxel_ml)
        report(1.0)

        masks = {LUNG: lung, AIRWAYS: airways, BONE: bone, BODY: body}
        return [
            Structure(name, mask, color=COLORS[name][0], opacity=COLORS[name][1])
            for name, mask in masks.items()
        ]


def _largest_components(mask: np.ndarray, min_fraction: float) -> np.ndarray:
    """Behält das grösste zusammenhängende Gebiet und alle mit mindestens `min_fraction` davon."""
    labels, count = ndimage.label(mask)
    if count == 0:
        return np.zeros_like(mask)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return (sizes >= min_fraction * sizes.max())[labels]


def _remove_small(mask: np.ndarray, min_voxels: float) -> np.ndarray:
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return (sizes >= min_voxels)[labels]


def _fill_slices(mask: np.ndarray) -> np.ndarray:
    """Füllt Löcher in jeder axialen Schicht.

    Der Hintergrund wird Schicht für Schicht beschriftet (keine Verbindung entlang z).
    Was den Bildrand nicht berührt, ist ein Loch.
    """
    structure = np.zeros((3, 3, 3), dtype=bool)
    structure[1] = ndimage.generate_binary_structure(2, 1)
    labels, count = ndimage.label(~mask, structure)
    outside = np.zeros(count + 1, dtype=bool)
    for edge in (labels[:, 0, :], labels[:, -1, :], labels[:, :, 0], labels[:, :, -1]):
        outside[np.unique(edge)] = True
    outside[0] = False
    return ~outside[labels]


def _airways(hu: np.ndarray, body: np.ndarray, volume: Volume, voxel_ml: float) -> np.ndarray:
    seed = _find_trachea(hu, body, volume)
    if seed is None:
        return np.zeros_like(body)

    accepted = None
    previous_ml = 0.0
    for threshold in AIRWAY_THRESHOLDS_HU:
        region = _region_at(body & (hu < threshold), seed)
        size_ml = np.count_nonzero(region) * voxel_ml
        if size_ml > AIRWAY_MAX_ML:
            break
        if previous_ml >= AIRWAY_MIN_ML and size_ml > AIRWAY_MAX_GROWTH * previous_ml:
            break
        accepted, previous_ml = region, size_ml

    if accepted is None or not accepted.any():
        return np.zeros_like(body)
    # Mischvoxel am Rand dazunehmen, damit die Wand der Atemwege nicht ausgefranst wirkt.
    # Nur im Bereich der Atemwege rechnen, das spart viel Zeit.
    box = _bounding_box(accepted, margin=1)
    low, high = AIRWAY_WALL_HU
    wall = (hu[box] > low) & (hu[box] < high) & body[box]
    result = np.zeros_like(body)
    result[box] = accepted[box] | (ndimage.binary_dilation(accepted[box]) & wall)
    return result


def _bounding_box(mask: np.ndarray, margin: int) -> tuple[slice, ...]:
    box = []
    for axis in range(mask.ndim):
        other = tuple(a for a in range(mask.ndim) if a != axis)
        indices = np.flatnonzero(mask.any(axis=other))
        box.append(slice(max(indices[0] - margin, 0), indices[-1] + margin + 1))
    return tuple(box)


def _region_at(mask: np.ndarray, seed: tuple[int, int, int]) -> np.ndarray:
    """Zusammenhängendes Gebiet um den Startpunkt (Nachbarn über Flächen)."""
    if not mask[seed]:
        return np.zeros_like(mask)
    return flood(mask, seed, connectivity=1)


def _find_trachea(hu: np.ndarray, body: np.ndarray, volume: Volume) -> tuple[int, int, int] | None:
    """Sucht in den obersten Schichten einen Luftkreis nahe der Körpermitte."""
    dx, dy, dz = volume.spacing
    pixel_mm2 = dx * dy
    low, high = (area / pixel_mm2 for area in TRACHEA_AREA_MM2)
    top = body.shape[0] - 1
    search = max(1, int(round(TRACHEA_SEARCH_MM / dz)))

    for k in range(top, max(top - search, -1), -1):
        if not body[k].any():
            continue
        columns = np.flatnonzero(body[k].any(axis=0))
        center, width = (columns[0] + columns[-1]) / 2, columns[-1] - columns[0] + 1

        labels, count = ndimage.label(body[k] & (hu[k] < AIRWAY_THRESHOLDS_HU[-1]))
        if count == 0:
            continue
        areas = np.bincount(labels.ravel())
        candidates = np.flatnonzero((areas >= low) & (areas <= high))
        candidates = candidates[candidates > 0]
        if len(candidates) == 0:
            continue
        centers = ndimage.center_of_mass(np.ones_like(labels), labels, candidates)
        central = [
            label
            for label, (_, col) in zip(candidates, centers)
            if abs(col - center) <= TRACHEA_MAX_OFFSET * width
        ]
        if central:
            # Startpunkt ist der dunkelste Voxel im grössten Querschnitt
            label = max(central, key=lambda c: areas[c])
            rows, cols = np.nonzero(labels == label)
            darkest = np.argmin(hu[k, rows, cols])
            return (k, int(rows[darkest]), int(cols[darkest]))
    return None
