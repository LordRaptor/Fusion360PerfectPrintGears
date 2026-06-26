# tests/test_gear_math.py
import math
import pytest
from core import gear_math as gm


def test_derived_geometry_matches_hand_calc():
    inp = gm.GearInputs(wheel_teeth=50, pinion_teeth=10, module_mm=1.0,
                        feature_width_mm=2.388, clearance_mm=0.1)
    geo = gm.derive_geometry(inp)
    assert geo.pitch_radius_wheel == pytest.approx(25.0)
    assert geo.pitch_radius_pinion == pytest.approx(5.0)
    assert geo.center_distance == pytest.approx(30.0)
    assert geo.ratio == pytest.approx(5.0)
    assert geo.circular_pitch == pytest.approx(math.pi)


# tests/test_gear_math.py  (append)
def _valid_inputs(**over):
    base = dict(wheel_teeth=50, pinion_teeth=10, module_mm=1.0,
                feature_width_mm=2.388, clearance_mm=0.1)
    base.update(over)
    return gm.GearInputs(**base)


def test_validate_accepts_good_inputs():
    gm.validate_inputs(_valid_inputs())  # must not raise


def test_validate_rejects_low_pinion_teeth():
    with pytest.raises(ValueError, match="pinion teeth"):
        gm.validate_inputs(_valid_inputs(pinion_teeth=5))


def test_validate_rejects_wheel_smaller_than_pinion():
    with pytest.raises(ValueError, match="wheel teeth"):
        gm.validate_inputs(_valid_inputs(wheel_teeth=8, pinion_teeth=10))


def test_validate_rejects_nonpositive_module():
    with pytest.raises(ValueError, match="module"):
        gm.validate_inputs(_valid_inputs(module_mm=0.0))


def test_validate_rejects_feature_width_causing_overlap():
    # feature width wider than the circular pitch guarantees overlapping teeth
    with pytest.raises(ValueError, match="feature width"):
        gm.validate_inputs(_valid_inputs(module_mm=1.0, feature_width_mm=4.0))


def test_validate_rejects_clearance_ge_feature_width():
    with pytest.raises(ValueError, match="clearance"):
        gm.validate_inputs(_valid_inputs(clearance_mm=2.388))


# tests/test_gear_math.py  (append)
def test_rotate_point_90_about_origin():
    x, y = gm.rotate_point((1.0, 0.0), (0.0, 0.0), math.pi / 2)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(1.0, abs=1e-9)


def test_rotate_point_about_offset_center():
    x, y = gm.rotate_point((2.0, 1.0), (1.0, 1.0), math.pi)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(1.0, abs=1e-9)


def test_line_intersection_crossing():
    p = gm.line_intersection((0, 0), (2, 2), (0, 2), (2, 0))
    assert p == pytest.approx((1.0, 1.0))


def test_line_intersection_parallel_returns_none():
    assert gm.line_intersection((0, 0), (1, 0), (0, 1), (1, 1)) is None


# tests/test_gear_math.py  (append)
def test_wheel_tip_envelope_spans_pitch_to_centerline():
    inp = _valid_inputs(wheel_teeth=50, pinion_teeth=10, module_mm=1.0,
                        feature_width_mm=2.388, clearance_mm=0.0, resolution=40)
    geo = gm.derive_geometry(inp)
    pts = gm.wheel_tip_halfprofile(inp, geo)

    assert len(pts) >= 5
    radii = [math.hypot(x, y) for (x, y) in pts]

    # The tip lives outside the pitch circle, below the addendum ceiling.
    addendum_ceiling = geo.pitch_radius_wheel + 2.0 * inp.module_mm
    for r in radii:
        assert geo.pitch_radius_wheel - 1e-6 <= r <= addendum_ceiling + 1e-6

    # Ordered from the pitch-circle end (near R_w) up to the apex (largest radius).
    assert radii[0] == pytest.approx(geo.pitch_radius_wheel, abs=0.15)
    assert radii == sorted(radii)  # monotonically increasing toward the apex

    # All points sit on the +x side within a half-tooth angular wedge.
    half_tooth_angle = math.pi / inp.wheel_teeth
    for (x, y) in pts:
        assert x > 0
        assert 0 <= math.atan2(y, x) <= half_tooth_angle + 1e-6


# tests/test_gear_math.py  (append)
def test_wheel_tooth_segments_are_connected_and_typed():
    inp = _valid_inputs(module_mm=1.0, feature_width_mm=2.388, clearance_mm=0.1,
                        resolution=40)
    geo = gm.derive_geometry(inp)
    segs = gm.build_wheel_tooth(inp, geo)

    kinds = [s.kind for s in segs]
    assert kinds.count('spline') == 2          # mirrored tip halves
    assert 'line' in kinds                       # flanks + root
    # Consecutive segments share endpoints (a continuous path).
    for cur, nxt in zip(segs, segs[1:]):
        assert cur.points[-1][0] == pytest.approx(nxt.points[0][0], abs=1e-6)
        assert cur.points[-1][1] == pytest.approx(nxt.points[0][1], abs=1e-6)
    # The apex of the tip sits on the tooth centerline (x-axis).
    apex = segs[1].points[-1]
    assert apex[1] == pytest.approx(0.0, abs=1e-6)


# tests/test_gear_math.py  (append)
def test_pinion_tooth_has_arc_tip_and_constant_width_flanks():
    inp = _valid_inputs(module_mm=1.0, feature_width_mm=2.388, clearance_mm=0.1)
    geo = gm.derive_geometry(inp)
    segs = gm.build_pinion_tooth(inp, geo)

    kinds = [s.kind for s in segs]
    assert kinds.count('arc3') == 1            # one rounded (semicircular) tip
    assert kinds.count('line') >= 2            # two parallel flanks

    # The two flanks are separated by the feature width (constant-width tooth),
    # measured perpendicular to the radial. The pinion tooth is centered on the
    # +x axis here (it is repositioned to point at the wheel during arraying).
    flanks = [s for s in segs if s.kind == 'line']
    ys = [pt[1] for s in flanks for pt in s.points]
    assert max(ys) - min(ys) == pytest.approx(inp.feature_width_mm, abs=1e-6)


# tests/test_gear_math.py  (append)
def test_array_tooth_produces_n_copies():
    seg = gm.Segment('line', [(10.0, 0.0), (12.0, 0.0)])
    out = gm.array_tooth([seg], teeth=4, base_angle=0.0)
    assert len(out) == 4
    # second copy rotated by 90 degrees: (10,0) -> (0,10)
    p = out[1].points[0]
    assert p == pytest.approx((0.0, 10.0), abs=1e-6)


def test_build_gear_pair_places_centers_for_meshing():
    inp = _valid_inputs(wheel_teeth=50, pinion_teeth=10, module_mm=1.0,
                        feature_width_mm=2.388, clearance_mm=0.1, resolution=40)
    pair = gm.build_gear_pair(inp)
    assert pair.center_distance == pytest.approx(30.0)
    assert pair.wheel.center == pytest.approx((0.0, 0.0))
    assert pair.pinion.center == pytest.approx((30.0, 0.0))
    assert pair.wheel.teeth == 50 and pair.pinion.teeth == 10
    assert len(pair.wheel.segments) == 50 * 4      # 4 segments per wheel tooth
    assert len(pair.pinion.segments) == 10 * 3     # 3 segments per pinion tooth
    assert pair.wheel.pitch_radius == pytest.approx(25.0)
    assert pair.pinion.pitch_radius == pytest.approx(5.0)


# tests/test_gear_math.py  (append)
def test_peterson_50_10_example_is_sane():
    # 50T wheel, 10T pinion, 5:1 (the worked example in the document).
    inp = _valid_inputs(wheel_teeth=50, pinion_teeth=10, module_mm=1.0,
                        feature_width_mm=2.388, clearance_mm=0.1, resolution=48)
    pair = gm.build_gear_pair(inp)

    # Pitch circles are tangent at the line of centers.
    assert pair.wheel.pitch_radius + pair.pinion.pitch_radius == \
        pytest.approx(pair.center_distance)

    # Wheel tip rises above its pitch circle (real addendum) but stays sane.
    assert pair.wheel.addendum_radius > pair.wheel.pitch_radius
    assert pair.wheel.addendum_radius < pair.wheel.pitch_radius + 2.0 * inp.module_mm

    # Roots are inside the pitch circles.
    assert pair.wheel.root_radius < pair.wheel.pitch_radius
    assert pair.pinion.root_radius < pair.pinion.pitch_radius

    # Every wheel segment is finite and on the gear (no NaNs / runaway points).
    for s in pair.wheel.segments:
        for (x, y) in s.points:
            assert math.isfinite(x) and math.isfinite(y)
            assert math.hypot(x, y) <= pair.wheel.addendum_radius + 1e-6


# tests/test_gear_math.py  (append)
def test_other_ratio_60_8_builds():
    inp = _valid_inputs(wheel_teeth=60, pinion_teeth=8, module_mm=0.8,
                        feature_width_mm=1.6, clearance_mm=0.08, resolution=48)
    pair = gm.build_gear_pair(inp)
    assert len(pair.wheel.segments) == 60 * 4
    assert len(pair.pinion.segments) == 8 * 3
    assert pair.center_distance == pytest.approx(0.8 * (60 + 8) / 2)
