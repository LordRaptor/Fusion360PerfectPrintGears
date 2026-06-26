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


MIN_PINION_TEETH = 6


def validate_inputs(inp: GearInputs) -> None:
    """Raise ValueError with a human-readable message if inputs are unusable."""
    if inp.pinion_teeth < MIN_PINION_TEETH:
        raise ValueError(f"pinion teeth must be at least {MIN_PINION_TEETH}")
    if inp.wheel_teeth < inp.pinion_teeth:
        raise ValueError("wheel teeth must be >= pinion teeth")
    if inp.module_mm <= 0:
        raise ValueError("module must be greater than 0")
    if inp.feature_width_mm <= 0:
        raise ValueError("feature width must be greater than 0")

    geo = derive_geometry(inp)
    # Teeth would touch/overlap if the tooth is wider than the tooth-to-tooth spacing.
    # Require the tooth to occupy less than the circular pitch so a real gap remains.
    if inp.feature_width_mm >= geo.circular_pitch:
        raise ValueError(
            "feature width is too large for this module/teeth (teeth would overlap); "
            "reduce feature width or increase module"
        )
    # Pinion flanks (offset half-width from a radial) must not cross the pinion centre.
    if inp.feature_width_mm / 2.0 >= geo.pitch_radius_pinion:
        raise ValueError("feature width is too large for the pinion size")
    if inp.clearance_mm < 0:
        raise ValueError("clearance must be >= 0")
    if inp.clearance_mm >= inp.feature_width_mm:
        raise ValueError("clearance must be less than the feature width")
