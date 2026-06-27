# tests/test_settings.py
from core import settings


def test_roundtrip_defaults():
    d = settings.defaults()
    s = settings.to_json(d)
    back = settings.from_json(s)
    assert back == d


def test_from_json_handles_garbage():
    # Bad JSON falls back to defaults rather than raising.
    assert settings.from_json("not json") == settings.defaults()


def test_from_json_fills_missing_keys():
    partial = '{"wheel_teeth": 40}'
    out = settings.from_json(partial)
    assert out["wheel_teeth"] == 40
    assert out["pinion_teeth"] == settings.defaults()["pinion_teeth"]


def test_defaults_use_tooth_fraction_not_feature_width():
    d = settings.defaults()
    assert d["tooth_fraction"] == 0.45
    assert d["module_mm"] == 1.5
    assert d["resolution"] == 4
    # feature width is derived, never stored
    assert "feature_width_mm" not in d
    assert "width_is_percent" not in d


def test_resolve_absolute_passthrough():
    assert settings.resolve_length(False, abs_mm=2.0, pct=90.0, basis_mm=10.0) == 2.0


def test_resolve_percent_of_basis():
    # 90% of a 10 mm basis = 9 mm
    assert settings.resolve_length(True, abs_mm=2.0, pct=90.0, basis_mm=10.0) == 9.0
