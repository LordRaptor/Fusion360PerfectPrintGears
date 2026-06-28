"""Pure (de)serialization of dialog settings. No Fusion imports."""
import json

_DEFAULTS = {
    "driving_teeth": 50,
    "driven_teeth": 10,
    "module_mm": 1.5,
    # Feature width is DERIVED (= tooth_fraction * circular pitch), not stored.
    # tooth_fraction is the circumferential-backlash knob (< 0.5 thins the teeth).
    # Default 0.45 leaves ~10% circumferential play so the gears mesh with backlash.
    "tooth_fraction": 0.45,
    "clearance_is_percent": False,
    "clearance_mm": 0.1,
    "clearance_pct": 5.0,
    "thickness_mm": 5.0,          # extrude depth
    "dedendum_factor": 1.0,
    "resolution": 4,          # driving-tip Bezier: <=4 -> degree 3, else degree 5
    "tangent_join": False,    # tip leaves the flank join tangent (smoother, worse fit)
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
