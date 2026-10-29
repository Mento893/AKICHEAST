"""Geometrie beim Zusammensetzen: jede Ausrichtung muss am selben Weltpunkt denselben Wert liefern."""

import numpy as np
import pytest

from akicheast3d.loading.geometry import build_volume

ORIENTATIONS = {
    "axial": ((1, 0, 0), (0, 1, 0)),
    "axial gespiegelt": ((-1, 0, 0), (0, -1, 0)),
    "koronal": ((1, 0, 0), (0, 0, -1)),
    "sagittal": ((0, 1, 0), (0, 0, -1)),
    "sagittal gespiegelt": ((0, -1, 0), (0, 0, 1)),
}


def world_points(positions, row, column, spacing, shape):
    """Weltpunkt jedes Pixels, Form (Schicht, Zeile, Spalte, 3)."""
    count, rows, columns = shape
    j, i = np.meshgrid(np.arange(rows), np.arange(columns), indexing="ij")
    row, column = np.asarray(row, float), np.asarray(column, float)
    offsets = i[..., None] * spacing[0] * row + j[..., None] * spacing[1] * column
    return positions[:, None, None, :] + offsets[None]


@pytest.mark.parametrize("name", ORIENTATIONS)
def test_axis_aligned_orientations_are_exact(name):
    row, column = ORIENTATIONS[name]
    shape = (4, 5, 6)
    spacing = (0.7, 0.9)
    dz = 1.5
    normal = np.cross(row, column)
    positions = np.array([10.0, -20.0, 30.0]) + np.arange(shape[0])[:, None] * dz * normal
    rng = np.random.default_rng(1)
    slices = rng.integers(-1000, 1000, size=shape).astype(np.int16)

    # Schichten in zufälliger Reihenfolge übergeben
    order = rng.permutation(shape[0])
    volume, warnings = build_volume(slices[order], positions[order], row, column, spacing)

    assert warnings == []
    assert np.array_equal(volume.direction, np.eye(3))
    points = world_points(positions, row, column, spacing, shape)
    for k, j, i in np.ndindex(shape):
        assert volume.hu_at_world(points[k, j, i]) == slices[k, j, i]


def test_duplicate_positions_are_skipped_with_warning():
    slices = np.zeros((3, 2, 2), dtype=np.int16)
    positions = np.array([[0, 0, 0], [0, 0, 1], [0, 0, 1]], dtype=float)
    volume, warnings = build_volume(slices, positions, (1, 0, 0), (0, 1, 0), (1.0, 1.0))
    assert volume.size == (2, 2, 2)
    assert "doppelte Schichten" in warnings[0]


def test_coarse_spacing_warns():
    slices = np.zeros((3, 2, 2), dtype=np.int16)
    positions = np.array([[0, 0, 0], [0, 0, 5], [0, 0, 10]], dtype=float)
    _, warnings = build_volume(slices, positions, (1, 0, 0), (0, 1, 0), (1.0, 1.0))
    assert len(warnings) == 1
    assert "grob" in warnings[0]


def test_oblique_slices_are_resampled_with_warning():
    angle = np.radians(20)
    row = (np.cos(angle), np.sin(angle), 0.0)
    column = (-np.sin(angle), np.cos(angle), 0.0)
    slices = np.full((5, 10, 10), 100, dtype=np.int16)
    positions = np.array([[0.0, 0.0, z] for z in range(5)])
    volume, warnings = build_volume(slices, positions, row, column, (1.0, 1.0))
    assert "Schräge Schichtführung" in warnings[0]
    assert np.array_equal(volume.direction, np.eye(3))
    # Mitte des gedrehten Quadrats
    center = 4.5 * np.asarray(row) + 4.5 * np.asarray(column) + (0, 0, 2)
    assert volume.hu_at_world(center) == 100


def test_single_position_raises():
    slices = np.zeros((2, 2, 2), dtype=np.int16)
    positions = np.zeros((2, 3))
    with pytest.raises(ValueError):
        build_volume(slices, positions, (1, 0, 0), (0, 1, 0), (1.0, 1.0))
