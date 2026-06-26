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
