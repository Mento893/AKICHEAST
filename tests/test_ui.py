"""Oberflächenteile ohne 3D-Ansicht, ohne sichtbares Fenster."""

import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from akicheast3d.core import Session, Volume
from akicheast3d.loading import LoadError, SeriesInfo, SeriesKind
from akicheast3d.ui.disclaimer import DISCLAIMER_TEXT, create_disclaimer
from akicheast3d.ui.info_panel import InfoPanel, describe
from akicheast3d.ui.series_dialog import RECOMMENDED, SeriesDialog, recommended_series
from akicheast3d.ui.tasks import TaskThread, stage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_disclaimer_says_no_diagnosis(app):
    assert "kein Medizinprodukt" in DISCLAIMER_TEXT
    assert "keine Befunde" in DISCLAIMER_TEXT
    box = create_disclaimer()
    assert box.text() == DISCLAIMER_TEXT


# Serienwahl


def info(number, thickness, count, kind=SeriesKind.VOLUME, note=""):
    return SeriesInfo(
        uid=str(number),
        number=number,
        description=f"Serie {number}",
        modality="CT",
        slice_thickness=thickness,
        files=tuple(f"f{n}" for n in range(count)),
        kind=kind,
        note=note,
    )


def test_recommended_is_thinnest_then_most_slices():
    series = [
        info(1, 5.0, 60),
        info(2, 1.0, 300),
        info(3, 1.0, 320),
        info(4, 0.5, 1, SeriesKind.LOCALIZER, "Topogramm"),
    ]
    assert recommended_series(series).number == 3
    assert recommended_series([series[3]]) is None


def test_dialog_preselects_and_blocks_unloadable(app):
    series = [info(1, 5.0, 60), info(2, 1.0, 300), info(3, None, 1, SeriesKind.LOCALIZER, "Topogramm")]
    dialog = SeriesDialog(series)
    assert dialog.selected_series() is series[1]
    assert dialog.table.item(1, 4).text() == RECOMMENDED
    assert dialog._ok.isEnabled()

    dialog.table.selectRow(2)
    assert dialog.selected_series() is not series[2]
    dialog.table.selectRow(0)
    assert dialog.selected_series() is series[0]


def test_dialog_without_loadable_series(app):
    dialog = SeriesDialog([info(1, None, 1, SeriesKind.DOSE_REPORT, "Dosisbericht")])
    assert dialog.selected_series() is None
    assert not dialog._ok.isEnabled()


# Infofeld


def make_session(warnings):
    volume = Volume(np.zeros((40, 50, 60), dtype=np.int16), spacing=(0.7, 0.7, 1.25))
    return Session(volume, series_description="Thorax <1 mm>", warnings=warnings)


def test_info_shows_geometry_and_escapes_text():
    text = describe(make_session([]))
    assert "Thorax &lt;1 mm&gt;" in text
    assert "Schichten: 40" in text
    assert "Schichtabstand: 1.25 mm" in text
    assert "Pixelgrösse: 0.700 x 0.700 mm" in text
    assert "ohne Warnungen" in text


def test_info_shows_warnings(app):
    panel = InfoPanel()
    panel.set_session(make_session(["Gekippte Gantry (15.0°)."]))
    assert "Gekippte Gantry" in panel.label.text()
    panel.set_session(None)
    assert "Keine Serie geladen" in panel.label.text()


# Hintergrund-Aufgaben


def run_task(app, function):
    results = {"progress": []}
    task = TaskThread(function)
    task.progress.connect(lambda value, text: results["progress"].append((value, text)))
    task.succeeded.connect(lambda value: results.__setitem__("result", value))
    task.failed.connect(lambda message: results.__setitem__("error", message))
    task.start()
    deadline = time.time() + 10
    while not task.isFinished() and time.time() < deadline:
        app.processEvents()
    task.wait()
    app.processEvents()
    return results


def test_task_reports_progress_and_result(app):
    def work(report):
        progress = stage(report, 0.5, 1.0, "Teil 2")
        progress(0.5)
        return 42

    results = run_task(app, work)
    assert results["result"] == 42
    assert results["progress"] == [(0.5, "Teil 2"), (0.75, "Teil 2")]


def test_task_reports_load_error_as_message(app):
    def work(report):
        raise LoadError("Diese Serie geht nicht.")

    assert run_task(app, work)["error"] == "Diese Serie geht nicht."


def test_task_reports_unexpected_error(app):
    def work(report):
        raise RuntimeError("kaputt")

    assert run_task(app, work)["error"] == "Unerwarteter Fehler: kaputt"
