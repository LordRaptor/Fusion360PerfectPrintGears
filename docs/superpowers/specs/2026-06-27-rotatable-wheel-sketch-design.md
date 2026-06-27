# Rotatable wheel sketch — design

**Date:** 2026-06-27
**Status:** Approved (brainstorm). **Revised** mid-implementation — the original
"constraint-only" plan hit a fundamental Fusion limitation; see "Why this changed".

## Goal

Make the **wheel** sketch rotate cleanly as a rigid body, driven by a single
editable angle dimension — the prerequisite for the handover §6
"rotate-the-arrangement" feature. To get there, re-represent the wheel tip with a
curve type that can be **fully constrained relative to a movable frame** (a
control-point spline), and add a user toggle for a tangent vs. faithful tip join.

## Why this changed (the fitted-spline wall)

The original plan was constraint-only: remove `isFixed`, lock the fitted spline's
fit points relative to the centerline, swap `horizontal` for an angle dimension.
In Fusion testing this failed at a fundamental point: a **fitted spline carries
per-fit-point tangent/curvature handle degrees of freedom** (`activateTangentHandle`
/ `activateCurvatureHandle`) that fit-point constraints do **not** remove. Only
`isFixed` removes them — and `isFixed` pins to absolute sketch coordinates, so the
tip won't rotate. Therefore a fitted-spline tip cannot be both fully constrained
*and* rotatable.

A **control-point spline** (`SketchControlPointSpline`) is defined entirely by its
control points (the control frame) and a fixed degree — it has **no tangent/curvature
handles**. Constrain every control point relative to the centerline frame and the
curve is fully constrained and rotates rigidly with the frame. That is the fix.

## Approach

Three layers, engine-first (testable) then Fusion (manual test).

### 1. Engine (`core/gear_math.py`) — represent the tip as a Bézier

- Add `fit_tip_bezier(locus, degree, tangent_join)`: least-squares-fit a single
  clamped Bézier to the dense conjugate tip locus (the existing
  `wheel_tip_points` envelope — **the conjugate math is untouched**). Endpoints are
  clamped exactly to the flank join and the apex; interior control points are free
  (or, with `tangent_join`, the first interior point is constrained so the curve
  leaves the join horizontally). Returns `degree+1` control points.
  - **degree 3 → 4 control points; degree 5 → 6 control points.** These are the
    only degrees Fusion's `SketchControlPointSplines.add` accepts, and a single
    Bézier of either degree has a **forced knot vector** (no interior knots), so
    the engine's control points reproduce *exactly* in Fusion — no knot ambiguity.
- Add Bézier evaluation helpers (`_bezier_point`, `bezier_curve`).
- `Segment` gains a `degree` field and a new `kind = 'cpspline'` (control points
  stored in `points`).
- `build_wheel_tooth` emits the lower and upper tip as `'cpspline'` segments (the
  upper is the y-mirror of the lower control points).
- `densify_segments` evaluates `'cpspline'` via `bezier_curve`, so the interference
  test (`closed_gear_polygon`) validates the **actual drawn shape** (unifying the
  drawn and validated curve — previously the fitted spline and the engine clamped
  cubic were separate approximations).

**Fidelity (measured against the true conjugate locus, default 50/10, m=1.5):**

| Tip representation | Max deviation |
|---|---|
| Old engine clamped-cubic (4 fit points) | 19.8 µm |
| **4-CP Bézier, free (tangent OFF)** | **3.0 µm** |
| 4-CP Bézier, tangent ON (horizontal at join) | 40.1 µm |

The free fit is *more* faithful than the old representation and preserves the real
~12° flank/tip corner (handover §3). Forcing the tangent smooths that corner and
deviates more — hence it is an opt-in toggle, not the default.

### 2. Engine/inputs — the tangent toggle and degree

- `GearInputs` gains `tangent_join: bool = False` (default = faithful free fit).
- Tip degree: derived from the existing `resolution` input — `degree = 3 if
  resolution <= 4 else 5` (4 vs 6 control points). This reuses the existing knob as
  the "number of control points" exploration lever the user asked for; default
  `resolution = 4` → degree 3 → the validated 3 µm case.
- `core/settings.py` (de)serializes `tangent_join`.

### 3. Fusion (`core/sketch_builder.py`) — draw + constrain + rotate

- `_draw_outline` draws `'cpspline'` via
  `sketch.sketchCurves.sketchControlPointSplines.add(controlPoints, degree_enum)`
  (`SplineDegrees.SplineDegreeThree` / `SplineDegreeFive`).
- Wheel tip: remove `isFixed`. Constrain the lower spline's **control points**
  relative to the centerline frame — interior control points dimensioned to the
  centre and the apex (both on the centerline, so they rotate with it); the end
  control points are the curve ends (Fusion auto-coincides the drawn joins; the
  apex end is coincident to the centerline end). Mirror the upper spline's control
  points to the lower per point by symmetry about the centerline. No handle DOF →
  fully constrained.
- Replace the centerline `horizontal` with an **angular dimension** between the
  centerline and a horizontal construction reference line through the centre
  (default 0° = today's orientation). Editing it rotates the whole wheel; the
  circular pattern carries it to every tooth.
- The pinion is unchanged (tangent-arc tip + existing angular phase dim).

### 4. Dialog (`commands/generateGears/entry.py`)

- Add a **"Tangent tip join"** boolean checkbox input (default unchecked),
  persisted via settings. Wire it into the build.

## Validation

- `pytest tests/ -q` — engine changes are TDD'd:
  - `fit_tip_bezier` returns `degree+1` control points; endpoints equal the locus
    ends; deviation from the locus is < 5 µm (free) and the tangent variant leaves
    the join horizontal.
  - `build_wheel_tooth` emits `['line','cpspline','cpspline','line']`.
  - **The interference guard must still pass at the noise floor** (re-run; expect
    ≤ current, since the Bézier tracks the envelope better).
- Fusion (manual, user): wheel builds fully constrained (no handle DOF), tip shape
  correct; rotating via the angle dimension does not tear; the tangent toggle
  visibly changes the join.

## Docs

Update `README.md` and the manifest `description` for the new tangent toggle and
the rotatable wheel. Update `docs/HANDOVER.md` §6.

## Out of scope (future)

- Exposing the rotation angle in the dialog / rotating wheel + pinion together
  (the rest of rotate-the-arrangement).
- Degrees other than 3 and 5, or multi-segment tip splines (single Bézier at
  degree 3/5 is exact in Fusion and already < 3 µm).
