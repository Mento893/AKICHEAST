"""Exporter, die Ergebnisse in Dateien schreiben.

Registrierung: Jedes Exporter-Modul wird hier importiert, damit es sich
beim Start in `akicheast3d.core.registry.exporters` anmeldet.
"""

from akicheast3d.export import screenshot  # noqa: F401
