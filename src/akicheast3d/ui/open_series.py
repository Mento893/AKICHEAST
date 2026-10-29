"""Eine Serie öffnen: einlesen, Strukturen trennen, Oberflächen berechnen."""

from __future__ import annotations

from dataclasses import dataclass

import pyvista as pv

from akicheast3d.core import Segmenter, Session, Structure
from akicheast3d.loading import SeriesInfo, load_series
from akicheast3d.ui.surface import mask_to_surface
from akicheast3d.ui.tasks import Report, stage


@dataclass
class OpenedSeries:
    session: Session
    surfaces: list[tuple[Structure, pv.PolyData]]


def open_series(series: SeriesInfo, segmenter: Segmenter, report: Report) -> OpenedSeries:
    session = load_series(series, stage(report, 0.0, 0.4, "Serie wird eingelesen"))

    structures = segmenter.segment(
        session.volume, stage(report, 0.4, 0.8, "Strukturen werden getrennt")
    )
    for structure in structures:
        session.add_structure(structure)

    progress = stage(report, 0.8, 1.0, "3D-Modell wird berechnet")
    surfaces = []
    for n, structure in enumerate(structures, start=1):
        surfaces.append((structure, mask_to_surface(structure.mask, session.volume)))
        progress(n / len(structures))
    return OpenedSeries(session, surfaces)
