"""Laden der öffentlichen LIDC-IDRI-Serien, gegengeprüft mit SimpleITK.

Wird übersprungen, wenn testdata/lidc_idri fehlt.
"""

import numpy as np
import pytest
import SimpleITK as sitk

from akicheast3d.loading import SeriesKind, load_series, scan

EXPECTED = {
    "LIDC-IDRI-0508": (250, 1.0),
    "LIDC-IDRI-0709": (100, 3.0),
    "LIDC-IDRI-0736": (250, 1.0),
    "LIDC-IDRI-0999": (250, 1.25),
}


@pytest.fixture(scope="module", params=sorted(EXPECTED))
def lidc_case(request, lidc_dir):
    directory = lidc_dir / request.param
    if not directory.is_dir():
        pytest.skip(f"{request.param} fehlt")
    (series,) = scan(directory)
    return request.param, directory, series, load_series(series)


def test_series_is_found(lidc_case):
    name, _, series, _ = lidc_case
    assert series.kind is SeriesKind.VOLUME
    assert series.slice_count == EXPECTED[name][0]


def test_geometry_without_warnings(lidc_case):
    name, _, _, session = lidc_case
    volume = session.volume
    assert session.warnings == []
    assert volume.size[2] == EXPECTED[name][0]
    assert volume.spacing[2] == pytest.approx(EXPECTED[name][1], abs=1e-3)
    assert np.array_equal(volume.direction, np.eye(3))


def test_same_values_as_simpleitk(lidc_case):
    """Der Referenzleser SimpleITK muss dieselben HU-Werte und dieselbe Geometrie liefern."""
    _, directory, _, session = lidc_case
    volume = session.volume
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(reader.GetGDCMSeriesFileNames(str(directory)))
    image = reader.Execute()

    assert np.allclose(np.array(image.GetDirection()).reshape(3, 3), np.eye(3), atol=1e-6)
    assert image.GetSpacing() == pytest.approx(volume.spacing, abs=1e-4)
    assert image.GetOrigin() == pytest.approx(volume.origin, abs=1e-3)
    assert np.array_equal(sitk.GetArrayFromImage(image), volume.hu)
