"""Ganzer Ablauf im Hauptfenster mit echtem Fenster, Ergebnisse als JSON.

Aufruf: python -m tests.gui_checks.main_window_check <arbeitsordner>
"""

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

import akicheast3d.export  # noqa: F401
import akicheast3d.segmentation  # noqa: F401
import akicheast3d.tools  # noqa: F401
from akicheast3d.loading import scan
from akicheast3d.ui.main_window import APP_TITLE, MainWindow
from akicheast3d.ui.slicing import Orientation
from tests.phantoms.generator import ALL_PHANTOMS, write_phantom


def wait_for_task(app: QApplication, window: MainWindow) -> None:
    task = window._task
    if not task.isFinished():
        loop = QEventLoop()
        task.finished.connect(loop.quit)
        loop.exec()
    app.processEvents()


def main() -> None:
    workdir = Path(sys.argv[1])
    write_phantom(ALL_PHANTOMS["kugel"](), workdir / "kugel")
    write_phantom(ALL_PHANTOMS["gekippte_gantry"](), workdir / "gantry")
    write_phantom(ALL_PHANTOMS["topogramm"](), workdir / "topogramm")

    app = QApplication([])
    warnings = []
    QMessageBox.warning = lambda parent, title, text: warnings.append(text)

    window = MainWindow()
    window.show()
    app.processEvents()
    result = {
        "title": window.windowTitle(),
        "export_enabled_before": [a.isEnabled() for a in window.export_actions],
        "info_before": window.info_panel.label.text(),
    }

    (series,) = scan(workdir / "gantry")
    window.load(series)
    wait_for_task(app, window)
    session = window.session
    result["structures"] = [s.name for s in session.structures]
    result["panel_rows"] = len(window.structure_panel.rows)
    result["info"] = window.info_panel.label.text()
    result["actors"] = sorted(window.viewer_3d._actors)
    result["axial_slices"] = window.viewer_2d.views[Orientation.AXIAL].slice_count
    result["export_enabled_after"] = [a.isEnabled() for a in window.export_actions]
    result["open_enabled_after"] = window.open_folder_action.isEnabled()

    body_row = next(r for r in window.structure_panel.rows if r.structure.name == "Körperumriss")
    body_row.checkbox.setChecked(False)
    result["body_actor_visible"] = bool(window.viewer_3d._actors["Körperumriss"].GetVisibility())

    target = workdir / "bild.png"
    window.export("Screenshot (PNG)", target)
    image = QImage(str(target))
    result["screenshot"] = [image.width(), image.height()]

    (localizer,) = scan(workdir / "topogramm")
    window.load(localizer)
    wait_for_task(app, window)
    result["warnings"] = warnings
    result["session_kept"] = window.session is session

    window.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
