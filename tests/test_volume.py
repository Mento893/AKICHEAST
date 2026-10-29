import numpy as np
import pytest

from akicheast3d.core import Volume


def make_volume(**kwargs) -> Volume:
    defaults = dict(hu=np.zeros((4, 5, 6), dtype=np.int16), spacing=(0.5, 0.8, 2.0))
    defaults.update(kwargs)
    return Volume(**defaults)


def test_size_is_in_ijk_order():
    volume = make_volume()
    assert volume.size == (6, 5, 4)


def test_extent_and_voxel_volume():
    volume = make_volume()
    assert volume.extent_mm == pytest.approx((3.0, 4.0, 8.0))
    assert volume.voxel_volume_mm3 == pytest.approx(0.8)


def test_index_to_world_with_identity_direction():
    volume = make_volume(origin=(10.0, -20.0, 30.0))
    assert volume.index_to_world((0, 0, 0)) == pytest.approx((10.0, -20.0, 30.0))
    assert volume.index_to_world((2, 1, 3)) == pytest.approx((11.0, -19.2, 36.0))


def test_index_to_world_with_flipped_axes():
    # Spalten zeigen nach rechts (-x), Schichten zu den Füssen (-z)
    direction = np.diag([-1.0, 1.0, -1.0])
    volume = make_volume(direction=direction)
    assert volume.index_to_world((2, 1, 3)) == pytest.approx((-1.0, 0.8, -6.0))


def test_world_to_index_inverts_index_to_world():
    angle = np.radians(30)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
    )
    volume = make_volume(origin=(5.0, 6.0, 7.0), direction=rotation)
    indices = np.array([[0, 0, 0], [1, 2, 3], [5, 4, 3]], dtype=float)
    world = volume.index_to_world(indices)
    assert volume.world_to_index(world) == pytest.approx(indices)


def test_hu_at_world_uses_nearest_voxel():
    hu = np.zeros((4, 5, 6), dtype=np.int16)
    hu[3, 1, 2] = 123
    volume = make_volume(hu=hu, origin=(1.0, 1.0, 1.0))
    assert volume.hu_at_world((2.1, 1.7, 7.4)) == 123


def test_hu_at_world_outside_raises():
    volume = make_volume()
    with pytest.raises(IndexError):
        volume.hu_at_world((-5.0, 0.0, 0.0))


def test_hu_is_read_only():
    volume = make_volume()
    with pytest.raises(ValueError):
        volume.hu[0, 0, 0] = 1


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(hu=np.zeros((4, 5))),
        dict(spacing=(1.0, 0.0, 1.0)),
        dict(spacing=(1.0, 1.0)),
        dict(origin=(0.0, 0.0)),
        dict(direction=np.eye(2)),
        dict(direction=np.diag([2.0, 1.0, 1.0])),
    ],
)
def test_invalid_volume_raises(kwargs):
    with pytest.raises(ValueError):
        make_volume(**kwargs)
