"""
AKICHEAST 3D: Öffentliche Testdaten laden

Lädt vier ausgewählte Lungen-CT-Serien aus dem öffentlichen Datensatz
LIDC-IDRI (NCI Imaging Data Commons) nach testdata/lidc_idri/.

Die Daten sind anonymisiert und stehen unter der Lizenz CC BY 3.0.
Das Skript ist ein Entwicklungswerkzeug und nicht Teil der .exe.
Internet wird nur für diesen einmaligen Download benötigt.

Autor: Mihailo Obradovic

Aufruf aus dem Projektordner:
    pip install -r requirements-dev.txt
    python scripts/testdaten_laden.py               Daten laden
    python scripts/testdaten_laden.py --nur-anzeigen nur Auswahl und Grösse anzeigen
"""

import argparse
import sys
from pathlib import Path

try:
    from idc_index import IDCClient
except ImportError:
    sys.exit("idc-index fehlt. Bitte zuerst ausführen: pip install -r requirements-dev.txt")


# Bewusst gemischte Auswahl: vier Hersteller, zwei DICOM-Kodierungen,
# viele dünne Schichten und eine Serie mit wenigen, dickeren Schichten.
TESTSERIEN = [
    {
        "patient": "LIDC-IDRI-0999",
        "hersteller": "GE",
        "zweck": "Dünnschicht, Implicit VR",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.216882370221919561230873289517",
    },
    {
        "patient": "LIDC-IDRI-0736",
        "hersteller": "Siemens",
        "zweck": "Dünnschicht, Explicit VR",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.756684168227383088294595834066",
    },
    {
        "patient": "LIDC-IDRI-0508",
        "hersteller": "Philips",
        "zweck": "Dünnschicht, Explicit VR",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.404768898286087278137462774930",
    },
    {
        "patient": "LIDC-IDRI-0709",
        "hersteller": "Toshiba",
        "zweck": "wenige, dickere Schichten",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.309707676674808510671394142910",
    },
]

QUELLE_TEXT = """# Quelle der Testdaten

Die Daten in `lidc_idri/` stammen aus dem öffentlichen Datensatz LIDC-IDRI,
bezogen über die NCI Imaging Data Commons.

- Lizenz: CC BY 3.0 (Quellenangabe erforderlich)
- DOI: https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX
- Die Daten sind anonymisiert und enthalten keine echten Patientennamen.

Dieser Ordner gehört nicht ins Git (siehe .gitignore).
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Öffentliche Testdaten für AKICHEAST 3D laden")
    parser.add_argument(
        "--nur-anzeigen",
        action="store_true",
        help="Auswahl und Grösse anzeigen, ohne etwas herunterzuladen",
    )
    args = parser.parse_args()

    projekt = Path(__file__).resolve().parent.parent
    ziel = projekt / "testdata"
    ziel.mkdir(exist_ok=True)

    client = IDCClient.client()
    uids = [s["series_uid"] for s in TESTSERIEN]

    # Prüfen, ob alle Serien im aktuellen Index vorhanden sind
    liste = ",".join(f"'{u}'" for u in uids)
    info = client.sql_query(
        f"SELECT SeriesInstanceUID, instanceCount, series_size_MB "
        f"FROM index WHERE SeriesInstanceUID IN ({liste})"
    )
    gefunden = set(info["SeriesInstanceUID"])

    print("Ausgewählte Testserien:")
    gesamt_mb = 0.0
    for s in TESTSERIEN:
        zeile = info[info["SeriesInstanceUID"] == s["series_uid"]]
        if zeile.empty:
            print(f"  FEHLT  {s['patient']} ({s['hersteller']})")
            continue
        anzahl = int(zeile["instanceCount"].iloc[0])
        mb = float(zeile["series_size_MB"].iloc[0])
        gesamt_mb += mb
        print(f"  {s['patient']}  {s['hersteller']:<8} {anzahl:>4} Schichten  {mb:6.0f} MB  {s['zweck']}")
    print(f"Gesamt: ca. {gesamt_mb:.0f} MB")

    if len(gefunden) != len(uids):
        sys.exit("Nicht alle Serien sind im Index vorhanden. Bitte idc-index aktualisieren.")

    if args.nur_anzeigen:
        return

    print(f"\nLade nach {ziel / 'lidc_idri'} ...")
    client.download_from_selection(
        seriesInstanceUID=uids,
        downloadDir=str(ziel),
        dirTemplate="%collection_id/%PatientID",
    )

    (ziel / "QUELLE.md").write_text(QUELLE_TEXT, encoding="utf-8")
    print("Fertig. Quellenangabe in testdata/QUELLE.md gespeichert.")


if __name__ == "__main__":
    main()
