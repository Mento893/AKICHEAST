"""Segmentierer, die aus einem Volumen Strukturen erzeugen.

Registrierung: Jedes Segmentierer-Modul wird hier importiert, damit es sich
beim Start in `akicheast3d.core.registry.segmenters` anmeldet.
"""

from akicheast3d.segmentation import threshold  # noqa: F401
