"""Pure (de)serialization of dialog settings. No Fusion imports."""
import json

_DEFAULTS = {
    "wheel_teeth": 50,
    "pinion_teeth": 10,
    "module_mm": 1.5,
    "width_is_percent": False,
    "feature_width_mm": 2.388,
    "feature_width_pct": 90.0,
    "clearance_is_percent": False,
    "clearance_mm": 0.1,
    "clearance_pct": 5.0,
    "addendum_factor": 1.0,
    "dedendum_factor": 1.0,
    "resolution": 24,
}


def defaults() -> dict:
    return dict(_DEFAULTS)


def to_json(d: dict) -> str:
    return json.dumps(d)


def from_json(s: str) -> dict:
    out = defaults()
    try:
        loaded = json.loads(s)
        if isinstance(loaded, dict):
            out.update({k: v for k, v in loaded.items() if k in out})
    except (ValueError, TypeError):
        pass
    return out


def resolve_length(is_percent: bool, abs_mm: float, pct: float, basis_mm: float) -> float:
    """Return the absolute length in mm. If is_percent, interpret pct as a
    percentage of basis_mm (e.g. circular pitch); otherwise return abs_mm."""
    if is_percent:
        return basis_mm * pct / 100.0
    return abs_mm
