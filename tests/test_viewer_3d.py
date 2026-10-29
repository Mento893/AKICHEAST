"""3D-Ansicht, Oberflächen, Strukturen-Panel und Screenshot-Exporter."""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from akicheast3d.core import Structure, Volume, exporters
from akicheast3d.loading import load_series, scan
from akicheast3d.ui import surface as surface_module
from akicheast3d.ui.structure_panel import StructurePanel
from akicheast3d.ui.surface import mask_to_surface

PROJECT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def sphere_volume(phantom_dirs):
    (series,) = scan(phantom_dirs["kugel"])
    return load_series(series).volume


# Oberflächen


def test_sphere_surface_has_true_size_and_position(sphere_volume):
    surface = mask_to_surface(sphere_volume.hu > -500, sphere_volume)
    assert surface.n_open_edges == 0
    assert surface.volume == pytest.approx(4 / 3 * math.pi * 25.0**3, rel=0.01)
    assert surface.bounds == pytest.approx((-25, 25, -25, 25, -25, 25), abs=0.2)
    assert surface.center == pytest.approx((0, 0, 0), abs=0.05)


def test_halved_resolution_keeps_size(sphere_volume, monkeypatch):
    monkeypatch.setattr(surface_module, "LARGE_VOXELS", 0)
    monkeypatch.setattr(surface_module, "FINE_PIXEL_MM", 10.0)
    surface = mask_to_surface(sphere_volume.hu > -500, sphere_volume)
    assert surface.volume == pytest.approx(4 / 3 * math.pi * 25.0**3, rel=0.02)
    assert surface.center == pytest.approx((0, 0, 0), abs=0.3)


def test_structure_cut_at_border_is_closed():
    mask = np.ones((10, 10, 10), dtype=bool)
    volume = Volume(np.zeros((10, 10, 10)), spacing=(1.0, 1.0, 1.0))
    surface = mask_to_surface(mask, volume)
    assert surface.n_open_edges == 0
    assert surface.volume == pytest.approx(1000, rel=0.1)


def test_surface_follows_direction():
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[2:5, 2:5, 2:5] = True
    flipped = Volume(np.zeros((10, 10, 10)), spacing=(1.0, 1.0, 1.0), direction=np.diag([-1.0, 1.0, 1.0]))
    surface = mask_to_surface(mask, flipped)
    assert surface.center[0] == pytest.approx(-3.0, abs=0.1)


def test_empty_mask_gives_empty_surface():
    volume = Volume(np.zeros((4, 4, 4)), spacing=(1.0, 1.0, 1.0))
    assert mask_to_surface(np.zeros((4, 4, 4), dtype=bool), volume).n_points == 0


# Strukturen-Panel


def make_structures():
    full = np.ones((2, 2, 2), dtype=bool)
    return [
        Structure("Lunge", full, color=(0.5, 0.7, 0.9), opacity=0.6),
        Structure("Atemwege", np.zeros((2, 2, 2), dtype=bool), color=(0.3, 0.8, 0.5)),
    ]


def test_panel_changes_structure_and_emits(app):
    panel = StructurePanel()
    structures = make_structures()
    panel.set_structures(structures)
    changed = []
    panel.changed.connect(changed.append)

    row = panel.rows[0]
    assert row.opacity.value() == 60
    row.checkbox.setChecked(False)
    row.opacity.setValue(25)
    row.set_color(QColor(255, 0, 0))

    lung = structures[0]
    assert not lung.visible
    assert lung.opacity == 0.25
    assert lung.color == (1.0, 0.0, 0.0)
    assert changed == [lung, lung, lung]


def test_panel_disables_structures_not_found(app):
    panel = StructurePanel()
    panel.set_structures(make_structures())
    assert panel.rows[0].checkbox.isEnabled()
    assert not panel.rows[1].checkbox.isEnabled()


def test_panel_replaces_rows(app):
    panel = StructurePanel()
    panel.set_structures(make_structures())
    panel.set_structures(make_structures()[:1])
    assert len(panel.rows) == 1


# Screenshot


def test_screenshot_exporter_writes_png(tmp_path):
    import akicheast3d.export  # noqa: F401

    pixels = np.zeros((20, 30, 3), dtype=np.uint8)
    pixels[:, :15] = (255, 0, 0)
    pixels[:, 15:] = (0, 0, 255)

    class Context:
        session = None

        def render_image(self):
            return pixels

    exporter = exporters.create("Screenshot (PNG)")
    target = tmp_path / "bild.png"
    exporter.export(Context(), target)

    image = QImage(str(target))
    assert (image.width(), image.height()) == (30, 20)
    assert image.pixelColor(2, 2) == QColor(255, 0, 0)
    assert image.pixelColor(28, 18) == QColor(0, 0, 255)


# 3D-Ansicht im echten Fenster


@pytest.fixture(scope="module")
def viewer_result():
    env = {k: v for k, v in os.environ.items() if k != "QT_QPA_PLATFORM"}
    process = subprocess.run(
        [sys.executable, "-m", "tests.gui_checks.viewer_3d_check"],
        cwd=PROJECT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if process.returncode != 0:
        pytest.fail(process.stderr[-2000:])
    return json.loads(process.stdout.strip().splitlines()[-1])


def test_viewer_shows_and_hides_structures(viewer_result):
    assert viewer_result["actors"] == ["Rot"]
    red, green, blue = viewer_result["visible"]
    assert red > 150 and green < 60 and blue < 60
    assert max(viewer_result["hidden"]) < 60
    red, green, blue = viewer_result["recolored"]
    assert blue > 150 and red < 60


def test_viewer_standard_views(viewer_result):
    views = viewer_result["views"]
    assert views["Vorne"] == pytest.approx([0, -1, 0], abs=0.01)
    assert views["Hinten"] == pytest.approx([0, 1, 0], abs=0.01)
    assert views["Links"] == pytest.approx([1, 0, 0], abs=0.01)
    assert views["Rechts"] == pytest.approx([-1, 0, 0], abs=0.01)
    assert views["Oben"] == pytest.approx([0, 0, 1], abs=0.01)


def test_viewer_rotation_and_clear(viewer_result):
    assert viewer_result["rotated"]
    assert viewer_result["rotating"]
    assert viewer_result["after_clear"] == []
    assert viewer_result["image_shape"][2] == 3
