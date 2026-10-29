"""Schwellenwert-Segmentierer am Thorax-Phantom mit bekannten Masken."""

import numpy as np
import pytest

from akicheast3d.core import segmenters
from akicheast3d.segmentation.threshold import AIRWAYS, BODY, BONE, LUNG, ThresholdSegmenter
from tests.phantoms.thorax import thorax_phantom


def dice(a: np.ndarray, b: np.ndarray) -> float:
    return 2 * np.count_nonzero(a & b) / (np.count_nonzero(a) + np.count_nonzero(b))


@pytest.fixture(scope="module")
def phantom():
    return thorax_phantom()


@pytest.fixture(scope="module")
def result(phantom):
    structures = ThresholdSegmenter().segment(phantom.volume)
    return {s.name: s for s in structures}


def test_is_registered():
    import akicheast3d.segmentation  # noqa: F401

    assert ThresholdSegmenter.name in segmenters


def test_returns_four_structures_in_order(phantom):
    structures = ThresholdSegmenter().segment(phantom.volume)
    assert [s.name for s in structures] == [LUNG, AIRWAYS, BONE, BODY]
    for structure in structures:
        assert structure.mask.shape == phantom.volume.hu.shape
        assert structure.visible


def test_body(phantom, result):
    assert dice(result[BODY].mask, phantom.body) > 0.98
    assert not (result[BODY].mask & phantom.table).any()


def test_lung(phantom, result):
    lung = result[LUNG].mask
    assert dice(lung, phantom.lung) > 0.95
    assert not (lung & phantom.stomach).any()
    assert np.count_nonzero(lung & phantom.airways) < 0.05 * np.count_nonzero(phantom.airways)


def test_airways(phantom, result):
    airways = result[AIRWAYS].mask
    assert dice(airways, phantom.airways) > 0.8
    # Keine Luft aus der Lunge oder dem Magen
    assert np.count_nonzero(airways & phantom.lung) < 0.1 * np.count_nonzero(phantom.airways)
    assert not (airways & phantom.stomach).any()


def test_bone(phantom, result):
    bone = result[BONE].mask
    assert dice(bone, phantom.bone) > 0.95
    assert not (bone & phantom.table).any()
    assert not (bone & phantom.calcification).any()


def test_progress(phantom):
    reported = []
    ThresholdSegmenter().segment(phantom.volume, reported.append)
    assert reported == sorted(reported)
    assert reported[-1] == 1.0


def test_volume_is_not_changed(phantom):
    before = phantom.volume.hu.copy()
    ThresholdSegmenter().segment(phantom.volume)
    assert np.array_equal(phantom.volume.hu, before)


def test_no_trachea_gives_empty_airways(phantom):
    from akicheast3d.core import Volume

    hu = phantom.volume.hu.copy()
    hu[phantom.airways] = -850
    volume = Volume(hu, phantom.volume.spacing, phantom.volume.origin)
    result = {s.name: s for s in ThresholdSegmenter().segment(volume)}
    assert result[AIRWAYS].voxel_count == 0
    assert result[LUNG].voxel_count > 0


def test_lidc_volumes_are_plausible(lidc_dir):
    """Grobe Plausibilität an echten, anonymisierten Lungen-CTs (keine Diagnose)."""
    from akicheast3d.loading import load_series, scan

    for directory in sorted(p for p in lidc_dir.iterdir() if p.is_dir()):
        (series,) = scan(directory)
        volume = load_series(series).volume
        ml = volume.voxel_volume_mm3 / 1000
        result = {s.name: s.voxel_count * ml for s in ThresholdSegmenter().segment(volume)}
        assert 2000 < result[LUNG] < 8000, directory.name
        assert 10 < result[AIRWAYS] < 300, directory.name
        assert result[BONE] > 300, directory.name
        assert result[BODY] > result[LUNG], directory.name
