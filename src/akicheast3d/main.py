"""Startpunkt von AKICHEAST 3D.

Aufruf:
    AKICHEAST3D.exe                                   normal starten
    AKICHEAST3D.exe <ordner>                          Ordner direkt öffnen
    AKICHEAST3D.exe --selbsttest <ordner> <bild.png>  Selbsttest (siehe ui/self_test.py)
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

SELF_TEST = "--selbsttest"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == [SELF_TEST] and len(args) == 3:
        output = Path(args[2])
        try:
            return _run(args)
        except Exception:  # noqa: BLE001
            # Ohne Konsole würde ein Fehlerfenster auf einen Klick warten.
            output.with_suffix(".txt").write_text(traceback.format_exc(), encoding="utf-8")
            return 1
    return _run(args)


def _run(args: list[str]) -> int:
    from PySide6.QtWidgets import QApplication

    # Die Pakete melden beim Import ihre Module in den Registries an.
    import akicheast3d.export  # noqa: F401
    import akicheast3d.segmentation  # noqa: F401
    import akicheast3d.tools  # noqa: F401
    from akicheast3d.ui.disclaimer import show_disclaimer
    from akicheast3d.ui.main_window import APP_TITLE, MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()

    if args[:1] == [SELF_TEST]:
        from akicheast3d.ui.self_test import run_self_test

        return run_self_test(app, window, Path(args[1]), Path(args[2]))

    show_disclaimer(window)
    if args:
        window.scan_path(Path(args[0]))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
