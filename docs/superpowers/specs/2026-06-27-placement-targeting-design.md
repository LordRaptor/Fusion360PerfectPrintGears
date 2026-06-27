# Placement & Targeting — Design

**Date:** 2026-06-27
**Status:** Approved, ready for implementation plan
**Scope:** Three related Fusion-layer placement features in one branch. The pure geometry
engine is **not** touched.

## Goal

Give the user control over *where* the generated gears are placed, via three new dialog
selections, each optional and defaulting to today's behavior:

1. **Separate target components** for the wheel and the pinion.
2. **A selectable sketch plane** (shared by both gears) to build the sketches on.
3. **A selectable center point** for the wheel.

## Non-goals / invariants

- **The pure engine (`core/gear_math.py`) is unchanged.** It still emits the wheel at the
  origin and the pinion at `(center_distance, 0)` in mm. All placement is Fusion-layer only,
  so the validated conjugate geometry and `tests/test_interference.py` are unaffected.
- The pinion stays **live-meshed** to the wheel (projected pitch circle + tangent), including
  across components — moving the wheel moves the pinion. No independent placement.
- Selections are **not persisted** to settings (they are entity references), consistent with
  how the current `target` selection works.

## Architecture & layering

- **`core/gear_math.py`** — unchanged.
- **`core/sketch_builder.py`** — `build_pair` and `build_gear` gain placement parameters; the
  sketch is created on the passed plane instead of the hardcoded `xYConstructionPlane`, and the
  wheel center is constrained to the passed point instead of always the sketch origin.
- **`commands/generateGears/entry.py`** — the single `target` selection input is replaced by the
  new inputs; `command_execute` resolves them and passes them through; `_resolve_target` becomes
  per-gear resolution.

## Dialog inputs & defaults

The single `Target component` input is replaced by the following. All are optional; an untouched
dialog produces output identical to today.

| Input | Type | Default | Feature |
|---|---|---|---|
| **Wheel component** | Occurrence/Root selection (limit 0–1) | active component | 1 |
| **Pinion component** | Occurrence/Root selection (limit 0–1) | active component | 1 |
| **Sketch plane** | Construction plane **or** planar face (limit 0–1) | wheel component's XY plane | 2 |
| **Wheel center** | Point: sketch point / construction point / BRep vertex (limit 0–1) | sketch origin | 3 |

- If **Wheel component == Pinion component** (including both empty ⇒ active), both gears are built
  in that one component as two sketches — exactly today's behavior, mesh intact.
- The **Sketch plane** is shared by both gears (they must be coplanar to mesh).
- Selection filters: planar faces only for the plane; point-like entities only for the center.

## Signatures

```
build_pair(wheel_component, pinion_component, pair, thickness_mm, plane, wheel_center=None)
build_gear(component, profile, thickness_mm, name, plane,
           lock_center=False, mesh_to_pitch=None, center_point=None)
```

(Previously `build_pair(component, pair, thickness_mm=5.0)` and
`build_gear(component, profile, thickness_mm, name, lock_center=False, mesh_to_pitch=None)`.)

## Constraint mechanics

- **Plane**: `sketch = component.sketches.add(plane)`. `plane` is the selected construction plane
  or planar face; default is the wheel component's `xYConstructionPlane`.
- **Wheel center**: when `center_point` is given, project it into the sketch
  (`sketch.project` / `include`) to obtain an in-plane sketch point, then coincide the three
  circle centers and the centerline start to *that* point instead of `sketch.originPoint`. When
  empty, use `sketch.originPoint` (today's path).
- **Pinion mesh**: unchanged logic — `sketch.include(wheel_pitch_circle)` (now a cross-component
  projection when the components differ) → `addTangent` + `addHorizontalPoints`.

### Research / step-by-step items (build with Fusion testing, research the API first)

1. Creating a sketch in the **pinion** component on a plane/face owned by another component or the
   root — verify Fusion allows it and that it behaves correctly under occurrence transforms.
2. The line-of-centers `addHorizontalPoints` assumes both sketches share an X-axis orientation;
   two sketches on the same plane may not. May require setting the sketch reference orientation
   explicitly, or constraining to a projected axis instead of relying on "horizontal".

## Error handling

- Every new constraint/placement call is wrapped in `try/except` + `futil.log`, matching the
  existing defensive pattern, so a single solver rejection can't abort the build.
- **Off-plane center point**: projected onto the plane along its normal (Fusion projection).
- **Cross-component reference / projection failure**: logged via `handle_error` with a message
  box; the build continues where it safely can.
- Selection filters keep picks valid; the existing `validateInputs` continues to gate only the
  numeric gear parameters (the new selections are optional and don't block OK).

## Testing

- The engine is untouched ⇒ the **existing 38 pytest tests stay green**; no new engine tests are
  warranted.
- No new persisted settings keys ⇒ settings tests unaffected.
- All new logic lives in the `adsk` layer (not unit-testable here). Verification is
  **`compileall` + manual Fusion testing, one feature at a time**, with DXF export to `tmp/` if
  geometry inspection is needed — consistent with the project's Fusion-layer verification.

## Build order (collaborative, step by step)

1. **Sketch plane** selection → build on it (default XY unchanged).
2. **Wheel center** point → coincide the wheel center to the projected point.
3. **Split into two components**, including the cross-component mesh projection.

Each step is tested in Fusion by the user before the next.

## Docs

Update `README.md`'s dialog/usage table with the new inputs and their "empty = current behavior"
defaults. The `manifest` `description` is high-level (does not enumerate dialog fields) and does
not need changing.
