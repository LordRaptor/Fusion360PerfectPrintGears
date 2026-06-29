# tests/test_interference.py
"""Conjugacy / interference guard -- the test that was missing before (sanity
checks alone let a non-conjugate curve ship). Assemble both gears as CLOSED
polygons, roll them under the SAME kinematic model used to generate the tip
(driven +tau, driving -tau/ratio), and assert penetration DEPTH stays tiny.

Hygiene (each item caused a false result historically): closed polygons with
root bridges; build local then a single placement transform; penetration depth
(point-in-poly + distance-to-boundary), not nearest distance; arcs through the
mid point; ONE kinematic model; and a GEOMETRY-DERIVED mesh zone (a hard-coded
zone silently gave a false 0 when diameters changed).
"""
import math
import pytest
from core import gear_math as gm


def _place(poly, spin, cx, cy):
    s, c = math.sin(spin), math.cos(spin)
    return [(c * x - s * y + cx, s * x + c * y + cy) for (x, y) in poly]


def _point_in_poly(px, py, poly):
    ins = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and \
                (px < (xj - xi) * (py - yi) / (yj - yi + 1e-30) + xi):
            ins = not ins
        j = i
    return ins


def _dist_to_poly(px, py, poly):
    best = 1e18
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def _max_penetration(inp):
    geo = gm.derive_geometry(inp)
    rw, rp = geo.pitch_radius_driving, geo.pitch_radius_driven
    C, ratio, m = geo.center_distance, geo.ratio, inp.module_mm
    base = math.pi + math.pi / inp.driven_teeth

    driving_local = gm.closed_gear_polygon(gm.build_driving_tooth(inp, geo),
                                           inp.driving_teeth, 0.0, n_spline=18, n_arc=8)
    driven_local = gm.closed_gear_polygon(gm.build_driven_tooth(inp, geo),
                                          inp.driven_teeth, base, n_spline=18, n_arc=8)

    # mesh zone derived from geometry (centered on the pitch point), NOT hard-coded
    zx0, zx1, zy = rw - 4 * m, rw + 4 * m, 4 * m

    def in_zone(p):
        return zx0 < p[0] < zx1 and -zy < p[1] < zy

    def penetration(tau):
        w = _place(driving_local, -tau / ratio, 0.0, 0.0)
        p = _place(driven_local, tau, C, 0.0)
        depth = 0.0
        for q in w:
            if in_zone(q) and _point_in_poly(q[0], q[1], p):
                depth = max(depth, _dist_to_poly(q[0], q[1], p))
        for q in p:
            if in_zone(q) and _point_in_poly(q[0], q[1], w):
                depth = max(depth, _dist_to_poly(q[0], q[1], w))
        return depth

    tp = 2.0 * math.pi / inp.driven_teeth
    n = 41
    return max(penetration(-tp + 2.0 * tp * i / (n - 1)) for i in range(n))


@pytest.mark.parametrize("nw,np_", [
    (50, 10), (36, 12), (56, 8),     # step-ups (driving > driven)
    (20, 20),                        # 1:1
    (10, 40), (12, 36), (6, 24),     # reductions (driving < driven)
])
def test_no_interference_with_backlash(nw, np_):
    # Realistic tooth fraction (< 0.5) gives circumferential backlash; the driving
    # flanks never overlap -> ~0 penetration across the whole mesh cycle.
    inp = gm.GearInputs(driving_teeth=nw, driven_teeth=np_, module_mm=1.5,
                        tooth_fraction=0.4, clearance_mm=0.1, resolution=8)
    depth_um = _max_penetration(inp) * 1000.0
    assert depth_um < 60.0, f"penetration {depth_um:.1f} um too high (ratio {nw}/{np_})"


def test_zone_actually_captures_contact():
    # Guard against a false zero: at the snug fraction (0.5) the driving flanks
    # touch, so the mesh zone MUST report a (small, spline-noise) nonzero depth.
    # If this is ~0 too, the zone is missing the contact (the old false-0 bug).
    inp = gm.GearInputs(driving_teeth=50, driven_teeth=10, module_mm=1.5,
                        tooth_fraction=0.5, clearance_mm=0.1, resolution=8)
    depth_um = _max_penetration(inp) * 1000.0
    assert depth_um > 1.0, "mesh zone captured no contact (false-zero) -- check the zone"


def test_zone_captures_contact_reduction():
    # Same false-zero guard as above, but for a reduction (driving < driven): at the
    # snug fraction the driving flanks touch, so the zone MUST report nonzero depth.
    inp = gm.GearInputs(driving_teeth=10, driven_teeth=40, module_mm=1.5,
                        tooth_fraction=0.5, clearance_mm=0.1, resolution=8)
    depth_um = _max_penetration(inp) * 1000.0
    assert depth_um > 1.0, "mesh zone captured no contact for a reduction (false-zero)"


def _round_driven_tooth(inp, geo):
    """The OLD semicircular driven tip, rebuilt locally as the regression baseline."""
    rp, hw = geo.pitch_radius_driven, geo.half_w
    flank_top_x = math.sqrt(rp ** 2 - hw ** 2)
    cap_apex_x = flank_top_x + hw
    driving_apex_x = gm.driving_tip_points(inp, geo)[-1][0]
    root_radius = rp - ((driving_apex_x - geo.pitch_radius_driving) + inp.clearance_mm) * inp.dedendum_factor
    foot_x = math.sqrt(root_radius ** 2 - hw ** 2)
    return [
        gm.Segment('line', [(foot_x, -hw), (flank_top_x, -hw)]),
        gm.Segment('arc3', [(flank_top_x, -hw), (cap_apex_x, 0.0), (flank_top_x, hw)]),
        gm.Segment('line', [(flank_top_x, hw), (foot_x, hw)]),
    ]


def _max_penetration_with(inp, driven_builder):
    """Copy of _max_penetration but with a swappable driven-tooth builder."""
    geo = gm.derive_geometry(inp)
    rw, rp = geo.pitch_radius_driving, geo.pitch_radius_driven
    C, ratio, m = geo.center_distance, geo.ratio, inp.module_mm
    base = math.pi + math.pi / inp.driven_teeth
    driving_local = gm.closed_gear_polygon(gm.build_driving_tooth(inp, geo),
                                           inp.driving_teeth, 0.0, n_spline=18, n_arc=8)
    driven_local = gm.closed_gear_polygon(driven_builder(inp, geo),
                                          inp.driven_teeth, base, n_spline=18, n_arc=8)
    zx0, zx1, zy = rw - 4 * m, rw + 4 * m, 4 * m

    def in_zone(p):
        return zx0 < p[0] < zx1 and -zy < p[1] < zy

    def penetration(tau):
        w = _place(driving_local, -tau / ratio, 0.0, 0.0)
        p = _place(driven_local, tau, C, 0.0)
        depth = 0.0
        for q in w:
            if in_zone(q) and _point_in_poly(q[0], q[1], p):
                depth = max(depth, _dist_to_poly(q[0], q[1], p))
        for q in p:
            if in_zone(q) and _point_in_poly(q[0], q[1], w):
                depth = max(depth, _dist_to_poly(q[0], q[1], w))
        return depth

    tp = 2.0 * math.pi / inp.driven_teeth
    n = 41
    return max(penetration(-tp + 2.0 * tp * i / (n - 1)) for i in range(n))


@pytest.mark.parametrize("nw,np_", [(10, 40), (6, 24)])
def test_oval_tip_beats_round_tip_at_snug_fit(nw, np_, monkeypatch):
    # At the snug fraction (0.5) the round tip's corners interfere; the oval must do
    # strictly better for these small-driven ratios where the tip dominates contact.
    # Baseline = the self-consistent HISTORICAL round design: round driven tip AND a
    # driving root sized for it (restore the old _driven_cap_apex_x for the baseline,
    # else the tall round tip meshes against the new shallow oval-sized driving root
    # and the comparison is an artifact).
    inp = gm.GearInputs(driving_teeth=nw, driven_teeth=np_, module_mm=1.5,
                        tooth_fraction=0.5, clearance_mm=0.1, resolution=8)
    oval = _max_penetration_with(inp, gm.build_driven_tooth) * 1000.0
    monkeypatch.setattr(
        gm, "_driven_cap_apex_x",
        lambda geo: math.sqrt(geo.pitch_radius_driven ** 2 - geo.half_w ** 2) + geo.half_w,
    )
    round_ = _max_penetration_with(inp, _round_driven_tooth) * 1000.0
    assert oval < round_ - 5.0, f"oval {oval:.1f} not clearly better than round {round_:.1f} um"
