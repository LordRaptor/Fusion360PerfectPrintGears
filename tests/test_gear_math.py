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
