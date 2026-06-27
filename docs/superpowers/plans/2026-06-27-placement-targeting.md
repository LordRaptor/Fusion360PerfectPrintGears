# Placement & Targeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user choose separate target components for the wheel and pinion, a shared sketch plane to build on, and the wheel's center point — all optional, each defaulting to today's behavior.

**Architecture:** Pure-Python engine (`core/gear_math.py`) is untouched — it still emits the wheel at origin and pinion at `(center_distance, 0)`. All three features are Fusion-layer placement only: `core/sketch_builder.py` gains a `plane`, a `wheel_center`/`center_point`, and per-gear components; `commands/generateGears/entry.py` gains the dialog inputs and resolvers.

**Tech Stack:** Python 3, Fusion 360 `adsk` API (not unit-testable here — verified by `compileall`, the pytest regression suite, and **manual testing in Fusion**), pytest.

---

## CRITICAL working-mode note (read before starting)

Per `CLAUDE.md` and the project memory: **geometry/sketch-constraint work is collaborative and verified in Fusion one step at a time.** The `adsk` layer cannot be unit-tested in this repo. For every task here:

- The automated gates are only `compileall` (syntax) and `pytest tests/ -q` (proves the engine/settings still pass — **38 passed**).
- The **real** acceptance gate is the **manual Fusion verification step** at the end of each task, performed by the user. **Do not start the next task until the user confirms the current one in Fusion.**
- **Research the Fusion API before using an unfamiliar call** (WebFetch the help page). Several plausible-but-wrong calls exist.

This makes **inline collaborative execution** (propose one task, user tests in Fusion, confirm, next) the appropriate execution mode — not autonomous subagent batches.

## File structure (no new files)

| File | Change |
|---|---|
| `commands/generateGears/entry.py` | Dialog inputs (sketch plane, wheel center, wheel/pinion components), resolvers, `command_execute` wiring. |
| `core/sketch_builder.py` | `build_pair`/`build_gear` placement parameters; sketch on the passed plane; wheel center on the passed point; per-gear components + cross-component mesh. |
| `README.md` | Document the new dialog inputs. |

## Signature evolution (kept consistent across tasks)

- After **Task 1**: `build_pair(component, pair, thickness_mm=5.0, plane=None)` and `build_gear(component, profile, thickness_mm, name, plane, lock_center=False, mesh_to_pitch=None)`.
- After **Task 2**: `build_pair(component, pair, thickness_mm=5.0, plane=None, wheel_center=None)` and `build_gear(..., plane, lock_center=False, mesh_to_pitch=None, center_point=None)` (build_gear final).
- After **Task 3**: `build_pair(wheel_component, pinion_component, pair, thickness_mm=5.0, plane=None, wheel_center=None)` (build_gear unchanged; called with each component).

---

### Task 1: Selectable sketch plane (feature 2)

**Files:**
- Modify: `commands/generateGears/entry.py`
- Modify: `core/sketch_builder.py`

- [ ] **Step 1: Research the Fusion API**

WebFetch the Fusion 360 API help for the **`Sketches.add` Method** and confirm it accepts both a `ConstructionPlane` and a planar `BRepFace` as the `planarEntity` argument. Note the signature; do not guess.

- [ ] **Step 2: Add the sketch-plane selection input**

In `commands/generateGears/entry.py`, `_build_inputs`, immediately after the existing `target` selection block (currently the `inputs.addSelectionInput('target', ...)` block ending with `sel.setSelectionLimits(0, 1)`), add:

```python
    futil.log('build: sketchPlane')
    plane_sel = inputs.addSelectionInput('sketchPlane', 'Sketch plane',
                                         'Plane or planar face to build the gear sketches on '
                                         '(default: the wheel component XY plane)')
    plane_sel.addSelectionFilter('ConstructionPlanes')
    plane_sel.addSelectionFilter('PlanarFaces')
    plane_sel.setSelectionLimits(0, 1)
```

- [ ] **Step 3: Add a plane resolver**

In `commands/generateGears/entry.py`, add next to `_resolve_target` (around entry.py:196):

```python
def _resolve_plane(inputs):
    """The selected construction plane / planar face, or None to use a default."""
    sel = inputs.itemById('sketchPlane')
    if sel.selectionCount == 1:
        return sel.selection(0).entity
    return None
```

- [ ] **Step 4: Pass the plane through `command_execute`**

In `commands/generateGears/entry.py`, `command_execute`, change the build call. Current:

```python
        target = _resolve_target(inputs)
        thickness_mm = inputs.itemById('thickness').value / 0.1
        sketch_builder.build_pair(target, pair, thickness_mm)
```

to:

```python
        target = _resolve_target(inputs)
        plane = _resolve_plane(inputs)
        thickness_mm = inputs.itemById('thickness').value / 0.1
        sketch_builder.build_pair(target, pair, thickness_mm, plane)
```

- [ ] **Step 5: Thread `plane` through `build_pair`**

In `core/sketch_builder.py`, replace the whole `build_pair` (currently at sketch_builder.py:394-402):

```python
def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair,
               thickness_mm: float = 5.0, plane=None) -> None:
    """Build both gears into `component` in meshing layout. The wheel is built
    first with its circle centres locked to the origin; the pinion then references
    the wheel's pitch circle and is constrained tangent to it (the mesh).

    `plane` is the planar entity (construction plane or planar face) the sketches
    are drawn on; defaults to the component's XY construction plane."""
    if plane is None:
        plane = component.xYConstructionPlane
    _, wheel_pitch = build_gear(component, pair.wheel, thickness_mm,
                                f'PPG Wheel {pair.wheel.teeth}T', plane, lock_center=True)
    build_gear(component, pair.pinion, thickness_mm,
               f'PPG Pinion {pair.pinion.teeth}T', plane, mesh_to_pitch=wheel_pitch)
```

- [ ] **Step 6: Use `plane` in `build_gear`**

In `core/sketch_builder.py`, change the `build_gear` signature (currently sketch_builder.py:155-157) to insert `plane` after `name`:

```python
def build_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
               thickness_mm: float, name: str, plane,
               lock_center: bool = False, mesh_to_pitch=None):
```

and change the sketch creation (currently `sketch = component.sketches.add(component.xYConstructionPlane)` at sketch_builder.py:173) to:

```python
    sketch = component.sketches.add(plane)
```

- [ ] **Step 7: Syntax-check and regression-test**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py core/sketch_builder.py`
Expected: no output.

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed`.

- [ ] **Step 8: Manual Fusion verification (USER)**

Ask the user to reload the add-in and confirm:
- With **no** plane selected, gears build on XY exactly as before (clean log, fully constrained).
- With a **construction plane** selected, both gear sketches are created on it.
- With a **planar face** selected, both gear sketches are created on that face.

Do not proceed until the user confirms.

- [ ] **Step 9: Commit**

```bash
git add commands/generateGears/entry.py core/sketch_builder.py
git commit -m "feat(fusion): let the user pick the sketch plane for the gears"
```

---

### Task 2: Selectable wheel center point (feature 3)

**Files:**
- Modify: `commands/generateGears/entry.py`
- Modify: `core/sketch_builder.py`

- [ ] **Step 1: Research the Fusion API**

WebFetch the Fusion 360 API help for the **`Sketch.project` Method**. Confirm it accepts a point-like entity (`SketchPoint`, `ConstructionPoint`, `BRepVertex`) and returns an `ObjectCollection` whose `item(0)` is the projected `SketchPoint`. Note the behavior for an entity off the sketch plane (it projects along the plane normal).

- [ ] **Step 2: Add the wheel-center selection input**

In `commands/generateGears/entry.py`, `_build_inputs`, immediately after the `sketchPlane` block from Task 1, add:

```python
    futil.log('build: wheelCenter')
    ctr_sel = inputs.addSelectionInput('wheelCenter', 'Wheel center',
                                       'Point to place the wheel center on '
                                       '(default: the sketch origin)')
    ctr_sel.addSelectionFilter('SketchPoints')
    ctr_sel.addSelectionFilter('ConstructionPoints')
    ctr_sel.addSelectionFilter('Vertices')
    ctr_sel.setSelectionLimits(0, 1)
```

- [ ] **Step 3: Add a center-point resolver**

In `commands/generateGears/entry.py`, add next to `_resolve_plane`:

```python
def _resolve_wheel_center(inputs):
    """The selected wheel-center point entity, or None to use the sketch origin."""
    sel = inputs.itemById('wheelCenter')
    if sel.selectionCount == 1:
        return sel.selection(0).entity
    return None
```

- [ ] **Step 4: Pass the center through `command_execute`**

In `command_execute`, extend the resolve+build block from Task 1 to:

```python
        target = _resolve_target(inputs)
        plane = _resolve_plane(inputs)
        wheel_center = _resolve_wheel_center(inputs)
        thickness_mm = inputs.itemById('thickness').value / 0.1
        sketch_builder.build_pair(target, pair, thickness_mm, plane, wheel_center)
```

- [ ] **Step 5: Thread `wheel_center` through `build_pair`**

In `core/sketch_builder.py`, update `build_pair` from Task 1: add the parameter and pass it to the wheel only.

Signature line becomes:

```python
def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair,
               thickness_mm: float = 5.0, plane=None, wheel_center=None) -> None:
```

and the wheel build call becomes:

```python
    _, wheel_pitch = build_gear(component, pair.wheel, thickness_mm,
                                f'PPG Wheel {pair.wheel.teeth}T', plane,
                                lock_center=True, center_point=wheel_center)
```

(The pinion `build_gear` call is unchanged.)

- [ ] **Step 6: Add `center_point` to `build_gear` and resolve the centre anchor**

In `core/sketch_builder.py`, update the `build_gear` signature to add `center_point=None` at the end:

```python
def build_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
               thickness_mm: float, name: str, plane,
               lock_center: bool = False, mesh_to_pitch=None, center_point=None):
```

Then, immediately after `gc = sketch.geometricConstraints` (currently sketch_builder.py:198) and before the `if lock_center:` circle-centre loop, insert:

```python
    # The wheel's centre anchor: a projected sketch point if the user picked a
    # centre, else the sketch origin. (Only meaningful when lock_center is True.)
    center_anchor = sketch.originPoint
    if lock_center and center_point is not None:
        try:
            center_anchor = sketch.project(center_point).item(0)
        except Exception:
            futil.handle_error('project wheel centre point')
            center_anchor = sketch.originPoint
```

- [ ] **Step 7: Use `center_anchor` instead of the origin in the lock_center branches**

In `core/sketch_builder.py`, in the `if lock_center:` circle loop, change:

```python
            try:
                gc.addCoincident(c.centerSketchPoint, sketch.originPoint)
            except Exception:
                futil.handle_error('addCoincident(center, origin)')
```

to use `center_anchor`:

```python
            try:
                gc.addCoincident(c.centerSketchPoint, center_anchor)
            except Exception:
                futil.handle_error('addCoincident(center, anchor)')
```

And in the centerline-start coincidence (currently sketch_builder.py:250-252), change:

```python
        if lock_center:
            gc.addCoincident(centerline.startSketchPoint, sketch.originPoint)
```

to:

```python
        if lock_center:
            gc.addCoincident(centerline.startSketchPoint, center_anchor)
```

- [ ] **Step 8: Syntax-check and regression-test**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py core/sketch_builder.py`
Expected: no output.

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed`.

- [ ] **Step 9: Manual Fusion verification (USER)**

Ask the user to reload and confirm:
- With **no** wheel-center selected, the wheel sits at the sketch origin as before (fully constrained, clean log).
- With a **sketch point / construction point / vertex** selected, the wheel center coincides with it (projected onto the plane), and the **pinion follows** (still meshed).

Do not proceed until the user confirms.

- [ ] **Step 10: Commit**

```bash
git add commands/generateGears/entry.py core/sketch_builder.py
git commit -m "feat(fusion): let the user pick the wheel center point"
```

---

### Task 3: Separate wheel/pinion components + cross-component mesh (feature 1)

**Files:**
- Modify: `commands/generateGears/entry.py`
- Modify: `core/sketch_builder.py`

- [ ] **Step 1: Research the Fusion API**

WebFetch the Fusion 360 API help and confirm two things, noting any constraints:
1. **`Sketches.add`** can create a sketch in component B on a planar entity that belongs to component A or the root (cross-component plane reference), and how occurrence transforms affect the sketch's coordinate frame.
2. **`Sketch.include`** can project a `SketchCircle` that lives in another component's sketch into the current sketch (cross-component projection).

If either is not supported as assumed, **stop and report** before editing — this may need a different approach (e.g. projecting through the root component).

- [ ] **Step 2: Replace the single target input with two component inputs**

In `commands/generateGears/entry.py`, `_build_inputs`, replace the current `target` block:

```python
    futil.log('build: target')
    sel = inputs.addSelectionInput('target', 'Target component',
                                   'Component to draw the gear sketches into')
    sel.addSelectionFilter('Occurrences')
    sel.addSelectionFilter('RootComponents')
    sel.setSelectionLimits(0, 1)
```

with two inputs:

```python
    futil.log('build: wheelComponent')
    wsel = inputs.addSelectionInput('wheelComponent', 'Wheel component',
                                    'Component to draw the wheel into (default: active)')
    wsel.addSelectionFilter('Occurrences')
    wsel.addSelectionFilter('RootComponents')
    wsel.setSelectionLimits(0, 1)

    futil.log('build: pinionComponent')
    psel = inputs.addSelectionInput('pinionComponent', 'Pinion component',
                                    'Component to draw the pinion into (default: active)')
    psel.addSelectionFilter('Occurrences')
    psel.addSelectionFilter('RootComponents')
    psel.setSelectionLimits(0, 1)
```

- [ ] **Step 3: Replace `_resolve_target` with a per-id resolver**

In `commands/generateGears/entry.py`, replace `_resolve_target` (currently entry.py:196-204):

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
```

with:

```python
def _resolve_component(inputs, input_id):
    """Resolve a component selection input to a Component; default to active."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    sel = inputs.itemById(input_id)
    if sel.selectionCount == 1:
        entity = sel.selection(0).entity
        if isinstance(entity, adsk.fusion.Occurrence):
            return entity.component
        return entity  # a Component (root)
    return design.activeComponent
```

- [ ] **Step 4: Resolve both components in `command_execute` and default the plane to the wheel's**

In `command_execute`, change the resolve+build block (from Task 2) to:

```python
        wheel_component = _resolve_component(inputs, 'wheelComponent')
        pinion_component = _resolve_component(inputs, 'pinionComponent')
        plane = _resolve_plane(inputs)
        wheel_center = _resolve_wheel_center(inputs)
        thickness_mm = inputs.itemById('thickness').value / 0.1
        sketch_builder.build_pair(wheel_component, pinion_component, pair,
                                  thickness_mm, plane, wheel_center)
```

- [ ] **Step 5: Split `build_pair` into wheel/pinion components**

In `core/sketch_builder.py`, replace `build_pair` (from Task 2) with:

```python
def build_pair(wheel_component: adsk.fusion.Component,
               pinion_component: adsk.fusion.Component,
               pair: gear_math.GearPair, thickness_mm: float = 5.0,
               plane=None, wheel_center=None) -> None:
    """Build the wheel and pinion into their (possibly separate) components in a
    meshing layout. The wheel is built first with its centre locked (to the chosen
    point or the sketch origin); the pinion then references the wheel's pitch circle
    and is constrained tangent to it (the mesh) -- a cross-component projection when
    the components differ.

    `plane` is the shared planar entity both sketches are drawn on; defaults to the
    wheel component's XY construction plane. If `wheel_component is pinion_component`
    (e.g. both default to the active component), both gears are built into that one
    component, exactly as before."""
    if plane is None:
        plane = wheel_component.xYConstructionPlane
    _, wheel_pitch = build_gear(wheel_component, pair.wheel, thickness_mm,
                                f'PPG Wheel {pair.wheel.teeth}T', plane,
                                lock_center=True, center_point=wheel_center)
    build_gear(pinion_component, pair.pinion, thickness_mm,
               f'PPG Pinion {pair.pinion.teeth}T', plane, mesh_to_pitch=wheel_pitch)
```

(`build_gear` is unchanged — it already takes a single `component` and is now simply called with `wheel_component` then `pinion_component`.)

- [ ] **Step 6: Syntax-check and regression-test**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py core/sketch_builder.py`
Expected: no output.

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: `38 passed`.

- [ ] **Step 7: Manual Fusion verification (USER)**

Ask the user to reload and confirm:
- With **both** component selections empty (or set to the same component), both gears build into the active component, two sketches, meshed — exactly as before.
- With **different** components selected for wheel and pinion, the wheel is built in its component and the pinion in its own, the pinion sketch projects the wheel's pitch circle across components, and the pair still meshes (pinion tangent to the wheel pitch circle, fully constrained, clean log).
- Verify the line-of-centers orientation is correct (pinion sits along the expected direction). If the `addHorizontalPoints` constraint misbehaves across two sketches (per spec research item 2), report it so we adjust the constraint approach with the user.

Do not proceed until the user confirms.

- [ ] **Step 8: Commit**

```bash
git add commands/generateGears/entry.py core/sketch_builder.py
git commit -m "feat(fusion): build wheel and pinion into separate components"
```

---

### Task 4: Update docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Inspect the README usage section**

Read `README.md` and locate the dialog-inputs table (the `| Input | Meaning |` table under `## Usage`).

- [ ] **Step 2: Replace the single Target-component row with the new placement rows**

In `README.md`, replace the existing target-component row:

```
| **Target component** | Where the two gears are built (defaults to the active component). |
```

with four rows describing the new inputs (match the table's existing wording style):

```
| **Wheel component** | Component to build the wheel into (defaults to the active component). |
| **Pinion component** | Component to build the pinion into (defaults to the active component). Set the same as the wheel to build both into one component. |
| **Sketch plane** *(optional)* | Construction plane or planar face the gear sketches are drawn on (defaults to the wheel component's XY plane). Shared by both gears so they stay coplanar and mesh. |
| **Wheel center** *(optional)* | Point (sketch point, construction point, or vertex) to place the wheel center on (defaults to the sketch origin). The pinion meshes relative to the wheel. |
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the new placement inputs (components, plane, center)"
```

---

## Self-Review

- **Spec coverage:** feature 1 separate components (Task 3) ✓; feature 2 sketch plane (Task 1) ✓; feature 3 wheel center (Task 2) ✓; engine untouched (no engine task — by design) ✓; optional inputs default to current behavior (Tasks 1-3 resolvers return None/active) ✓; live cross-component mesh kept (Task 3 Step 5 passes `wheel_pitch` to the pinion) ✓; not-persisted selections (no settings changes in any task) ✓; docs (Task 4) ✓; manifest unchanged (noted, no task) ✓.
- **Placeholder scan:** No TBD/TODO; every code step shows full code; commands have expected output; the two API-uncertainty items are explicit research steps with a stop-and-report instruction, not vague hand-waving.
- **Type/signature consistency:** `build_pair` evolves `component→(plane)→(wheel_center)→(wheel_component, pinion_component)` with each task showing the full replacement; `build_gear` reaches its final signature in Task 2 and is unchanged in Task 3; `_resolve_plane`/`_resolve_wheel_center`/`_resolve_component` are defined before they are called in `command_execute`; input ids (`sketchPlane`, `wheelCenter`, `wheelComponent`, `pinionComponent`) match between their `addSelectionInput` and their resolvers; `center_point`/`center_anchor` defined in Task 2 Step 6 and used in Step 7.
