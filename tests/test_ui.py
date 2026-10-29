import pytest
from PySide6.QtWidgets import QApplication

from akicheast3d.ui.disclaimer import DISCLAIMER_TEXT, create_disclaimer
from akicheast3d.ui.main_window import APP_TITLE, MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_main_window_title(app):
    window = MainWindow()
    assert window.windowTitle() == APP_TITLE


def test_disclaimer_says_no_diagnosis(app):
    assert "kein Medizinprodukt" in DISCLAIMER_TEXT
    assert "keine Befunde" in DISCLAIMER_TEXT
    box = create_disclaimer()
    assert box.text() == DISCLAIMER_TEXT
