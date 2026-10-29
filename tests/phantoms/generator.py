"""Künstliche CT-Serien (Phantome) mit bekannten Massen als DICOM erzeugen.

Alle Koordinaten sind DICOM-Patientenkoordinaten (LPS) in mm:
+x zeigt nach links, +y nach hinten, +z zum Kopf.

Das Gitter ist absichtlich nicht quadratisch und hat in jeder Richtung einen
anderen Voxelabstand. So fallen vertauschte Achsen sofort auf. Die Dateinamen
sind zufällig, damit niemand sich auf die Reihenfolge der Namen verlässt.

Die Patienten-Tags enthalten Fantasiewerte. Sie dienen als Prüfung, dass das
Programm diese Tags nie anzeigt, protokolliert oder exportiert.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import (
    CTImageStorage,
    ExplicitVRLittleEndian,
    ImplicitVRLittleEndian,
    JPEG2000Lossless,
    UID,
    XRayRadiationDoseSRStorage,
    generate_uid,
)

FAKE_PATIENT_NAME = "Phantom^Geheim"
FAKE_PATIENT_ID = "PHANTOM-GEHEIM-0001"
FAKE_BIRTH_DATE = "19000101"

AIR_HU = -1000

# Gitter: (Spalten, Zeilen, Schichten) und Abstände (x, y, z) in mm.
# Jede Achse ist 60 mm lang, die Mitte liegt im Weltpunkt (0, 0, 0)
# genau zwischen zwei Voxeln.
GRID_SIZE = (96, 120, 48)
GRID_SPACING = (0.625, 0.5, 1.25)

SPHERE_DIAMETER_MM = 50.0
SPHERE_HU = 50

# Würfel für die Orientierung: Mittelpunkt in mm und Dichtewert.
MARKER_SIZE_MM = 10.0
ORIENTATION_MARKERS = {
    "links": ((20.0, 0.0, 0.0), 1000),
    "vorne": ((0.0, -20.0, 0.0), 500),
    "kopf": ((0.0, 0.0, 20.0), 200),
}

TILT_DEG = 15.0

HuFunction = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


@dataclass
class Phantom:
    """Eine künstliche Serie und die Wahrheit, die das Programm liefern muss.

    `hu` hat die Form (Schicht, Zeile, Spalte) und enthält genau die Schichten,
    die als Dateien geschrieben werden, in der Reihenfolge von `positions`.
    """

    name: str
    description: str
    hu: np.ndarray
    spacing: tuple[float, float]
    """Pixelabstand (x, y) innerhalb einer Schicht in mm."""
    slice_thickness: float
    positions: np.ndarray
    """ImagePositionPatient jeder Schicht, Form (N, 3)."""
    row_direction: tuple[float, float, float] = (1.0, 0.0, 0.0)
    column_direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
    rescale_slope: float = 1.0
    rescale_intercept: float = -1024.0
    signed: bool = False
    transfer_syntax: UID = ExplicitVRLittleEndian
    compression: UID | None = None
    image_type: tuple[str, ...] = ("ORIGINAL", "PRIMARY", "AXIAL")
    expected: dict[str, Any] = field(default_factory=dict)


def _origin() -> np.ndarray:
    """Mittelpunkt des ersten Voxels, so dass die Gittermitte bei (0, 0, 0) liegt."""
    size = np.asarray(GRID_SIZE)
    spacing = np.asarray(GRID_SPACING)
    return -(size * spacing) / 2 + spacing / 2


def _regular_positions(flip_xy: bool = False) -> np.ndarray:
    """Positionen der Schichten, von den Füssen zum Kopf.

    Mit `flip_xy` beginnt jede Schicht in der Ecke hinten links statt vorne
    rechts, passend zu Zeilen- und Spaltenrichtung (-1, 0, 0) und (0, -1, 0).
    """
    nz = GRID_SIZE[2]
    origin = _origin()
    if flip_xy:
        origin[:2] *= -1
    positions = np.tile(origin, (nz, 1))
    positions[:, 2] += np.arange(nz) * GRID_SPACING[2]
    return positions


def _rasterize(
    hu_function: HuFunction,
    positions: np.ndarray,
    row_direction: tuple[float, float, float],
    column_direction: tuple[float, float, float],
) -> np.ndarray:
    """Berechnet den Dichtewert jedes Voxels aus seiner Weltposition."""
    ni, nj, _ = GRID_SIZE
    dx, dy, _ = GRID_SPACING
    ii, jj = np.meshgrid(np.arange(ni) * dx, np.arange(nj) * dy)
    row = np.asarray(row_direction)
    col = np.asarray(column_direction)
    slices = []
    for p in positions:
        world = p + ii[..., None] * row + jj[..., None] * col
        slices.append(hu_function(world[..., 0], world[..., 1], world[..., 2]))
    return np.stack(slices).astype(np.int16)


def _sphere_hu(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    radius = SPHERE_DIAMETER_MM / 2
    inside = x**2 + y**2 + z**2 <= radius**2
    return np.where(inside, SPHERE_HU, AIR_HU)


def _orientation_hu(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    hu = np.full(x.shape, AIR_HU)
    half = MARKER_SIZE_MM / 2
    for (cx, cy, cz), value in ORIENTATION_MARKERS.values():
        inside = (abs(x - cx) < half) & (abs(y - cy) < half) & (abs(z - cz) < half)
        hu[inside] = value
    return hu


def _sphere_expected() -> dict[str, Any]:
    return {
        "sphere_center_mm": (0.0, 0.0, 0.0),
        "sphere_diameter_mm": SPHERE_DIAMETER_MM,
        "sphere_hu": SPHERE_HU,
        "background_hu": AIR_HU,
    }


def sphere_phantom() -> Phantom:
    """Kugel mit genau 50 mm Durchmesser, ungesignte Pixel mit Rescale-Intercept."""
    positions = _regular_positions()
    return Phantom(
        name="kugel",
        description="Phantom Kugel 50 mm",
        hu=_rasterize(_sphere_hu, positions, (1, 0, 0), (0, 1, 0)),
        spacing=GRID_SPACING[:2],
        slice_thickness=GRID_SPACING[2],
        positions=positions,
        expected=_sphere_expected(),
    )


def orientation_phantom() -> Phantom:
    """Drei Würfel links, vorne und beim Kopf. Gesignte Pixel, Implicit VR."""
    positions = _regular_positions()
    return Phantom(
        name="orientierung",
        description="Phantom Orientierung",
        hu=_rasterize(_orientation_hu, positions, (1, 0, 0), (0, 1, 0)),
        spacing=GRID_SPACING[:2],
        slice_thickness=GRID_SPACING[2],
        positions=positions,
        rescale_intercept=0.0,
        signed=True,
        transfer_syntax=ImplicitVRLittleEndian,
        expected={
            "markers": dict(ORIENTATION_MARKERS),
            "marker_size_mm": MARKER_SIZE_MM,
            "background_hu": AIR_HU,
        },
    )


def flipped_orientation_phantom() -> Phantom:
    """Wie das Orientierungs-Phantom, aber mit umgedrehten Zeilen und Spalten.

    Die Schichten stehen vom Kopf zu den Füssen in der Datei-Reihenfolge.
    Nach dem Laden müssen die Würfel an denselben Weltpunkten liegen.
    """
    positions = _regular_positions(flip_xy=True)[::-1]
    row, column = (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)
    phantom = orientation_phantom()
    phantom.name = "orientierung_gedreht"
    phantom.description = "Phantom Orientierung gedreht"
    phantom.hu = _rasterize(_orientation_hu, positions, row, column)
    phantom.positions = positions
    phantom.row_direction = row
    phantom.column_direction = column
    phantom.transfer_syntax = ExplicitVRLittleEndian
    return phantom


def compressed_sphere_phantom() -> Phantom:
    """Kugel, verlustfrei als JPEG 2000 komprimiert."""
    phantom = sphere_phantom()
    phantom.name = "kugel_komprimiert"
    phantom.description = "Phantom Kugel komprimiert"
    phantom.compression = JPEG2000Lossless
    return phantom


def localizer_phantom() -> Phantom:
    """Übersichtsbild (Topogramm): eine einzelne koronale Aufnahme."""
    positions = np.array([[_origin()[0], 0.0, -_origin()[2]]])
    row, column = (1.0, 0.0, 0.0), (0.0, 0.0, -1.0)
    return Phantom(
        name="topogramm",
        description="Topogramm",
        hu=_rasterize(_sphere_hu, positions, row, column),
        spacing=GRID_SPACING[:2],
        slice_thickness=GRID_SPACING[2],
        positions=positions,
        row_direction=row,
        column_direction=column,
        image_type=("ORIGINAL", "PRIMARY", "LOCALIZER"),
    )


def missing_slice_phantom() -> Phantom:
    """Kugel, bei der eine Schicht in der Mitte fehlt."""
    phantom = sphere_phantom()
    missing = GRID_SIZE[2] // 2
    keep = [k for k in range(GRID_SIZE[2]) if k != missing]
    phantom.name = "fehlende_schicht"
    phantom.description = "Phantom fehlende Schicht"
    phantom.expected = {
        **_sphere_expected(),
        "missing_z_mm": float(phantom.positions[missing, 2]),
    }
    phantom.hu = phantom.hu[keep]
    phantom.positions = phantom.positions[keep]
    return phantom


def uneven_spacing_phantom() -> Phantom:
    """Kugel, deren obere Hälfte mit 1.5 statt 1.25 mm Schichtabstand aufgenommen ist."""
    nz = GRID_SIZE[2]
    dz = GRID_SPACING[2]
    wide = 1.5
    steps = np.where(np.arange(nz - 1) < nz // 2, dz, wide)
    positions = np.tile(_origin(), (nz, 1))
    positions[1:, 2] += np.cumsum(steps)
    return Phantom(
        name="ungleiche_abstaende",
        description="Phantom ungleiche Abstaende",
        hu=_rasterize(_sphere_hu, positions, (1, 0, 0), (0, 1, 0)),
        spacing=GRID_SPACING[:2],
        slice_thickness=dz,
        positions=positions,
        expected={**_sphere_expected(), "slice_steps_mm": sorted({dz, wide})},
    )


def tilted_gantry_phantom() -> Phantom:
    """Kugel, aufgenommen mit um 15 Grad gekippter Gantry.

    Die Schichten sind gekippt, der Tisch fährt aber weiter entlang z.
    Die Schichtnormale ist deshalb nicht parallel zur Verschiebung der Positionen.
    """
    angle = np.radians(TILT_DEG)
    column = (0.0, round(float(np.cos(angle)), 6), round(float(-np.sin(angle)), 6))
    positions = _regular_positions()
    return Phantom(
        name="gekippte_gantry",
        description="Phantom gekippte Gantry",
        hu=_rasterize(_sphere_hu, positions, (1, 0, 0), column),
        spacing=GRID_SPACING[:2],
        slice_thickness=GRID_SPACING[2],
        positions=positions,
        column_direction=column,
        expected={**_sphere_expected(), "gantry_tilt_deg": TILT_DEG},
    )


ALL_PHANTOMS: dict[str, Callable[[], Phantom]] = {
    "kugel": sphere_phantom,
    "kugel_komprimiert": compressed_sphere_phantom,
    "orientierung": orientation_phantom,
    "orientierung_gedreht": flipped_orientation_phantom,
    "topogramm": localizer_phantom,
    "fehlende_schicht": missing_slice_phantom,
    "ungleiche_abstaende": uneven_spacing_phantom,
    "gekippte_gantry": tilted_gantry_phantom,
}


def write_dose_report(directory: Path) -> Path:
    """Schreibt einen Dosisbericht (Structured Report ohne Bilddaten)."""
    directory.mkdir(parents=True, exist_ok=True)
    sop_uid = generate_uid()
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = XRayRadiationDoseSRStorage
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = XRayRadiationDoseSRStorage
    ds.SOPInstanceUID = sop_uid
    ds.Modality = "SR"
    ds.PatientName = FAKE_PATIENT_NAME
    ds.PatientID = FAKE_PATIENT_ID
    ds.PatientBirthDate = FAKE_BIRTH_DATE
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = 999
    ds.SeriesDescription = "Dosisbericht"
    ds.InstanceNumber = 1
    ds.ValueType = "CONTAINER"

    path = directory / "dosis.dcm"
    ds.save_as(path, enforce_file_format=True)
    return path


def write_phantom(phantom: Phantom, directory: Path, seed: int = 0) -> list[Path]:
    """Schreibt jede Schicht als eigene DICOM-Datei mit zufälligem Namen."""
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_uid = generate_uid()

    paths = []
    for index in range(len(phantom.positions)):
        ds = _slice_dataset(phantom, index, study_uid, series_uid, frame_uid)
        path = directory / f"{rng.integers(0, 16**8):08x}.dcm"
        ds.save_as(path, enforce_file_format=True)
        paths.append(path)
    return paths


def _slice_dataset(
    phantom: Phantom, index: int, study_uid: str, series_uid: str, frame_uid: str
) -> Dataset:
    sop_uid = generate_uid()

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = phantom.transfer_syntax

    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.Modality = "CT"
    ds.ImageType = list(phantom.image_type)

    ds.PatientName = FAKE_PATIENT_NAME
    ds.PatientID = FAKE_PATIENT_ID
    ds.PatientBirthDate = FAKE_BIRTH_DATE

    ds.StudyInstanceUID = study_uid
    ds.StudyDate = "20260101"
    ds.StudyTime = "120000"
    ds.StudyID = "1"
    ds.SeriesInstanceUID = series_uid
    ds.FrameOfReferenceUID = frame_uid
    ds.SeriesNumber = 1
    ds.SeriesDescription = phantom.description
    ds.InstanceNumber = index + 1

    ds.ImagePositionPatient = [round(float(v), 4) for v in phantom.positions[index]]
    ds.ImageOrientationPatient = list(phantom.row_direction) + list(phantom.column_direction)
    dx, dy = phantom.spacing
    ds.PixelSpacing = [dy, dx]  # DICOM: Zeilenabstand zuerst
    ds.SliceThickness = phantom.slice_thickness

    rows, columns = phantom.hu.shape[1:]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = rows
    ds.Columns = columns
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1 if phantom.signed else 0
    ds.RescaleIntercept = phantom.rescale_intercept
    ds.RescaleSlope = phantom.rescale_slope
    ds.RescaleType = "HU"

    stored = (phantom.hu[index] - phantom.rescale_intercept) / phantom.rescale_slope
    dtype = np.int16 if phantom.signed else np.uint16
    info = np.iinfo(dtype)
    if stored.min() < info.min or stored.max() > info.max:
        raise ValueError(f"Die Dichtewerte von '{phantom.name}' passen nicht in {dtype.__name__}.")
    ds.PixelData = np.rint(stored).astype(dtype).tobytes()
    if phantom.compression is not None:
        ds.compress(phantom.compression)
    return ds
