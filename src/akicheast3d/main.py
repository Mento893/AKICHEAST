"""Startpunkt von AKICHEAST 3D."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

# Die Pakete melden beim Import ihre Module in den Registries an.
import akicheast3d.export  # noqa: F401
import akicheast3d.segmentation  # noqa: F401
import akicheast3d.tools  # noqa: F401
from akicheast3d.ui.disclaimer import show_disclaimer
from akicheast3d.ui.main_window import APP_TITLE, MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    window = MainWindow()
    window.show()
    show_disclaimer(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
