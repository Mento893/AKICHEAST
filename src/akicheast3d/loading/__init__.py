"""DICOM einlesen, Serien erkennen, Prüfungen und Anonymisierung.

Anonymisierung: Es werden nur die Tags aus `tags.py` gelesen. Patientendaten
gelangen gar nicht erst ins Programm.
"""

from akicheast3d.loading.reader import LoadError, load_series
from akicheast3d.loading.series import SeriesInfo, SeriesKind, scan

__all__ = ["LoadError", "SeriesInfo", "SeriesKind", "load_series", "scan"]
