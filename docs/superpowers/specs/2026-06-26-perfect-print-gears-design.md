# Perfect Print Gears — Fusion 360 Add-in (Project Meta-Spec)

**Date:** 2026-06-26
**Status:** Approved design — ready for implementation planning
**Author:** Christopher Schank (with Claude)

---

## 1. Purpose

A Fusion 360 add-in that generates **Perfect Print Gears** — the 3D-printing-optimized
cycloidal gear profile developed by Steve Peterson and documented in his *Clock Design
Guidelines* (Nov 2025), pp. 61–66.

Given a mating **wheel** (large gear) and **pinion** (small gear), the add-in produces the
two matched tooth profiles **as sketches** that the user can extrude and finish themselves.

### What makes these gears special
- The **pinion** working flanks are two **parallel straight lines**, each offset from a
  radial by half a chosen *feature width* (constant tooth thickness), capped by a free
  rounded tip. The feature width is decoupled from pitch and tuned to the printer.
- The **wheel** tip is **conjugate-generated** to match that specific pinion, giving
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
| **Curve type** | **Fitted spline** for the generated wheel-tip flanks |
| **Pitch input** | **Module** (mm) + tooth counts |
| **Feature (tooth) width** | Switchable **absolute length / % of circular pitch**, default absolute |
| **Clearance** | Switchable **absolute / %**, default absolute; applied by narrowing the wheel tooth |
| **Pinion tip** | Rounded semicircle (radius = half feature width) |
| **Tooth heights** | Root depths **auto** from clearance; optional addendum/dedendum override factors |
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
- Feature width `w`; circular pitch `CP = π·m`.

### 4.2 Tooth construction
Both gears have **width-`w` parallel flanks** — each working flank is a straight line
parallel to a gear radial, offset by `w/2`.
- **Pinion:** straight flanks + **rounded tip** (semicircle radius `w/2`). The tip is free
  (never contacts the wheel) and only needs to clear the wheel root.
- **Wheel:** straight flanks + **conjugate-generated tip** (the working surface), narrowed
  by the clearance value.

### 4.3 Conjugation — generating the wheel tip from the pinion flank
1. Define the pinion's working flank as a line at a reference instant: parallel to the
   pinion radial pointing toward the pitch point, offset `w/2` on the leading side.
2. For `k = 0 … K` (K = resolution steps spanning one pinion tooth pitch `2π/N_p`,
   step `Δ = (2π/N_p)/K`):
   - rotate the flank line about `O_p` by `θ_p = k·Δ`, **and**
   - rotate it about `O_w` by `θ_w = k·Δ / ratio` (opposite sense — Peterson's "rotate up").
   This freezes the meshing motion at K snapshots (Peterson's blue reference lines).
3. The wheel tip is the **envelope** tangent to that family of lines. Compute envelope
   points as the **intersection of consecutive lines** `L_k ∩ L_{k+1}` (robust; matches
   "draw a line along the curve defined by the reference lines").
4. Clip the envelope to the span from the **tooth centerline** to where it meets the
   **straight wheel flank** (≈ pitch circle), **mirror** about the centerline, and join to
   the flanks to form one complete wheel tooth.

### 4.4 Clearance & heights
- **Clearance:** narrow the wheel tooth by the clearance value (Peterson's "narrow the main
  gear") so the pair runs with play. Absolute or % of feature width.
- **Root (slot) depth:** auto-computed so each gear's tooth space clears the mating tooth's
  tip plus clearance. Optional addendum/dedendum override factors (default = auto).
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
The formulas are authored here, but validated against Peterson's documented worked example
(50T wheel / 10T pinion, 5:1) and additional ratios in `tests/`. This gives a concrete
"matches the document" check rather than relying on faith in the math. If a generated gear
ever looks wrong, these tests are the first debugging step.

---

## 5. Command & dialog (`commands/generateGears/entry.py`)

Single command **"Generate Perfect Print Gears"**, added to the **Solid → Create** panel
(button promoted). Dialog inputs:

- **Target component** — selection input; defaults to the active component. Both sketches
  are drawn here.
- **Wheel teeth** / **Pinion teeth** — integer spinners (defaults 50 / 10).
- **Module** — value input, mm (default 0.8).
- **Feature width** — switchable: absolute length (document units, default 2.388 mm) **or**
  % of circular pitch; the disabled field shows the converted value live.
- **Clearance** — switchable absolute / % the same way (default ~0.1 mm).
- **Advanced (collapsible):** addendum factor, dedendum factor (default = auto), and
  **resolution** (envelope step count, default ~24).

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
  - feature width small enough that pinion teeth don't overlap (checked against the
    tooth-space arc at the pitch circle);
  - clearance < feature width.
  - Inline error message in the dialog; OK disabled until valid.
- All `adsk` calls wrapped via the template's `handle_error`.
- The pure engine raises plain `ValueError`s with clear messages (surfaced if hit at runtime).

---

## 8. Testing

- **`tests/test_gear_math.py`** — plain Python (`python -m pytest`), no Fusion:
  - Peterson 50T/10T golden checks: center distance, ratio, tip-envelope endpoints &
    monotonicity, tooth/feature-width geometry;
  - additional ratios (e.g. 60/8, 40/12);
  - validation/edge cases (overlap, clearance bounds).
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