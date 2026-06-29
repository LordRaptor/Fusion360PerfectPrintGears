# tests/test_gear_math.py
import math
import pytest
from core import gear_math as gm


def _valid_inputs(**over):
    base = dict(driving_teeth=50, driven_teeth=10, module_mm=1.5,
                tooth_fraction=0.5, clearance_mm=0.1, resolution=4)
    base.update(over)
    return gm.GearInputs(**base)


# ----------------------------------------------------------- derived geometry
def test_derived_geometry_matches_hand_calc():
    inp = _valid_inputs(module_mm=1.0, tooth_fraction=0.5)
    geo = gm.derive_geometry(inp)
    assert geo.pitch_radius_driving == pytest.approx(25.0)
    assert geo.pitch_radius_driven == pytest.approx(5.0)
    assert geo.center_distance == pytest.approx(30.0)
    assert geo.ratio == pytest.approx(5.0)
    assert geo.circular_pitch == pytest.approx(math.pi)
    # feature width is DERIVED from the module via the tooth fraction
    assert geo.feature_width_mm == pytest.approx(0.5 * math.pi)
    assert geo.half_w == pytest.approx(0.25 * math.pi)


def test_feature_width_scales_with_tooth_fraction():
    geo_a = gm.derive_geometry(_valid_inputs(tooth_fraction=0.5))
    geo_b = gm.derive_geometry(_valid_inputs(tooth_fraction=0.4))
    assert geo_b.feature_width_mm == pytest.approx(0.8 * geo_a.feature_width_mm)


# ------------------------------------------------ tooth-width <-> module helpers
def test_tooth_width_from_module():
    # tooth_width = tooth_fraction * pi * module
    assert gm.tooth_width_from_module(2.0, 0.5) == pytest.approx(0.5 * math.pi * 2.0)


def test_module_from_tooth_width_inverts():
    assert gm.module_from_tooth_width(0.5 * math.pi * 2.0, 0.5) == pytest.approx(2.0)


def test_module_tooth_width_roundtrip():
    m, tf = 1.5, 0.45
    assert gm.module_from_tooth_width(gm.tooth_width_from_module(m, tf), tf) == pytest.approx(m)


def test_module_from_tooth_width_rejects_nonpositive_fraction():
    with pytest.raises(ValueError, match="tooth_fraction"):
        gm.module_from_tooth_width(2.0, 0.0)


# ------------------------------------------------------------------ validation
def test_validate_accepts_good_inputs():
    gm.validate_inputs(_valid_inputs())
    gm.validate_inputs(_valid_inputs(tooth_fraction=0.4))


def test_validate_rejects_low_teeth_on_either_gear():
    with pytest.raises(ValueError, match="at least 6"):
        gm.validate_inputs(_valid_inputs(driven_teeth=5))
    with pytest.raises(ValueError, match="at least 6"):
        gm.validate_inputs(_valid_inputs(driving_teeth=5))


def test_validate_accepts_reduction_driving_smaller_than_driven():
    # The whole point: the driving (tip) gear may now be smaller than the driven gear.
    gm.validate_inputs(_valid_inputs(driving_teeth=10, driven_teeth=40))
    gm.validate_inputs(_valid_inputs(driving_teeth=20, driven_teeth=20))  # 1:1


def test_validate_rejects_nonpositive_module():
    with pytest.raises(ValueError, match="module"):
        gm.validate_inputs(_valid_inputs(module_mm=0.0))


def test_validate_rejects_tooth_fraction_too_large():
    with pytest.raises(ValueError, match="tooth fraction"):
        gm.validate_inputs(_valid_inputs(tooth_fraction=0.6))


def test_validate_rejects_tooth_fraction_nonpositive():
    with pytest.raises(ValueError, match="tooth fraction"):
        gm.validate_inputs(_valid_inputs(tooth_fraction=0.0))


def test_validate_rejects_clearance_ge_feature_width():
    # feature width at module 1.5, fraction 0.5 is ~2.356 mm
    with pytest.raises(ValueError, match="clearance"):
        gm.validate_inputs(_valid_inputs(clearance_mm=3.0))


# --------------------------------------------------------------------- 2D math
def test_rotate_point_90_about_origin():
    x, y = gm.rotate_point((1.0, 0.0), (0.0, 0.0), math.pi / 2)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(1.0, abs=1e-9)


def test_line_intersection_crossing():
    p = gm.line_intersection((0, 0), (2, 2), (0, 2), (2, 0))
    assert p == pytest.approx((1.0, 1.0))


def test_line_intersection_parallel_returns_none():
    assert gm.line_intersection((0, 0), (1, 0), (0, 1), (1, 1)) is None


def test_foot_of_perpendicular():
    f = gm.foot_of_perpendicular((1.0, 1.0), (0.0, 0.0), (2.0, 0.0))
    assert f == pytest.approx((1.0, 0.0))


# --------------------------------------------------------- driving-tip conjugate
def test_contacting_flank_meets_driving_flank_at_pitch_circle():
    # The driven tooth angle alpha = 2*asin(half_w/Rp) places its top flank's
    # pitch endpoint at Q = (C - sqrt(Rp^2 - half_w^2), -half_w) on the driven
    # pitch circle, where the driving BOTTOM flank ends.
    inp = _valid_inputs()
    geo = gm.derive_geometry(inp)
    p_pitch, _ = gm._contacting_flank(geo)
    xq = geo.center_distance - math.sqrt(geo.pitch_radius_driven ** 2 - geo.half_w ** 2)
    assert p_pitch == pytest.approx((xq, -geo.half_w), abs=1e-9)


def test_driving_tip_spans_join_to_apex():
    inp = _valid_inputs()
    geo = gm.derive_geometry(inp)
    pts = gm.driving_tip_points(inp, geo, samples=80)
    assert len(pts) == 80
    # starts at the flank level (y = -half_w), ends on the centerline apex (y = 0)
    assert pts[0][1] == pytest.approx(-geo.half_w, abs=1e-3)
    assert pts[-1][1] == pytest.approx(0.0, abs=1e-12)
    # apex is a real addendum: outside the pitch circle, below a sane ceiling
    apex_r = math.hypot(*pts[-1])
    assert geo.pitch_radius_driving < apex_r < geo.pitch_radius_driving + 2.0 * inp.module_mm
    # x grows monotonically from join toward the apex
    xs = [p[0] for p in pts]
    assert all(xs[i + 1] >= xs[i] - 1e-9 for i in range(len(xs) - 1))


def test_envelope_perp_equals_consecutive_intersection():
    # The foot-of-perpendicular envelope point must equal the limit of the
    # intersection of two consecutive flank snapshots (the classic envelope) --
    # the two extraction methods agree.
    inp = _valid_inputs()
    geo = gm.derive_geometry(inp)
    base = gm._contacting_flank(geo)
    tp = 2.0 * math.pi / inp.driven_teeth
    for frac in (-0.2, -0.1, 0.0, 0.1, 0.2):
        tau = frac * tp
        c = gm.driving_contact_point(geo, base, tau)
        l1 = gm.flank_in_driving_frame(geo, base, tau)
        l2 = gm.flank_in_driving_frame(geo, base, tau + 1e-4)
        ip = gm.line_intersection(l1[0], l1[1], l2[0], l2[1])
        assert ip is not None
        assert math.hypot(ip[0] - c[0], ip[1] - c[1]) < 0.02


# ----------------------------------------------------------------- driving tooth
def test_driving_tooth_structure_and_continuity():
    inp = _valid_inputs(resolution=4)
    geo = gm.derive_geometry(inp)
    segs = gm.build_driving_tooth(inp, geo)

    assert [s.kind for s in segs] == ['line', 'cpspline', 'cpspline', 'line']
    # default resolution -> degree-3 Bezier (4 control points) per tip half
    assert segs[1].degree == 3
    assert len(segs[1].points) == 4
    # continuous path (clamped-Bezier ends ARE the first/last control points)
    for cur, nxt in zip(segs, segs[1:]):
        assert cur.points[-1] == pytest.approx(nxt.points[0], abs=1e-9)
    # apex where the two splines meet, on the centerline
    apex = segs[1].points[-1]
    assert apex == pytest.approx(segs[2].points[0], abs=1e-12)
    assert apex[1] == pytest.approx(0.0, abs=1e-12)
    # real addendum
    apex_r = math.hypot(*apex)
    assert geo.pitch_radius_driving < apex_r < geo.pitch_radius_driving + 2.0 * inp.module_mm


def test_driving_tooth_flanks_at_half_width_no_clearance_narrowing():
    # Backlash now comes from the tooth fraction, NOT from narrowing the driving
    # tooth -- the flanks sit exactly at +/- half_w regardless of clearance.
    inp = _valid_inputs(clearance_mm=0.3)
    geo = gm.derive_geometry(inp)
    segs = gm.build_driving_tooth(inp, geo)
    for pt in segs[3].points:                 # upper flank
        assert pt[1] == pytest.approx(geo.half_w, abs=1e-12)
    for pt in segs[0].points:                 # lower flank
        assert pt[1] == pytest.approx(-geo.half_w, abs=1e-12)


def test_driving_tooth_resolution_selects_degree5():
    # resolution > 4 selects a degree-5 Bezier (6 control points) per tip half
    inp = _valid_inputs(resolution=6)
    geo = gm.derive_geometry(inp)
    segs = gm.build_driving_tooth(inp, geo)
    assert segs[1].degree == 5
    assert len(segs[1].points) == 6


def test_driving_tip_densifies_close_to_conjugate_locus():
    # the drawn tip (densified Bezier) tracks the true conjugate locus closely
    inp = _valid_inputs(resolution=4)
    geo = gm.derive_geometry(inp)
    segs = gm.build_driving_tooth(inp, geo)
    dense = gm.densify_segments([segs[1]], n_spline=2000)   # fine, to measure true dev
    locus = _driving_tip_locus(inp)
    worst = 0.0
    for q in locus:
        worst = max(worst, min(math.hypot(q[0] - d[0], q[1] - d[1]) for d in dense))
    assert worst < 0.005                      # < 5 microns


# ------------------------------------------------------------- bezier tip fit
def test_bezier_point_endpoints_and_cubic_midpoint():
    ctrl = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    assert gm._bezier_point(ctrl, 0.0) == pytest.approx((0.0, 0.0))
    assert gm._bezier_point(ctrl, 1.0) == pytest.approx((1.0, 0.0))
    # cubic at t=0.5 == (P0 + 3P1 + 3P2 + P3)/8
    assert gm._bezier_point(ctrl, 0.5) == pytest.approx((0.5, 0.75))


def test_bezier_curve_samples_n_plus_one_points():
    ctrl = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]      # degree 2
    pts = gm.bezier_curve(ctrl, 10)
    assert len(pts) == 11
    assert pts[0] == pytest.approx((0.0, 0.0))
    assert pts[-1] == pytest.approx((2.0, 0.0))


def _driving_tip_locus(inp):
    geo = gm.derive_geometry(inp)
    locus = gm.driving_tip_points(inp, geo)
    hw = geo.half_w
    locus[0] = (locus[0][0], -hw)
    locus[-1] = (locus[-1][0], 0.0)
    return locus


def _max_dev_from_locus(ctrl, locus):
    fine = gm.bezier_curve(ctrl, 2000)
    worst = 0.0
    for q in locus:
        worst = max(worst, min(math.hypot(q[0] - f[0], q[1] - f[1]) for f in fine))
    return worst


def test_fit_tip_bezier_degree3_tracks_locus_within_5um():
    inp = _valid_inputs(resolution=4)
    locus = _driving_tip_locus(inp)
    ctrl = gm.fit_tip_bezier(locus, degree=3, tangent_join=False)
    assert len(ctrl) == 4
    assert ctrl[0] == pytest.approx(locus[0], abs=1e-12)
    assert ctrl[-1] == pytest.approx(locus[-1], abs=1e-12)
    assert _max_dev_from_locus(ctrl, locus) < 0.005      # < 5 microns


def test_fit_tip_bezier_degree5_has_six_points_and_tracks_tightly():
    inp = _valid_inputs(resolution=6)
    locus = _driving_tip_locus(inp)
    ctrl = gm.fit_tip_bezier(locus, degree=5, tangent_join=False)
    assert len(ctrl) == 6
    assert _max_dev_from_locus(ctrl, locus) < 0.005


def test_fit_tip_bezier_tangent_join_leaves_join_horizontal():
    inp = _valid_inputs(resolution=4)
    locus = _driving_tip_locus(inp)
    ctrl = gm.fit_tip_bezier(locus, degree=3, tangent_join=True)
    # horizontal leave at the join: control point 1 shares the join's y
    assert ctrl[1][1] == pytest.approx(ctrl[0][1], abs=1e-12)


def test_fit_tip_bezier_rejects_unsupported_degree():
    inp = _valid_inputs()
    locus = _driving_tip_locus(inp)
    with pytest.raises(ValueError):
        gm.fit_tip_bezier(locus, degree=4)


# ---------------------------------------------------------------- driven tooth
def test_driven_tooth_elliptical_tip_and_constant_width_flanks():
    inp = _valid_inputs()
    geo = gm.derive_geometry(inp)
    segs = gm.build_driven_tooth(inp, geo)

    kinds = [s.kind for s in segs]
    assert kinds.count('earc') == 1
    assert kinds.count('line') == 2
    # constant width == feature width
    flanks = [s for s in segs if s.kind == 'line']
    ys = [pt[1] for s in flanks for pt in s.points]
    assert max(ys) - min(ys) == pytest.approx(geo.feature_width_mm, abs=1e-9)

    hw = geo.half_w
    chord_x = math.sqrt(geo.pitch_radius_driven ** 2 - hw ** 2)
    co_x = chord_x - 0.25 * hw
    earc = [s for s in segs if s.kind == 'earc'][0]
    center, start, apex, end = earc.points
    assert center == pytest.approx((co_x, 0.0), abs=1e-9)            # 0.25hw inside pitch circle
    assert start == pytest.approx((co_x, -hw), abs=1e-9)            # lower flank top (co-vertex)
    assert end == pytest.approx((co_x, hw), abs=1e-9)               # upper flank top (co-vertex)
    assert apex == pytest.approx((chord_x + 0.5 * hw, 0.0), abs=1e-9)  # bulges 0.5hw past pitch circle
    # radial (minor) semi-axis 0.75hw, tangential (major) semi-axis hw
    assert math.hypot(apex[0] - center[0], apex[1] - center[1]) == pytest.approx(0.75 * hw, abs=1e-9)
    assert math.hypot(end[0] - center[0], end[1] - center[1]) == pytest.approx(hw, abs=1e-9)
    # flanks now end at the co-vertices, NOT on the pitch circle
    flank_tops_x = [pt[0] for s in flanks for pt in s.points if abs(abs(pt[1]) - hw) < 1e-9]
    assert max(flank_tops_x) == pytest.approx(co_x, abs=1e-9)


def test_driven_cap_apex_x_matches_elliptical_apex():
    geo = gm.derive_geometry(_valid_inputs())
    hw = geo.half_w
    chord_x = math.sqrt(geo.pitch_radius_driven ** 2 - hw ** 2)
    assert gm._driven_cap_apex_x(geo) == pytest.approx(chord_x + 0.5 * hw, abs=1e-9)


# -------------------------------------------------------------- array + pair
def test_array_tooth_produces_n_copies():
    seg = gm.Segment('line', [(10.0, 0.0), (12.0, 0.0)])
    out = gm.array_tooth([seg], teeth=4, base_angle=0.0)
    assert len(out) == 4
    assert out[1].points[0] == pytest.approx((0.0, 10.0), abs=1e-6)


def test_array_tooth_preserves_cpspline_degree():
    # the Fusion layer arrays one tooth to apply base_angle before drawing, so the
    # control-point spline's degree must survive arraying (else add() gets degree 0)
    seg = gm.Segment('cpspline', [(1.0, 0.0), (1.0, 1.0), (2.0, 1.0), (2.0, 0.0)],
                     degree=3)
    out = gm.array_tooth([seg], teeth=1, base_angle=0.0)
    assert out[0].kind == 'cpspline'
    assert out[0].degree == 3


def test_build_gear_pair_places_centers_for_meshing():
    inp = _valid_inputs()
    pair = gm.build_gear_pair(inp)
    rw, rp = 1.5 * 50 / 2.0, 1.5 * 10 / 2.0
    assert pair.center_distance == pytest.approx(rw + rp)
    assert pair.driving.center == pytest.approx((0.0, 0.0))
    assert pair.driven.center == pytest.approx((rw + rp, 0.0))
    assert len(pair.driving.segments) == 50 * 5      # 4 tooth segments + 1 root bridge
    assert len(pair.driven.segments) == 10 * 4     # 3 tooth segments + 1 root bridge
    assert pair.driving.pitch_radius == pytest.approx(rw)
    assert pair.driven.pitch_radius == pytest.approx(rp)


def test_peterson_50_10_example_is_sane():
    inp = _valid_inputs(resolution=6)
    pair = gm.build_gear_pair(inp)
    assert pair.driving.pitch_radius + pair.driven.pitch_radius == \
        pytest.approx(pair.center_distance)
    assert pair.driving.addendum_radius > pair.driving.pitch_radius
    assert pair.driving.addendum_radius < pair.driving.pitch_radius + 2.0 * inp.module_mm
    assert pair.driving.root_radius < pair.driving.pitch_radius
    assert pair.driven.root_radius < pair.driven.pitch_radius
    for s in pair.driving.segments:
        for (x, y) in s.points:
            assert math.isfinite(x) and math.isfinite(y)
            assert math.hypot(x, y) <= pair.driving.addendum_radius + 1e-6


def test_other_ratio_60_8_builds():
    inp = _valid_inputs(driving_teeth=60, driven_teeth=8, module_mm=0.8,
                        tooth_fraction=0.4, clearance_mm=0.05, resolution=6)
    pair = gm.build_gear_pair(inp)
    assert len(pair.driving.segments) == 60 * 5
    assert len(pair.driven.segments) == 8 * 4
    assert pair.center_distance == pytest.approx(0.8 * (60 + 8) / 2)


def _seg_endpoints(seg):
    """Return (path_start, path_end) for a segment, accounting for earc whose
    points[0] is the center (not the path start)."""
    if seg.kind == 'earc':
        # earc layout: [center, start, apex, end] -- start=points[1], end=points[3]
        return seg.points[1], seg.points[3]
    return seg.points[0], seg.points[-1]


def test_gear_outlines_form_single_closed_loop():
    inp = _valid_inputs()
    pair = gm.build_gear_pair(inp)
    for prof in (pair.driving, pair.driven):
        segs = prof.segments
        for cur, nxt in zip(segs, segs[1:] + segs[:1]):
            _, cur_end = _seg_endpoints(cur)
            nxt_start, _ = _seg_endpoints(nxt)
            assert cur_end == pytest.approx(nxt_start, abs=1e-6)


# ------------------------------------------------------------------ ratio format
def test_format_ratio_step_up():
    assert gm.format_ratio(60, 12) == "5 : 1 (step-up)"


def test_format_ratio_reduction():
    assert gm.format_ratio(10, 40) == "1 : 4 (reduction)"


def test_format_ratio_non_integer_reduces():
    assert gm.format_ratio(50, 15) == "10 : 3 (step-up)"


def test_format_ratio_equal_counts_is_one_to_one():
    assert gm.format_ratio(20, 20) == "1 : 1"


# ------------------------------------------------------------- earc densify
def test_earc_densify_traces_axis_aligned_ellipse():
    # right half-ellipse: center (5,0), tangential(major) b=2 along y, radial(minor) a=1 along x
    center, start, apex, end = (5.0, 0.0), (5.0, -2.0), (6.0, 0.0), (5.0, 2.0)
    seg = gm.Segment('earc', [center, start, apex, end])
    pts = gm.densify_segments([seg], n_arc=64)
    assert pts[0] == pytest.approx((5.0, -2.0), abs=1e-9)    # start
    assert pts[-1] == pytest.approx((5.0, 2.0), abs=1e-9)    # end
    # every sample satisfies ((x-cx)/a)^2 + ((y-cy)/b)^2 == 1, and bulges +x (x >= cx)
    for x, y in pts:
        assert ((x - 5.0) / 1.0) ** 2 + ((y - 0.0) / 2.0) ** 2 == pytest.approx(1.0, abs=1e-6)
        assert x >= 5.0 - 1e-9
    assert max(x for x, _ in pts) == pytest.approx(6.0, abs=1e-6)   # apex reached


def test_earc_densify_survives_rotation():
    # after array_tooth rotates the four points, densify still traces the ellipse
    center, start, apex, end = (5.0, 0.0), (5.0, -2.0), (6.0, 0.0), (5.0, 2.0)
    seg = gm.Segment('earc', [center, start, apex, end])
    rot = gm.array_tooth([seg], teeth=1, base_angle=math.pi / 3)[0]
    pts = gm.densify_segments([rot], n_arc=64)
    rc = rot.points[0]
    # distances to center are bounded by the two semi-axes (1 and 2)
    for x, y in pts:
        d = math.hypot(x - rc[0], y - rc[1])
        assert 1.0 - 1e-6 <= d <= 2.0 + 1e-6
    # apex sits on the minor/radial semi-axis (1), endpoint on the major/tangential (2)
    rapex, rend = rot.points[2], rot.points[3]
    assert math.hypot(rapex[0] - rc[0], rapex[1] - rc[1]) == pytest.approx(1.0, abs=1e-6)
    assert math.hypot(rend[0] - rc[0], rend[1] - rc[1]) == pytest.approx(2.0, abs=1e-6)
    assert math.hypot(pts[-1][0] - rc[0], pts[-1][1] - rc[1]) == pytest.approx(2.0, abs=1e-6)
