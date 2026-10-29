"""Prüft, dass die Phantome als DICOM genau die bekannten Werte enthalten.

Gelesen wird hier unabhängig vom Programm: einmal direkt mit pydicom und
einmal mit SimpleITK als Referenz.
"""

import math

import numpy as np
import pydicom
import pytest
import SimpleITK as sitk
from pydicom.uid import ImplicitVRLittleEndian

from tests.phantoms.generator import (
    FAKE_PATIENT_ID,
    FAKE_PATIENT_NAME,
    GRID_SIZE,
    GRID_SPACING,
)


def read_series(directory):
    """Liest eine Serie mit pydicom, sortiert nach Position entlang der Schichtnormalen."""
    datasets = [pydicom.dcmread(p) for p in directory.glob("*.dcm")]
    orientation = np.array(datasets[0].ImageOrientationPatient, dtype=float)
    normal = np.cross(orientation[:3], orientation[3:])
    datasets.sort(key=lambda ds: float(np.dot(ds.ImagePositionPatient, normal)))
    hu = np.stack(
        [ds.pixel_array * float(ds.RescaleSlope) + float(ds.RescaleIntercept) for ds in datasets]
    )
    positions = np.array([ds.ImagePositionPatient for ds in datasets], dtype=float)
    return datasets, hu, positions


def world_to_index(world, origin):
    return np.rint((np.asarray(world) - origin) / np.asarray(GRID_SPACING)).astype(int)


def test_file_names_are_not_in_position_order(phantom_dirs):
    names = sorted(p.name for p in phantom_dirs["kugel"].glob("*.dcm"))
    by_name = [float(pydicom.dcmread(phantom_dirs["kugel"] / n).ImagePositionPatient[2]) for n in names]
    assert by_name != sorted(by_name)


def test_fake_patient_tags_are_present(phantom_dirs):
    ds = next(iter(phantom_dirs["kugel"].glob("*.dcm")))
    ds = pydicom.dcmread(ds)
    assert str(ds.PatientName) == FAKE_PATIENT_NAME
    assert ds.PatientID == FAKE_PATIENT_ID


def test_sphere_geometry_and_hu(phantoms, phantom_dirs):
    expected = phantoms["kugel"].expected
    datasets, hu, positions = read_series(phantom_dirs["kugel"])

    ni, nj, nk = GRID_SIZE
    assert hu.shape == (nk, nj, ni)
    assert [float(v) for v in datasets[0].PixelSpacing] == [GRID_SPACING[1], GRID_SPACING[0]]
    assert np.diff(positions[:, 2]) == pytest.approx(GRID_SPACING[2])

    origin = positions[0]
    center = world_to_index(np.asarray(expected["sphere_center_mm"]) + 0.01, origin)
    i, j, k = center
    assert hu[k, j, i] == expected["sphere_hu"]
    assert hu[0, 0, 0] == expected["background_hu"]

    # Ausdehnung der Kugel entlang jeder Achse: genau 50 mm
    inside = hu > -500
    for axis, spacing in zip((2, 1, 0), GRID_SPACING):
        other = tuple(a for a in range(3) if a != axis)
        count = np.count_nonzero(inside.any(axis=other))
        assert count * spacing == pytest.approx(expected["sphere_diameter_mm"])

    # Volumen auf 1 % genau
    radius = expected["sphere_diameter_mm"] / 2
    volume = np.count_nonzero(inside) * math.prod(GRID_SPACING)
    assert volume == pytest.approx(4 / 3 * math.pi * radius**3, rel=0.01)


def test_orientation_markers(phantoms, phantom_dirs):
    expected = phantoms["orientierung"].expected
    datasets, hu, positions = read_series(phantom_dirs["orientierung"])
    assert datasets[0].file_meta.TransferSyntaxUID == ImplicitVRLittleEndian
    assert datasets[0].PixelRepresentation == 1

    origin = positions[0]
    for name, (center, value) in expected["markers"].items():
        i, j, k = world_to_index(center, origin)
        assert hu[k, j, i] == value, name

    # Der linke Würfel liegt bei grossen Spaltenindizes, der vordere bei kleinen
    # Zeilenindizes, der Kopf-Würfel bei grossen Schichtindizes.
    k, j, i = np.argwhere(hu == expected["markers"]["links"][1]).mean(axis=0)
    assert i > GRID_SIZE[0] / 2
    k, j, i = np.argwhere(hu == expected["markers"]["vorne"][1]).mean(axis=0)
    assert j < GRID_SIZE[1] / 2
    k, j, i = np.argwhere(hu == expected["markers"]["kopf"][1]).mean(axis=0)
    assert k > GRID_SIZE[2] / 2


def test_missing_slice(phantoms, phantom_dirs):
    expected = phantoms["fehlende_schicht"].expected
    _, _, positions = read_series(phantom_dirs["fehlende_schicht"])
    assert len(positions) == GRID_SIZE[2] - 1
    assert expected["missing_z_mm"] not in positions[:, 2].round(4)
    assert np.diff(positions[:, 2]).max() == pytest.approx(2 * GRID_SPACING[2])


def test_uneven_spacing(phantoms, phantom_dirs):
    expected = phantoms["ungleiche_abstaende"].expected
    _, _, positions = read_series(phantom_dirs["ungleiche_abstaende"])
    steps = sorted(set(np.diff(positions[:, 2]).round(4)))
    assert steps == pytest.approx(expected["slice_steps_mm"])


def test_tilted_gantry(phantoms, phantom_dirs):
    expected = phantoms["gekippte_gantry"].expected
    datasets, _, positions = read_series(phantom_dirs["gekippte_gantry"])
    orientation = np.array(datasets[0].ImageOrientationPatient, dtype=float)
    normal = np.cross(orientation[:3], orientation[3:])
    step = positions[1] - positions[0]
    angle = math.degrees(math.acos(np.dot(normal, step) / np.linalg.norm(step)))
    assert angle == pytest.approx(expected["gantry_tilt_deg"], abs=0.01)


@pytest.mark.parametrize("name", ["kugel", "orientierung"])
def test_simpleitk_reads_same_values(name, phantoms, phantom_dirs):
    """Referenzleser SimpleITK muss dieselben Werte und Geometrie liefern."""
    phantom = phantoms[name]
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(reader.GetGDCMSeriesFileNames(str(phantom_dirs[name])))
    image = reader.Execute()

    assert image.GetSpacing() == pytest.approx(GRID_SPACING)
    assert image.GetOrigin() == pytest.approx(tuple(phantom.positions[0]), abs=1e-3)
    assert np.array_equal(sitk.GetArrayFromImage(image), phantom.hu)
