# AKICHEAST 3D

Projektleitung und Autor: Mihailo Obradovic

@PROJEKT.md

## Arbeitsweise

- Kommunikation, Kommentare und Programmoberfläche auf Deutsch (Schweizer Schreibweise, ss statt ß). Bezeichner im Code auf Englisch.
- Keine Gedankenstriche (—) in Texten, Kommentaren oder der Oberfläche.
- Phase für Phase nach dem Phasenplan in PROJEKT.md arbeiten. Die nächste Phase erst nach Freigabe von Mihailo beginnen.
- Vor grösseren Schritten zuerst einen Plan vorschlagen und auf die Freigabe warten.
- Mit der Entwicklung erst beginnen, wenn Mihailo das Startsignal gibt.

## Architekturregeln

- Der Kern (`core/`) kennt keine Module. Segmentierer, Werkzeuge und Exporter greifen nur über die Schnittstellen in `core/` zu.
- Neue Funktionen immer als eigenes Modul umsetzen, nicht in den Kern oder ins Hauptfenster einbauen.
- Alle Koordinaten und Masse in Millimetern, Dichtewerte in Hounsfield-Einheiten.

## KI (Phase 4)

- Nicht umsetzen, solange Mihailo es nicht ausdrücklich verlangt. Keine Abhängigkeiten wie PyTorch oder TotalSegmentator in requirements.txt aufnehmen.
- Die Segmentierer-Schnittstelle so gestalten, dass eine KI-Variante später ohne Änderungen am Kern ergänzt werden kann.

## Qualität

- Jede Funktion bekommt Tests. Lade- und Messlogik wird mit den Phantomen aus `tests/phantoms/` geprüft.
- Eine Phase ist fertig, wenn alle Tests grün sind und die .exe sich bauen und starten lässt.

## Datenschutz und Zweck (zwingend)

- Niemals echte Patientendaten öffnen, lesen oder analysieren. Für Tests nur Dateien aus `testdata/` und `tests/phantoms/` verwenden.
- Im Programmcode keine Netzwerkzugriffe: keine Requests, keine Telemetrie, keine Update-Prüfung.
- Patienten-Tags (Name, Geburtsdatum, Patienten-ID) nie anzeigen, loggen oder in Exporte schreiben.
- `testdata/` gehört in die `.gitignore`.
- Keine Funktionen, die Befunde erstellen oder Auffälligkeiten automatisch erkennen.

## Befehle

Python 3.13 ist nicht im PATH. Alles läuft über die virtuelle Umgebung `.venv`.

- Einrichten: `<Python313>\python.exe -m venv .venv`, dann `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` und `.venv\Scripts\python.exe -m pip install -e .`
- Tests: `.venv\Scripts\python.exe -m pytest -q`
- Programm starten: `.venv\Scripts\python.exe -m akicheast3d.main` (optional mit einem Ordner als Argument, der direkt geöffnet wird)
- .exe bauen: `build.bat` (Tests, Build, danach Selbsttest der .exe mit einem komprimierten Phantom; Ergebnis in `dist\AKICHEAST3D\AKICHEAST3D.exe`)
- Selbsttest von Hand: `AKICHEAST3D.exe --selbsttest <ordner> <bild.png>` lädt die empfohlene Serie ohne Rückfragen, speichert einen Screenshot, Protokoll in `<bild>.txt`, Rückgabewert 0 heisst bestanden
- Tests in `tests/gui_checks/` laufen als eigener Prozess mit echtem Fenster, weil VTK OpenGL braucht. Beim Testlauf blitzen deshalb kurz Fenster auf.
- Testdaten laden: `.venv\Scripts\python.exe scripts\testdaten_laden.py` (`--nur-anzeigen` zeigt nur die Auswahl)
- Phantome als DICOM schreiben, zum Beispiel für 3D Slicer: `.venv\Scripts\python.exe -m tests.phantoms` (nach `testdata\phantome\`)

## Konventionen im Code

- Volumen-Arrays haben die Form (k, j, i) = (Schicht, Zeile, Spalte). Indizes, Abstände und Ursprung stehen in der Reihenfolge (i, j, k) bzw. (x, y, z).
- Weltkoordinaten sind DICOM-Patientenkoordinaten (LPS): +x links, +y hinten, +z Kopf.
- Module melden sich mit `@segmenters.register`, `@tools.register` oder `@exporters.register` an und werden im `__init__.py` ihres Pakets importiert.
