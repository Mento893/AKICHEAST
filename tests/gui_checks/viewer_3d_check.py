"""Prüft die 3D-Ansicht in einem echten Fenster und gibt die Ergebnisse als JSON aus.

VTK braucht ein sichtbares Fenster zum Zeichnen. Deshalb läuft dieses Skript
als eigener Prozess ohne QT_QPA_PLATFORM=offscreen (siehe test_viewer_3d.py).
"""

import json

import numpy as np
import pyvista as pv
from PySide6.QtWidgets import QApplication

from akicheast3d.core import Structure
from akicheast3d.ui.viewer_3d import VIEWS, Viewer3D


def center_pixel(viewer: Viewer3D) -> list[int]:
    image = viewer.render_image()
    return image[image.shape[0] // 2, image.shape[1] // 2].tolist()


def main() -> None:
    app = QApplication([])
    viewer = Viewer3D()
    viewer.resize(500, 400)
    viewer.show()
    app.processEvents()

    red = Structure("Rot", np.ones((2, 2, 2), dtype=bool), color=(1.0, 0.0, 0.0))
    empty = Structure("Leer", np.zeros((2, 2, 2), dtype=bool), color=(0.0, 1.0, 0.0))
    viewer.set_surfaces([(red, pv.Sphere(radius=20)), (empty, pv.PolyData())])

    result = {"actors": sorted(viewer._actors), "image_shape": list(viewer.render_image().shape)}
    result["visible"] = center_pixel(viewer)

    red.visible = False
    viewer.update_structure(red)
    result["hidden"] = center_pixel(viewer)

    red.visible = True
    red.color = (0.0, 0.0, 1.0)
    viewer.update_structure(red)
    result["recolored"] = center_pixel(viewer)

    result["views"] = {}
    for name in VIEWS:
        viewer.set_view(name)
        position, focal, _ = viewer.plotter.camera_position
        result["views"][name] = (np.subtract(position, focal) / np.linalg.norm(np.subtract(position, focal))).round(3).tolist()

    viewer.set_view("Vorne")
    before = viewer.plotter.camera_position[0]
    viewer._rotate_step()
    result["rotated"] = bool(not np.allclose(before, viewer.plotter.camera_position[0]))
    viewer.set_rotating(True)
    result["rotating"] = viewer.is_rotating and viewer.rotate_button.isChecked()
    viewer.set_rotating(False)

    viewer.clear()
    result["after_clear"] = sorted(viewer._actors)
    viewer.close_viewer()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
