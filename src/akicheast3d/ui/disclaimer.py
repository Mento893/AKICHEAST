"""Hinweis beim Start: Anschauungswerkzeug, keine Diagnose."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

DISCLAIMER_TITLE = "Wichtiger Hinweis"

DISCLAIMER_TEXT = (
    "AKICHEAST 3D ist ein Anschauungs- und Gesprächswerkzeug und kein Medizinprodukt.\n\n"
    "Das Programm erstellt keine Befunde und erkennt keine Auffälligkeiten. "
    "Die Darstellung darf nicht für diagnostische oder therapeutische Entscheide "
    "verwendet werden."
)


def create_disclaimer(parent: QWidget | None = None) -> QMessageBox:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(DISCLAIMER_TITLE)
    box.setText(DISCLAIMER_TEXT)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return box


def show_disclaimer(parent: QWidget | None = None) -> None:
    create_disclaimer(parent).exec()
