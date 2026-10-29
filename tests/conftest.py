import os
from pathlib import Path

import pytest

# Qt ohne sichtbares Fenster, damit die Tests auch ohne Bildschirm laufen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.phantoms import ALL_PHANTOMS, Phantom, write_phantom  # noqa: E402


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
