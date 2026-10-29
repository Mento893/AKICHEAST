"""Schnittebenen und Fensterung: radiologische Darstellung wie in 3D Slicer."""

import itertools

import numpy as np
import pytest

from akicheast3d.core import Volume
from akicheast3d.loading import load_series, scan
from akicheast3d.ui.slicing import (
    LABELS,
    Orientation,
    display_to_index,
    extract_slice,
    format_position,
    index_to_display,
    pixel_size_mm,
    slice_count,
)
from akicheast3d.ui.windowing import PRESETS, WindowPreset, apply_window


@pytest.fixture(scope="module")
def orientation_volume(phantom_dirs):
    (series,) = scan(phantom_dirs["orientierung"])
    return load_series(series).volume


@pytest.fixture(scope="module")
def markers(phantoms):
    return phantoms["orientierung"].expected["markers"]


def marker_center_in_image(volume, orientation, center, value):
    """Schicht durch den Würfel holen und Lage des Würfels im Bild als (Spalte, Zeile) relativ 0..1."""
    index = np.rint(volume.world_to_index(center)).astype(int)
    slice_index, _, _ = index_to_display(volume, orientation, tuple(index))
    plane = extract_slice(volume, orientation, slice_index)
    rows, columns = np.nonzero(plane == value)
    return columns.mean() / plane.shape[1], rows.mean() / plane.shape[0]


def test_axial_left_is_right_and_front_is_top(orientation_volume, markers):
    column, _ = marker_center_in_image(orientation_volume, Orientation.AXIAL, *markers["links"])
    assert column > 0.5
    _, row = marker_center_in_image(orientation_volume, Orientation.AXIAL, *markers["vorne"])
    assert row < 0.5


def test_coronal_left_is_right_and_head_is_top(orientation_volume, markers):
    column, _ = marker_center_in_image(orientation_volume, Orientation.CORONAL, *markers["links"])
    assert column > 0.5
    _, row = marker_center_in_image(orientation_volume, Orientation.CORONAL, *markers["kopf"])
    assert row < 0.5


def test_sagittal_front_is_left_and_head_is_top(orientation_volume, markers):
    column, _ = marker_center_in_image(orientation_volume, Orientation.SAGITTAL, *markers["vorne"])
    assert column < 0.5
    _, row = marker_center_in_image(orientation_volume, Orientation.SAGITTAL, *markers["kopf"])
    assert row < 0.5


def test_labels_match_display_direction():
    assert LABELS[Orientation.AXIAL].right == "L"
    assert LABELS[Orientation.AXIAL].top == "V"
    assert LABELS[Orientation.CORONAL].top == "K"
    assert LABELS[Orientation.SAGITTAL].left == "V"


def test_shapes_counts_and_pixel_sizes():
    volume = Volume(np.zeros((4, 5, 6), dtype=np.int16), spacing=(0.5, 0.8, 2.0))
    assert extract_slice(volume, Orientation.AXIAL, 0).shape == (5, 6)
    assert extract_slice(volume, Orientation.CORONAL, 0).shape == (4, 6)
    assert extract_slice(volume, Orientation.SAGITTAL, 0).shape == (4, 5)
    assert [slice_count(volume, o) for o in Orientation] == [4, 5, 6]
    assert pixel_size_mm(volume, Orientation.AXIAL) == (0.5, 0.8)
    assert pixel_size_mm(volume, Orientation.CORONAL) == (0.5, 2.0)
    assert pixel_size_mm(volume, Orientation.SAGITTAL) == (0.8, 2.0)


@pytest.mark.parametrize("orientation", list(Orientation))
def test_display_and_index_roundtrip(orientation):
    rng = np.random.default_rng(0)
    hu = rng.integers(-1000, 1000, size=(4, 5, 6)).astype(np.int16)
    volume = Volume(hu, spacing=(1.0, 1.0, 1.0))
    for i, j, k in itertools.product(range(6), range(5), range(4)):
        slice_index, column, row = index_to_display(volume, orientation, (i, j, k))
        assert display_to_index(volume, orientation, slice_index, column, row) == (i, j, k)
        plane = extract_slice(volume, orientation, slice_index)
        assert plane[row, column] == hu[k, j, i]


def test_format_position_uses_direction_letters():
    assert format_position((12.34, -4.0, 100.5)) == "L 12.3  V 4.0  K 100.5 mm"
    assert format_position((-1.0, 2.0, -3.0)) == "R 1.0  H 2.0  F 3.0 mm"


def test_window_maps_range_to_grey_values():
    preset = WindowPreset("Test", width=200, level=0)
    values = apply_window(np.array([-500, -100, 0, 100, 500]), preset)
    assert values.dtype == np.uint8
    assert list(values) == [0, 0, 128, 255, 255]


def test_presets():
    assert (PRESETS["Lunge"].width, PRESETS["Lunge"].level) == (1500, -600)
    assert (PRESETS["Weichteil"].width, PRESETS["Weichteil"].level) == (400, 40)
    assert (PRESETS["Knochen"].width, PRESETS["Knochen"].level) == (1800, 400)
