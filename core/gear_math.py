# core/gear_math.py
"""Pure-Python Perfect Print gear geometry engine. No Fusion (adsk) imports and
no third-party deps (no numpy) -- Fusion's bundled Python may not have them.

All lengths are in millimeters. The caller (Fusion layer) converts mm -> cm.
Coordinate frame: wheel center at origin (0,0); pinion center at (center_distance, 0).

Conjugation method (validated; see docs/superpowers/specs §4.3 and tmp/peterson_*.py):
one kinematic model drives both generation and verification -- pinion rotates +tau
about O_p, wheel rotates -tau/ratio about O_w. The wheel tip is the locus of the
foot of the perpendicular from the pitch point onto the straight pinion flank
(exact for a straight flank), trimmed flank->apex and mirrored, represented as a
control-point (Bezier) spline fitted to the envelope (see fit_tip_bezier).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

Point = Tuple[float, float]


# ============================================================ data + geometry
@dataclass
class GearInputs:
    wheel_teeth: int
    pinion_teeth: int
    module_mm: float
    tooth_fraction: float = 0.5          # tooth width as a fraction of circular pitch
    clearance_mm: float = 0.1            # radial tip-to-root play
    dedendum_factor: float = 1.0         # scales root depth
    resolution: int = 4                  # tip control points: <=4 -> degree 3, else degree 5
    tangent_join: bool = False           # tip leaves the flank join tangent (smoother, worse fit)


@dataclass
class DerivedGeometry:
    pitch_radius_wheel: float
    pitch_radius_pinion: float
    center_distance: float
    ratio: float
    circular_pitch: float
    feature_width_mm: float              # derived = tooth_fraction * circular_pitch
    half_w: float


def derive_geometry(inp: GearInputs) -> DerivedGeometry:
    rw = inp.module_mm * inp.wheel_teeth / 2.0
    rp = inp.module_mm * inp.pinion_teeth / 2.0
    cp = math.pi * inp.module_mm
    fw = tooth_width_from_module(inp.module_mm, inp.tooth_fraction)
    return DerivedGeometry(
        pitch_radius_wheel=rw,
        pitch_radius_pinion=rp,
        center_distance=rw + rp,
        ratio=inp.wheel_teeth / inp.pinion_teeth,
        circular_pitch=cp,
        feature_width_mm=fw,
        half_w=fw / 2.0,
    )


def tooth_width_from_module(module_mm: float, tooth_fraction: float) -> float:
    """Tooth width (mm) implied by a module and tooth fraction: tf * pi * module."""
    return tooth_fraction * math.pi * module_mm


def module_from_tooth_width(width_mm: float, tooth_fraction: float) -> float:
    """Module (mm) that yields a given tooth width at a fixed tooth fraction.
    The inverse of tooth_width_from_module; raises on a non-positive fraction
    (guards a divide-by-zero from an in-progress dialog edit)."""
    if tooth_fraction <= 0:
        raise ValueError("tooth_fraction must be greater than 0")
    return width_mm / (tooth_fraction * math.pi)


MIN_PINION_TEETH = 6


def validate_inputs(inp: GearInputs) -> None:
    """Raise ValueError with a human-readable message if inputs are unusable."""
    if inp.pinion_teeth < MIN_PINION_TEETH:
        raise ValueError(f"pinion teeth must be at least {MIN_PINION_TEETH}")
    if inp.wheel_teeth < inp.pinion_teeth:
        raise ValueError("wheel teeth must be >= pinion teeth")
    if inp.module_mm <= 0:
        raise ValueError("module must be greater than 0")
    # Feature width is DERIVED from the tooth fraction, so the old "teeth overlap"
    # case is structurally impossible; instead bound the fraction. At 0.5 the teeth
    # exactly fill the pitch (clearance provides the gap); above 0.5 there is no gap.
    if not (0.0 < inp.tooth_fraction <= 0.5):
        raise ValueError("tooth fraction must be between 0 and 0.5")
    geo = derive_geometry(inp)
    if inp.clearance_mm < 0:
        raise ValueError("clearance must be >= 0")
    if inp.clearance_mm >= geo.feature_width_mm:
        raise ValueError("clearance must be less than the feature width")
    if geo.half_w >= geo.pitch_radius_pinion:
        raise ValueError("feature width is too large for the pinion size")


def format_ratio(wheel_teeth: int, pinion_teeth: int) -> str:
    """Human-readable reduction ratio: decimal to 2 dp plus the GCD-reduced
    integer pair, e.g. format_ratio(50, 15) == "3.33 : 1 (10 : 3)"."""
    decimal = wheel_teeth / pinion_teeth
    g = math.gcd(int(wheel_teeth), int(pinion_teeth))
    rw, rp = int(wheel_teeth) // g, int(pinion_teeth) // g
    return f"{decimal:.2f} : 1 ({rw} : {rp})"


# ===================================================================== 2D math
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


def foot_of_perpendicular(pt: Point, a: Point, b: Point) -> Point:
    """Foot of the perpendicular from pt onto the line through a, b."""
    abx, aby = b[0] - a[0], b[1] - a[1]
    t = ((pt[0] - a[0]) * abx + (pt[1] - a[1]) * aby) / (abx * abx + aby * aby)
    return (a[0] + t * abx, a[1] + t * aby)


def _norm_angle(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _polar(r: float, ang: float) -> Point:
    return (r * math.cos(ang), r * math.sin(ang))


# ============================================================= bezier (tip)
# A control-point (Bezier) spline represents the wheel tip in the sketch: unlike a
# fitted spline it has no per-point tangent handles, so constraining every control
# point fully constrains it -- which lets the tip rotate with the centerline frame.
# Fusion only accepts degree 3 (4 control points) or 5 (6); a single Bezier of
# either degree has a forced knot vector, so engine control points reproduce
# exactly in Fusion. Pure Python (no numpy): Fusion does not bundle it.
def _binom(n: int, k: int) -> float:
    c = 1.0
    for i in range(k):
        c = c * (n - i) / (i + 1)
    return c


def _bernstein(degree: int, i: int, t: float) -> float:
    return _binom(degree, i) * (t ** i) * ((1.0 - t) ** (degree - i))


def _bezier_point(ctrl: List[Point], t: float) -> Point:
    d = len(ctrl) - 1
    x = y = 0.0
    for i, (px, py) in enumerate(ctrl):
        b = _bernstein(d, i, t)
        x += b * px
        y += b * py
    return (x, y)


def bezier_curve(ctrl: List[Point], n: int = 24) -> List[Point]:
    """Sample a Bezier defined by `ctrl` into n+1 points over t in [0, 1]."""
    return [_bezier_point(ctrl, k / n) for k in range(n + 1)]


def _solve_linear(A: List[List[float]], b: List[float]) -> List[float]:
    """Solve A x = b for a small square system (Gaussian elimination, partial
    pivot). Pure Python -- the tip fit is at most 4x4."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r != col and M[r][col] != 0.0:
                f = M[r][col] / pv
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def _chord_params(pts: List[Point]) -> List[float]:
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.hypot(pts[i][0] - pts[i - 1][0],
                                    pts[i][1] - pts[i - 1][1]))
    total = d[-1] or 1.0
    return [x / total for x in d]


def _fit_bezier_coord(locus: List[Point], t: List[float], coord: int, degree: int,
                      p0c: float, pdc: float, fixed_interior: dict) -> List[float]:
    """Least-squares-fit the interior control-point values (indices 1..degree-1)
    for one coordinate, with the endpoints (0, degree) and any `fixed_interior`
    indices held fixed. Returns values for all interior indices 1..degree-1."""
    free = [i for i in range(1, degree) if i not in fixed_interior]
    rows = []
    rhs = []
    # Build basis (M) and residual (target minus fixed contributions) per sample.
    basis = []
    res = []
    for tk, q in zip(t, locus):
        fixed_sum = (_bernstein(degree, 0, tk) * p0c
                     + _bernstein(degree, degree, tk) * pdc)
        for i, v in fixed_interior.items():
            fixed_sum += _bernstein(degree, i, tk) * v
        basis.append([_bernstein(degree, i, tk) for i in free])
        res.append(q[coord] - fixed_sum)
    # Normal equations (M^T M) x = M^T res.
    m = len(free)
    A = [[0.0] * m for _ in range(m)]
    b = [0.0] * m
    for k in range(len(t)):
        bk = basis[k]
        rk = res[k]
        for a in range(m):
            b[a] += bk[a] * rk
            for c in range(m):
                A[a][c] += bk[a] * bk[c]
    sol = _solve_linear(A, b) if m else []
    result = dict(fixed_interior)
    for j, i in enumerate(free):
        result[i] = sol[j]
    return [result[i] for i in range(1, degree)]


def fit_tip_bezier(locus: List[Point], degree: int = 3,
                   tangent_join: bool = False) -> List[Point]:
    """Least-squares-fit a single clamped Bezier of `degree` (3 or 5) to the dense
    conjugate tip `locus`. Endpoints are clamped to locus[0] (flank join) and
    locus[-1] (apex); interior control points are free. With `tangent_join`, the
    first interior control point shares the join's y so the curve leaves the join
    horizontally (tangent to the flank) -- smoother but a worse envelope fit.
    Returns degree+1 control points."""
    if degree not in (3, 5):
        raise ValueError("tip Bezier degree must be 3 or 5 (Fusion limitation)")
    P0, Pd = locus[0], locus[-1]
    t = _chord_params(locus)
    xs = _fit_bezier_coord(locus, t, 0, degree, P0[0], Pd[0], {})
    fixed_y = {1: P0[1]} if tangent_join else {}
    ys = _fit_bezier_coord(locus, t, 1, degree, P0[1], Pd[1], fixed_y)
    return [P0] + [(xs[i], ys[i]) for i in range(degree - 1)] + [Pd]


# ============================================ wheel-tip conjugate envelope
def _arc3_curve(p1: Point, p2: Point, p3: Point, n: int = 24) -> List[Point]:
    """Sample the circular arc through 3 points, passing THROUGH the mid point p2."""
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    d = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return [p1, p2, p3]
    cx = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1)
          + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    cy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3)
          + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    r = math.hypot(x1 - cx, y1 - cy)
    a1 = math.atan2(y1 - cy, x1 - cx)
    a2 = math.atan2(y2 - cy, x2 - cx)
    a3 = math.atan2(y3 - cy, x3 - cx)
    TAU = 2.0 * math.pi
    a2n = a1 + ((a2 - a1) % TAU)
    a3n = a1 + ((a3 - a1) % TAU)
    end = a3n if a2n <= a3n else a3n - TAU
    return [(cx + r * math.cos(a1 + (end - a1) * i / n),
             cy + r * math.sin(a1 + (end - a1) * i / n)) for i in range(n + 1)]


def _contacting_flank(geo: DerivedGeometry) -> Tuple[Point, Point]:
    """Two points on the contacting pinion flank (top flank) at the reference
    instant, in world coords. The pinion tooth is placed by alpha = 2*asin(half_w/Rp)
    so its top flank meets the wheel bottom flank at Q on the pinion pitch circle."""
    C = geo.center_distance
    Rp = geo.pitch_radius_pinion
    hw = geo.half_w
    Op = (C, 0.0)
    xq = C - math.sqrt(Rp ** 2 - hw ** 2)
    Q = (xq, -hw)
    S = (xq, hw)
    alpha = _norm_angle(math.atan2(Q[1], Q[0] - C) - math.atan2(S[1], S[0] - C))
    p_pitch = rotate_point((xq, hw), Op, alpha)        # == Q
    p_in = rotate_point((xq - 1.0, hw), Op, alpha)     # a second point on the line
    return (p_pitch, p_in)


def flank_in_wheel_frame(geo: DerivedGeometry, base: Tuple[Point, Point],
                         tau: float) -> Tuple[Point, Point]:
    """The contacting pinion flank at mesh parameter tau, expressed in the wheel
    frame: rotate +tau about O_p, then +tau/ratio about O_w."""
    Op = (geo.center_distance, 0.0)
    Ow = (0.0, 0.0)
    tw = tau / geo.ratio
    p0 = rotate_point(rotate_point(base[0], Op, tau), Ow, tw)
    p1 = rotate_point(rotate_point(base[1], Op, tau), Ow, tw)
    return (p0, p1)


def wheel_contact_point(geo: DerivedGeometry, base: Tuple[Point, Point],
                        tau: float) -> Point:
    """Wheel-tip point at parameter tau = foot of perpendicular from the pitch
    point onto the (world) flank, carried into the wheel frame."""
    Op = (geo.center_distance, 0.0)
    Ow = (0.0, 0.0)
    P = (geo.pitch_radius_wheel, 0.0)
    l0 = rotate_point(base[0], Op, tau)
    l1 = rotate_point(base[1], Op, tau)
    foot = foot_of_perpendicular(P, l0, l1)
    return rotate_point(foot, Ow, tau / geo.ratio)


def wheel_tip_points(inp: GearInputs, geo: DerivedGeometry,
                     samples: int = 240) -> List[Point]:
    """Dense wheel-tip locus, ordered from the flank join (y = -half_w) up to the
    centerline apex (y = 0), on the -y (lower) side, in wheel coords. This is the
    exact conjugate locus (foot-of-perpendicular envelope) before splining."""
    base = _contacting_flank(geo)
    hw = geo.half_w
    tooth_pitch = 2.0 * math.pi / inp.pinion_teeth
    # scan a WIDE tau range (the crossing tau shifts with ratio)
    N = 4000
    lo, hi = -1.5 * tooth_pitch, 1.5 * tooth_pitch
    prev_t = lo
    prev_y = wheel_contact_point(geo, base, lo)[1]

    def find_cross(target):
        pt, py = lo, wheel_contact_point(geo, base, lo)[1]
        for i in range(1, N + 1):
            tt = lo + (hi - lo) * i / N
            yy = wheel_contact_point(geo, base, tt)[1]
            if (py - target) * (yy - target) <= 0 and py != yy:
                f = (target - py) / (yy - py)
                return pt + f * (tt - pt)
            pt, py = tt, yy
        return None

    tau_join = find_cross(-hw)
    tau_apex = find_cross(0.0)
    if tau_join is None or tau_apex is None:
        raise ValueError("could not locate wheel-tip join/apex (check inputs)")
    pts = []
    for i in range(samples):
        tau = tau_join + (tau_apex - tau_join) * i / (samples - 1)
        pts.append(wheel_contact_point(geo, base, tau))
    pts[-1] = (pts[-1][0], 0.0)            # snap apex onto the centerline
    return pts


# ===================================================================== segments
@dataclass
class Segment:
    kind: str                            # 'line' | 'arc3' | 'cpspline'
    points: List[Point]                  # for 'cpspline': the Bezier control points
    degree: int = 0                      # for 'cpspline': Bezier degree (3 or 5)


def _pinion_cap_apex_x(geo: DerivedGeometry) -> float:
    return math.sqrt(geo.pitch_radius_pinion ** 2 - geo.half_w ** 2) + geo.half_w


def build_wheel_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One wheel tooth centered on the +x axis, as a connected counter-clockwise
    list of Segments: lower flank (line) -> lower tip (cpspline) -> upper tip
    (cpspline) -> upper flank (line). The tip is the conjugate envelope fitted as a
    single clamped Bezier per half (a control-point spline -- no tangent-handle DOF,
    so it can be fully constrained and rotated in the sketch). `resolution` selects
    the degree (<=4 -> 3, else 5); `tangent_join` makes the tip leave the flank join
    horizontally. The apex is a sharp point (printer smooths it)."""
    rw = geo.pitch_radius_wheel
    hw = geo.half_w

    locus = wheel_tip_points(inp, geo)               # join(y=-hw) -> apex(y=0)
    # snap the endpoints exactly onto the flank level and the centerline (the
    # tau-crossing scan lands within ~1e-7 of them)
    locus[0] = (locus[0][0], -hw)
    apex = (locus[-1][0], 0.0)
    locus[-1] = apex
    join_x = locus[0][0]
    apex_x = apex[0]

    degree = 3 if inp.resolution <= 4 else 5
    lower = fit_tip_bezier(locus, degree, inp.tangent_join)   # control points
    upper = [(x, -y) for (x, y) in reversed(lower)]  # apex -> join(y=+hw)
    wheel_tip_h = apex_x - rw
    # root clears the MATING tooth's tip (pinion cap) + clearance
    pinion_tip_h = _pinion_cap_apex_x(geo) - geo.pitch_radius_pinion
    root_radius = rw - (pinion_tip_h + inp.clearance_mm) * inp.dedendum_factor
    if root_radius <= hw:
        raise ValueError("computed wheel root radius is too small; teeth too large")
    foot_x = math.sqrt(root_radius ** 2 - hw ** 2)

    segs: List[Segment] = []
    segs.append(Segment('line', [(foot_x, -hw), (join_x, -hw)]))
    segs.append(Segment('cpspline', lower, degree=degree))    # join -> apex
    segs.append(Segment('cpspline', upper, degree=degree))    # apex -> join
    segs.append(Segment('line', [(join_x, hw), (foot_x, hw)]))
    return segs


def build_pinion_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One pinion tooth centered on the +x axis: two parallel straight flanks a
    feature-width apart ending ON the pinion pitch circle, capped by a semicircular
    tip (radius half_w, centered just inside the pitch circle). The tip is free
    (never contacts the wheel); only the flanks are working surfaces."""
    rp = geo.pitch_radius_pinion
    hw = geo.half_w
    flank_top_x = math.sqrt(rp ** 2 - hw ** 2)       # flank ends on the pitch circle
    cap_apex_x = flank_top_x + hw

    # root clears the MATING tooth's tip (wheel apex) + clearance
    wheel_apex_x = wheel_tip_points(inp, geo)[-1][0]
    wheel_tip_h = wheel_apex_x - geo.pitch_radius_wheel
    root_radius = rp - (wheel_tip_h + inp.clearance_mm) * inp.dedendum_factor
    if root_radius <= hw:
        raise ValueError("computed pinion root radius is too small; teeth too large")
    foot_x = math.sqrt(root_radius ** 2 - hw ** 2)

    segs: List[Segment] = []
    segs.append(Segment('line', [(foot_x, -hw), (flank_top_x, -hw)]))
    segs.append(Segment('arc3', [(flank_top_x, -hw), (cap_apex_x, 0.0), (flank_top_x, hw)]))
    segs.append(Segment('line', [(flank_top_x, hw), (foot_x, hw)]))
    return segs


# ====================================================== arraying + assembly
def array_tooth(tooth: List[Segment], teeth: int, base_angle: float) -> List[Segment]:
    """Replicate one tooth `teeth` times around the origin, each rotated by the
    tooth pitch, starting from `base_angle`."""
    pitch = 2.0 * math.pi / teeth
    out: List[Segment] = []
    for k in range(teeth):
        ang = base_angle + k * pitch
        for seg in tooth:
            out.append(Segment(seg.kind,
                               [rotate_point(p, (0.0, 0.0), ang) for p in seg.points],
                               seg.degree))
    return out


def close_gear_loop(tooth: List[Segment], teeth: int, base_angle: float) -> List[Segment]:
    """Array one tooth `teeth` times and bridge adjacent teeth with arcs along the
    root circle, producing a single closed outline."""
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


@dataclass
class GearProfile:
    role: str
    teeth: int
    center: Point
    pitch_radius: float
    root_radius: float
    addendum_radius: float
    segments: List[Segment]                 # all teeth, closed loop (gear-local)
    tooth_segments: Optional[List[Segment]] = None   # ONE tooth (gear-local, +x)
    base_angle: float = 0.0                  # orientation of tooth 0 for patterning


@dataclass
class GearPair:
    wheel: GearProfile
    pinion: GearProfile
    center_distance: float
    circular_pitch: float


def _radii(segments: List[Segment]) -> Tuple[float, float]:
    rr = [math.hypot(x, y) for s in segments for (x, y) in s.points]
    return (min(rr), max(rr))


def build_gear_pair(inp: GearInputs) -> GearPair:
    validate_inputs(inp)
    geo = derive_geometry(inp)

    wheel_tooth = build_wheel_tooth(inp, geo)
    pinion_tooth = build_pinion_tooth(inp, geo)

    wheel_segs = close_gear_loop(wheel_tooth, inp.wheel_teeth, base_angle=0.0)
    # Pinion tooth points toward the wheel (-x), offset half a pitch so a pinion
    # tooth-GAP faces each wheel tooth.
    pinion_half_pitch = math.pi / inp.pinion_teeth
    pinion_segs = close_gear_loop(pinion_tooth, inp.pinion_teeth,
                                  base_angle=math.pi + pinion_half_pitch)

    w_root, w_add = _radii(wheel_segs)
    p_root, p_add = _radii(pinion_segs)

    wheel = GearProfile('wheel', inp.wheel_teeth, (0.0, 0.0),
                        geo.pitch_radius_wheel, w_root, w_add, wheel_segs,
                        tooth_segments=wheel_tooth, base_angle=0.0)
    pinion = GearProfile('pinion', inp.pinion_teeth, (geo.center_distance, 0.0),
                         geo.pitch_radius_pinion, p_root, p_add, pinion_segs,
                         tooth_segments=pinion_tooth,
                         base_angle=math.pi + pinion_half_pitch)
    return GearPair(wheel, pinion, geo.center_distance, geo.circular_pitch)


# ============================================ densify (for interference/testing)
def densify_segments(segments: List[Segment], n_spline: int = 24,
                     n_arc: int = 24) -> List[Point]:
    """Flatten a connected segment list to a dense polyline (local frame). Control-
    point splines are evaluated as Beziers; arcs are sampled through the mid point."""
    out: List[Point] = []
    for s in segments:
        if s.kind == 'line':
            pts = list(s.points)
        elif s.kind == 'arc3':
            pts = _arc3_curve(s.points[0], s.points[1], s.points[2], n_arc)
        elif s.kind == 'cpspline':
            pts = bezier_curve(s.points, n_spline)
        else:
            pts = list(s.points)
        if out and pts and abs(out[-1][0] - pts[0][0]) < 1e-9 and abs(out[-1][1] - pts[0][1]) < 1e-9:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return out


def closed_gear_polygon(tooth: List[Segment], teeth: int, base_angle: float,
                        n_spline: int = 24, n_arc: int = 12) -> List[Point]:
    """Closed dense polygon of a full gear: densify one local tooth, array it, and
    bridge the gaps with root-circle arcs. Densifying BEFORE arraying keeps the
    spline tangent clamp in its local (horizontal) frame."""
    local = densify_segments(tooth, n_spline, n_arc)
    root_r = min(math.hypot(x, y) for (x, y) in local)
    poly: List[Point] = []
    pitch = 2.0 * math.pi / teeth
    for k in range(teeth):
        ang = base_angle + k * pitch
        this = [rotate_point(p, (0.0, 0.0), ang) for p in local]
        poly.extend(this)
        # bridge to next tooth start along the root circle
        end_pt = this[-1]
        ang_next = base_angle + ((k + 1) % teeth) * pitch
        start_next = rotate_point(local[0], (0.0, 0.0), ang_next)
        a0 = math.atan2(end_pt[1], end_pt[0])
        a1 = math.atan2(start_next[1], start_next[0])
        while a1 <= a0:
            a1 += 2.0 * math.pi
        for j in range(1, n_arc):
            aa = a0 + (a1 - a0) * j / n_arc
            poly.append(_polar(root_r, aa))
    return poly
