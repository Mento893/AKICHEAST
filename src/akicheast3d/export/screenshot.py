"""Screenshot der 3D-Ansicht als PNG. Enthält nur das Bild, keine Patientendaten."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from akicheast3d.core import ExportContext, Exporter
from akicheast3d.core.registry import exporters


@exporters.register
class ScreenshotExporter(Exporter):
    name = "Screenshot (PNG)"
    file_filter = "PNG-Bild (*.png)"

    def export(self, context: ExportContext, path: Path) -> None:
        pixels = np.ascontiguousarray(context.render_image(), dtype=np.uint8)
        height, width, _ = pixels.shape
        image = QImage(pixels.data, width, height, 3 * width, QImage.Format.Format_RGB888)
        if not image.save(str(path), "PNG"):
            raise OSError(f"Das Bild konnte nicht gespeichert werden: {path}")
