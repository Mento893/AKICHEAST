"""Arbeiten im Hintergrund, damit das Fenster beim Laden nicht einfriert."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal

from akicheast3d.core import ProgressCallback
from akicheast3d.loading import LoadError

Report = Callable[[float, str], None]
"""Meldet Fortschritt (0.0 bis 1.0) und einen kurzen Text."""


class TaskThread(QThread):
    """Führt eine Funktion im Hintergrund aus. Die Signale kommen im Hauptthread an."""

    progress = Signal(float, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, function: Callable[[Report], Any], parent=None) -> None:
        super().__init__(parent)
        self._function = function

    def run(self) -> None:
        try:
            result = self._function(self.progress.emit)
        except LoadError as error:
            self.failed.emit(str(error))
        except Exception as error:  # noqa: BLE001 - jeder Fehler soll in der Oberfläche landen
            self.failed.emit(f"Unerwarteter Fehler: {error}")
        else:
            self.succeeded.emit(result)


def stage(report: Report, start: float, end: float, text: str) -> ProgressCallback:
    """Bildet den Fortschritt eines Teilschritts auf den Bereich start bis end ab."""
    report(start, text)
    return lambda value: report(start + (end - start) * value, text)
