"""Die drei Schnittstellen, über die Module an den Kern andocken.

- Segmentierer: erzeugt Strukturen aus einem Volumen
- Werkzeug: Funktion mit eigenem Button oder Panel
- Exporter: schreibt Ergebnisse in eine Datei

Der Kern kennt keine konkreten Module. Jede Klasse hat einen eindeutigen
Anzeigenamen `name` und wird in einer Registry angemeldet (siehe registry.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, Protocol

import numpy as np

from akicheast3d.core.session import Session
from akicheast3d.core.structure import Structure
from akicheast3d.core.volume import Volume

ProgressCallback = Callable[[float], None]
"""Meldet den Fortschritt als Wert zwischen 0.0 und 1.0."""


class Segmenter(ABC):
    """Erzeugt Strukturen aus einem Volumen.

    Ein Segmenter verändert das Volumen nicht. Die Masken der zurückgegebenen
    Strukturen haben dieselbe Form wie `volume.hu`. Lang laufende Verfahren
    melden ihren Fortschritt über `progress`.
    """

    name: ClassVar[str]

    @abstractmethod
    def segment(
        self, volume: Volume, progress: ProgressCallback | None = None
    ) -> list[Structure]: ...


class ToolContext(Protocol):
    """Was ein Werkzeug vom Programm sieht."""

    @property
    def session(self) -> Session: ...

    def request_redraw(self) -> None:
        """Zeichnet 2D- und 3D-Ansicht nach einer Änderung neu."""
        ...


class Tool(ABC):
    """Funktion mit eigenem Button oder Panel im Hauptfenster."""

    name: ClassVar[str]

    @abstractmethod
    def create_panel(self, context: ToolContext) -> Any:
        """Gibt das Qt-Widget des Werkzeugs zurück."""

    def close(self) -> None:
        """Gibt Ressourcen frei, wenn das Werkzeug geschlossen wird."""


class ExportContext(Protocol):
    """Was ein Exporter vom Programm sieht."""

    @property
    def session(self) -> Session: ...

    def render_image(self) -> np.ndarray:
        """Aktuelle 3D-Ansicht als RGB-Bild der Form (Höhe, Breite, 3), uint8."""
        ...


class Exporter(ABC):
    """Schreibt Ergebnisse in eine Datei. Exporte enthalten keine Patientendaten."""

    name: ClassVar[str]
    file_filter: ClassVar[str]
    """Filter für den Dateidialog, zum Beispiel 'PNG-Bild (*.png)'."""

    @abstractmethod
    def export(self, context: ExportContext, path: Path) -> None: ...
