"""Alle Phantome als DICOM-Ordner schreiben, zum Beispiel für den Vergleich mit 3D Slicer.

Aufruf aus dem Projektordner:
    python -m tests.phantoms                 schreibt nach testdata/phantome/
    python -m tests.phantoms <zielordner>
"""

import sys
from pathlib import Path

from tests.phantoms.generator import ALL_PHANTOMS, write_phantom


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("testdata") / "phantome"
    for name, build in ALL_PHANTOMS.items():
        paths = write_phantom(build(), target / name)
        print(f"{name:<22} {len(paths):>3} Schichten  {target / name}")


if __name__ == "__main__":
    main()
