import numpy as np
import pytest

from akicheast3d.core import Structure


def test_structure_defaults_and_voxel_count():
    mask = np.zeros((3, 4, 5), dtype=np.uint8)
    mask[1, 2, 3] = 1
    mask[0, 0, 0] = 1
    structure = Structure("Lunge", mask, color=(0.2, 0.6, 1.0))
    assert structure.mask.dtype == bool
    assert structure.voxel_count == 2
    assert structure.visible
    assert structure.opacity == 1.0


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(name="  "),
        dict(mask=np.zeros((3, 4))),
        dict(color=(1.0, 1.0)),
        dict(color=(1.0, 1.5, 0.0)),
        dict(opacity=1.2),
        dict(opacity=-0.1),
    ],
)
def test_invalid_structure_raises(kwargs):
    args = dict(name="Knochen", mask=np.zeros((3, 4, 5)), color=(1.0, 1.0, 0.9))
    args.update(kwargs)
    with pytest.raises(ValueError):
        Structure(**args)
