# core/gear_math.py
"""Pure-Python Perfect Print gear geometry engine. No Fusion (adsk) imports.

All lengths are in millimeters. The caller (Fusion layer) converts mm -> cm.
Coordinate frame: wheel center at origin (0,0); pinion center at (center_distance, 0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]


@dataclass
class GearInputs:
    wheel_teeth: int
    pinion_teeth: int
    module_mm: float
    feature_width_mm: float
    clearance_mm: float
    addendum_factor: float = 1.0
    dedendum_factor: float = 1.0
    resolution: int = 24


@dataclass
class DerivedGeometry:
    pitch_radius_wheel: float
    pitch_radius_pinion: float
    center_distance: float
    ratio: float
    circular_pitch: float


def derive_geometry(inp: GearInputs) -> DerivedGeometry:
    rw = inp.module_mm * inp.wheel_teeth / 2.0
    rp = inp.module_mm * inp.pinion_teeth / 2.0
    return DerivedGeometry(
        pitch_radius_wheel=rw,
        pitch_radius_pinion=rp,
        center_distance=rw + rp,
        ratio=inp.wheel_teeth / inp.pinion_teeth,
        circular_pitch=math.pi * inp.module_mm,
    )
