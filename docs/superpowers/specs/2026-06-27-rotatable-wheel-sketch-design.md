# Rotatable wheel sketch — design

**Date:** 2026-06-27
**Status:** Approved (brainstorm); ready for implementation planning.

## Goal

Make the **wheel** sketch rotate cleanly as a rigid body, driven by a single
editable angle dimension. This is the prerequisite for the handover §6
"rotate-the-arrangement" feature: once the wheel's orientation is a dimension
(not a `horizontal` constraint pinned to world X, and not an `isFixed` spline
pinned to world coordinates), rotating the assembly becomes editing that one
value.

## Scope

- **Wheel-only, constraint-only.** The pinion already rotates cleanly (its tip
  is a tangent arc — fully relative — and its phase is already an angular
  dimension between its centerline and the line of centers). Nothing about the
  pinion changes.
- **The validated conjugate geometry is NOT touched.** This is purely a sketch
  constraint rework. The pure engine (`core/gear_math.py`) is unchanged.
- All changes live in `core/sketch_builder.py`.

## Background / why this is needed

Today the wheel tip is locked with `lower_spline.isFixed = True`
(`core/sketch_builder.py:327`), which pins the spline's fit points to absolute
sketch coordinates. The wheel centerline is also `horizontal`
(`core/sketch_builder.py:305`), pinning the tooth orientation to world X.

The handover §6 #2 assumes rotation only needs to "swap that horizontal for an
angle dimension." That is necessary but **not sufficient**: with the tip spline
still `isFixed`, its fit points will not follow the rotating centerline, so the
tip tears. Removing `isFixed` (and replacing what it locked with relative
constraints) is the real work.

A second, related fact: `_draw_outline` (`core/sketch_builder.py:26`) draws each
segment as an independent curve and does **not** add coincidence constraints
between adjacent segment endpoints — it relies on shared coordinates, which is
enough for profile detection but not for degrees of freedom. So `isFixed` is
currently doing double duty: locking the spline shape **and** implicitly
anchoring the flank-top / tip join. Removing it will expose new DOF at the joins
too, not just at the interior fit points.

## New constraint scheme for the wheel tip

Replace the two absolute anchors with relative locks:

1. **Remove** `lower_spline.isFixed = True`.
2. **Add the join coincidences** that `isFixed` was implicitly providing:
   - lower-spline start ↔ lower flank top
   - upper-spline start ↔ upper flank top

   (The apex ↔ centerline-end coincidence already exists at line 323.)
3. **Lock each interior fit point of the lower spline relative to the frame**
   with two driving dimensions each:
   - perpendicular distance to the centerline, and
   - distance to the centre.

   The upper half stays mirrored by the existing per-fit-point symmetry about
   the centerline, so locking the lower half fully determines the whole tip.
   At the default resolution this is ~2–3 interior points → ~4–6 dimensions.
   The dimension *values* are the computed conjugate-shape numbers (not
   meaningful round numbers); that is acceptable.
4. **Replace** the centerline `horizontal` with an **angular dimension** between
   the centerline and a new horizontal construction reference line through the
   centre. Default **0°**, which reproduces today's orientation exactly (the
   wheel's `base_angle` is `0.0`, so tooth 0 points along +X today). Editing this
   angle rotates the whole tooth; the existing circular pattern carries the
   rotation to every tooth.

## Acknowledged risk

The one "plausible-but-must-verify-in-Fusion" assumption is that locking all fit
points (without `isFixed`) fully pins the fitted spline, including any
end-tangent degrees of freedom. We verify this on the first build before relying
on it. If tangent DOF remain, the fallback is to pin the end tangents explicitly
(or, worst case, fall back to rotating the sketch plane / occurrence — the
"Approach 2" alternative — but only if the relative-lock approach proves
unworkable).

## Implementation strategy (step by step, DOF-driven)

Per the project working mode (CLAUDE.md / handover §7), do not guess the DOF
statically — let Fusion report it. Each step is one change the user tests in
Fusion and confirms before the next.

1. Remove `isFixed`; rebuild; read what Fusion now flags as under-constrained.
2. Add the join coincidences; rebuild; confirm only the tip interior is loose.
3. Add the per-fit-point relative dimensions; rebuild; confirm the tooth is rigid
   with `horizontal` still in place.
4. Swap `horizontal` → angular dimension (default 0°); confirm the geometry is
   identical to today.
5. Test rotation: set the angle to several values in Fusion; confirm the tip
   follows without tearing.

## Verification

- `.venv/Scripts/python.exe -m pytest tests/ -q` stays green. The engine is
  untouched, so all existing tests (incl. the interference guard, which is
  geometry-only) pass unchanged. This is a regression guard, not new coverage.
- `.venv/Scripts/python.exe -m compileall -q core` for the Fusion layer.
- Final Fusion check: rotate the wheel through a few angles; optionally export a
  DXF to `tmp/fusion_sketches/` and confirm with `tmp/render_dxf.py` /
  `tmp/check_tangency.py` that the tip shape at 0° is unchanged from today.

## Docs

This is mostly internal plumbing for the next feature (rotate-the-arrangement)
and does not yet expose a dialog input, so user-facing docs change little. Update
`README.md` and the manifest `description` only if behavior the user sees
changes; otherwise defer the doc update to the rotate-the-arrangement change that
surfaces the angle in the dialog. Update `docs/HANDOVER.md` §6 to mark this
prerequisite done.

## Out of scope (future work)

- Exposing the rotation angle in the command dialog (part of
  rotate-the-arrangement, handover §6 #2/#3).
- Rotating the *whole assembly* (wheel + pinion together) — this change only
  makes the wheel individually rotatable; the pinion phase already references the
  line of centers, so the arrangement rotation builds on top of this.
