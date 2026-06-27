# Free-swing pinion for manual alignment — design

**Date:** 2026-06-27
**Status:** Approved, ready to implement
**Goal:** Let the user rotate the gear arrangement so the pinion can be aligned to
existing features (e.g. a second axle hole) in their Fusion document.

## Background

Today `build_gear` locates the pinion fully: its pitch circle is made **tangent** to
the wheel's pitch circle (fixing the meshing center distance), and an
`addHorizontalPoints(pinion_center, wheel_center)` constraint forces the line of
centers to be **horizontal** — so the pinion always lands straight out the +X side of
the wheel. The pinion's tooth phase is already dimensioned **relative to the line of
centers** (`loc` = pinion center → wheel center, lines ~478–484 of
`core/sketch_builder.py`): move the pinion center and its teeth rotate with it to hold
that angle.

## Decision

Leave the pinion **free to swing around the wheel** and let the user align it with
native Fusion constraints, rather than adding a dialog input + computed rotation +
validation. This was chosen over a "pick a pinion target point / enter an angle"
auto-placement approach because it is far simpler, needs no new validation, and gives
the user maximum flexibility to align to any feature (point, edge, angle).

### The change

`core/sketch_builder.py` only: **remove** the `addHorizontalPoints(pinion_center,
wheel_center)` constraint (the block at ~lines 336–341) and update its log message.
Everything else stays — crucially the `addTangent` to the wheel's pitch circle and the
phase angular dimension.

### Resulting behavior

- The pinion is born at its current horizontal home (the engine layout is unchanged,
  so the interference test's canonical geometry is untouched).
- It has exactly **one degree of freedom**: swing around the wheel on the locus of
  valid centers. The tangent holds the center distance; the phase dimension keeps its
  teeth aimed along the line of centers as it swings.
- The user adds their own locating constraint (coincident to an axle point, an angle
  dimension, collinear to an edge). Because the pinion is locked tangent (center
  distance fixed), a target at the wrong spacing simply won't solve — **Fusion's
  solver is the validation**; we write none.
- An under-constrained sketch is valid in Fusion (blue, not an error); the extrude +
  circular pattern still build at the as-drawn position.

### Accepted caveat — modeled mesh phase

The **wheel's** tooth orientation stays absolute (its existing horizontal / 90° angle
dimension); it does not follow the line of centers. So when the pinion is swung, the
pinion's teeth re-aim correctly but the wheel's teeth do not, and the *modeled* mesh
can look clocked off by up to half a tooth. This is **cosmetic only** — for 3D-printed
gears, center distance is what matters physically; the gears are rotated to mesh on
assembly. Keeping the modeled mesh visually correct (re-tying the wheel orientation to
the line of centers via a reverse cross-component reference) was considered and
explicitly deferred as unnecessary.

## Explicitly out of scope (YAGNI)

- No new dialog inputs (no target-point picker, no assembly-angle field).
- No `core/settings.py` or `commands/generateGears/entry.py` changes.
- No engine helper, no center-distance blocking check, no tolerance constant.
- No toggle — the free pinion is simply the default.

## Files touched

- `core/sketch_builder.py` — remove the one constraint + fix the log message.
- `README.md` and the `description` field in `PerfectPrintGears.manifest` — document
  that the pinion is intentionally left free to rotate about the wheel so it can be
  aligned to existing features (per the repo's "keep docs in sync" rule).

## Verification

- `py_compile` the Fusion layer (CI parity).
- `pytest` — unchanged (engine untouched), still 38 passing.
- Manual in Fusion (user): confirm the pinion swings freely about the wheel and
  re-meshes correctly when constrained to a point/angle, and that a wrong-spacing
  target fails to solve.
