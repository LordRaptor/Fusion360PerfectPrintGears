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
