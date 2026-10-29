"""Erlaubte DICOM-Tags.

Das Programm liest nur die hier aufgeführten Tags. Patienten-Tags wie Name,
Geburtsdatum oder Patienten-ID werden gar nicht erst eingelesen und können
deshalb weder angezeigt noch protokolliert noch exportiert werden.
"""

from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.dataset import Dataset

HEADER_TAGS = [
    "SOPClassUID",
    "SOPInstanceUID",
    "Modality",
    "ImageType",
    "SeriesInstanceUID",
    "SeriesNumber",
    "SeriesDescription",
    "SliceThickness",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "NumberOfFrames",
]

PIXEL_TAGS = [
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "PixelSpacing",
    "RescaleSlope",
    "RescaleIntercept",
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "Rows",
    "Columns",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "PlanarConfiguration",
    "NumberOfFrames",
    "PixelData",
]


def read_header(path: Path) -> Dataset | None:
    """Liest die erlaubten Kopfdaten. Gibt None zurück, wenn die Datei kein DICOM ist."""
    try:
        return pydicom.dcmread(path, stop_before_pixels=True, specific_tags=HEADER_TAGS)
    except Exception:
        # Andere Dateien im Ordner (Bilder, Texte, beschädigte Dateien) werden übersprungen.
        return None


def read_pixels(path: Path) -> Dataset:
    """Liest Bilddaten und Geometrie einer Schicht."""
    return pydicom.dcmread(path, specific_tags=PIXEL_TAGS)
