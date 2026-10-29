"""Vereinfachter Thorax mit bekannten Strukturen, für die Tests der Segmentierung.

Das Phantom wird direkt als Volumen erzeugt (ohne DICOM), zusammen mit den
wahren Masken. Koordinaten in mm, Mitte des Volumens bei (0, 0, 0),
+x links, +y hinten, +z Kopf.

Aufbau:
- Körper: elliptischer Zylinder, Weichteil 40 HU
- zwei Lungen: Ellipsoide mit -850 HU, unten von der Zwerchfellkuppe eingedrückt
- in jeder Lunge ein Gefässbaum aus drei Ästen (Weichteil 40 HU)
- Luftröhre ab z = 30 mm nach oben, zwei Hauptbronchien bis in die Lungen, -1000 HU
- Wirbelsäule und Rippen mit 700 HU
- Untersuchungstisch unter dem Körper (500 HU), darf nicht als Knochen gelten
- Luftblase im Magen und ein kleiner Kalkfleck, dürfen nicht zur Lunge bzw. zu den Knochen
- Bildrauschen mit 15 HU
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from akicheast3d.core import Volume

SPACING = (1.5, 1.5, 2.0)
EXTENT_MM = (210.0, 180.0, 160.0)

SOFT_TISSUE_HU = 40
LUNG_HU = -850
AIR_HU = -1000
BONE_HU = 700
TABLE_HU = 500
NOISE_HU = 15

BODY_AXES = (85.0, 65.0)
LUNG_CENTERS = ((-40.0, 0.0, 0.0), (40.0, 0.0, 0.0))
LUNG_AXES = (28.0, 45.0, 60.0)
TRACHEA = ((0.0, -15.0), 8.0, 30.0)  # Mitte (x, y), Radius, unteres Ende z
CARINA = np.array([0.0, -15.0, 30.0])
BRONCHUS_ENDS = (np.array([-35.0, -5.0, 15.0]), np.array([35.0, -5.0, 15.0]))
BRONCHUS_RADIUS = 5.0
SPINE = ((0.0, 45.0), 15.0)
RIB_AXES = (78.0, 58.0)
RIB_THICKNESS = 5.0
RIB_CENTERS_Z = (-50.0, -25.0, 0.0, 25.0, 50.0)
RIB_HEIGHT = 8.0
LUNG_BASE_Z = -45.0
"""Die Lungen sind unten flach abgeschnitten, wie ein breiter Lungenboden."""
DOME_CENTERS = ((-40.0, 0.0, -60.0), (40.0, 0.0, -60.0))
DOME_AXES = (14.0, 24.0, 25.0)
VESSEL_RADIUS = 2.5
VESSEL_BRANCHES = (  # für die linke Lunge (+x), rechts gespiegelt
    ((25.0, 5.0, -10.0), (50.0, 5.0, -40.0)),
    ((25.0, 5.0, -10.0), (50.0, 5.0, 20.0)),
    ((25.0, 5.0, -10.0), (55.0, 15.0, -10.0)),
)
STOMACH = ((30.0, 10.0, -72.0), 6.0)
CALCIFICATION = (0.0, -40.0, -40.0)


@dataclass
class ThoraxPhantom:
    volume: Volume
    lung: np.ndarray
    vessels: np.ndarray
    dome: np.ndarray
    airways: np.ndarray
    bone: np.ndarray
    body: np.ndarray
    table: np.ndarray
    stomach: np.ndarray
    calcification: np.ndarray


def thorax_phantom(seed: int = 0) -> ThoraxPhantom:
    size = [int(round(e / s)) for e, s in zip(EXTENT_MM, SPACING)]
    origin = [-(n - 1) * s / 2 for n, s in zip(size, SPACING)]
    z, y, x = np.meshgrid(
        *(o + np.arange(n) * s for o, n, s in zip(origin[::-1], size[::-1], SPACING[::-1])),
        indexing="ij",
    )

    body = (x / BODY_AXES[0]) ** 2 + (y / BODY_AXES[1]) ** 2 <= 1
    lungs = np.zeros_like(body)
    for cx, cy, cz in LUNG_CENTERS:
        a, b, c = LUNG_AXES
        lungs |= ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 + ((z - cz) / c) ** 2 <= 1
    lungs &= z >= LUNG_BASE_Z
    dome = np.zeros_like(body)
    for cx, cy, cz in DOME_CENTERS:
        a, b, c = DOME_AXES
        dome |= ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 + ((z - cz) / c) ** 2 <= 1
    lungs &= ~dome

    vessels = np.zeros_like(body)
    for sign in (-1.0, 1.0):
        for start, end in VESSEL_BRANCHES:
            mirror = np.array([sign, 1.0, 1.0])
            vessels |= _cylinder(x, y, z, np.array(start) * mirror, np.array(end) * mirror, VESSEL_RADIUS)
    vessels &= lungs

    (tx, ty), radius, bottom = TRACHEA
    airways = ((x - tx) ** 2 + (y - ty) ** 2 <= radius**2) & (z >= bottom)
    for end in BRONCHUS_ENDS:
        airways |= _cylinder(x, y, z, CARINA, end, BRONCHUS_RADIUS)
    airways &= body

    (sx, sy), spine_radius = SPINE
    bone = (x - sx) ** 2 + (y - sy) ** 2 <= spine_radius**2
    outer = (x / RIB_AXES[0]) ** 2 + (y / RIB_AXES[1]) ** 2 <= 1
    inner_axes = (RIB_AXES[0] - RIB_THICKNESS, RIB_AXES[1] - RIB_THICKNESS)
    inner = (x / inner_axes[0]) ** 2 + (y / inner_axes[1]) ** 2 <= 1
    in_rib_slab = np.zeros_like(body)
    for center in RIB_CENTERS_Z:
        in_rib_slab |= np.abs(z - center) <= RIB_HEIGHT / 2
    bone |= outer & ~inner & in_rib_slab

    table = (y >= BODY_AXES[1] + 10) & (y <= BODY_AXES[1] + 20) & (np.abs(x) <= 90)

    (gx, gy, gz), stomach_radius = STOMACH
    stomach = (x - gx) ** 2 + (y - gy) ** 2 + (z - gz) ** 2 <= stomach_radius**2

    cx, cy, cz = CALCIFICATION
    calcification = (np.abs(x - cx) <= 1) & (np.abs(y - cy) <= 1) & (np.abs(z - cz) <= 1)

    hu = np.full(body.shape, AIR_HU, dtype=np.float32)
    hu[body] = SOFT_TISSUE_HU
    hu[table] = TABLE_HU
    hu[lungs] = LUNG_HU
    hu[vessels] = SOFT_TISSUE_HU
    hu[airways] = AIR_HU
    hu[bone] = BONE_HU
    hu[stomach] = AIR_HU
    hu[calcification] = 300
    hu += np.random.default_rng(seed).normal(0, NOISE_HU, hu.shape)

    volume = Volume(np.rint(hu).astype(np.int16), SPACING, tuple(origin))
    return ThoraxPhantom(
        volume=volume,
        lung=lungs & ~airways,
        vessels=vessels & ~airways,
        dome=dome & body,
        airways=airways,
        bone=bone,
        body=body,
        table=table,
        stomach=stomach,
        calcification=calcification,
    )


def _cylinder(x, y, z, start: np.ndarray, end: np.ndarray, radius: float) -> np.ndarray:
    """Zylinder entlang der Strecke von start nach end."""
    axis = end - start
    length = np.linalg.norm(axis)
    axis = axis / length
    rel = np.stack([x - start[0], y - start[1], z - start[2]], axis=-1)
    along = rel @ axis
    distance = np.linalg.norm(rel - along[..., None] * axis, axis=-1)
    return (along >= 0) & (along <= length) & (distance <= radius)
