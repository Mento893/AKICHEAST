"""Eine Serie einlesen und als Sitzung bereitstellen."""

from __future__ import annotations

import numpy as np

from akicheast3d.core import ProgressCallback, Session
from akicheast3d.loading.geometry import build_volume
from akicheast3d.loading.series import SeriesInfo
from akicheast3d.loading.tags import read_pixels

ORIENTATION_TOLERANCE = 1e-3
READ_SHARE = 0.9
"""Anteil des Fortschritts für das Lesen der Dateien, der Rest für die Geometrie."""


class LoadError(Exception):
    """Die Serie kann nicht als Volumen gelesen werden. Die Meldung ist für die Oberfläche."""


def load_series(series: SeriesInfo, progress: ProgressCallback | None = None) -> Session:
    if not series.loadable:
        raise LoadError(series.note or "Diese Serie kann nicht geladen werden.")

    slices = []
    positions = []
    reference = None
    for n, path in enumerate(series.files, start=1):
        ds = read_pixels(path)
        geometry = _slice_geometry(ds)
        if reference is None:
            reference = geometry
        else:
            _check_consistent(reference, geometry)
        slices.append(_to_hu(ds))
        positions.append(geometry["position"])
        if progress:
            progress(READ_SHARE * n / len(series.files))

    volume, warnings = build_volume(
        np.stack(slices),
        np.array(positions),
        reference["row"],
        reference["column"],
        reference["spacing"],
    )
    if progress:
        progress(1.0)
    return Session(volume, series_description=series.description, warnings=warnings)


def _slice_geometry(ds) -> dict:
    if int(ds.get("SamplesPerPixel", 1)) != 1:
        raise LoadError("Farbbilder werden nicht unterstützt.")
    try:
        orientation = np.array(ds.ImageOrientationPatient, dtype=float)
        position = np.array(ds.ImagePositionPatient, dtype=float)
        row_spacing, column_spacing = (float(v) for v in ds.PixelSpacing)
    except AttributeError as error:
        raise LoadError("Der Serie fehlen Angaben zu Position oder Pixelgrösse.") from error
    return {
        "row": orientation[:3],
        "column": orientation[3:],
        "position": position,
        # DICOM nennt den Zeilenabstand zuerst; hier steht (x, y) = (Spalten, Zeilen)
        "spacing": (column_spacing, row_spacing),
        "shape": (int(ds.Rows), int(ds.Columns)),
    }


def _check_consistent(reference: dict, geometry: dict) -> None:
    if geometry["shape"] != reference["shape"]:
        raise LoadError("Die Schichten der Serie haben unterschiedliche Bildgrössen.")
    if not np.allclose(geometry["spacing"], reference["spacing"], atol=1e-4):
        raise LoadError("Die Schichten der Serie haben unterschiedliche Pixelgrössen.")
    same_row = np.allclose(geometry["row"], reference["row"], atol=ORIENTATION_TOLERANCE)
    same_column = np.allclose(geometry["column"], reference["column"], atol=ORIENTATION_TOLERANCE)
    if not (same_row and same_column):
        raise LoadError("Die Schichten der Serie haben unterschiedliche Ausrichtungen.")


def _to_hu(ds) -> np.ndarray:
    """Rechnet die Rohwerte mit den Faktoren dieser Datei in Hounsfield-Einheiten um."""
    slope = float(ds.get("RescaleSlope", 1.0) or 1.0)
    intercept = float(ds.get("RescaleIntercept", 0.0) or 0.0)
    hu = ds.pixel_array.astype(np.float32) * slope + intercept
    info = np.iinfo(np.int16)
    return np.clip(np.rint(hu), info.min, info.max).astype(np.int16)
