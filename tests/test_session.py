import numpy as np
import pytest

from akicheast3d.core import Marker, SavedView, Session, Structure, Volume

SHAPE = (3, 4, 5)


@pytest.fixture
def session() -> Session:
    volume = Volume(np.zeros(SHAPE, dtype=np.int16), spacing=(1.0, 1.0, 1.0))
    return Session(volume, series_description="Thorax 1 mm", warnings=["Testwarnung"])


def structure(name: str, shape=SHAPE) -> Structure:
    return Structure(name, np.zeros(shape, dtype=bool), color=(1.0, 0.0, 0.0))


def test_new_session_is_empty(session):
    assert session.structures == []
    assert session.markers == []
    assert session.views == {}
    assert session.warnings == ["Testwarnung"]


def test_structures_keep_insertion_order(session):
    session.add_structure(structure("Lunge"))
    session.add_structure(structure("Knochen"))
    assert [s.name for s in session.structures] == ["Lunge", "Knochen"]
    assert session.structure("Knochen").name == "Knochen"


def test_duplicate_structure_raises(session):
    session.add_structure(structure("Lunge"))
    with pytest.raises(ValueError):
        session.add_structure(structure("Lunge"))


def test_mask_shape_must_match_volume(session):
    with pytest.raises(ValueError):
        session.add_structure(structure("Lunge", shape=(3, 4, 6)))


def test_remove_and_clear_structures(session):
    session.add_structure(structure("Lunge"))
    session.add_structure(structure("Knochen"))
    session.remove_structure("Lunge")
    assert [s.name for s in session.structures] == ["Knochen"]
    with pytest.raises(KeyError):
        session.remove_structure("Lunge")
    session.clear_structures()
    assert session.structures == []


def test_markers_and_views(session):
    session.add_marker(Marker((1.0, 2.0, 3.0), "Spitze"))
    assert session.markers[0].position_mm == (1.0, 2.0, 3.0)

    session.save_view(SavedView("Front", (0, -500, 0), (0, 0, 0), (0, 0, 1)))
    session.save_view(SavedView("Front", (0, -300, 0), (0, 0, 0), (0, 0, 1)))
    assert list(session.views) == ["Front"]
    assert session.views["Front"].camera_position == (0, -300, 0)
