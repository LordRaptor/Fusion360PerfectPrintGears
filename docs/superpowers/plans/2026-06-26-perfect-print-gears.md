# Perfect Print Gears Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **⚠ REVISION 2026-06-27 — geometry method rebuilt and validated.**
> The original conjugation (Task 5 envelope-by-consecutive-intersection, and the shipped
> `method='cycloidal'` default) produced a **non-conjugate** tip (~0.22–0.41 mm interference).
> It is **replaced** by the validated Peterson method (interference ~0, confirmed across
> ratios 3/5/7). Changes below:
> - **Task 3** — feature width is now *derived*; validate `TOOTH_FRACTION` instead.
> - **Task 5** — rewritten: one kinematic model (pinion `+tau`, wheel `−tau/ratio`) +
>   foot-of-perpendicular envelope, cross-checked against consecutive-intersection.
> - **Task 6** — rewritten: tip as a ~4-point clamped spline with a **horizontal start-tangent**
>   at the flank join (smooth); sharp apex; roots from the *mating* tip height + clearance.
> - **Task 9b (NEW)** — conjugacy / interference guard in pytest (closed polygons, penetration
>   depth, one kinematic model, **geometry-derived mesh zone**). Sanity checks alone let the
>   wrong curve ship; a hard-coded mesh zone gives a false 0 (both happened — see §retro).
> - **Tasks 12 & 15** — settings/UI: drop feature width as input (derived, read-only); add
>   `TOOTH_FRACTION` (backlash knob); module default 1.5.
> Validated reference implementation (all pass): `tmp/peterson_step1.py … peterson_step5.py`,
> `tmp/peterson_spline.py`, `tmp/peterson_assemble.py`. See spec §4.3/§4.6 and `docs/TODO.md`.

**Goal:** Build a Fusion 360 add-in that generates Steve Peterson's "Perfect Print" gear pairs as paired sketches (wheel + matching pinion) into a user-selected component.

**Architecture:** A pure-Python conjugation engine (`core/gear_math.py`, no `adsk` import, unit-tested with pytest) produces plain geometric data; a thin Fusion layer (`core/sketch_builder.py`) draws that data into sketches; a command module (`commands/generateGears/entry.py`) owns the dialog, validation, and settings persistence. Engine works entirely in **millimeters**; the Fusion layer converts mm→cm at the boundary (Fusion's internal unit is cm).

**Tech Stack:** Python 3, Autodesk Fusion 360 Python API (`adsk.core`, `adsk.fusion`), pytest (for the pure engine only).

**Spec:** `docs/superpowers/specs/2026-06-26-perfect-print-gears-design.md`

**Testing note:** Tasks 2–9 (the engine + validation) are pure Python and are developed strictly TDD with pytest — run them with `python -m pytest`. Tasks 10–17 (the Fusion layer, UI, persistence) **cannot be unit-tested headless** — Fusion can't be driven from pytest. Those tasks are verified by loading the add-in in Fusion using the checklist in Task 18. Where a Fusion task has an automatable pure-logic helper, that helper is split out and tested.

---

## File structure

| File | Responsibility |
|---|---|
| `PerfectPrintGears.manifest` | Add-in manifest (id, name, version, runOnStartup) |
| `PerfectPrintGears.py` | `run(context)` / `stop(context)` entry points |
| `config.py` | `ADDIN_NAME`, `COMPANY_NAME`, ids, `DEBUG` |
| `commands/__init__.py` | Registers the command list; `start()`/`stop()` fan-out |
| `commands/generateGears/__init__.py` | Re-exports `entry` |
| `commands/generateGears/entry.py` | Command def, dialog inputs, events, settings persistence |
| `commands/generateGears/resources/` | Button icons |
| `core/__init__.py` | Marks `core` a package |
| `core/gear_math.py` | **Pure** conjugation engine — no `adsk` import |
| `core/sketch_builder.py` | Draws engine output into Fusion sketches |
| `lib/fusionAddInUtils/` | Ported event/log/error helpers |
| `tests/test_gear_math.py` | pytest for the pure engine |
| `tests/conftest.py` | Makes `core` importable in tests |

---

## Task 1: Project scaffold

**Files:**
- Create: `config.py`
- Create: `PerfectPrintGears.py`
- Create: `PerfectPrintGears.manifest`
- Create: `commands/__init__.py`
- Create: `commands/generateGears/__init__.py`
- Create: `core/__init__.py`
- Create: `lib/fusionAddInUtils/__init__.py`
- Create: `lib/fusionAddInUtils/general_utils.py`
- Create: `lib/fusionAddInUtils/event_utils.py`
- Create: `tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `config.py`**

```python
# Application-wide constants shared across modules.
import os

DEBUG = True

ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = 'NorthstarData'
```

- [ ] **Step 2: Create `lib/fusionAddInUtils/general_utils.py`**

```python
import traceback
import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

try:
    from ... import config
    DEBUG = config.DEBUG
except Exception:
    DEBUG = False


def log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel, force_console: bool = False):
    print(message)
    if level == adsk.core.LogLevels.ErrorLogLevel:
        app.log(message, level, adsk.core.LogTypes.FileLogType)
    if DEBUG or force_console:
        app.log(message, level, adsk.core.LogTypes.ConsoleLogType)


def handle_error(name: str, show_message_box: bool = False):
    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel)
    if show_message_box:
        ui.messageBox(f'{name}\n{traceback.format_exc()}')
```

- [ ] **Step 3: Create `lib/fusionAddInUtils/event_utils.py`**

```python
import sys
from typing import Callable
import adsk.core
from .general_utils import handle_error

_handlers = []


def add_handler(event: adsk.core.Event, callback: Callable, *, name: str = None, local_handlers: list = None):
    module = sys.modules[event.__module__]
    handler_type = module.__dict__[event.add.__annotations__['handler']]
    handler = _create_handler(handler_type, callback, event, name, local_handlers)
    event.add(handler)
    return handler


def clear_handlers():
    global _handlers
    _handlers = []


def _create_handler(handler_type, callback, event, name=None, local_handlers=None):
    handler = _define_handler(handler_type, callback, name)()
    (local_handlers if local_handlers is not None else _handlers).append(handler)
    return handler


def _define_handler(handler_type, callback, name=None):
    name = name or handler_type.__name__

    class Handler(handler_type):
        def __init__(self):
            super().__init__()

        def notify(self, args):
            try:
                callback(args)
            except Exception:
                handle_error(name)

    return Handler
```

- [ ] **Step 4: Create `lib/fusionAddInUtils/__init__.py`**

```python
from .general_utils import *
from .event_utils import *
```

- [ ] **Step 5: Create `commands/generateGears/__init__.py`**

```python
from . import entry
```

- [ ] **Step 6: Create `commands/__init__.py`**

```python
from .generateGears import entry as generateGears

commands = [
    generateGears,
]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
```

- [ ] **Step 7: Create `core/__init__.py`** (empty file)

```python
```

- [ ] **Step 8: Create `PerfectPrintGears.py`**

```python
from . import commands
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        commands.start()
    except Exception:
        futil.handle_error('run')


def stop(context):
    try:
        futil.clear_handlers()
        commands.stop()
    except Exception:
        futil.handle_error('stop')
```

- [ ] **Step 9: Create `PerfectPrintGears.manifest`**

```json
{
    "autodeskProduct": "Fusion",
    "type": "addin",
    "author": "Christopher Schank",
    "description": {
        "": "Generates Perfect Print gear pairs as sketches"
    },
    "version": "0.1.0",
    "runOnStartup": false,
    "supportedOS": "windows|mac",
    "editEnabled": true
}
```

- [ ] **Step 10: Create `tests/conftest.py`** (so `import core...` resolves from the repo root)

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

- [ ] **Step 11: Append to `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 12: Verify the engine package imports in plain Python**

Run: `python -c "import core.gear_math" 2>&1 | head -1`
Expected: `ModuleNotFoundError: No module named 'core.gear_math'` (the module doesn't exist yet — that's fine; it confirms `core` is found as a package). If it instead says "No module named 'core'", fix `core/__init__.py`.

- [ ] **Step 13: Commit**

```bash
git add config.py PerfectPrintGears.py PerfectPrintGears.manifest commands core lib tests .gitignore
git commit -m "scaffold: Perfect Print Gears add-in package and utils"
```

---

## Task 2: Engine data types and derived geometry

**Files:**
- Create: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gear_math.py::test_derived_geometry_matches_hand_calc -v`
Expected: FAIL — `AttributeError: module 'core.gear_math' has no attribute 'GearInputs'`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/gear_math.py
"""Pure-Python Perfect Print gear geometry engine. No Fusion (adsk) imports.

All lengths are in millimeters. The caller (Fusion layer) converts mm -> cm.
Coordinate frame: wheel center at origin (0,0); pinion center at (center_distance, 0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]


@dataclass
class GearInputs:
    wheel_teeth: int
    pinion_teeth: int
    module_mm: float
    feature_width_mm: float
    clearance_mm: float
    addendum_factor: float = 1.0
    dedendum_factor: float = 1.0
    resolution: int = 24


@dataclass
class DerivedGeometry:
    pitch_radius_wheel: float
    pitch_radius_pinion: float
    center_distance: float
    ratio: float
    circular_pitch: float


def derive_geometry(inp: GearInputs) -> DerivedGeometry:
    rw = inp.module_mm * inp.wheel_teeth / 2.0
    rp = inp.module_mm * inp.pinion_teeth / 2.0
    return DerivedGeometry(
        pitch_radius_wheel=rw,
        pitch_radius_pinion=rp,
        center_distance=rw + rp,
        ratio=inp.wheel_teeth / inp.pinion_teeth,
        circular_pitch=math.pi * inp.module_mm,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gear_math.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): gear inputs and derived geometry"
```

---

## Task 3: Input validation

> **▶ REVISED 2026-06-27.** Feature width is no longer an input — it is derived
> `feature_width_mm = TOOTH_FRACTION * π * module_mm`. `GearInputs` gains `tooth_fraction`
> (default 0.5) and **drops** `feature_width_mm` as a direct field (expose a derived property
> or compute in `derive_geometry`). Validation changes accordingly:
> - replace the "feature width too large / overlap" checks (now structurally impossible) with
>   `0 < tooth_fraction < 0.5`;
> - keep `clearance >= 0` and `clearance < feature_width` (using the *derived* width);
> - keep teeth-count and module checks.
> The code block below is the original (feature-width-as-input) version — adapt it to the
> derived model.

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gear_math.py -k validate -v`
Expected: FAIL — `AttributeError: ... has no attribute 'validate_inputs'`.

- [ ] **Step 3: Write minimal implementation (append to `core/gear_math.py`)**

```python
MIN_PINION_TEETH = 6


def validate_inputs(inp: GearInputs) -> None:
    """Raise ValueError with a human-readable message if inputs are unusable."""
    if inp.pinion_teeth < MIN_PINION_TEETH:
        raise ValueError(f"pinion teeth must be at least {MIN_PINION_TEETH}")
    if inp.wheel_teeth < inp.pinion_teeth:
        raise ValueError("wheel teeth must be >= pinion teeth")
    if inp.module_mm <= 0:
        raise ValueError("module must be greater than 0")
    if inp.feature_width_mm <= 0:
        raise ValueError("feature width must be greater than 0")

    geo = derive_geometry(inp)
    # Teeth would touch/overlap if the tooth is wider than the tooth-to-tooth spacing.
    # Require the tooth to occupy less than half the circular pitch so a real gap remains.
    if inp.feature_width_mm >= geo.circular_pitch * 0.5:
        raise ValueError(
            "feature width is too large for this module/teeth (teeth would overlap); "
            "reduce feature width or increase module"
        )
    # Pinion flanks (offset half-width from a radial) must not cross the pinion centre.
    if inp.feature_width_mm / 2.0 >= geo.pitch_radius_pinion:
        raise ValueError("feature width is too large for the pinion size")
    if inp.clearance_mm < 0:
        raise ValueError("clearance must be >= 0")
    if inp.clearance_mm >= inp.feature_width_mm:
        raise ValueError("clearance must be less than the feature width")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gear_math.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): input validation"
```

---

## Task 4: 2D math helpers (rotate, line intersection)

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gear_math.py -k "rotate or intersection" -v`
Expected: FAIL — attributes not defined.

- [ ] **Step 3: Write minimal implementation (append to `core/gear_math.py`)**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gear_math.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): 2d rotate and line-intersection helpers"
```

---

## Task 5: Conjugate wheel-tip envelope (the core algorithm)

> **▶ REWRITTEN 2026-06-27 — port from `tmp/peterson_assemble.py` (validated).**
> The original method below (rotate a horizontal reference flank, take consecutive-line
> intersections, empirically guess signs) is **superseded** — it generated from the wrong
> flank instant and its sanity test couldn't detect a non-conjugate result. Use instead:
> 1. **One kinematic model** driven by a single `tau`: pinion `+tau` about `O_p`, wheel
>    `−tau/ratio` about `O_w`. This same model is reused by the Task 9b interference test —
>    do not introduce a second sign/phase convention anywhere.
> 2. **Contacting flank** = the pinion top flank placed by `alpha = 2·asin(half_w/R_p)` so it
>    meets the wheel bottom flank at `Q` on the pinion pitch circle.
> 3. **Envelope point(tau)** = foot of perpendicular from the pitch point `P` onto the
>    (rotated) flank line, then rotated `+tau/ratio` about `O_w`. Exact for a straight flank.
> 4. Find `tau_join` (envelope y = −half_w) and `tau_apex` (y = 0) by scanning a **wide**
>    tau range (`±1.5·tooth_pitch`, not ±0.6 — the crossing's tau shifts with ratio); the
>    half-tip is the locus between them.
> Keep `wheel_tip_halfprofile(...)` returning ordered pitch-end→apex points (the rest of the
> engine consumes that). The function below is kept only as historical reference.

This computes the half-profile of the wheel tooth tip as the envelope of the moving pinion flank. **Sign conventions for the two rotations are confirmed empirically by the test below** — if the test fails on the endpoint/monotonicity assertions, flip `wheel_dir` from `-1` to `+1` (Step 4 explains).

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test (robust, sign-independent invariants)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gear_math.py::test_wheel_tip_envelope_spans_pitch_to_centerline -v`
Expected: FAIL — `wheel_tip_halfprofile` not defined.

- [ ] **Step 3: Write the implementation (append to `core/gear_math.py`)**

```python
def wheel_tip_halfprofile(inp: GearInputs, geo: DerivedGeometry,
                          pinion_dir: int = 1, wheel_dir: int = -1) -> List[Point]:
    """Half of the wheel tooth tip, generated as the conjugate envelope of the
    moving pinion flank. Returns points ordered from the pitch-circle end to the
    tooth-centerline apex, in wheel-centered coordinates (mm), on the +x side.

    Method (Peterson, Clock Design Guidelines pp. 63-64):
      * The pinion working flank is a straight line parallel to a pinion radial,
        offset by half the feature width.
      * Step the meshing motion: rotate that flank about the pinion centre by
        k*delta, and simultaneously about the wheel centre by k*delta/ratio
        (opposite sense). delta spans one pinion tooth pitch over `resolution` steps.
      * The envelope tangent to that family of lines is the wheel tip; sample it
        as the intersection of consecutive line snapshots.
    """
    op = (geo.center_distance, 0.0)            # pinion centre
    ow = (0.0, 0.0)                            # wheel centre
    half_w = inp.feature_width_mm / 2.0

    # Reference upper flank: horizontal line at y=+half_w (parallel to the pinion
    # radial that points toward the wheel), defined by two points spanning well
    # past the pitch point so the family covers the whole tip.
    reach = geo.center_distance + geo.pitch_radius_pinion
    a_ref = (op[0], half_w)
    b_ref = (op[0] - reach, half_w)

    pitch_angle_pinion = 2.0 * math.pi / inp.pinion_teeth
    k_steps = max(8, inp.resolution)
    delta = pitch_angle_pinion / k_steps

    lines = []
    for k in range(k_steps + 1):
        tp = pinion_dir * k * delta
        tw = wheel_dir * k * delta / geo.ratio
        a = rotate_point(rotate_point(a_ref, op, tp), ow, tw)
        b = rotate_point(rotate_point(b_ref, op, tp), ow, tw)
        lines.append((a, b))

    half_tooth_angle = math.pi / inp.wheel_teeth
    addendum_ceiling = geo.pitch_radius_wheel + 2.0 * inp.module_mm

    raw = []
    for k in range(len(lines) - 1):
        e = line_intersection(lines[k][0], lines[k][1],
                              lines[k + 1][0], lines[k + 1][1])
        if e is None:
            continue
        x, y = e
        r = math.hypot(x, y)
        if x <= 0:
            continue
        ang = math.atan2(y, x)
        if not (-1e-9 <= ang <= half_tooth_angle + 1e-9):
            continue
        if not (geo.pitch_radius_wheel - 1e-6 <= r <= addendum_ceiling + 1e-6):
            continue
        raw.append((max(ang, 0.0), (x, y), r))

    # Order from the pitch-circle end (smallest radius) to the apex (largest radius).
    raw.sort(key=lambda t: t[2])
    return [p for (_a, p, _r) in raw]
```

- [ ] **Step 4: Run test; if it fails, flip the wheel rotation direction**

Run: `python -m pytest tests/test_gear_math.py::test_wheel_tip_envelope_spans_pitch_to_centerline -v`
Expected: PASS.
If it FAILS with points on the wrong side (negative `x`/`y`, or radii not spanning R_w→apex), the meshing sense is reversed: change the default `wheel_dir=-1` to `wheel_dir=1` (and if still wrong, also `pinion_dir=-1`) and re-run. One of the four sign combinations produces the valid envelope; the assertions pin the correct one.

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): conjugate wheel-tip envelope"
```

---

## Task 6: Build one wheel tooth (mirror tip, add flanks and root)

> **▶ REWRITTEN 2026-06-27 — port from `tmp/peterson_assemble.py` / `tmp/peterson_spline.py`.**
> - Tip is a **clamped cubic spline** through ~`resolution` fit points (default 4) per half,
>   with the **start tangent horizontal at the join** (clamp `y'(join)=0`, x natural) so it
>   leaves tangent to the straight flank — no corner. Emit the fit points **and** the
>   horizontal start-tangent so `sketch_builder` can add a Fusion fitted spline with a tangent
>   constraint. (Old code applied a clearance-narrowing rotation to the tip — **remove that**;
>   backlash now comes from `TOOTH_FRACTION`, not from narrowing the wheel tip.)
> - **Apex stays a sharp point** (printer smooths it) — do not round it.
> - **Root radius** = `R_w − (pinion_tip_height + clearance)` (mating tip, not `1.25·module`);
>   place the flank foot on the root circle via `sqrt(root² − half_w²)`.
> - Flanks end at the join level (≈ pinion pitch circle), where the tip peels off.
> The block below is the original (clearance-narrowed, fixed-root) version — adapt it.

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gear_math.py::test_wheel_tooth_segments_are_connected_and_typed -v`
Expected: FAIL — `Segment` / `build_wheel_tooth` not defined.

- [ ] **Step 3: Write the implementation (append to `core/gear_math.py`)**

```python
@dataclass
class Segment:
    kind: str               # 'line' | 'spline' | 'arc3' (arc3 = [start, mid, end])
    points: List[Point]


def _polar(r: float, ang: float) -> Point:
    return (r * math.cos(ang), r * math.sin(ang))


def build_wheel_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One wheel tooth centered on the +x axis, as a connected list of Segments,
    ordered counter-clockwise: lower root -> lower flank -> tip (2 splines) ->
    upper flank -> upper root. Clearance narrows the tooth (both flanks pulled in).
    """
    tip = wheel_tip_halfprofile(inp, geo)            # pitch-end -> apex, upper (+y) side
    if not tip:
        raise ValueError("could not generate wheel tip envelope")

    # Pull the tip in by the clearance to leave running play (narrow the wheel tooth).
    clr = inp.clearance_mm
    upper_tip = []                                    # ordered pitch-end -> apex
    for (x, y) in tip:
        ang = math.atan2(y, x)
        r = math.hypot(x, y)
        ang_in = ang - (clr / 2.0) / r               # rotate toward centerline by clearance
        upper_tip.append(_polar(r, ang_in))
    apex = (upper_tip[-1][0], 0.0)                    # force apex onto the centerline
    lower_tip = [(x, -y) for (x, y) in upper_tip]     # mirror across the x-axis (pitch-end -> apex)

    # Flanks: straight radial walls from the root up to the pitch-circle end of the
    # tip, at the same angle as the tip's pitch-end point.
    root_radius = geo.pitch_radius_wheel - (inp.module_mm * 1.25 * inp.dedendum_factor)
    up_ang = math.atan2(upper_tip[0][1], upper_tip[0][0])
    lo_ang = math.atan2(lower_tip[0][1], lower_tip[0][0])
    upper_root_pt = _polar(root_radius, up_ang)
    lower_root_pt = _polar(root_radius, lo_ang)

    # Connected counter-clockwise path:
    #   lower flank -> lower tip (pitch-end..apex) -> upper tip (apex..pitch-end) -> upper flank
    segs: List[Segment] = []
    segs.append(Segment('line', [lower_root_pt, lower_tip[0]]))            # lower flank
    segs.append(Segment('spline', lower_tip + [apex]))                    # lower tip -> apex
    segs.append(Segment('spline', [apex] + list(reversed(upper_tip))))    # apex -> upper pitch-end
    segs.append(Segment('line', [upper_tip[0], upper_root_pt]))           # upper flank
    return segs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gear_math.py::test_wheel_tooth_segments_are_connected_and_typed -v`
Expected: PASS. The path is continuous: lower flank ends at `lower_tip[0]` (seg1 start); seg1 ends at `apex` (seg2 start); seg2 ends at `upper_tip[0]` (seg3 start).

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): assemble one wheel tooth from mirrored tip + flanks"
```

---

## Task 7: Build one pinion tooth (straight flanks + rounded tip)

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gear_math.py::test_pinion_tooth_has_arc_tip_and_constant_width_flanks -v`
Expected: FAIL — `build_pinion_tooth` not defined.

- [ ] **Step 3: Write the implementation (append to `core/gear_math.py`)**

```python
def build_pinion_tooth(inp: GearInputs, geo: DerivedGeometry) -> List[Segment]:
    """One pinion tooth centered on the +x axis: two parallel straight flanks a
    feature-width apart, capped by a semicircular tip, with root feet. Returned
    as a connected counter-clockwise path. The tip is free (never contacts the
    wheel); only the flanks are working surfaces.
    """
    half_w = inp.feature_width_mm / 2.0
    root_radius = geo.pitch_radius_pinion - (inp.module_mm * 1.25 * inp.dedendum_factor)
    # Pinion addendum: flanks extend a little past the pitch circle, then a
    # semicircular cap of radius half_w. Tip apex height chosen so the cap is a
    # clean semicircle just beyond the pitch radius.
    flank_top_x = geo.pitch_radius_pinion + (inp.module_mm * inp.addendum_factor)

    lower_root = (root_radius, -half_w)
    lower_flank_top = (flank_top_x, -half_w)
    upper_flank_top = (flank_top_x, half_w)
    upper_root = (root_radius, half_w)
    tip_mid = (flank_top_x + half_w, 0.0)            # outermost point of the cap

    segs: List[Segment] = []
    segs.append(Segment('line', [lower_root, lower_flank_top]))             # lower flank
    segs.append(Segment('arc3', [lower_flank_top, tip_mid, upper_flank_top]))  # rounded tip
    segs.append(Segment('line', [upper_flank_top, upper_root]))             # upper flank
    return segs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gear_math.py::test_pinion_tooth_has_arc_tip_and_constant_width_flanks -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): pinion tooth with constant-width flanks and rounded tip"
```

---

## Task 8: Array teeth and assemble the GearPair

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gear_math.py  (append)
def test_array_tooth_produces_n_copies():
    seg = gm.Segment('line', [(10.0, 0.0), (12.0, 0.0)])
    out = gm.array_tooth([seg], teeth=4, base_angle=0.0)
    assert len(out) == 4
    # second copy rotated by 90 degrees: (10,0) -> (0,10)
    p = out[1][0].points[0]
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gear_math.py -k "array_tooth or gear_pair" -v`
Expected: FAIL — symbols not defined.

- [ ] **Step 3: Write the implementation (append to `core/gear_math.py`)**

```python
@dataclass
class GearProfile:
    role: str                       # 'wheel' | 'pinion'
    teeth: int
    center: Point                   # placement in the component frame (mm)
    pitch_radius: float
    root_radius: float
    addendum_radius: float
    segments: List[Segment]         # all teeth, gear-local coords (centered at origin), mm


@dataclass
class GearPair:
    wheel: GearProfile
    pinion: GearProfile
    center_distance: float
    circular_pitch: float


def array_tooth(tooth: List[Segment], teeth: int, base_angle: float) -> List[Segment]:
    """Replicate one tooth `teeth` times around the origin, each rotated by the
    tooth pitch, starting from `base_angle`."""
    pitch = 2.0 * math.pi / teeth
    out: List[Segment] = []
    for k in range(teeth):
        ang = base_angle + k * pitch
        for seg in tooth:
            out.append(Segment(seg.kind,
                               [rotate_point(p, (0.0, 0.0), ang) for p in seg.points]))
    return out


def _radii(segments: List[Segment]) -> Tuple[float, float]:
    rr = [math.hypot(x, y) for s in segments for (x, y) in s.points]
    return (min(rr), max(rr))


def build_gear_pair(inp: GearInputs) -> GearPair:
    validate_inputs(inp)
    geo = derive_geometry(inp)

    wheel_tooth = build_wheel_tooth(inp, geo)
    pinion_tooth = build_pinion_tooth(inp, geo)

    wheel_segs = array_tooth(wheel_tooth, inp.wheel_teeth, base_angle=0.0)
    # Pinion tooth points toward the wheel (-x from the pinion centre) to mesh.
    pinion_segs = array_tooth(pinion_tooth, inp.pinion_teeth, base_angle=math.pi)

    w_root, w_add = _radii(wheel_segs)
    p_root, p_add = _radii(pinion_segs)

    wheel = GearProfile('wheel', inp.wheel_teeth, (0.0, 0.0),
                        geo.pitch_radius_wheel, w_root, w_add, wheel_segs)
    pinion = GearProfile('pinion', inp.pinion_teeth, (geo.center_distance, 0.0),
                         geo.pitch_radius_pinion, p_root, p_add, pinion_segs)
    return GearPair(wheel, pinion, geo.center_distance, geo.circular_pitch)
```

- [ ] **Step 4: Run the whole engine suite**

Run: `python -m pytest tests/test_gear_math.py -v`
Expected: PASS (all tests, every task so far).

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): array teeth and assemble GearPair"
```

---

## Task 9: Golden check against Peterson's documented example

**Files:**
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python -m pytest tests/test_gear_math.py::test_peterson_50_10_example_is_sane -v`
Expected: PASS (the engine is already complete; this locks the documented example as a regression guard). If it FAILS, the failing assertion identifies which geometric property is off — fix the relevant engine function before proceeding.

- [ ] **Step 3: (Optional) Add a second ratio as a regression guard**

```python
# tests/test_gear_math.py  (append)
def test_other_ratio_60_8_builds():
    inp = _valid_inputs(wheel_teeth=60, pinion_teeth=8, module_mm=0.8,
                        feature_width_mm=1.6, clearance_mm=0.08, resolution=48)
    pair = gm.build_gear_pair(inp)
    assert len(pair.wheel.segments) == 60 * 4
    assert len(pair.pinion.segments) == 8 * 3
    assert pair.center_distance == pytest.approx(0.8 * (60 + 8) / 2)
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gear_math.py
git commit -m "test(engine): Peterson 50/10 golden check and second ratio"
```

---

## Task 9b: Conjugacy / interference guard (NEW — the critical test)

> **Added 2026-06-27.** This is the test that was missing — sanity assertions let a
> non-conjugate curve ship. Port the trustworthy interference test from
> `tmp/peterson_assemble.py`.

**Files:**
- Test: `tests/test_gear_math.py` (or a dedicated `tests/test_interference.py`)
- Possibly expose small helpers from `core/gear_math.py` (closed-polygon assembly).

- [ ] **Step 1: Build closed gear polygons** from `build_gear_pair` output — each gear's full
  outline plus **root-bridge arcs** between teeth (an open zig-zag makes point-in-polygon
  garbage). Arcs sampled **through the mid point**.

- [ ] **Step 2: Roll under ONE kinematic model** — the same as generation: pinion `+tau`
  about `O_p`, wheel `−tau/ratio` about `O_w`. Build each gear in **local** coords, then a
  **single** placement transform (no double translation). Pinion phase = `π + π/N_p` (a gap
  faces the wheel).

- [ ] **Step 3: Measure penetration DEPTH** (not nearest distance): for vertices of one gon
  inside the other (ray-cast point-in-poly), take distance-to-boundary; max over the cycle.
  **Restrict candidate vertices to a geometry-derived mesh zone** centered on the pitch point
  `(R_w, 0)` and scaled by module — **never hard-code the zone** (a fixed zone gave a false 0
  when diameters changed; catch it by checking the snug `TOOTH_FRACTION=0.5` case reports a
  *nonzero* residual).

- [ ] **Step 4: Assert** max penetration depth < tolerance (e.g. < 60 µm, comfortably above
  the spline/sampling floor) over `±1` pinion pitch, at a realistic `TOOTH_FRACTION` (e.g.
  0.4). Add a second ratio (e.g. 36/12 and 56/8) so the guard isn't 50/10-specific.

- [ ] **Step 5: Commit**

```bash
git add tests/ core/gear_math.py
git commit -m "test(engine): conjugacy/interference guard (penetration depth, one kinematic model)"
```

---

## Task 10: Sketch builder — draw one gear into a sketch

The Fusion layer. Not unit-testable headless; verified in Task 18. Keep it dumb: it only translates engine `Segment`s into sketch curves and converts mm→cm.

**Files:**
- Create: `core/sketch_builder.py`

- [ ] **Step 1: Implement `core/sketch_builder.py`**

```python
"""Draws gear_math output into Fusion sketches. Converts mm (engine) -> cm (Fusion)."""
import adsk.core
import adsk.fusion

from . import gear_math

MM_TO_CM = 0.1


def _pt(x_mm: float, y_mm: float) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x_mm * MM_TO_CM, y_mm * MM_TO_CM, 0.0)


def _draw_segments(sketch: adsk.fusion.Sketch, segments, cx_mm: float, cy_mm: float):
    curves = sketch.sketchCurves
    for seg in segments:
        pts = [(p[0] + cx_mm, p[1] + cy_mm) for p in seg.points]
        if seg.kind == 'line':
            for a, b in zip(pts, pts[1:]):
                curves.sketchLines.addByTwoPoints(_pt(*a), _pt(*b))
        elif seg.kind == 'arc3':
            s, m, e = pts
            curves.sketchArcs.addByThreePoints(_pt(*s), _pt(*m), _pt(*e))
        elif seg.kind == 'spline':
            coll = adsk.core.ObjectCollection.create()
            for p in pts:
                coll.add(_pt(*p))
            curves.sketchFittedSplines.add(coll)


def draw_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
              name: str) -> adsk.fusion.Sketch:
    """Create one sketch in `component` containing: center point, construction
    circles (pitch/root/addendum), and the full toothed outline for `profile`."""
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = name
    cx, cy = profile.center

    sketch.isComputeDeferred = True
    try:
        # Center point.
        sketch.sketchPoints.add(_pt(cx, cy))

        # Construction circles.
        circles = sketch.sketchCurves.sketchCircles
        for r in (profile.pitch_radius, profile.root_radius, profile.addendum_radius):
            c = circles.addByCenterRadius(_pt(cx, cy), r * MM_TO_CM)
            c.isConstruction = True

        # Toothed outline.
        _draw_segments(sketch, profile.segments, cx, cy)
    finally:
        sketch.isComputeDeferred = False

    return sketch
```

- [ ] **Step 2: Sanity-check it imports as a module body (syntax only)**

Run: `python -m py_compile core/sketch_builder.py && echo OK`
Expected: `OK` (this only checks syntax; `adsk` is unavailable outside Fusion, but `py_compile` does not execute imports).

- [ ] **Step 3: Commit**

```bash
git add core/sketch_builder.py
git commit -m "feat(fusion): sketch builder for a single gear"
```

---

## Task 11: Sketch builder — build both gears of a pair

**Files:**
- Modify: `core/sketch_builder.py`

- [ ] **Step 1: Append `build_pair` to `core/sketch_builder.py`**

```python
def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair) -> None:
    """Draw both gears of `pair` into `component` as two sketches in meshing layout
    (wheel at origin, pinion at the center distance on +x)."""
    draw_gear(component, pair.wheel, f'PPG Wheel {pair.wheel.teeth}T')
    draw_gear(component, pair.pinion, f'PPG Pinion {pair.pinion.teeth}T')
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile core/sketch_builder.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add core/sketch_builder.py
git commit -m "feat(fusion): build both gears of a pair into a component"
```

---

## Task 12: Settings (de)serialization helper — pure and testable

> **▶ REVISED 2026-06-27.** Defaults change: `module_mm` → **1.5**; **remove** the
> feature-width input keys (`width_is_percent`, `feature_width_mm`, `feature_width_pct`) —
> width is derived; **add** `tooth_fraction` → **0.5**. `resolution` is now the spline
> fit-points-per-half (default 4). Keep the clearance absolute/percent keys.

The save/load of dialog values to a JSON string is pure logic; split it out so it can be tested without Fusion.

**Files:**
- Create: `core/settings.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL — `No module named 'core.settings'`.

- [ ] **Step 3: Implement `core/settings.py`**

```python
"""Pure (de)serialization of dialog settings. No Fusion imports."""
import json

_DEFAULTS = {
    "wheel_teeth": 50,
    "pinion_teeth": 10,
    "module_mm": 0.8,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/settings.py tests/test_settings.py
git commit -m "feat(settings): pure dialog-settings serialization"
```

---

## Task 13: Width/clearance resolution helper — pure and testable

Converts the switchable absolute/percent dialog values into the absolute mm the engine needs.

**Files:**
- Modify: `core/settings.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings.py  (append)
def test_resolve_absolute_passthrough():
    assert settings.resolve_length(False, abs_mm=2.0, pct=90.0, basis_mm=10.0) == 2.0


def test_resolve_percent_of_basis():
    # 90% of a 10 mm basis = 9 mm
    assert settings.resolve_length(True, abs_mm=2.0, pct=90.0, basis_mm=10.0) == 9.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings.py -k resolve -v`
Expected: FAIL — `resolve_length` not defined.

- [ ] **Step 3: Implement (append to `core/settings.py`)**

```python
def resolve_length(is_percent: bool, abs_mm: float, pct: float, basis_mm: float) -> float:
    """Return the absolute length in mm. If is_percent, interpret pct as a
    percentage of basis_mm (e.g. circular pitch); otherwise return abs_mm."""
    if is_percent:
        return basis_mm * pct / 100.0
    return abs_mm
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/settings.py tests/test_settings.py
git commit -m "feat(settings): absolute/percent length resolution"
```

---

## Task 14: Command scaffold — button appears in Fusion

**Files:**
- Create: `commands/generateGears/entry.py`
- Create: `commands/generateGears/resources/` (copy 16/32/64 px PNG icons from the SpurGear sample or any placeholder; an empty folder is tolerated but the button will have no icon)

- [ ] **Step 1: Implement the start/stop + empty command in `entry.py`**

```python
import os
import adsk.core
import adsk.fusion

from ...lib import fusionAddInUtils as futil
from ... import config
from ...core import gear_math, sketch_builder, settings

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_generateGears'
CMD_NAME = 'Generate Perfect Print Gears'
CMD_DESC = 'Generate a matched Perfect Print wheel + pinion as sketches'
IS_PROMOTED = True
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

ATTR_GROUP = 'PerfectPrintGears'
ATTR_NAME = 'Settings'

local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_DESC, ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.itemById(CMD_ID)
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if control:
        control.deleteMe()
    if cmd_def:
        cmd_def.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}: command_created')
    # Inputs added in Task 15.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}: execute (stub)')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    pass


def command_validate(args: adsk.core.ValidateInputsEventArgs):
    args.areInputsValid = True


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile commands/generateGears/entry.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add commands/generateGears/entry.py commands/generateGears/resources
git commit -m "feat(ui): command scaffold adds button to Create panel"
```

- [ ] **Step 4: Manual Fusion check (record result, do not block)**

Load the add-in (Utilities → Add-Ins → Scripts and Add-Ins → green **+** → pick this folder → Run). Confirm **"Generate Perfect Print Gears"** appears in Solid → Create and clicking it opens an empty dialog without error. (Detailed checklist in Task 18.)

---

## Task 15: Dialog inputs

> **▶ REVISED 2026-06-27.** Replace the feature-width input (and its abs/percent toggle) with:
> - a **Tooth fraction** value input (default 0.5; valid `0 < f < 0.5`), and
> - a **read-only** feature-width display (`= tooth_fraction · π · module`), updated live in
>   `command_input_changed` as module/fraction change (use a read-only text/value input).
> Module default → 1.5. Clearance abs/percent stays. `resolution` label → "tip spline points".

**Files:**
- Modify: `commands/generateGears/entry.py`

- [ ] **Step 1: Replace `command_created` body (before the `add_handler` calls) to build inputs**

```python
def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}: command_created')
    inputs = args.command.commandInputs

    design = adsk.fusion.Design.cast(app.activeProduct)
    s = settings.defaults()
    if design:
        attr = design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
        if attr:
            s = settings.from_json(attr.value)

    # Target component (single selection); defaults to the active component on execute.
    sel = inputs.addSelectionInput('target', 'Target component',
                                   'Component to draw the gear sketches into')
    sel.addSelectionFilter('Occurrences')
    sel.addSelectionFilter('RootComponents')
    sel.setSelectionLimits(0, 1)

    inputs.addIntegerSpinnerCommandInput('wheelTeeth', 'Wheel teeth', 6, 2000, 1, int(s['wheel_teeth']))
    inputs.addIntegerSpinnerCommandInput('pinionTeeth', 'Pinion teeth', 6, 2000, 1, int(s['pinion_teeth']))

    inputs.addValueInput('module', 'Module (mm)', 'mm',
                         adsk.core.ValueInput.createByReal(s['module_mm'] * 0.1))

    # Feature width: switchable absolute / percent.
    wmode = inputs.addButtonRowCommandInput('widthMode', 'Tooth width mode', False)
    wmode.listItems.add('Absolute', not s['width_is_percent'])
    wmode.listItems.add('Percent', s['width_is_percent'])
    fw = inputs.addValueInput('featureWidth', 'Feature width', 'mm',
                              adsk.core.ValueInput.createByReal(s['feature_width_mm'] * 0.1))
    fwp = inputs.addValueInput('featureWidthPct', 'Feature width %', '',
                               adsk.core.ValueInput.createByReal(s['feature_width_pct']))
    fw.isVisible = not s['width_is_percent']
    fwp.isVisible = s['width_is_percent']

    # Clearance: switchable absolute / percent.
    cmode = inputs.addButtonRowCommandInput('clearanceMode', 'Clearance mode', False)
    cmode.listItems.add('Absolute', not s['clearance_is_percent'])
    cmode.listItems.add('Percent', s['clearance_is_percent'])
    cl = inputs.addValueInput('clearance', 'Clearance', 'mm',
                              adsk.core.ValueInput.createByReal(s['clearance_mm'] * 0.1))
    clp = inputs.addValueInput('clearancePct', 'Clearance %', '',
                               adsk.core.ValueInput.createByReal(s['clearance_pct']))
    cl.isVisible = not s['clearance_is_percent']
    clp.isVisible = s['clearance_is_percent']

    # Advanced group.
    adv = inputs.addGroupCommandInput('advanced', 'Advanced')
    adv.isExpanded = False
    a = adv.children
    a.addValueInput('addendumFactor', 'Addendum factor', '',
                    adsk.core.ValueInput.createByReal(s['addendum_factor']))
    a.addValueInput('dedendumFactor', 'Dedendum factor', '',
                    adsk.core.ValueInput.createByReal(s['dedendum_factor']))
    a.addIntegerSpinnerCommandInput('resolution', 'Resolution (steps)', 8, 200, 1, int(s['resolution']))

    inputs.addTextBoxCommandInput('errMsg', '', '', 2, True).isFullWidth = True

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile commands/generateGears/entry.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "feat(ui): full dialog inputs"
```

- [ ] **Step 4: Manual Fusion check (record result)** — reload the add-in; confirm all inputs render and the absolute/percent fields show/hide per the button rows' initial state.

---

## Task 16: Input-changed (mode toggles) and validation

**Files:**
- Modify: `commands/generateGears/entry.py`

- [ ] **Step 1: Replace `command_input_changed` and `command_validate`**

```python
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs
    changed = args.input
    if changed.id == 'widthMode':
        is_pct = inputs.itemById('widthMode').selectedItem.name == 'Percent'
        inputs.itemById('featureWidth').isVisible = not is_pct
        inputs.itemById('featureWidthPct').isVisible = is_pct
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct


def _read_inputs(inputs):
    """Collect dialog values into a gear_math.GearInputs (all mm). Raises ValueError."""
    module_mm = inputs.itemById('module').value / 0.1          # cm -> mm
    circular_pitch = 3.141592653589793 * module_mm

    width_is_pct = inputs.itemById('widthMode').selectedItem.name == 'Percent'
    feature_width_mm = settings.resolve_length(
        width_is_pct,
        abs_mm=inputs.itemById('featureWidth').value / 0.1,
        pct=inputs.itemById('featureWidthPct').value,
        basis_mm=circular_pitch)

    clr_is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
    clearance_mm = settings.resolve_length(
        clr_is_pct,
        abs_mm=inputs.itemById('clearance').value / 0.1,
        pct=inputs.itemById('clearancePct').value,
        basis_mm=feature_width_mm)

    adv = inputs.itemById('advanced').children
    return gear_math.GearInputs(
        wheel_teeth=inputs.itemById('wheelTeeth').value,
        pinion_teeth=inputs.itemById('pinionTeeth').value,
        module_mm=module_mm,
        feature_width_mm=feature_width_mm,
        clearance_mm=clearance_mm,
        addendum_factor=adv.itemById('addendumFactor').value,
        dedendum_factor=adv.itemById('dedendumFactor').value,
        resolution=adv.itemById('resolution').value,
    )


def command_validate(args: adsk.core.ValidateInputsEventArgs):
    inputs = args.inputs
    err = inputs.itemById('errMsg')
    try:
        gi = _read_inputs(inputs)
        gear_math.validate_inputs(gi)
        err.text = ''
        args.areInputsValid = True
    except ValueError as e:
        err.text = str(e)
        args.areInputsValid = False
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile commands/generateGears/entry.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "feat(ui): mode toggles and live validation"
```

- [ ] **Step 4: Manual Fusion check (record result)** — toggle Absolute/Percent for both width and clearance; set pinion teeth to 5 and confirm an inline error appears and OK disables.

---

## Task 17: Execute — generate the sketches and persist settings

**Files:**
- Modify: `commands/generateGears/entry.py`

- [ ] **Step 1: Replace `command_execute`**

```python
def _resolve_target(inputs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    sel = inputs.itemById('target')
    if sel.selectionCount == 1:
        entity = sel.selection(0).entity
        if isinstance(entity, adsk.fusion.Occurrence):
            return entity.component
        return entity  # a Component (root)
    return design.activeComponent


def _persist_settings(inputs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    s = settings.defaults()
    s.update({
        'wheel_teeth': inputs.itemById('wheelTeeth').value,
        'pinion_teeth': inputs.itemById('pinionTeeth').value,
        'module_mm': inputs.itemById('module').value / 0.1,
        'width_is_percent': inputs.itemById('widthMode').selectedItem.name == 'Percent',
        'feature_width_mm': inputs.itemById('featureWidth').value / 0.1,
        'feature_width_pct': inputs.itemById('featureWidthPct').value,
        'clearance_is_percent': inputs.itemById('clearanceMode').selectedItem.name == 'Percent',
        'clearance_mm': inputs.itemById('clearance').value / 0.1,
        'clearance_pct': inputs.itemById('clearancePct').value,
        'addendum_factor': inputs.itemById('advanced').children.itemById('addendumFactor').value,
        'dedendum_factor': inputs.itemById('advanced').children.itemById('dedendumFactor').value,
        'resolution': inputs.itemById('advanced').children.itemById('resolution').value,
    })
    attr = design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
    if attr:
        attr.value = settings.to_json(s)
    else:
        design.attributes.add(ATTR_GROUP, ATTR_NAME, settings.to_json(s))


def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    try:
        gi = _read_inputs(inputs)
        pair = gear_math.build_gear_pair(gi)
        target = _resolve_target(inputs)
        sketch_builder.build_pair(target, pair)
        _persist_settings(inputs)
        futil.log(f'{CMD_NAME}: generated {pair.wheel.teeth}T / {pair.pinion.teeth}T')
    except Exception:
        futil.handle_error('command_execute', show_message_box=True)
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile commands/generateGears/entry.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Run the full pure-Python suite (nothing regressed)**

Run: `python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "feat(ui): execute generates sketches and persists settings"
```

---

## Task 18: Manual Fusion acceptance + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Perfect Print Gears (Fusion 360 add-in)

Generates Steve Peterson's "Perfect Print" gear pairs (a 3D-print-optimized
cycloidal profile) as **sketches** — a matched wheel + pinion — drawn into a
component you select. No bodies are created; extrude and finish them yourself.

## Install
1. Copy this folder to your Fusion add-ins directory, or run it in place.
2. Fusion → **Utilities → Add-Ins → Scripts and Add-Ins** → **Add-Ins** tab →
   green **+** → select this folder → **Run**.
3. The command appears under **Solid → Create → Generate Perfect Print Gears**.

## Use
Set wheel/pinion teeth, module (mm), feature width, and clearance, pick a target
component, and click OK. Two sketches are created in meshing layout.

## Develop / test
The geometry engine is pure Python and unit-tested without Fusion:

```
python -m pytest tests/ -v
```
````

- [ ] **Step 2: Run the full automated suite one last time**

Run: `python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 3: Manual Fusion acceptance checklist (perform in Fusion; this is the real end-to-end verification)**

1. Load the add-in (steps in README). No errors on load.
2. Create a new design; run **Generate Perfect Print Gears**.
3. Defaults (50/10, module 0.8, width 2.388 mm, clearance 0.1 mm) → OK.
4. Confirm **two sketches** appear (`PPG Wheel 50T`, `PPG Pinion 10T`) in the
   target component — and **no new components or bodies** were created.
5. Confirm each sketch has: a center point, three construction circles
   (pitch/root/addendum), and a closed toothed outline.
6. Confirm the two gears are positioned **meshing** (pitch circles tangent on the x-axis).
7. Extrude one wheel tooth profile region to confirm the outline is closed/valid.
8. Re-run the command → confirm the dialog is **pre-filled** with the last-used values.
9. Try an invalid combo (pinion teeth 5) → confirm inline error + OK disabled.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README and manual acceptance checklist"
```

- [ ] **Step 5: Push**

```bash
git push
```

---

## Self-review notes (for the implementer)

- **Spec coverage:** sketches-only output (Tasks 10–11, 17), two gears (11), target component not new components (17 `_resolve_target`), full outline + center point + construction circles (10), fitted spline tip (6/10), module-mm pitch (15), switchable width & clearance (13/15/16), rounded pinion tip (7), auto heights + override factors (6/7/15), meshing layout (8/11), settings persistence (12/17), validation (3/16), Peterson golden test (9). All present.
- **The one empirical step:** Task 5 Step 4 — the conjugation rotation signs. The test pins the correct combination; do not skip running it.
- **Engine units are mm; Fusion is cm.** Conversions live only in `sketch_builder.py` and the `entry.py` value-input reads (`/ 0.1`, `* 0.1`). The engine never sees cm.
- **If a generated tooth looks wrong in Fusion** but `pytest` passes, the likely culprits are (a) the clearance direction in `build_wheel_tooth`, or (b) pinion phase (`base_angle`) in `build_gear_pair` — both are isolated and adjustable without touching the conjugation core.
