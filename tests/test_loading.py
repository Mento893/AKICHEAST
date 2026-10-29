"""Laden mit den Phantomen: Werte und Geometrie müssen exakt stimmen."""

import math
import shutil

import numpy as np
import pytest
from pydicom.fileset import FileSet

from akicheast3d.loading import LoadError, SeriesKind, load_series, scan
from akicheast3d.loading.tags import read_header
from tests.phantoms.generator import (
    FAKE_BIRTH_DATE,
    FAKE_PATIENT_ID,
    FAKE_PATIENT_NAME,
    GRID_SIZE,
    GRID_SPACING,
)

FAKE_VALUES = (FAKE_PATIENT_NAME, FAKE_PATIENT_ID, FAKE_BIRTH_DATE, "Geheim")


def load(directory):
    (series,) = scan(directory)
    return load_series(series)


def sphere_extent_mm(volume, threshold=-500):
    """Ausdehnung der Kugel entlang (x, y, z) in mm."""
    inside = volume.hu > threshold
    extents = []
    for axis, spacing in zip((2, 1, 0), volume.spacing):
        other = tuple(a for a in range(3) if a != axis)
        extents.append(np.count_nonzero(inside.any(axis=other)) * spacing)
    return np.array(extents)


def sphere_center_mm(volume, threshold=-500):
    k, j, i = np.nonzero(volume.hu > threshold)
    return volume.index_to_world(np.column_stack([i, j, k])).mean(axis=0)


# Serien finden


def test_scan_study_finds_series_and_skips_other_files(study_dir):
    series = {s.description: s for s in scan(study_dir)}
    assert set(series) == {"Phantom Kugel 50 mm", "Topogramm", "Dosisbericht"}

    sphere = series["Phantom Kugel 50 mm"]
    assert sphere.kind is SeriesKind.VOLUME
    assert sphere.loadable
    assert sphere.slice_count == GRID_SIZE[2]
    assert sphere.slice_thickness == pytest.approx(GRID_SPACING[2])
    assert sphere.note == ""

    assert series["Topogramm"].kind is SeriesKind.LOCALIZER
    assert "kein 3D" in series["Topogramm"].note
    assert series["Dosisbericht"].kind is SeriesKind.DOSE_REPORT
    assert not series["Dosisbericht"].loadable


def test_scan_reports_progress(study_dir):
    reported = []
    scan(study_dir, reported.append)
    assert reported == sorted(reported)
    assert reported[-1] == pytest.approx(1.0)


def test_duplicate_files_count_once(phantom_dirs, tmp_path):
    shutil.copytree(phantom_dirs["kugel"], tmp_path / "original")
    shutil.copytree(phantom_dirs["kugel"], tmp_path / "kopie")
    (series,) = scan(tmp_path)
    assert series.slice_count == GRID_SIZE[2]


def test_scan_via_dicomdir(phantom_dirs, tmp_path):
    fileset = FileSet()
    for path in phantom_dirs["kugel"].glob("*.dcm"):
        fileset.add(path)
    fileset.write(tmp_path / "cd")
    (series,) = scan(tmp_path / "cd" / "DICOMDIR")
    assert series.slice_count == GRID_SIZE[2]
    assert load_series(series).volume.size == GRID_SIZE


# Datenschutz


def test_patient_tags_are_never_read(phantom_dirs):
    path = next(phantom_dirs["kugel"].glob("*.dcm"))
    ds = read_header(path)
    for keyword in ("PatientName", "PatientID", "PatientBirthDate"):
        assert keyword not in ds


def test_patient_values_do_not_reach_series_or_session(phantom_dirs):
    (series,) = scan(phantom_dirs["kugel"])
    session = load_series(series)
    texts = [repr(series), session.series_description, *session.warnings, repr(vars(session))]
    for text in texts:
        for value in FAKE_VALUES:
            assert value not in text


# Werte und Geometrie


def test_sphere_loads_exactly(phantoms, phantom_dirs):
    phantom = phantoms["kugel"]
    session = load(phantom_dirs["kugel"])
    volume = session.volume

    assert session.warnings == []
    assert volume.size == GRID_SIZE
    assert volume.spacing == pytest.approx(GRID_SPACING)
    assert volume.origin == pytest.approx(tuple(phantom.positions[0]))
    assert np.array_equal(volume.direction, np.eye(3))
    assert np.array_equal(volume.hu, phantom.hu)
    assert volume.hu_at_world((0.0, 0.0, 0.0)) == phantom.expected["sphere_hu"]
    assert sphere_extent_mm(volume) == pytest.approx([50.0, 50.0, 50.0])


def test_compressed_sphere_has_same_values(phantoms, phantom_dirs):
    volume = load(phantom_dirs["kugel_komprimiert"]).volume
    assert np.array_equal(volume.hu, phantoms["kugel"].hu)


@pytest.mark.parametrize("name", ["orientierung", "orientierung_gedreht"])
def test_orientation_markers_at_world_positions(name, phantoms, phantom_dirs):
    expected = phantoms[name].expected
    volume = load(phantom_dirs[name]).volume
    assert np.array_equal(volume.direction, np.eye(3))
    for marker, (center, value) in expected["markers"].items():
        assert volume.hu_at_world(center) == value, marker


def test_flipped_orientation_gives_identical_volume(phantom_dirs):
    normal = load(phantom_dirs["orientierung"]).volume
    flipped = load(phantom_dirs["orientierung_gedreht"]).volume
    assert np.array_equal(normal.hu, flipped.hu)
    assert normal.origin == pytest.approx(flipped.origin)


def test_progress_reaches_one(phantom_dirs):
    (series,) = scan(phantom_dirs["kugel"])
    reported = []
    load_series(series, reported.append)
    assert reported == sorted(reported)
    assert reported[-1] == 1.0


def test_localizer_cannot_be_loaded(phantom_dirs):
    (series,) = scan(phantom_dirs["topogramm"])
    with pytest.raises(LoadError, match="Topogramm"):
        load_series(series)


# Auffällige Serien: umrechnen und warnen


def test_missing_slice_is_interpolated_with_warning(phantoms, phantom_dirs):
    expected = phantoms["fehlende_schicht"].expected
    session = load(phantom_dirs["fehlende_schicht"])
    volume = session.volume

    assert len(session.warnings) == 1
    assert "Fehlende Schichten" in session.warnings[0]
    assert "2.5 mm" in session.warnings[0]
    assert volume.size == GRID_SIZE
    assert volume.spacing[2] == pytest.approx(GRID_SPACING[2])
    assert volume.hu_at_world((0.0, 0.0, expected["missing_z_mm"])) == expected["sphere_hu"]
    assert sphere_extent_mm(volume) == pytest.approx([50.0, 50.0, 50.0])


def test_uneven_spacing_is_resampled_with_warning(phantom_dirs):
    session = load(phantom_dirs["ungleiche_abstaende"])
    volume = session.volume

    assert len(session.warnings) == 1
    assert "Ungleiche Schichtabstände" in session.warnings[0]
    assert volume.spacing[2] == pytest.approx(GRID_SPACING[2])
    assert sphere_extent_mm(volume) == pytest.approx([50.0, 50.0, 50.0], abs=GRID_SPACING[2])
    assert sphere_center_mm(volume) == pytest.approx([0.0, 0.0, 0.0], abs=0.5)


def test_tilted_gantry_is_resampled_with_warning(phantom_dirs):
    session = load(phantom_dirs["gekippte_gantry"])
    volume = session.volume

    assert len(session.warnings) == 1
    assert "Gekippte Gantry (15.0°)" in session.warnings[0]
    assert np.array_equal(volume.direction, np.eye(3))
    assert sphere_center_mm(volume) == pytest.approx([0.0, 0.0, 0.0], abs=0.5)
    assert sphere_extent_mm(volume) == pytest.approx([50.0, 50.0, 50.0], abs=GRID_SPACING[2])
    sphere_volume = np.count_nonzero(volume.hu > -500) * volume.voxel_volume_mm3
    assert sphere_volume == pytest.approx(4 / 3 * math.pi * 25.0**3, rel=0.03)
