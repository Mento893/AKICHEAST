"""2D-Ansicht als Widget, ohne sichtbares Fenster."""

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from akicheast3d.core import Volume
from akicheast3d.ui.slice_view import SliceView
from akicheast3d.ui.slicing import Orientation
from akicheast3d.ui.viewer_2d import Viewer2D
from akicheast3d.ui.windowing import PRESETS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def volume():
    hu = np.arange(10 * 20 * 30, dtype=np.int16).reshape(10, 20, 30)
    return Volume(hu, spacing=(1.0, 1.0, 2.0), origin=(-15.0, -10.0, -10.0))


def wheel(view: SliceView, notches: int) -> None:
    center = QPointF(view.width() / 2, view.height() / 2)
    event = QWheelEvent(
        center,
        view.mapToGlobal(center),
        QPoint(0, 0),
        QPoint(0, 120 * notches),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    view.wheelEvent(event)


def test_view_starts_in_the_middle_and_clamps(app, volume):
    view = SliceView(Orientation.AXIAL)
    view.set_volume(volume)
    assert view.slice_count == 10
    assert view.slice_index == 5
    view.set_slice(99)
    assert view.slice_index == 9
    view.set_slice(-3)
    assert view.slice_index == 0


def test_mouse_wheel_scrolls(app, volume):
    view = SliceView(Orientation.CORONAL)
    view.resize(300, 300)
    view.set_volume(volume)
    start = view.slice_index
    wheel(view, 2)
    assert view.slice_index == start + 2
    wheel(view, -3)
    assert view.slice_index == start - 1


def test_image_keeps_aspect_ratio_in_mm(app, volume):
    view = SliceView(Orientation.CORONAL)
    view.resize(500, 500)
    view.set_volume(volume)
    rect = view.image_rect()
    # Koronal: 30 mm breit, 10 Schichten zu 2 mm = 20 mm hoch
    assert rect.width() / rect.height() == pytest.approx(30 / 20, rel=0.01)


def test_index_at_maps_widget_point_to_voxel(app, volume):
    view = SliceView(Orientation.AXIAL)
    view.resize(400, 400)
    view.set_volume(volume)
    rect = view.image_rect()
    assert view.index_at(rect.topLeft() + QPointF(0.5, 0.5)) == (0, 0, view.slice_index)
    assert view.index_at(rect.bottomRight() - QPointF(0.5, 0.5)) == (29, 19, view.slice_index)
    assert view.index_at(QPointF(1, 1)) is None


def test_view_renders_without_volume_and_with_volume(app, volume):
    view = SliceView(Orientation.SAGITTAL)
    view.resize(200, 200)
    assert not view.grab().isNull()
    view.set_volume(volume)
    view.set_cursor((3, 4, 5))
    assert not view.grab().isNull()


def test_click_moves_other_views(app, volume):
    viewer = Viewer2D()
    viewer.set_volume(volume)
    viewer.go_to((7, 3, 2))
    views = viewer.views
    assert views[Orientation.AXIAL].slice_index == 2
    assert views[Orientation.CORONAL].slice_index == 3
    assert views[Orientation.SAGITTAL].slice_index == 7


def test_slider_follows_view(app, volume):
    viewer = Viewer2D()
    viewer.set_volume(volume)
    panel = viewer.panels[Orientation.AXIAL]
    assert panel.slider.maximum() == 9
    panel.view.set_slice(4)
    assert panel.slider.value() == 4
    panel.slider.setValue(8)
    assert panel.view.slice_index == 8


def test_hover_shows_position_and_hu(app, volume):
    viewer = Viewer2D()
    viewer.set_volume(volume)
    viewer._show_value((1, 2, 3))
    hu = int(volume.hu[3, 2, 1])
    assert viewer.status.text() == f"R 14.0  V 8.0  F 4.0 mm    {hu} HU"
    viewer._show_value(None)
    assert viewer.status.text() == ""


def test_window_buttons(app, volume):
    viewer = Viewer2D()
    viewer.set_volume(volume)
    viewer.set_window(PRESETS["Knochen"])
    checked = [b.text() for b in viewer.window_buttons.buttons() if b.isChecked()]
    assert checked == ["Knochen"]
