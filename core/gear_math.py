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
    # Meshing constraint: a wheel tooth (narrowed by the clearance) plus the pinion
    # tooth it meshes against must fit within one circular pitch, otherwise the
    # wheel tooth cannot fit the pinion gap and the teeth overlap. The wheel tooth
    # contributes (feature_width - clearance); the pinion gap is one pitch minus
    # the full pinion feature_width, so the requirement is:
    #     2*feature_width - clearance < circular_pitch.
    if 2.0 * inp.feature_width_mm - inp.clearance_mm >= geo.circular_pitch:
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


def wheel_tip_envelope(inp: GearInputs, geo: DerivedGeometry,
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


def radius_at_angle(a: float, pinion_teeth: int, wheel_teeth: int) -> float:
    """Epicycloid radius (pitch circle = unit) at angle `a` measured from the
    tooth edge. Ported exactly from the validated prototype's `radiusAtAngle`
    (FusionCycloidalGears / Keveney). Returns 1.0 (pitch circle) at a==0 and grows
    as the angle approaches the apex.
    """
    if a == 0:
        return 1.0
    error_limit = 1e-9
    t0 = 1.0
    t1 = 0.0
    b = 0.0
    r2 = 2.0 * wheel_teeth / pinion_teeth
    rg = 1.0 / r2
    while abs(t1 - t0) > error_limit:
        t0 = t1
        b = math.atan2(math.sin(t0), (1.0 + r2 - math.cos(t0)))
        t1 = r2 * (a + b)
    return (math.sin(t1) * rg) / math.sin(b)


def _build_wheel_tooth_cycloidal(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """Cycloidal wheel tooth centered on the +x axis (ported from the prototype's
    `wheel_tooth`): epicycloidal addendum (edge at the pitch circle, apex on the
    tooth centerline) scaled by the wheel pitch radius, plus constant-width
    straight dedendum flanks down to root feet. Clearance narrows the tooth by
    pulling the effective half-width in by clearance/2 on each side.

    Returned as a connected counter-clockwise list of Segments:
      lower flank (line) -> lower tip half (spline) -> upper tip half (spline)
      -> upper flank (line). Two splines for the tip, meeting at the apex.
    """
    rw = geo.pitch_radius_wheel
    # Clearance narrows the wheel tooth: reduce the effective half-width.
    half_w = inp.feature_width_mm / 2.0 - inp.clearance_mm / 2.0
    if half_w <= 0:
        raise ValueError("clearance narrows the wheel tooth to zero width")

    w_amid = math.asin(half_w / rw)        # half tooth angle at the pitch circle
    root_radius = rw - (inp.module_mm * 1.25 * inp.dedendum_factor)
    steps = max(8, inp.resolution)

    # Addendum upper half: angle aa runs 0 (at the edge / pitch circle) -> w_amid
    # (at the apex). radius_at_angle measures angle from the edge; the absolute
    # angle from the centerline is (w_amid - aa).
    upper: List[Point] = []
    for n in range(steps + 1):
        aa = w_amid * n / steps
        r = radius_at_angle(aa, inp.pinion_teeth, inp.wheel_teeth) * rw
        ang = w_amid - aa
        upper.append((math.cos(ang) * r, math.sin(ang) * r))

    apex = (upper[-1][0], 0.0)                 # apex forced onto the centerline
    edge = upper[0]                            # at the pitch circle, angle +w_amid
    # Straight constant-width flank: foot at the root radius, offset +half_w.
    foot = (math.sqrt(max(root_radius ** 2 - half_w ** 2, 0.0)), half_w)

    # upper tip ordered apex -> edge (so spline goes apex outward to the pitch end)
    upper_tip = [apex] + list(reversed(upper))   # apex .. edge
    lower_tip = [(x, -y) for (x, y) in upper_tip]
    upper_foot = foot
    lower_foot = (foot[0], -foot[1])

    # Connected counter-clockwise path:
    #   lower flank (foot->edge) -> lower tip (edge->apex) -> upper tip (apex->edge)
    #   -> upper flank (edge->foot)
    segs: List[Segment] = []
    segs.append(Segment('line', [lower_foot, lower_tip[-1]]))          # lower flank
    segs.append(Segment('spline', list(reversed(lower_tip))))         # edge -> apex (lower)
    segs.append(Segment('spline', upper_tip))                         # apex -> edge (upper)
    segs.append(Segment('line', [upper_tip[-1], upper_foot]))         # upper flank
    return segs


def _build_wheel_tooth_envelope(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """Conjugate-envelope wheel tooth (the preserved Peterson approach), assembled
    the way the old build_wheel_tooth did. Known-imperfect; kept runnable so we
    can return to it later via method='envelope'.
    """
    tip = wheel_tip_envelope(inp, geo)               # pitch-end -> apex, upper (+y) side
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


def build_wheel_tooth(inp: GearInputs, geo: DerivedGeometry,
                      method: str = 'cycloidal') -> List[Segment]:
    """One wheel tooth centered on the +x axis, as a connected counter-clockwise
    list of Segments: lower flank (line) -> tip (2 splines meeting at the apex) ->
    upper flank (line). Clearance narrows the wheel tooth.

    method='cycloidal' (default): epicycloidal addendum via radius_at_angle, the
        validated/meshing geometry ported from the prototype.
    method='envelope': the preserved Peterson conjugate-envelope approach
        (known-imperfect, kept runnable for future work).
    """
    if method == 'cycloidal':
        return _build_wheel_tooth_cycloidal(inp, geo)
    if method == 'envelope':
        return _build_wheel_tooth_envelope(inp, geo)
    raise ValueError(f"unknown wheel-tip method: {method!r}")


def build_pinion_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One pinion tooth centered on the +x axis: two parallel straight flanks a
    feature-width apart, capped by a semicircular tip, with root feet. Returned
    as a connected counter-clockwise path. The tip is free (never contacts the
    wheel); only the flanks are working surfaces.
    """
    half_w = inp.feature_width_mm / 2.0
    root_radius = geo.pitch_radius_pinion - (inp.module_mm * 1.25 * inp.dedendum_factor)
    # The pinion's WORKING flank is the part below the pitch circle (it is driven by
    # the wheel tip). Above the pitch circle the tooth is a free rounded cap. Per
    # Peterson's diagrams, the semicircular tip is centred ON the pitch circle, so
    # the straight flanks run from the root up to the pitch radius and the cap
    # (radius half_w) sits on top, reaching pitch_radius + half_w.
    flank_top_x = geo.pitch_radius_pinion

    lower_root = (root_radius, -half_w)
    lower_flank_top = (flank_top_x, -half_w)
    upper_flank_top = (flank_top_x, half_w)
    upper_root = (root_radius, half_w)
    tip_mid = (flank_top_x + half_w, 0.0)            # outermost point of the cap

    segs: List[Segment] = []
    segs.append(Segment('line', [lower_root, lower_flank_top]))             # lower flank
    segs.append(Segment('arc3', [lower_flank_top, tip_mid, upper_flank_top]))  # rounded tip
    segs.append(Segment('line', [upper_flank_top, upper_root]))             # upper flank
    return segs


@dataclass
class GearProfile:
    role: str                       # 'wheel' | 'pinion'
    teeth: int
    center: Point                   # placement in the component frame (mm)
    pitch_radius: float
    root_radius: float
    addendum_radius: float
    segments: List[Segment]         # all teeth, gear-local coords (centered at origin), mm


@dataclass
class GearPair:
    wheel: GearProfile
    pinion: GearProfile
    center_distance: float
    circular_pitch: float


def array_tooth(tooth: List[Segment], teeth: int, base_angle: float) -> List[Segment]:
    """Replicate one tooth `teeth` times around the origin, each rotated by the
    tooth pitch, starting from `base_angle`."""
    pitch = 2.0 * math.pi / teeth
    out: List[Segment] = []
    for k in range(teeth):
        ang = base_angle + k * pitch
        for seg in tooth:
            out.append(Segment(seg.kind,
                               [rotate_point(p, (0.0, 0.0), ang) for p in seg.points]))
    return out


def close_gear_loop(tooth: List[Segment], teeth: int, base_angle: float) -> List[Segment]:
    """Array one tooth `teeth` times and bridge the gaps between adjacent teeth
    with arcs along the root circle, producing a single closed outline. Each
    tooth path runs root -> flank -> tip -> flank -> root; the bridge arc joins
    one tooth's last point to the next tooth's first point. The arc is placed at
    the radius of those root points, so it follows the root circle."""
    spt = len(tooth)
    arrayed = array_tooth(tooth, teeth, base_angle)
    out: List[Segment] = []
    for k in range(teeth):
        this_tooth = arrayed[k * spt:(k + 1) * spt]
        out.extend(this_tooth)
        end_pt = this_tooth[-1].points[-1]
        start_next = arrayed[((k + 1) % teeth) * spt].points[0]
        a0 = math.atan2(end_pt[1], end_pt[0])
        a1 = math.atan2(start_next[1], start_next[0])
        while a1 <= a0:
            a1 += 2.0 * math.pi
        mid = (a0 + a1) / 2.0
        rho = math.hypot(end_pt[0], end_pt[1])
        out.append(Segment('arc3', [end_pt, _polar(rho, mid), start_next]))
    return out


def _radii(segments: List[Segment]) -> Tuple[float, float]:
    rr = [math.hypot(x, y) for s in segments for (x, y) in s.points]
    return (min(rr), max(rr))


def build_gear_pair(inp: GearInputs) -> GearPair:
    validate_inputs(inp)
    geo = derive_geometry(inp)

    wheel_tooth = build_wheel_tooth(inp, geo)
    pinion_tooth = build_pinion_tooth(inp, geo)

    wheel_segs = close_gear_loop(wheel_tooth, inp.wheel_teeth, base_angle=0.0)
    # Pinion tooth points toward the wheel (-x from the pinion centre) to mesh.
    # Offset by half a pinion pitch so a pinion tooth-GAP faces each wheel tooth
    # (the wheel tooth must enter the pinion gap, not collide with a pinion tooth).
    pinion_half_pitch = math.pi / inp.pinion_teeth
    pinion_segs = close_gear_loop(pinion_tooth, inp.pinion_teeth,
                                  base_angle=math.pi + pinion_half_pitch)

    w_root, w_add = _radii(wheel_segs)
    p_root, p_add = _radii(pinion_segs)

    wheel = GearProfile('wheel', inp.wheel_teeth, (0.0, 0.0),
                        geo.pitch_radius_wheel, w_root, w_add, wheel_segs)
    pinion = GearProfile('pinion', inp.pinion_teeth, (geo.center_distance, 0.0),
                         geo.pitch_radius_pinion, p_root, p_add, pinion_segs)
    return GearPair(wheel, pinion, geo.center_distance, geo.circular_pitch)
