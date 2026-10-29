"""Fensterung: welcher Bereich der Dichtewerte als Grautöne dargestellt wird."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WindowPreset:
    name: str
    width: float
    level: float


PRESETS = {
    preset.name: preset
    for preset in (
        WindowPreset("Lunge", 1500, -600),
        WindowPreset("Weichteil", 400, 40),
        WindowPreset("Knochen", 1800, 400),
    )
}
DEFAULT_PRESET = PRESETS["Lunge"]


def apply_window(hu: np.ndarray, preset: WindowPreset) -> np.ndarray:
    """Bildet Dichtewerte auf Grautöne 0 bis 255 ab (uint8)."""
    low = preset.level - preset.width / 2
    scaled = (hu.astype(np.float32) - low) * (255.0 / preset.width)
    return np.clip(np.rint(scaled), 0, 255).astype(np.uint8)
