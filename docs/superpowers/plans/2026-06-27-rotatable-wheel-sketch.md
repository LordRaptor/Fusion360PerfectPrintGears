# Rotatable Wheel Sketch Implementation Plan (REVISED — control-point spline)

> **For agentic workers:** Execute task-by-task. Engine tasks are TDD (pure
> Python, `pytest`). Fusion tasks are verified manually by the user in Fusion
> (the layer imports `adsk` and cannot be unit-tested here) — propose ONE change,
> user tests, confirm, proceed. Research the Fusion API before using a call.

**Goal:** Make the wheel sketch fully constrained *and* rotatable by re-representing
the tip as a control-point (Bézier) spline, with a user toggle for a tangent tip
join. Prerequisite for rotate-the-arrangement.

**Why revised:** a fitted spline has tangent/curvature handle DOF that only
`isFixed` removes (absolute → can't rotate). A control-point spline has no handles,
so constraining its control points fully constrains it AND lets it rotate. See the
spec for the full rationale and fidelity numbers (4-CP free Bézier = 3 µm).

**Working state:** branch `feat/wheel-rotation`. `isFixed` already removed and a
(now-superseded) interior-fit-point distance-dim approach is in `sketch_builder.py`
— it will be replaced by control-point constraints in Task 4.

---

## Task 1 — Engine: Bézier evaluation + fit helpers (TDD)

**Files:** `core/gear_math.py`, `tests/test_gear_math.py`

- [ ] Write failing tests: `_bezier_point`/`bezier_curve` reproduce endpoints and a
      known cubic midpoint; `fit_tip_bezier(locus, degree=3, tangent_join=False)`
      returns 4 control points, endpoints == locus ends, max deviation from the
      locus < 5 µm; `degree=5` returns 6 points; `tangent_join=True` makes
      control point 1 share the join's y (horizontal leave).
- [ ] Implement `_bezier_point(ctrl, t)`, `bezier_curve(ctrl, n)` (Bernstein), and
      `fit_tip_bezier(locus, degree, tangent_join)` (least-squares P1..P_{n-1},
      endpoints fixed; if `tangent_join`, fix CP1.y = CP0.y and fit only its x).
- [ ] `pytest tests/test_gear_math.py -q` → green. Commit.

## Task 2 — Engine: tip as 'cpspline' segment + densify + tangent input (TDD)

**Files:** `core/gear_math.py`, `tests/test_gear_math.py`, `tests/test_interference.py`

- [ ] `GearInputs` gains `tangent_join: bool = False`. `Segment` gains `degree: int
      = 0`; new `kind == 'cpspline'` (control points in `points`).
- [ ] `build_wheel_tooth`: `degree = 3 if inp.resolution <= 4 else 5`; fit the
      lower tip via `fit_tip_bezier(locus, degree, inp.tangent_join)`; upper =
      y-mirror of lower control points; emit both as `Segment('cpspline', ctrl,
      degree=degree)`.
- [ ] `densify_segments`: handle `'cpspline'` via `bezier_curve(s.points, n_spline)`.
- [ ] Update `test_gear_math` tip-structure tests: kinds now
      `['line','cpspline','cpspline','line']`; assert degree 3 / 4 control points
      at default resolution, degree 5 / 6 at resolution 6; drop the old
      `clamp_start/clamp_end` and `resolution-controls-fit-points` assertions
      (replace with a tip-fidelity assertion: densified tip within ~5 µm of the
      locus).
- [ ] `pytest tests/ -q` → all green, **including the interference guard at the
      noise floor** (print the measured penetration; expect ≤ current). Commit.

## Task 3 — Engine: settings (de)serialize the toggle (TDD)

**Files:** `core/settings.py`, `tests/test_settings.py`

- [ ] Failing test: round-trip a settings dict including `tangent_join`.
- [ ] Add `tangent_join` to settings (de)serialization with a default of `False`.
- [ ] `pytest tests/test_settings.py -q` → green. Commit.

## Task 4 — Fusion: draw control-point spline + constrain control points

**Files:** `core/sketch_builder.py` (manual Fusion test)

- [ ] Research: `SketchControlPointSplines.add(points, degree)` and
      `adsk.fusion.SplineDegrees` enum values (confirmed: `SplineDegreeThree`,
      `SplineDegreeFive`).
- [ ] `_draw_outline`: add `'cpspline'` → build an ObjectCollection of `Point3D`
      from the control points and call `sketchControlPointSplines.add(coll,
      SplineDegreeThree/Five)` per `seg.degree`.
- [ ] Wheel tip block: change `_lock_fit_points_to_frame` to operate on
      `controlPoints` (interior control points → distance dims to centre + apex);
      change the symmetry mirror loop from `fitPoints` to `controlPoints`. Keep the
      apex→centerline-end coincidence. `isFixed` stays removed.
- [ ] Compile (`compileall -q core`); USER tests in Fusion: wheel fully constrained
      (no handle DOF), tip shape correct, clean log. Commit.

## Task 5 — Fusion: drive wheel orientation by an angle dimension

**Files:** `core/sketch_builder.py` (manual Fusion test)

- [ ] Replace the centerline `horizontal` block with a horizontal construction
      reference line through the centre + an `addAngularDimension(centerline, ref,
      tp, True)` (default 0°). (Same as the prior plan's Task 2.)
- [ ] Compile; USER tests: geometry identical at 0°; editing the angle rotates the
      whole wheel without tearing; sketch stays fully constrained. Commit.

## Task 6 — Fusion: tangent-join dialog input

**Files:** `commands/generateGears/entry.py` (manual Fusion test)

- [ ] Add a boolean "Tangent tip join" checkbox (default off), persist via
      settings, pass to the build.
- [ ] Compile; USER tests: toggling it visibly changes the flank/tip join. Commit.

## Task 7 — Docs

**Files:** `README.md`, `PerfectPrintGears.manifest`, `docs/HANDOVER.md`

- [ ] README + manifest `description`: rotatable wheel + tangent toggle.
- [ ] HANDOVER §6: mark rotation prerequisite done; note the tip is now a
      control-point Bézier and why. Commit `[skip ci]`.

## Done criteria

- Wheel sketch fully constrained with **no `isFixed`** and **no handle DOF**;
  rotatable via the angle dimension without tearing.
- Tip is a degree-3/5 control-point Bézier matching the conjugate locus (~3 µm
  free); interference guard passes at the noise floor.
- Tangent toggle works end-to-end. Engine fully TDD'd; `pytest tests/ -q` green.
