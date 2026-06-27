# Perfect Print Gears — Fusion 360 Add-in (Project Meta-Spec)

**Date:** 2026-06-26 (geometry method revised 2026-06-27)
**Status:** Approved design; conjugation method rebuilt and validated (interference ~0)
**Author:** Christopher Schank (with Claude)

---

## 1. Purpose

A Fusion 360 add-in that generates **Perfect Print Gears** — the 3D-printing-optimized
cycloidal gear profile developed by Steve Peterson and documented in his *Clock Design
Guidelines* (Nov 2025), pp. 61–66.

Given a mating **wheel** (large gear) and **pinion** (small gear), the add-in produces the
two matched tooth profiles **as sketches** that the user can extrude and finish themselves.

### What makes these gears special
- Both gears have **constant-width** teeth: each working flank is a **straight line parallel
  to a gear radial**, offset by half the *feature width*. This decouples the tooth *shape*
  from an involute and keeps it printable.
- The **feature width is derived from the module**: `w = TOOTH_FRACTION · CP` where
  `CP = π·module` is the circular pitch. `TOOTH_FRACTION` (default 0.5 = equal tooth and
  space) is the user's **circumferential-backlash** knob; the width is shown read-only.
  Coupling it to the module means it can never violate the meshing constraint.
- The **pinion** tip is a free rounded cap (semicircle radius = half the feature width); it
  never contacts the wheel.
- The **wheel** tip is **conjugate-generated** to match that specific pinion flank — built as
  the envelope of the pinion flank under rolling (Peterson's method), giving
  constant-velocity, low-friction, bidirectional meshing that prints cleanly.
- Consequence (inherent to the method): **every wheel/pinion combination is unique** and
  must be generated for its specific mating partner.

---

## 2. Scope & key decisions

| Decision | Choice |
|---|---|
| **Output** | Sketches only — no bodies, no extrudes, no joints/motion links |
| **Count** | Two sketches per run — the wheel and its matching pinion |
| **Destination** | Drawn into a **user-selected existing component** (never auto-creates components) |
| **Sketch contents** | Full toothed outline (all teeth, one closed profile) + center **point** + construction circles (pitch, root, addendum) |
| **Curve type** | **Fitted spline** for the generated wheel tip, ~4 fit points per half, with a horizontal **start-tangent constraint** at the flank join (smooth), sharp apex |
| **Pitch input** | **Module** (mm) + tooth counts |
| **Feature (tooth) width** | **Derived** from module: `w = TOOTH_FRACTION · π·module`. Shown **read-only** (info), not a user input |
| **Tooth fraction** | User input `TOOTH_FRACTION` (default 0.5). Controls **circumferential backlash** = `CP·(1 − 2·TOOTH_FRACTION)`; flank-to-flank play |
| **Clearance** | Switchable **absolute / %**, default absolute; **radial** tip-to-root play (distinct from tooth-fraction backlash) |
| **Pinion tip** | Rounded semicircle (radius = half feature width); flanks **end on the pinion pitch circle** |
| **Tooth heights** | Root depths **auto** from the *mating* tooth's tip height + clearance; optional addendum/dedendum override factors |
| **Layout** | **Meshing** — wheel at origin, pinion at center distance, pitch circles tangent |
| **Settings persistence** | **Yes** — last-used inputs cached on the document, pre-filled next run |

### Explicitly out of scope (v1)
- Generating solid bodies / extrudes / fillets / center bores / spokes.
- Auto-creating components.
- Live in-canvas preview (generation happens on OK). Noted as a possible later addition.
- Gear trains / multi-mesh automation (user runs the command once per mesh).
- Helical, bevel, or internal gears.

---

## 3. Architecture

Approach: modern add-in template **+ a pure, Fusion-independent geometry core**, so the
risky conjugation math is unit-testable without Fusion running.

```
Fusion360 PerfectPrintGears/
├── PerfectPrintGears.manifest      # add-in manifest (name, id, version, runOnStartup)
├── PerfectPrintGears.py            # run(context)/stop(context) entry
├── config.py                       # ADDIN_NAME, COMPANY_NAME, ids, DEBUG flag
├── commands/
│   ├── __init__.py                 # registers command list (start/stop fan-out)
│   └── generateGears/
│       ├── __init__.py
│       ├── entry.py                # command def, dialog inputs, events, settings persistence
│       └── resources/              # button icons (16/32/64)
├── core/
│   ├── gear_math.py                # PURE python, no adsk import — the conjugation engine
│   └── sketch_builder.py           # thin Fusion layer: draws point/curve data into a sketch
├── lib/
│   └── fusionAddInUtils/           # ported event/log/error utils (from the template)
└── tests/
    └── test_gear_math.py           # runs in plain python (pytest), no Fusion
```

**Dependency direction (one-way):**
`entry.py` → reads inputs → calls `gear_math` (pure) → passes plain point data to
`sketch_builder` → draws into Fusion. `gear_math` imports no `adsk`; `sketch_builder` does
no math; `tests/` import only `gear_math`.

### Unit responsibilities
- **`gear_math.py`** — given parameters, returns plain geometric data (point lists, radii,
  center distance). The conjugation engine. No Fusion types.
- **`sketch_builder.py`** — given that data and a target component, creates the two sketches
  (spline + lines + circles + circular pattern). No math.
- **`entry.py`** — dialog, command inputs, validation, settings persistence; orchestrates
  `gear_math` → `sketch_builder`.

---

## 4. Geometry engine (`core/gear_math.py`)

### 4.1 Frame & definitions (wheel-centered)
- Wheel center `O_w = (0, 0)`; pinion center `O_p = (C, 0)`.
- Center distance `C = m·(N_w + N_p) / 2`.
- Pitch radii `R_w = m·N_w / 2`, `R_p = m·N_p / 2`.
- Pitch point on the x-axis at `(R_w, 0)` (tangent of the two pitch circles).
- Speed ratio `ratio = N_w / N_p` (pinion turns `ratio×` faster).
- Circular pitch `CP = π·m`; **feature width `w = TOOTH_FRACTION · CP`** (derived); `half_w = w/2`.

### 4.2 Tooth construction
Both gears have **width-`w` parallel flanks** — each working flank is a straight line
parallel to a gear radial, offset by `half_w`.
- **Pinion:** straight flanks ending **on the pinion pitch circle**, capped by a free
  **rounded tip** (semicircle radius `half_w`, centered just inside the pitch circle). The
  tip never contacts the wheel; it only needs to clear the wheel root.
- **Wheel:** straight (radial-offset) flanks + **conjugate-generated tip** (the working
  surface). The flanks end where the tip envelope meets the flank level (≈ pitch circle).

### 4.3 Conjugation — generating the wheel tip from the pinion flank
The method is Peterson's envelope, made rigorous with **one consistent kinematic model used
for both generation and verification** (a single parameter `tau` — eliminating the
phase/sign mismatch that defeated earlier attempts).

1. **Contacting flank.** Place the pinion tooth so its top flank meets the wheel bottom
   flank at point `Q` on the pinion pitch circle. The required pinion tooth angle is the
   closed form `2·asin(half_w / R_p)`. This contacting flank is the generator.
2. **Rolling motion (single parameter `tau`).** For the meshing motion, the pinion rotates
   `+tau` about `O_p` and the wheel `−tau/ratio` about `O_w` (external pair → opposite
   sense). Equivalently, express the world pinion flank in the wheel's body frame by rotating
   it `+tau` about `O_p` then `+tau/ratio` about `O_w` ("rotate up"). Sweep `tau` over one
   pinion tooth pitch.
3. **Envelope = foot of perpendicular.** For a *straight* flank the contact point is exactly
   the **foot of the perpendicular from the pitch point `P` onto the flank line** (law of
   gearing). Carry that contact point into the wheel frame (same `tau` rotation). This is the
   wheel tip locus — exact and robust, no noisy intersection extraction.
   - *Cross-check (not the production path):* the same curve is the envelope obtained from
     `L_k ∩ L_{k+1}` of the flank family; the two agree to ~0.01 mm and serve as a test.
4. **Trim & mirror.** Trim the locus from the flank level (`y = −half_w`, ≈ `Q`) up to the
   **centerline apex** (`y = 0`); mirror about the centerline. The apex is left a **sharp
   point** (the printer smooths it).
5. **Spline representation.** Fit the half-tip with a clamped cubic spline of ~4 fit points,
   with the **start tangent horizontal** (clamp `y'(join)=0`) so it leaves the join tangent
   to the straight flank — removing the small flank/tip corner. The engine emits the fit
   points + the horizontal start-tangent for Fusion's fitted spline.

### 4.4 Backlash, clearance & heights
- **Backlash (circumferential):** set by `TOOTH_FRACTION` (< 0.5 → thinner teeth → more
  flank-to-flank play); `backlash = CP·(1 − 2·TOOTH_FRACTION)`.
- **Clearance (radial):** tip-to-root play, so tips don't bottom out. Absolute or % of
  feature width. Distinct from backlash.
- **Root (slot) depth:** auto-computed so each gear's root clears the **mating** tooth's tip
  height + clearance (wheel root clears the pinion cap; pinion root clears the wheel tip
  apex). Optional addendum/dedendum override factors (default = auto).
- Root form: straight-line bottom joining the flanks (revisit arc bottom later if a printer
  prefers it).

### 4.5 Engine output (plain data — no Fusion types)
For each gear:
- ordered tip-envelope sample points (for the spline),
- straight flank endpoints and root points for one tooth,
- tooth count `N`,
- construction radii (pitch, root, addendum),
- gear center offset (`0` for wheel, `C` for pinion).

`sketch_builder` consumes this to draw spline + lines + circles and array `N` times.

### 4.6 Correctness strategy
The formulas are validated against Peterson's worked example (50T/10T, 5:1) and other ratios
in `tests/`. **Sanity assertions are not sufficient** — a plausible-but-wrong tip passes them
(this is exactly how a wrong curve shipped before). The suite therefore includes a
**conjugacy / interference test**: assemble both gears as **closed** polygons (with
root-bridge arcs), roll them through a full mesh cycle under the *same* kinematic model used
to generate the tip (pinion `+tau`, wheel `−tau/ratio`), and assert the **penetration depth**
(point-in-polygon containment × distance-to-boundary, **not** nearest-point distance) stays
below a small tolerance over the whole cycle. Required test hygiene (each caused a false
result historically): closed polygons; build each gear in local coords then a single
placement transform (no double translation); penetration depth not nearest distance; arcs
sampled **through the mid point**; generation and test share one kinematic model. Validated
result: ~0 µm at realistic `TOOTH_FRACTION` (the residual is spline/sampling approximation,
confirmed by a fit-point sensitivity sweep), versus 220–410 µm for the earlier methods.

---

## 5. Command & dialog (`commands/generateGears/entry.py`)

Single command **"Generate Perfect Print Gears"**, added to the **Solid → Create** panel
(button promoted). Dialog inputs:

- **Target component** — selection input; defaults to the active component. Both sketches
  are drawn here.
- **Wheel teeth** / **Pinion teeth** — integer spinners (defaults 50 / 10).
- **Module** — value input, mm (default 1.5; 0.8 was the original default but is too small —
  with the standard tooth fraction it left no room for a printable tooth).
- **Tooth fraction** — value input (default 0.5). The backlash knob: `< 0.5` thins the teeth
  for circumferential play. Feature width `= TOOTH_FRACTION · π·module` is shown **read-only**
  (info), recomputed live as module/fraction change.
- **Clearance** — switchable absolute / % the same way (default ~0.1 mm). Radial tip-to-root
  play, independent of tooth fraction.
- **Advanced (collapsible):** addendum factor, dedendum factor (default = auto), and
  **resolution** (wheel-tip spline fit points per half, default 4).

**Settings persistence:** on OK, serialize all inputs to JSON and store as a document
attribute group `PerfectPrintGears` / `Settings`; on open, pre-fill from it if present.

**Units note:** Module is always entered in mm (a metric concept). Feature width and
clearance follow document length units. Fusion works internally in cm — the layer converts.

**Live preview:** off for v1; generation runs on OK.

---

## 6. Sketch builder & output (`core/sketch_builder.py`)

Given the engine's point data and the target component, for **each** gear it creates one
sketch and draws:
- center **point** at the gear origin;
- **construction circles**: pitch, root, addendum (`isConstruction = True`);
- one tooth: tip **fitted spline** + straight flank **lines** + root lines;
- **circular pattern** of the tooth curves `N` times into a single closed outline.

Two sketches total, named e.g. `PPG Wheel 50T` and `PPG Pinion 10T`, in **meshing layout**
(wheel at origin, pinion at center distance `C` on the x-axis). Uses `isComputeDeferred`
while adding curves for speed. No extrudes, bodies, or joints.

---

## 7. Validation & error handling

- Require an active design and a selected/active target component.
- `validateInputs`:
  - pinion teeth ≥ ~6, wheel teeth ≥ pinion teeth;
  - module > 0;
  - `0 < TOOTH_FRACTION < 0.5` (≥ 0.5 leaves no circumferential gap; the feature width is
    derived from it, so the old "teeth overlap" case is now structurally impossible);
  - clearance ≥ 0 and clearance < feature width.
  - Inline error message in the dialog; OK disabled until valid.
- All `adsk` calls wrapped via the template's `handle_error`.
- The pure engine raises plain `ValueError`s with clear messages (surfaced if hit at runtime).

---

## 8. Testing

- **`tests/test_gear_math.py`** — plain Python (`python -m pytest`), no Fusion:
  - Peterson 50T/10T golden checks: center distance, ratio, tip endpoints & monotonicity,
    tooth geometry; pinion tooth angle `= 2·asin(half_w/R_p)`;
  - **two-method envelope agreement**: foot-of-perpendicular vs consecutive-intersection
    agree within ~0.01 mm;
  - **conjugacy / interference guard** (the critical test): closed polygons, single
    kinematic model, penetration **depth** below tolerance over a full mesh cycle, at a
    realistic `TOOTH_FRACTION`. Sanity checks alone are explicitly insufficient.
  - additional ratios (e.g. 60/8, 40/12);
  - validation/edge cases (`TOOTH_FRACTION` and clearance bounds).
  - This is where TDD happens.
- **Manual Fusion check** (user-run, with a provided checklist): load the add-in, generate
  50T/10T, confirm the two outlines visibly mesh and extrude cleanly. (Fusion cannot be
  driven headless, so this final acceptance step is manual.)

---

## 9. References

- Steve Peterson, *Clock Design Guidelines* (Nov 2025), pp. 61–66 — "Perfect Print Gears".
- Existing add-ins studied: *FusionCycloidalGears* (Matt Keveney) — template structure,
  pitch/unit handling, both-gear generation; *SpurGear* (Autodesk sample) — settings
  persistence, spline tooth drawing, `isComputeDeferred`, design-intent handling.
- Fusion 360 Python API:
  [Add-in template](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm),
  [Custom commands](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Commands_UM.htm),
  [Command inputs sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CommandInputsSample_Sample.htm).