"""Selbsttest der fertigen .exe: Serie laden, Screenshot speichern, beenden.

Prüft, ob beim Verpacken alle Teile mitgekommen sind. Aufruf:
    AKICHEAST3D.exe --selbsttest <ordner> <bild.png>

Das Protokoll steht in <bild>.txt. Rückgabewert 0 heisst bestanden.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication, QMessageBox

from akicheast3d.loading import scan
from akicheast3d.ui.main_window import MainWindow
from akicheast3d.ui.series_dialog import recommended_series


def run_self_test(app: QApplication, window: MainWindow, folder: Path, output: Path) -> int:
    log: list[str] = []
    # Meldungen ins Protokoll statt in ein Dialogfenster, das auf einen Klick warten würde
    QMessageBox.warning = lambda parent, title, text: log.append(f"Meldung: {text}")

    try:
        series = recommended_series(scan(folder))
        if series is None:
            log.append("Keine ladbare Serie gefunden.")
        else:
            log.append(f"Serie: {series.description}, {series.slice_count} Schichten")
            window.load(series)
            task = window._task
            if not task.isFinished():
                loop = QEventLoop()
                task.finished.connect(loop.quit)
                loop.exec()
            app.processEvents()
            if window.session is not None:
                log += [f"Struktur {s.name}: {s.voxel_count} Voxel" for s in window.session.structures]
                log += [f"Warnung: {w}" for w in window.session.warnings]
                window.export("Screenshot (PNG)", output)
    except Exception as error:  # noqa: BLE001 - alles ins Protokoll
        log.append(f"Fehler: {error!r}")

    passed = output.exists()
    log.append("BESTANDEN" if passed else "FEHLGESCHLAGEN")
    output.with_suffix(".txt").write_text("\n".join(log), encoding="utf-8")
    window.close()
    return 0 if passed else 1
