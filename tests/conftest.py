import os
import shutil
from pathlib import Path

import pytest

# Qt ohne sichtbares Fenster, damit die Tests auch ohne Bildschirm laufen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.phantoms import ALL_PHANTOMS, Phantom, write_phantom  # noqa: E402
from tests.phantoms.generator import write_dose_report  # noqa: E402

LIDC_DIR = Path(__file__).resolve().parent.parent / "testdata" / "lidc_idri"


@pytest.fixture(scope="session")
def phantoms() -> dict[str, Phantom]:
    return {name: build() for name, build in ALL_PHANTOMS.items()}


@pytest.fixture(scope="session")
def phantom_dirs(phantoms, tmp_path_factory) -> dict[str, Path]:
    """Schreibt jedes Phantom einmal pro Testlauf in einen eigenen Ordner."""
    root = tmp_path_factory.mktemp("phantome")
    dirs = {}
    for name, phantom in phantoms.items():
        write_phantom(phantom, root / name)
        dirs[name] = root / name
    return dirs


@pytest.fixture(scope="session")
def study_dir(phantom_dirs, tmp_path_factory) -> Path:
    """Ordner wie aus dem Spital: Serie, Topogramm, Dosisbericht und fremde Dateien."""
    root = tmp_path_factory.mktemp("untersuchung")
    shutil.copytree(phantom_dirs["kugel"], root / "serie1" / "a")
    shutil.copytree(phantom_dirs["topogramm"], root / "serie2")
    write_dose_report(root / "serie3")
    (root / "liesmich.txt").write_text("keine DICOM-Datei", encoding="utf-8")
    (root / "serie1" / "kaputt.dcm").write_bytes(b"\x00" * 50)
    return root


@pytest.fixture(scope="session")
def lidc_dir() -> Path:
    if not LIDC_DIR.is_dir():
        pytest.skip("Öffentliche Testdaten fehlen (scripts/testdaten_laden.py)")
    return LIDC_DIR
