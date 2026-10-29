"""Infofeld: Angaben zur geladenen Serie und Warnungen beim Einlesen. Keine Patientendaten."""

from __future__ import annotations

from html import escape

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from akicheast3d.core import Session

WARNING_COLOR = "#e0a030"


def describe(session: Session) -> str:
    volume = session.volume
    nx, ny, nz = volume.size
    dx, dy, dz = volume.spacing
    ex, ey, ez = volume.extent_mm
    lines = [
        f"<b>{escape(session.series_description)}</b>",
        f"Schichten: {nz}",
        f"Schichtabstand: {dz:.2f} mm",
        f"Pixelgrösse: {dx:.3f} x {dy:.3f} mm",
        f"Bildgrösse: {nx} x {ny} Pixel",
        f"Ausdehnung: {ex:.0f} x {ey:.0f} x {ez:.0f} mm",
    ]
    if session.warnings:
        lines.append(f"<br><b style='color:{WARNING_COLOR}'>Warnungen</b>")
        lines += [f"<span style='color:{WARNING_COLOR}'>{escape(w)}</span>" for w in session.warnings]
    else:
        lines.append("<br>Einlesen ohne Warnungen.")
    return "<br>".join(lines)


class InfoPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label = QLabel()
        self.label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Serie</b>"))
        layout.addWidget(self.label)
        self.set_session(None)

    def set_session(self, session: Session | None) -> None:
        if session is None:
            self.label.setText("Keine Serie geladen.<br>Datei &gt; Ordner öffnen")
        else:
            self.label.setText(describe(session))
