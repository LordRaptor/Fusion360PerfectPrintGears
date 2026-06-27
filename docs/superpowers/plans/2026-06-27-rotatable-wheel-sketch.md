# Rotatable Wheel Sketch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the wheel sketch rotate cleanly via a single angle dimension by replacing the tip spline's `isFixed` with relative locks — the prerequisite for rotate-the-arrangement.

**Architecture:** Wheel-only, constraint-only rework in `core/sketch_builder.py`. Remove `lower_spline.isFixed`; coincide the flank/tip joins that `isFixed` was implicitly holding; lock each interior tip fit point relative to the centerline frame with two point-to-point distance dimensions (to the centre and to the apex, both on the centerline, so the point rotates with the frame); replace the centerline `horizontal` with an angular dimension off a horizontal reference line (default 0°). The pure engine (`core/gear_math.py`) and the pinion are untouched.

**Tech Stack:** Fusion 360 Python API (`adsk`), Python 3, pytest (engine regression guard only).

---

## Working-mode override (READ FIRST)

This project's instructions (CLAUDE.md, handover §7) take priority over the writing-plans skill's default TDD-per-step cadence:

- **The Fusion layer cannot be unit-tested in this repo** — `core/sketch_builder.py` imports `adsk`, which only exists inside Fusion. Do **not** write pytest tests for sketch constraints; they cannot run.
- **Verification is manual, in Fusion, by the user, one step at a time.** Propose ONE change, the user loads the add-in and reports what Fusion shows (fully constrained = black; under-constrained = blue points; over-constrained = a solver error), then proceed.
- **`pytest` is a regression guard only.** The engine is untouched, so all 38 tests must keep passing; run it once per task as a safety net, not as the feature test.
- **Research the Fusion API before using a call** (WebFetch the help page). Several plausible-but-wrong signatures exist (handover §4).
- Commit only at coherent milestones (a fully-constrained sketch), never an intermediate under-constrained state.

## File Structure

- **Modify:** `core/sketch_builder.py`
  - Add two module-level helpers after `_constrain_flanks` (ends ~line 157) and before `build_gear`: `_coincide_spline_join`, `_lock_fit_points_to_frame`.
  - Replace the wheel-tip locking block (currently lines ~313–361): drop `isFixed`, call the two helpers, keep the existing per-fit-point symmetry mirror.
  - Replace the centerline `horizontal` block (currently lines ~303–307) with an angular-dimension block.
- **Modify:** `docs/HANDOVER.md` — mark the rotation prerequisite done in §6.
- **No engine changes.** `core/gear_math.py`, tests, and the pinion path are unchanged.

---

## Task 1: Lock the wheel tip relative to the centerline frame (remove `isFixed`)

**Files:**
- Modify: `core/sketch_builder.py` (add 2 helpers; replace wheel-tip block ~313–361)

- [ ] **Step 1: Baseline regression — confirm the engine is green before touching anything**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed`. (Establishes that anything that later breaks is in the Fusion layer, not the engine.)

- [ ] **Step 2: Research the dimension API**

WebFetch the Fusion help for `SketchDimensions.addDistanceDimension` and confirm the signature is
`addDistanceDimension(pointOne, pointTwo, orientation, textPoint, isDriving=True)` and that
`adsk.fusion.DimensionOrientations.AlignedDimensionOrientation` is the value for a straight point-to-point distance.
If the help differs, adjust the helper in Step 3 to match before proceeding.

- [ ] **Step 3: Add the two helper functions**

Add after the `_constrain_flanks` function, before `build_gear`:

```python
def _far_end(curve, px_cm, py_cm):
    """Return the endpoint of `curve` farther from (px,py) (cm)."""
    sp, ep = curve.startSketchPoint, curve.endSketchPoint
    ds = math.hypot(sp.geometry.x - px_cm, sp.geometry.y - py_cm)
    de = math.hypot(ep.geometry.x - px_cm, ep.geometry.y - py_cm)
    return ep if de > ds else sp


def _coincide_spline_join(gc, spline, flank_lines, gcx_cm, gcy_cm):
    """Coincide the spline's flank-side endpoint with the nearest flank TOP.

    `_draw_outline` leaves segment joins constrained only by shared coordinates;
    `isFixed` used to hold them implicitly. The apex endpoint is far from both
    flank tops (it is at the tip), so the distance threshold skips it -- it is
    pinned separately to the centerline end."""
    tops = [_far_end(f, gcx_cm, gcy_cm) for f in flank_lines[:2]]
    for end in (spline.startSketchPoint, spline.endSketchPoint):
        best, bestd = None, 1e18
        for t in tops:
            d = math.hypot(end.geometry.x - t.geometry.x,
                           end.geometry.y - t.geometry.y)
            if d < bestd:
                bestd, best = d, t
        if best is not None and bestd < 1e-3:        # cm: only the genuine join
            try:
                gc.addCoincident(end, best)
            except Exception:
                futil.handle_error('spline join coincident with flank top')


def _lock_fit_points_to_frame(sketch, spline, center_pt, apex_pt):
    """Lock each INTERIOR fit point of `spline` relative to the centerline frame
    with two point-to-point distance dimensions: to the centre and to the apex.
    Both references lie on the centerline, so each fit point rotates with the
    frame. The two endpoints (item 0 and the last) are the curve ends and are
    skipped -- they are already pinned (apex->centerline end, join->flank top)."""
    dims = sketch.sketchDimensions
    aligned = adsk.fusion.DimensionOrientations.AlignedDimensionOrientation
    fps = spline.fitPoints
    n = fps.count
    for i in range(1, n - 1):                          # interior only
        fp = fps.item(i)
        g = fp.geometry
        for ref in (center_pt, apex_pt):
            tp = adsk.core.Point3D.create(g.x, g.y, 0.0)
            try:
                dims.addDistanceDimension(fp, ref, aligned, tp)
            except Exception:
                futil.handle_error(f'tip fit-point distance dim {i}')
```

- [ ] **Step 4: Replace the wheel-tip locking block**

Replace the current `if lock_center:` wheel-tip block (the one that sets `lower_spline.isFixed = True`, ~lines 313–361) with:

```python
    if lock_center:
        # Wheel tip: lock the conjugate spline RELATIVE to the centerline frame
        # instead of isFixed, so it rotates with the centerline. Apex on the
        # centerline end; lower flank/tip join coincided (the drawn outline leaves
        # it un-constrained); interior lower fit points dimensioned to centre +
        # apex; the upper half follows by the existing per-fit-point symmetry.
        lower_spline = next((e for (s, e) in drawn
                             if s.kind == 'spline' and s.clamp_start), None)
        upper_spline = next((e for (s, e) in drawn
                             if s.kind == 'spline' and s.clamp_end), None)
        if lower_spline is not None:
            try:
                gc.addCoincident(lower_spline.endSketchPoint, centerline.endSketchPoint)
            except Exception:
                futil.handle_error('tip apex coincident with centerline end')
            # Joins (isFixed used to hold these); only the LOWER join -- the upper
            # join is positioned by the symmetry mirror below, so coinciding it too
            # would over-constrain.
            _coincide_spline_join(gc, lower_spline, flank_lines,
                                  cx * MM_TO_CM, cy * MM_TO_CM)
            # Interior fit points -> frame (centre + apex, both on the centerline).
            _lock_fit_points_to_frame(sketch, lower_spline,
                                      center_anchor, centerline.endSketchPoint)
            if upper_spline is not None:
                try:
                    lf, uf = lower_spline.fitPoints, upper_spline.fitPoints
                    futil.log(f'build_gear {name}: tip fit points lower={lf.count} upper={uf.count}')
                    # The apex fit point lies on the centerline, so its mirror is
                    # itself: a symmetry constraint there is degenerate (it throws
                    # VCS_SKETCH_SOLVING_FAILED) and is redundant -- the apex is
                    # already pinned (centerline-end coincident + closed tooth loop).
                    apex = lower_spline.endSketchPoint.geometry
                    # The mirror of a point across the centerline at y = cy is
                    # (x, 2*cy - y) -- NOT (x, -y), which only holds on the X axis.
                    cy_cm = cy * MM_TO_CM
                    for i in range(lf.count):
                        lp = lf.item(i)
                        if math.hypot(lp.geometry.x - apex.x, lp.geometry.y - apex.y) < 1e-4:
                            continue
                        tx, ty = lp.geometry.x, 2.0 * cy_cm - lp.geometry.y
                        best, bestd = None, 1e18
                        for j in range(uf.count):
                            up = uf.item(j)
                            d = math.hypot(up.geometry.x - tx, up.geometry.y - ty)
                            if d < bestd:
                                bestd, best = d, up
                        if best is not None:
                            try:
                                gc.addSymmetry(lp, best, centerline)
                            except Exception:
                                futil.handle_error(f'tip fit-point symmetry {i}')
                except Exception:
                    futil.handle_error('mirror tip spline fit points')
```

Note: the centerline `horizontal` (lines ~303–307) stays in place for this task — we test the tip lock with orientation still pinned, isolating the change. The horizontal→angle swap is Task 2.

- [ ] **Step 5: Syntax-check the Fusion layer**

Run: `.venv/Scripts/python.exe -m compileall -q core`
Expected: no output (clean compile).

- [ ] **Step 6: USER tests in Fusion — DOF-driven verification**

Ask the user to reload the add-in and run it, then report:
1. Does the wheel build with a clean log (no `handle_error` entries for the tip)?
2. Is the wheel tooth **fully constrained** (sketch geometry black), and is the tip shape visually identical to before?

Contingencies based on the report:
- **Upper tip apex shows blue (under-constrained):** the upper spline's apex endpoint is not pinned. Add, inside `if upper_spline is not None:` before the mirror loop:
  `gc.addCoincident(_far_end(upper_spline, cx * MM_TO_CM, cy * MM_TO_CM), centerline.endSketchPoint)`
  (the upper spline's apex is its end farthest from the centre... if that picks the wrong end, use the end nearest the lower apex instead). Re-test.
- **Over-constrained error (VCS_SKETCH_OVER_CONSTRAINTS):** a relative dim duplicates the symmetry. Most likely a fit point indexing mismatch — confirm `lf.count`/`uf.count` from the log and that only interior points get distance dims. Remove the offending dim and re-test.
- **Interior fit points still blue:** the fitted spline has free end-tangent DOF that `isFixed` previously removed. Fallback: activate and fix the spline's end tangent handles (`spline.activateTangentHandle(...)` / fix the handle line), or, if that proves unworkable, restore `isFixed` and switch to the spec's Approach 2 (rotate via the sketch plane). Stop and report before changing approach.

Only proceed once the user confirms the tooth is fully constrained and the shape is unchanged.

- [ ] **Step 7: Regression guard**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed` (engine untouched).

- [ ] **Step 8: Commit**

```bash
git add core/sketch_builder.py
git commit -m "refactor(fusion): lock wheel tip relative to centerline (drop isFixed)" \
  -m "Replace lower_spline.isFixed with relative locks: coincide the flank/tip
join the drawn outline left loose, and dimension each interior tip fit point to
the centre and apex (both on the centerline). The tip is now rigid relative to
the centerline frame, so it can rotate with it. Wheel-only; geometry unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Drive wheel orientation by an angle dimension (replace `horizontal`)

**Files:**
- Modify: `core/sketch_builder.py` (replace centerline `horizontal` block ~303–307)

- [ ] **Step 1: Research the angular-dimension API**

WebFetch the Fusion help for `SketchDimensions.addAngularDimension`. Confirm the signature
`addAngularDimension(lineOne, lineTwo, textPoint, isDriving=True)` (two lines sharing a vertex).
This is already used for the pinion phase at the bottom of `build_gear` — match that usage.

- [ ] **Step 2: Replace the centerline `horizontal` block**

Replace the current block (~lines 303–307):

```python
    if lock_center:
        try:
            gc.addHorizontal(centerline)
        except Exception:
            futil.handle_error('centerline horizontal')
```

with an angle-dimension block:

```python
    if lock_center:
        # Orientation by an ANGLE DIMENSION (not horizontal): a horizontal
        # construction reference line through the centre + an angular dim to the
        # centerline. Default 0deg reproduces today's orientation (wheel base_angle
        # is 0, so the centerline is drawn along +X); editing the angle rotates the
        # whole wheel (the circular pattern carries it to every tooth). This is the
        # prerequisite for rotate-the-arrangement.
        try:
            ref = sketch.sketchCurves.sketchLines.addByTwoPoints(
                _pt(cx, cy), _pt(cx + profile.addendum_radius, cy))
            ref.isConstruction = True
            gc.addCoincident(ref.startSketchPoint, center_anchor)
            gc.addHorizontal(ref)
            atp = adsk.core.Point3D.create(cx * MM_TO_CM + 0.5, cy * MM_TO_CM + 0.5, 0.0)
            sketch.sketchDimensions.addAngularDimension(centerline, ref, atp, True)
        except Exception:
            futil.handle_error('wheel orientation angle dimension')
```

- [ ] **Step 3: Syntax-check**

Run: `.venv/Scripts/python.exe -m compileall -q core`
Expected: no output.

- [ ] **Step 4: USER tests in Fusion — geometry unchanged at 0°, then rotation**

Ask the user to reload and run, then report:
1. The wheel builds fully constrained with a clean log, and the angle dimension reads **0°** with geometry **identical** to Task 1 (the horizontal→angle swap is behaviour-neutral at the default).
2. Editing the angle dimension to a few values (e.g. 10°, 30°, −15°) rotates the whole tooth/gear **without the tip tearing** and the sketch stays fully constrained.

Contingencies:
- **Over-constrained:** the reference line's `horizontal` plus the angle dim plus a leftover `horizontal` on the centerline conflict — confirm the old `addHorizontal(centerline)` was fully removed.
- **Tip tears on rotation:** a tip fit point is still pinned to absolute coords — revisit Task 1 Step 6 (an interior point missing its relative dims, or a residual `isFixed`).

Only proceed once the user confirms rotation works without tearing.

- [ ] **Step 5: Regression guard**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed`.

- [ ] **Step 6: Commit**

```bash
git add core/sketch_builder.py
git commit -m "feat(fusion): drive wheel orientation by an angle dimension" \
  -m "Replace the centerline horizontal constraint with an angular dimension off a
horizontal reference line (default 0deg = today's orientation). With the tip now
locked relative to the centerline, editing this angle rotates the whole wheel
without tearing -- the prerequisite for rotate-the-arrangement.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Documentation

**Files:**
- Modify: `docs/HANDOVER.md` (§6 follow-ons)

- [ ] **Step 1: Mark the prerequisite done in the handover**

In `docs/HANDOVER.md` §6, update item 2 to record that the wheel is now individually
rotatable via an angle dimension (the `isFixed` blocker is removed), and that what
remains for rotate-the-arrangement is wiring the angle into the dialog / rotating
wheel + pinion together. Keep it to a couple of sentences, consistent with the
existing §6 entries (e.g. strike through "swap that horizontal for an angle
dimension" since it's done, and note the real work — removing `isFixed` — that it
required).

- [ ] **Step 2: Decide on README / manifest**

This change exposes no new dialog input (orientation defaults to 0° and is edited
in the sketch, not the dialog), so `README.md` and the manifest `description` need
no change yet — confirm there is nothing user-facing to update and skip them. (The
README/manifest update lands with the later dialog-exposed rotate-the-arrangement
feature, per CLAUDE.md "Keep docs in sync".)

- [ ] **Step 3: Commit**

```bash
git add docs/HANDOVER.md
git commit -m "docs: note wheel is now rotatable (rotate-the-arrangement prereq) [skip ci]" \
  -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Done criteria

- The wheel sketch is fully constrained with **no `isFixed`**; the tip shape at 0° is identical to before.
- Editing the wheel's angle dimension rotates the whole gear without the tip tearing, sketch staying fully constrained.
- `pytest tests/ -q` → `38 passed`; `compileall -q core` clean.
- Handover §6 reflects that rotation's prerequisite is complete.
- The pinion and the pure engine are unchanged.
