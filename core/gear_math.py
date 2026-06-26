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


def rotate_point(p: Point, center: Point, angle: float) -> Point:
    s, c = math.sin(angle), math.cos(angle)
    dx, dy = p[0] - center[0], p[1] - center[1]
    return (center[0] + c * dx - s * dy, center[1] + s * dx + c * dy)


def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point):
    """Intersection of line(p1,p2) and line(p3,p4); None if (near) parallel."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12:
        return None
    a = x1 * y2 - y1 * x2
    b = x3 * y4 - y3 * x4
    px = (a * (x3 - x4) - (x1 - x2) * b) / den
    py = (a * (y3 - y4) - (y1 - y2) * b) / den
    return (px, py)


def wheel_tip_halfprofile(inp: GearInputs, geo: DerivedGeometry,
                          pinion_dir: int = 1, wheel_dir: int = 1) -> List[Point]:
    """Half of the wheel tooth tip, generated as the conjugate envelope of the
    moving pinion flank. Returns points ordered from the pitch-circle end to the
    tooth-centerline apex, in wheel-centered coordinates (mm), on the +x side.

    Method (Peterson, Clock Design Guidelines pp. 63-64):
      * The pinion working flank is a straight line parallel to a pinion radial,
        offset by half the feature width.
      * Step the meshing motion: rotate that flank about the pinion centre by
        k*delta, and simultaneously about the wheel centre by k*delta/ratio
        (opposite sense). delta spans one pinion tooth pitch over `resolution` steps.
      * The envelope tangent to that family of lines is the wheel tip; sample it
        as the intersection of consecutive line snapshots.
    """
    op = (geo.center_distance, 0.0)            # pinion centre
    ow = (0.0, 0.0)                            # wheel centre
    half_w = inp.feature_width_mm / 2.0

    # Reference upper flank: horizontal line at y=+half_w (parallel to the pinion
    # radial that points toward the wheel), defined by two points spanning well
    # past the pitch point so the family covers the whole tip.
    reach = geo.center_distance + geo.pitch_radius_pinion
    a_ref = (op[0], half_w)
    b_ref = (op[0] - reach, half_w)

    pitch_angle_pinion = 2.0 * math.pi / inp.pinion_teeth
    k_steps = max(8, inp.resolution)
    delta = pitch_angle_pinion / k_steps

    lines = []
    for k in range(k_steps + 1):
        tp = pinion_dir * k * delta
        tw = wheel_dir * k * delta / geo.ratio
        a = rotate_point(rotate_point(a_ref, op, tp), ow, tw)
        b = rotate_point(rotate_point(b_ref, op, tp), ow, tw)
        lines.append((a, b))

    half_tooth_angle = math.pi / inp.wheel_teeth
    addendum_ceiling = geo.pitch_radius_wheel + 2.0 * inp.module_mm

    raw = []
    for k in range(len(lines) - 1):
        e = line_intersection(lines[k][0], lines[k][1],
                              lines[k + 1][0], lines[k + 1][1])
        if e is None:
            continue
        x, y = e
        r = math.hypot(x, y)
        if x <= 0:
            continue
        ang = math.atan2(y, x)
        if not (-1e-9 <= ang <= half_tooth_angle + 1e-9):
            continue
        if not (geo.pitch_radius_wheel - 1e-6 <= r <= addendum_ceiling + 1e-6):
            continue
        raw.append((max(ang, 0.0), (x, y), r))

    # Order from the pitch-circle end (smallest radius) to the apex (largest radius).
    raw.sort(key=lambda t: t[2])
    return [p for (_a, p, _r) in raw]


@dataclass
class Segment:
    kind: str               # 'line' | 'spline' | 'arc3' (arc3 = [start, mid, end])
    points: List[Point]


def _polar(r: float, ang: float) -> Point:
    return (r * math.cos(ang), r * math.sin(ang))


def build_wheel_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One wheel tooth centered on the +x axis, as a connected list of Segments,
    ordered counter-clockwise: lower root -> lower flank -> tip (2 splines) ->
    upper flank -> upper root. Clearance narrows the tooth (both flanks pulled in).
    """
    tip = wheel_tip_halfprofile(inp, geo)            # pitch-end -> apex, upper (+y) side
    if not tip:
        raise ValueError("could not generate wheel tip envelope")

    # Pull the tip in by the clearance to leave running play (narrow the wheel tooth).
    clr = inp.clearance_mm
    upper_tip = []                                    # ordered pitch-end -> apex
    for (x, y) in tip:
        ang = math.atan2(y, x)
        r = math.hypot(x, y)
        ang_in = ang - (clr / 2.0) / r               # rotate toward centerline by clearance
        upper_tip.append(_polar(r, ang_in))
    apex = (upper_tip[-1][0], 0.0)                    # force apex onto the centerline
    lower_tip = [(x, -y) for (x, y) in upper_tip]     # mirror across the x-axis (pitch-end -> apex)

    # Flanks: straight radial walls from the root up to the pitch-circle end of the
    # tip, at the same angle as the tip's pitch-end point.
    root_radius = geo.pitch_radius_wheel - (inp.module_mm * 1.25 * inp.dedendum_factor)
    up_ang = math.atan2(upper_tip[0][1], upper_tip[0][0])
    lo_ang = math.atan2(lower_tip[0][1], lower_tip[0][0])
    upper_root_pt = _polar(root_radius, up_ang)
    lower_root_pt = _polar(root_radius, lo_ang)

    # Connected counter-clockwise path:
    #   lower flank -> lower tip (pitch-end..apex) -> upper tip (apex..pitch-end) -> upper flank
    segs: List[Segment] = []
    segs.append(Segment('line', [lower_root_pt, lower_tip[0]]))            # lower flank
    segs.append(Segment('spline', lower_tip + [apex]))                    # lower tip -> apex
    segs.append(Segment('spline', [apex] + list(reversed(upper_tip))))    # apex -> upper pitch-end
    segs.append(Segment('line', [upper_tip[0], upper_root_pt]))           # upper flank
    return segs
