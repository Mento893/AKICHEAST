# AKICHEAST 3D

**Projektbeschrieb**

| | |
|---|---|
| Projektleitung und Autor | Mihailo Obradovic |
| Version | 0.3 (Konzept) |
| Stand | 29. Oktober 2026 |
| Status | Planung, Entwicklung noch nicht gestartet |

## 1. Ziel

AKICHEAST 3D ist ein Windows-Programm, das Lungen-CTs im DICOM-Format einliest, dreidimensional darstellt und animiert. Die einzelnen Strukturen wie Lunge, Atemwege und Knochen werden voneinander getrennt und lassen sich einzeln ein- und ausblenden. So kann man zum Beispiel die Knochen entfernen und hat freie Sicht auf die Lunge.

## 2. Grundsätze

- **Basis zuerst:** Die Grundfunktionen werden so schnell wie möglich lauffähig. Zusatzfunktionen kommen später als eigenständige Module dazu, ohne den Kern zu verändern.
- **Komplett lokal:** Das Programm baut keine Internetverbindung auf. Keine Uploads, keine Telemetrie, keine Update-Prüfung.
- **Datenschutz:** Name, Geburtsdatum und Patienten-ID aus den DICOM-Dateien werden nie angezeigt, gespeichert oder protokolliert. Exporte enthalten keine Patientendaten.
- **Anschauung, keine Diagnose:** Das Programm ist ein Anschauungs- und Gesprächswerkzeug und kein Medizinprodukt (siehe Kapitel 9). Ein entsprechender Hinweis erscheint beim Start.
- **Testdaten:** Entwicklung und Tests nur mit öffentlichen, anonymisierten Datensätzen und eigenen Testobjekten. Echte Patientendaten gehören nicht in den Projektordner.

## 3. Ablauf für den Nutzer

1. DICOM-Ordner oder DICOMDIR auswählen. Einzelne Dateien müssen nicht ausgewählt werden.
2. Das Programm listet die enthaltenen Serien auf (Beschreibung, Anzahl Schichten, Schichtdicke).
3. Serie wählen, empfohlen ist eine Dünnschicht-Serie mit ca. 1 mm. Jede Serie kann beliebig oft geöffnet werden.
4. 2D- und 3D-Ansicht öffnen sich.
5. Strukturen ein- und ausblenden, Ansicht animieren, Ergebnis exportieren.

## 4. Phasenplan

| Phase | Inhalt | Ergebnis |
|---|---|---|
| 0 | Fundament | Projekt aufgesetzt, Schnittstellen, Tests und Testdaten bereit |
| 1 | Basis | erste lauffähige .exe mit 2D, 3D und ausblendbaren Strukturen |
| 2 | Animation und Export | Schnittebene, Kamerafahrten, Video, STL |
| 3 | Werkzeuge für Ärzte | Messen, MIP/MinIP, Notizen, Vergleich, Gesprächsmodus, PDF |
| 4 | KI-Schnittstelle (optional) | aktuell nicht geplant |

### Phase 0: Fundament

- Projektstruktur, requirements.txt, build.bat und .gitignore anlegen
- Kern-Datenmodell und die drei Schnittstellen festlegen (siehe Kapitel 5)
- Öffentliche Testdaten mit `scripts/testdaten_laden.py` nach `testdata/` laden
- Künstliche Testobjekte (Phantome) als DICOM erzeugen
- Testumgebung mit pytest einrichten

### Phase 1: Basis

**Laden**
- DICOM-Ordner und DICOMDIR einlesen, Serien erkennen und als Liste anzeigen
- Umrechnung in Hounsfield-Einheiten, Sortierung nach Position im Körper, Abstände aus den Positionen
- Prüfungen mit Warnungen: fehlende Schichten, ungleiche Abstände, gekippte Gantry
- Übersichtsbilder (Topogramm) und Dosisberichte kennzeichnen, da daraus kein 3D möglich ist

**2D-Ansicht**
- Schichten in drei Richtungen durchscrollen: axial, koronal, sagittal
- Fenster-Voreinstellungen: Lunge, Weichteil, Knochen
- Dichtewert unter dem Mauszeiger und Orientierungsmarker (rechts/links, vorne/hinten, Kopf/Fuss)

**3D-Ansicht**
- Strukturen über Dichtewerte getrennt: Lunge, Atemwege, Knochen, Körperumriss
- Pro Struktur: ein- und ausblenden, Farbe, Transparenz
- Drehen und Zoomen mit der Maus, automatische Rotation
- Screenshot (PNG)

**Allgemein**
- Infofeld mit Schichtanzahl, Schichtabstand, Pixelgrösse und Warnungen
- Hinweis beim Start: keine Diagnose
- Build als Windows-.exe

**Meilenstein:** Eine .exe lädt eine Test-Serie, zeigt sie in 2D und 3D und kann die Knochen ausblenden.

### Phase 2: Animation und Export

- Schnittebene, die durch das 3D-Modell fährt
- Kamerafahrten mit Start- und Endansicht
- Video-Export (MP4)
- STL-Export einzelner Strukturen, zum Beispiel für den 3D-Druck

### Phase 3: Werkzeuge für Ärzte

Jedes Werkzeug ist ein eigenes Modul und kann einzeln und in beliebiger Reihenfolge umgesetzt werden.

- **Messwerkzeuge:** Distanz, Winkel, Fläche, Volumen einer markierten Region
- **MIP und MinIP:** Standardansichten aus der Radiologie, MIP für Gefässe und kleine Strukturen, MinIP für die Atemwege
- **Markierungen und Notizen** in 2D und 3D, speicherbar
- **Vergleichsansicht:** zwei Untersuchungen nebeneinander, synchron gescrollt und gedreht
- **Patientengespräch-Modus:** vereinfachte, farbige 3D-Ansicht zum Erklären
- **Bericht als PDF** mit Screenshots, Messungen und Notizen

### Phase 4: KI-Schnittstelle (optional, aktuell nicht geplant)

Wird nicht umgesetzt, bis ausdrücklich entschieden wird. Die Architektur hält den Platz frei: Eine KI-Segmentierung wäre einfach ein weiterer Segmentierer (siehe Kapitel 5), der Kern bleibt unverändert.

Mögliche Inhalte:
- TotalSegmentator (Open Source), läuft lokal auf einer Nvidia-Grafikkarte
- Feinere Aufteilung der Strukturen (siehe Tabelle)
- Automatisch berechnetes Volumen pro Lungenlappen

Voraussetzungen: Lizenzen der Modelle prüfen, Modellgewichte einmalig laden und lokal mitliefern. Die .exe wird dadurch mehrere GB grösser.

| Struktur | Basis (Dichtewerte) | Optional mit KI |
|---|---|---|
| Lunge | als Ganzes | links und rechts, fünf Lappen einzeln |
| Atemwege | Luftröhre und grosse Bronchien | Luftröhre und Bronchien genauer |
| Knochen | alle zusammen | Rippen, Wirbel, Brustbein, Schlüsselbeine einzeln |
| Herz und Gefässe | nicht zuverlässig trennbar | Herz, Aorta, grosse Gefässe |
| Körperumriss | ja | ja |

## 5. Architektur und Erweiterbarkeit

Grundidee: ein kleiner, stabiler Kern. Alles andere hängt sich über klar definierte Schnittstellen an. Der Kern kennt keine Module, und Module greifen nur über die Schnittstellen auf den Kern zu.

**Kern**
- **Volumen:** Dichtewerte in Hounsfield-Einheiten mit Abstand, Ursprung und Ausrichtung, alles in echten Millimeter-Koordinaten
- **Struktur:** Name, Maske, Farbe, Transparenz, sichtbar ja oder nein
- **Sitzung:** geladene Serie, Strukturen, Markierungen und gespeicherte Ansichten

**Schnittstellen**

| Schnittstelle | Aufgabe | Basis | Später |
|---|---|---|---|
| Segmentierer | erzeugt Strukturen aus einem Volumen | Schwellenwert-Segmentierer | optional KI-Segmentierer (Phase 4) |
| Werkzeug | Funktion mit eigenem Button oder Panel | keine | Messen, MIP/MinIP, Notizen, Vergleich, Gesprächsmodus |
| Exporter | schreibt Ergebnisse in eine Datei | Screenshot | Video, STL, PDF |

Ein neues Werkzeug ist eine neue Datei im Ordner `tools/` plus eine Registrierung. Am Kern und am Hauptfenster muss dafür nichts geändert werden.

## 6. Genauigkeit und Qualitätssicherung

Die Animation verändert keine Daten, sie bewegt nur die Kamera. Die Genauigkeit entscheidet sich beim Einlesen und beim Trennen der Strukturen.

**Korrekt einlesen**
- Rohwerte mit den Umrechnungsfaktoren aus jeder Datei in Hounsfield-Einheiten umrechnen
- Schichten nach ihrer tatsächlichen Position sortieren, nicht nach Dateiname
- Abstände aus den Positionen berechnen und Ausrichtung übernehmen
- Bei Auffälligkeiten eine klare Warnung anzeigen statt ein still falsches Modell

**Gegenkontrolle**
- **Phantome:** selbst erzeugte DICOM-Dateien mit bekannten Massen, zum Beispiel eine Kugel mit genau 50 mm Durchmesser und eindeutige Markierungen für links und rechts. Das Programm muss genau diese Werte liefern.
- **Referenz 3D Slicer:** gleiche Serie öffnen und Dichtewerte sowie Distanzen an derselben Stelle vergleichen
- **Automatische Tests:** laufen bei jeder Änderung mit

**Abschluss jeder Phase:** alle Tests grün, Stichprobe gegen 3D Slicer stimmt, .exe lässt sich bauen und starten.

**Grenzen:** An Übergängen, etwa zwischen Lunge und Gefäss, gibt es immer etwas Unschärfe. Als Anschauungsmodell sehr gut, für millimetergenaue Aussagen ist Vorsicht nötig.

## 7. Technik

| Bereich | Lösung |
|---|---|
| Sprache | Python 3 (aktuelle Version) |
| DICOM einlesen | pydicom, SimpleITK |
| Bildverarbeitung | NumPy, scikit-image |
| 3D-Darstellung | PyVista (VTK), pyvistaqt |
| Oberfläche | PySide6 (Qt) |
| Tests | pytest |
| Verpackung | PyInstaller → Windows-.exe |
| Video (Phase 2) | imageio mit ffmpeg |
| PDF (Phase 3) | reportlab |
| KI (Phase 4, optional) | TotalSegmentator mit PyTorch, nicht Teil der Basis |

Zielsystem ist Windows 10 und 11. Die Basis enthält keine KI-Abhängigkeiten, die .exe bleibt dadurch klein.

## 8. Projektstruktur

```
akicheast3d/
├── CLAUDE.md
├── PROJEKT.md
├── requirements.txt
├── requirements-dev.txt  nur Entwicklung (Testdaten-Download, pytest)
├── build.bat
├── .gitignore
├── src/akicheast3d/
│   ├── main.py
│   ├── core/           Volumen, Struktur, Sitzung, Schnittstellen
│   ├── loading/        DICOM einlesen, Serien erkennen, Prüfungen, Anonymisierung
│   ├── segmentation/   Segmentierer (Basis: Schwellenwerte)
│   ├── ui/             Hauptfenster, 2D- und 3D-Ansicht
│   ├── tools/          Werkzeug-Module (ab Phase 3)
│   └── export/         Exporter (Screenshot, später Video, STL, PDF)
├── scripts/
│   └── testdaten_laden.py  lädt die öffentlichen Testdaten
├── tests/
│   └── phantoms/       Erzeugung der künstlichen Testobjekte
└── testdata/           nur öffentliche Testdaten, nicht im Git
```

## 9. Zweckbestimmung und Regulierung

AKICHEAST 3D ist ein Anschauungs- und Gesprächswerkzeug und kein Medizinprodukt. Es erstellt keine Befunde und erkennt keine Auffälligkeiten automatisch.

Software mit medizinischem Zweck, insbesondere für diagnostische oder therapeutische Entscheide, gilt in der Schweiz als Medizinprodukt (MepV, Regel 11, mindestens Klasse IIa) und braucht ein Konformitätsbewertungsverfahren mit einer benannten Stelle. Soll das Programm später so eingesetzt werden, ist das ein eigenes Projekt mit Qualitätsmanagement, Risikoanalyse und klinischer Bewertung. Saubere Tests und Dokumentation ab Phase 0 erleichtern diesen Schritt.

## 10. Testdaten

Vier ausgewählte Serien aus dem öffentlichen Datensatz LIDC-IDRI, geladen über die NCI Imaging Data Commons mit `scripts/testdaten_laden.py` (ca. 450 MB, Lizenz CC BY 3.0, Quellenangabe in `testdata/QUELLE.md`).

| Patient-ID | Hersteller | Schichten | Zweck |
|---|---|---|---|
| LIDC-IDRI-0999 | GE | 250 | Dünnschicht, Implicit VR |
| LIDC-IDRI-0736 | Siemens | 250 | Dünnschicht, Explicit VR |
| LIDC-IDRI-0508 | Philips | 250 | Dünnschicht, Explicit VR |
| LIDC-IDRI-0709 | Toshiba | 100 | wenige, dickere Schichten |

Die Mischung aus vier Herstellern und zwei DICOM-Kodierungen prüft, ob das Einlesen robust ist. Dazu kommen die eigenen Phantome aus `tests/phantoms/`.

## 11. Offene Punkte

- [ ] Echte DICOM-Daten beim Spital anfordern (vollständige Untersuchung inklusive Dünnschicht-Serien)
- [ ] Projektname final bestätigen
- [ ] Startsignal für Phase 0
- [ ] Entscheid über Phase 4 (KI), aktuell nicht geplant
