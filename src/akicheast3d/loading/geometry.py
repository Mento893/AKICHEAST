"""Aus einzelnen Schichten ein Volumen mit korrekter Geometrie bauen.

Die Schichten werden nach ihrer Position entlang der Schichtnormalen sortiert.
Danach liegt jedes Volumen gleich im Speicher: Achse i zeigt nach links (+x),
j nach hinten (+y), k zum Kopf (+z). Die Ausrichtung ist also immer die
Einheitsmatrix.

Reine Achsvertauschungen und Spiegelungen sind exakt. Fehlende Schichten,
ungleiche Abstände, gekippte Gantry und schräge Schichtführung werden auf ein
gleichmässiges Gitter interpoliert und mit einer Warnung gemeldet.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from akicheast3d.core import Volume

GAP_FACTOR = 1.5
"""Ein Abstand über dem 1.5-fachen des üblichen gilt als fehlende Schicht."""
SPACING_TOLERANCE_MM = 0.02
SPACING_TOLERANCE_REL = 0.02
TILT_TOLERANCE_DEG = 0.5
AXIS_TOLERANCE = 1e-3
COARSE_SPACING_MM = 3.0
MAX_LISTED_GAPS = 3


def build_volume(
    slices: np.ndarray,
    positions: np.ndarray,
    row: np.ndarray,
    column: np.ndarray,
    pixel_spacing: tuple[float, float],
) -> tuple[Volume, list[str]]:
    """Baut ein Volumen aus Schichten in beliebiger Reihenfolge.

    slices:        HU-Werte, Form (Anzahl, Zeilen, Spalten)
    positions:     ImagePositionPatient jeder Schicht, Form (Anzahl, 3)
    row, column:   Richtung der Zeilen und Spalten (ImageOrientationPatient)
    pixel_spacing: Abstand (x, y) zwischen Spalten und Zeilen in mm
    """
    row = _unit(row)
    column = _unit(column)
    normal = _unit(np.cross(row, column))
    positions = np.asarray(positions, dtype=float)

    order = np.argsort(positions @ normal, kind="stable")
    slices, positions = slices[order], positions[order]

    warnings: list[str] = []
    projection = positions @ normal
    keep = np.concatenate([[True], np.diff(projection) > 1e-3])
    if not keep.all():
        warnings.append(
            f"{np.count_nonzero(~keep)} doppelte Schichten an derselben Position wurden übersprungen."
        )
        slices, positions, projection = slices[keep], positions[keep], projection[keep]
    if len(slices) < 2:
        raise ValueError("Für ein Volumen braucht es mindestens zwei Schichten an verschiedenen Positionen.")

    steps = np.diff(projection)
    dz = float(np.median(steps))
    gaps = steps > GAP_FACTOR * dz
    tolerance = max(SPACING_TOLERANCE_MM, SPACING_TOLERANCE_REL * dz)
    uneven = ~gaps & (np.abs(steps - dz) > tolerance)

    stack = _unit(positions[-1] - positions[0])
    tilt = float(np.degrees(np.arccos(np.clip(abs(stack @ normal), 0.0, 1.0))))
    tilted = tilt > TILT_TOLERANCE_DEG
    direction = np.column_stack([row, column, normal])
    aligned = _is_axis_aligned(direction)

    if gaps.any():
        warnings.append(_gap_warning(positions, gaps, steps))
    if uneven.any():
        warnings.append(
            f"Ungleiche Schichtabstände ({steps.min():.2f} bis {steps.max():.2f} mm). "
            f"Die Serie wurde auf {dz:.2f} mm umgerechnet."
        )
    if tilted:
        warnings.append(
            f"Gekippte Gantry ({tilt:.1f}°). Die Serie wurde auf ein gerades Gitter umgerechnet."
        )
    elif not aligned:
        warnings.append("Schräge Schichtführung. Die Serie wurde auf ein gerades Gitter umgerechnet.")
    if dz > COARSE_SPACING_MM:
        warnings.append(
            f"Schichtabstand {dz:.1f} mm: Das 3D-Modell wird grob. "
            "Empfohlen ist eine Dünnschicht-Serie mit ca. 1 mm."
        )

    if gaps.any() or uneven.any() or tilted or not aligned:
        volume = _resample(slices, positions, row, column, pixel_spacing, dz)
    else:
        volume = _reorient(slices, positions[0], direction, (*pixel_spacing, dz))
    return volume, warnings


def _unit(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=float)
    return vector / np.linalg.norm(vector)


def _is_axis_aligned(direction: np.ndarray) -> bool:
    rounded = np.rint(np.abs(direction))
    is_permutation = np.array_equal(rounded.sum(axis=0), [1, 1, 1]) and np.array_equal(
        rounded.sum(axis=1), [1, 1, 1]
    )
    return is_permutation and np.allclose(np.abs(direction), rounded, atol=AXIS_TOLERANCE)


def _gap_warning(positions: np.ndarray, gaps: np.ndarray, steps: np.ndarray) -> str:
    indices = np.flatnonzero(gaps)
    if len(indices) > MAX_LISTED_GAPS:
        where = f"an {len(indices)} Stellen"
    else:
        parts = []
        for i in indices:
            z = (positions[i, 2] + positions[i + 1, 2]) / 2
            parts.append(f"Lücke von {steps[i]:.1f} mm bei z = {z:.1f} mm")
        where = ", ".join(parts)
    return f"Fehlende Schichten: {where}. Der Bereich wurde interpoliert."


def _reorient(
    slices: np.ndarray, origin: np.ndarray, direction: np.ndarray, spacing: tuple[float, float, float]
) -> Volume:
    """Vertauscht und spiegelt Achsen exakt, bis die Ausrichtung die Einheitsmatrix ist."""
    data = np.asarray(slices).transpose(2, 1, 0)  # Reihenfolge (i, j, k)
    origin = np.asarray(origin, dtype=float).copy()
    world_axis = np.argmax(np.abs(direction), axis=0)

    for axis in range(3):
        if direction[world_axis[axis], axis] < 0:
            data = np.flip(data, axis=axis)
            origin += direction[:, axis] * (data.shape[axis] - 1) * spacing[axis]

    source_axis = np.argsort(world_axis)  # für x, y, z: welche Achse der Schichten
    data = data.transpose(source_axis)
    new_spacing = tuple(float(spacing[a]) for a in source_axis)
    hu = np.ascontiguousarray(data.transpose(2, 1, 0))
    return Volume(hu, new_spacing, tuple(np.round(origin, 6)))


def _resample(
    slices: np.ndarray,
    positions: np.ndarray,
    row: np.ndarray,
    column: np.ndarray,
    pixel_spacing: tuple[float, float],
    dz: float,
) -> Volume:
    """Interpoliert die Schichten linear auf ein gerades, gleichmässiges Gitter."""
    count, rows, columns = slices.shape
    dx, dy = pixel_spacing
    origin = positions[0]
    stack = _unit(positions[-1] - positions[0])
    offsets = (positions - origin) @ stack

    # Weltpunkt = origin + a * row + b * column + t * stack
    to_local = np.linalg.inv(np.column_stack([row, column, stack]))

    corners = np.array(
        [
            origin + a * row + b * column + t * stack
            for a in (0.0, (columns - 1) * dx)
            for b in (0.0, (rows - 1) * dy)
            for t in (0.0, offsets[-1])
        ]
    )
    spacing = _target_spacing(row, column, stack, (dx, dy, dz))
    low, high = corners.min(axis=0), corners.max(axis=0)
    size = np.floor((high - low) / spacing + 1e-6).astype(int) + 1

    xs = low[0] + np.arange(size[0]) * spacing[0]
    ys = low[1] + np.arange(size[1]) * spacing[1]
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")
    fill = float(slices.min())
    source = slices.astype(np.float32)
    hu = np.empty((size[2], size[1], size[0]), dtype=np.int16)

    for k in range(size[2]):
        z = low[2] + k * spacing[2]
        world = np.stack([grid_x, grid_y, np.full_like(grid_x, z)], axis=-1) - origin
        a, b, t = np.moveaxis(world @ to_local.T, -1, 0)
        index_k = np.interp(t, offsets, np.arange(count), left=-1.0, right=float(count))
        coordinates = np.stack([index_k, b / dy, a / dx])
        plane = ndimage.map_coordinates(source, coordinates, order=1, mode="constant", cval=fill)
        hu[k] = _to_int16(plane)

    return Volume(hu, tuple(spacing), tuple(np.round(low, 6)))


def _target_spacing(
    row: np.ndarray, column: np.ndarray, stack: np.ndarray, spacing: tuple[float, float, float]
) -> np.ndarray:
    """Ordnet jeder Weltachse den Abstand der Schichtachse zu, die am besten passt."""
    result = np.full(3, min(spacing))
    taken: set[int] = set()
    for vector, value in zip((row, column, stack), spacing):
        axis = int(np.argmax(np.abs(vector)))
        if axis not in taken:
            result[axis] = value
            taken.add(axis)
    return result


def _to_int16(values: np.ndarray) -> np.ndarray:
    info = np.iinfo(np.int16)
    return np.clip(np.rint(values), info.min, info.max).astype(np.int16)
