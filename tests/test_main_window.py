"""Hauptfenster im echten Fenster: Serie öffnen, anzeigen, ausblenden, exportieren, Fehlerfall."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("hauptfenster")
    env = {k: v for k, v in os.environ.items() if k != "QT_QPA_PLATFORM"}
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.run(
        [sys.executable, "-m", "tests.gui_checks.main_window_check", str(workdir)],
        cwd=PROJECT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    if process.returncode != 0:
        pytest.fail(process.stderr[-3000:])
    return json.loads(process.stdout.strip().splitlines()[-1])


def test_start_state(result):
    assert result["title"] == "AKICHEAST 3D"
    assert result["export_enabled_before"] == [False]
    assert "Keine Serie geladen" in result["info_before"]


def test_series_is_shown_everywhere(result):
    assert result["structures"] == ["Lunge", "Atemwege", "Knochen", "Körperumriss"]
    assert result["panel_rows"] == 4
    assert result["actors"] == ["Körperumriss"]
    assert result["axial_slices"] > 40
    assert result["export_enabled_after"] == [True]
    assert result["open_enabled_after"]


def test_info_shows_tilt_warning(result):
    assert "Phantom gekippte Gantry" in result["info"]
    assert "Gekippte Gantry (15.0°)" in result["info"]


def test_hiding_structure_hides_actor(result):
    assert result["body_actor_visible"] is False


def test_screenshot_export(result):
    width, height = result["screenshot"]
    assert width > 100 and height > 100


def test_unloadable_series_shows_message_and_keeps_session(result):
    assert len(result["warnings"]) == 1
    assert "Topogramm" in result["warnings"][0]
    assert result["session_kept"]
