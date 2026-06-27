# Editable, Module-Linked Tooth Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tooth width an editable dialog input, mutually linked with module (edit one → the other updates), with tooth fraction kept as a third coupled field.

**Architecture:** Two pure-engine helpers carry the `tooth_width = tooth_fraction · π · module`
math (unit-testable). The Fusion dialog groups the three controls and live-links them in
`command_input_changed` behind a reentrancy guard. Source of truth for persistence and the
geometry engine stays `(module_mm, tooth_fraction)` — tooth width is always derivable, so there
is no settings migration and no geometry change.

**Tech Stack:** Python 3, Fusion 360 `adsk` API (dialog layer), pytest (engine layer).

**Working mode (project rule):** Fusion-layer files import `adsk` and cannot be imported/tested
here — they are syntax-checked with `compileall` and verified **manually in Fusion by the user**,
one step at a time. The pure engine is TDD'd with pytest.

---

### Task 1: Pure-engine tooth-width ↔ module helpers

**Files:**
- Modify: `core/gear_math.py` (add two functions after `derive_geometry`, ~line 62)
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_gear_math.py` (module already imports `math`, `pytest`, and `gear_math as gm`):

```python
def test_tooth_width_from_module():
    # tooth_width = tooth_fraction * pi * module
    assert gm.tooth_width_from_module(2.0, 0.5) == pytest.approx(0.5 * math.pi * 2.0)


def test_module_from_tooth_width_inverts():
    assert gm.module_from_tooth_width(0.5 * math.pi * 2.0, 0.5) == pytest.approx(2.0)


def test_module_tooth_width_roundtrip():
    m, tf = 1.5, 0.45
    assert gm.module_from_tooth_width(gm.tooth_width_from_module(m, tf), tf) == pytest.approx(m)


def test_module_from_tooth_width_rejects_nonpositive_fraction():
    with pytest.raises(ValueError, match="tooth_fraction"):
        gm.module_from_tooth_width(2.0, 0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gear_math.py -q -k "tooth_width or roundtrip"`
Expected: FAIL — `AttributeError: module 'core.gear_math' has no attribute 'tooth_width_from_module'`

- [ ] **Step 3: Write the helpers**

In `core/gear_math.py`, immediately after `derive_geometry` (after line 62), add:

```python
def tooth_width_from_module(module_mm: float, tooth_fraction: float) -> float:
    """Tooth width (mm) implied by a module and tooth fraction: tf * pi * module."""
    return tooth_fraction * math.pi * module_mm


def module_from_tooth_width(width_mm: float, tooth_fraction: float) -> float:
    """Module (mm) that yields a given tooth width at a fixed tooth fraction.
    The inverse of tooth_width_from_module; raises on a non-positive fraction
    (guards a divide-by-zero from an in-progress dialog edit)."""
    if tooth_fraction <= 0:
        raise ValueError("tooth_fraction must be greater than 0")
    return width_mm / (tooth_fraction * math.pi)
```

- [ ] **Step 4: DRY — reuse the helper in derive_geometry**

In `core/gear_math.py`, change the feature-width line inside `derive_geometry` (line 53) from:

```python
    fw = inp.tooth_fraction * cp
```

to:

```python
    fw = tooth_width_from_module(inp.module_mm, inp.tooth_fraction)
```

(`cp` is still used on line 59 for `circular_pitch`, so leave it.)

- [ ] **Step 5: Run the full suite to verify green**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — previous count (38) + 4 new tests, all passing.

- [ ] **Step 6: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): add tooth-width <-> module helpers"
```

---

### Task 2: Group the three controls in the dialog (structural, no behavior change)

Pure refactor: wrap Module + Tooth fraction + the existing read-only Tooth-width text box in a
new "Tooth sizing" group, and route every reference to the moved inputs through the group's
children (matching the existing Advanced-group pattern). Behavior is identical to today.

**Files:**
- Modify: `commands/generateGears/entry.py` (build section ~114–125; helpers/handlers that
  reference `module`/`toothFraction`/`featureWidthInfo`)

- [ ] **Step 1: Add a children-accessor helper**

In `commands/generateGears/entry.py`, add near the other module-level helpers (e.g. just above
`_update_feature_width_display`, ~line 167):

```python
def _tooth_inputs(inputs):
    """Children of the 'Tooth sizing' group (module / toothFraction / toothWidth).
    itemById is treated as non-recursive here, so nested inputs are reached via .children."""
    return inputs.itemById('toothSizing').children
```

- [ ] **Step 2: Build the group instead of three loose inputs**

Replace the build block at lines 114–125:

```python
    futil.log('build: module')
    inputs.addValueInput('module', 'Module (mm)', 'mm',
                         adsk.core.ValueInput.createByReal(s['module_mm'] * 0.1))

    futil.log('build: toothFraction')
    inputs.addValueInput('toothFraction', 'Tooth fraction', '',
                         adsk.core.ValueInput.createByReal(s['tooth_fraction']))

    futil.log('build: featureWidthInfo')
    # Feature width is DERIVED -> a read-only text box (info only), not editable.
    fwi = inputs.addTextBoxCommandInput('featureWidthInfo', 'Tooth width', '', 1, True)
    fwi.isFullWidth = False
```

with:

```python
    futil.log('build: toothSizing group')
    tsz = inputs.addGroupCommandInput('toothSizing', 'Tooth sizing')
    tsz.isExpanded = True
    t = tsz.children
    t.addValueInput('module', 'Module (mm)', 'mm',
                    adsk.core.ValueInput.createByReal(s['module_mm'] * 0.1))
    t.addValueInput('toothFraction', 'Tooth fraction', '',
                    adsk.core.ValueInput.createByReal(s['tooth_fraction']))
    fwi = t.addTextBoxCommandInput('featureWidthInfo', 'Tooth width', '', 1, True)
    fwi.isFullWidth = False
```

- [ ] **Step 3: Route `_update_feature_width_display` through the group**

Replace the body of `_update_feature_width_display` (lines 167–175):

```python
def _update_feature_width_display(inputs):
    """Recompute the derived feature width into the read-only text box (mm)."""
    try:
        module_mm = inputs.itemById('module').value / 0.1
        tf = inputs.itemById('toothFraction').value
        fw = tf * math.pi * module_mm
        inputs.itemById('featureWidthInfo').text = f'{fw:.3f} mm'
    except Exception:
        pass
```

with:

```python
def _update_feature_width_display(inputs):
    """Recompute the derived feature width into the read-only text box (mm)."""
    try:
        t = _tooth_inputs(inputs)
        module_mm = t.itemById('module').value / 0.1
        tf = t.itemById('toothFraction').value
        fw = gear_math.tooth_width_from_module(module_mm, tf)
        t.itemById('featureWidthInfo').text = f'{fw:.3f} mm'
    except Exception:
        pass
```

- [ ] **Step 4: Route `_read_inputs` through the group**

In `_read_inputs` (lines 203–204), change:

```python
    module_mm = inputs.itemById('module').value / 0.1          # cm -> mm
    tooth_fraction = inputs.itemById('toothFraction').value
```

to:

```python
    t = _tooth_inputs(inputs)
    module_mm = t.itemById('module').value / 0.1               # cm -> mm
    tooth_fraction = t.itemById('toothFraction').value
```

- [ ] **Step 5: Route `_persist_settings` through the group**

In `_persist_settings` (lines 286–287), change:

```python
        'module_mm': inputs.itemById('module').value / 0.1,
        'tooth_fraction': inputs.itemById('toothFraction').value,
```

to:

```python
        'module_mm': _tooth_inputs(inputs).itemById('module').value / 0.1,
        'tooth_fraction': _tooth_inputs(inputs).itemById('toothFraction').value,
```

(`command_input_changed` matches on `changed.id`, which is unaffected by nesting — no change
needed there in this task.)

- [ ] **Step 6: Syntax-check the Fusion layer**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py`
Expected: no output (compiles clean).

- [ ] **Step 7: Manual verification in Fusion (user)**

Reload the add-in and open the dialog. Confirm:
- Module, Tooth fraction, and the read-only Tooth-width readout now appear inside a **"Tooth
  sizing"** group (expanded).
- Editing Module or Tooth fraction still updates the Tooth-width readout.
- Generating a gear still works and the ratio readout is unchanged.

- [ ] **Step 8: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "refactor(fusion): group module/tooth-fraction/tooth-width in a Tooth sizing group"
```

---

### Task 3: Make tooth width editable and bidirectionally linked

Swap the read-only text box for an editable value input and replace the one-way display update
with the three-way coupling, guarded against reentrancy.

**Files:**
- Modify: `commands/generateGears/entry.py` (group build; `command_input_changed`; replace
  `_update_feature_width_display` usage with the coupling handler)

- [ ] **Step 1: Replace the read-only text box with an editable value input**

In the build block from Task 2, replace these two lines:

```python
    fwi = t.addTextBoxCommandInput('featureWidthInfo', 'Tooth width', '', 1, True)
    fwi.isFullWidth = False
```

with:

```python
    t.addValueInput('toothWidth', 'Tooth width (mm)', 'mm',
                    adsk.core.ValueInput.createByReal(
                        gear_math.tooth_width_from_module(s['module_mm'], s['tooth_fraction']) * 0.1))
```

- [ ] **Step 2: Add the coupling handler (replaces the display updater)**

Add a module-level guard flag near the top of the module (with the other module-level globals,
e.g. just after the imports/`app =` lines):

```python
_linking = False  # reentrancy guard: setting ValueInput.value re-fires command_input_changed
```

Replace `_update_feature_width_display` (the whole function) with `_relink_tooth_sizing`:

```python
def _relink_tooth_sizing(inputs, changed_id):
    """Keep module / tooth fraction / tooth width consistent with
    tooth_width = tooth_fraction * pi * module. The edited field plus the pinned
    field (tooth_fraction, except when it is itself edited) determine the third."""
    try:
        t = _tooth_inputs(inputs)
        module_mm = t.itemById('module').value / 0.1
        tf = t.itemById('toothFraction').value
        width_mm = t.itemById('toothWidth').value / 0.1
        if changed_id == 'toothWidth':
            t.itemById('module').value = gear_math.module_from_tooth_width(width_mm, tf) * 0.1
        else:  # 'module' or 'toothFraction' -> recompute width, tooth_fraction/module pinned
            t.itemById('toothWidth').value = gear_math.tooth_width_from_module(module_mm, tf) * 0.1
    except (ValueError, ZeroDivisionError):
        pass  # in-progress edit (e.g. tooth_fraction == 0); leave fields as-is
```

- [ ] **Step 3: Wire the handler into `command_input_changed` with the guard**

Replace `command_input_changed` (lines 188–198):

```python
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs
    changed = args.input
    if changed.id in ('module', 'toothFraction'):
        _update_feature_width_display(inputs)
    elif changed.id in ('wheelTeeth', 'pinionTeeth'):
        _update_ratio_display(inputs)
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct
```

with:

```python
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    global _linking
    if _linking:
        return
    inputs = args.inputs
    changed = args.input
    if changed.id in ('module', 'toothFraction', 'toothWidth'):
        _linking = True
        try:
            _relink_tooth_sizing(inputs, changed.id)
        finally:
            _linking = False
    elif changed.id in ('wheelTeeth', 'pinionTeeth'):
        _update_ratio_display(inputs)
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct
```

- [ ] **Step 4: Remove the now-unused build-time display call**

At the end of the build section, line 162 calls `_update_feature_width_display(inputs)`. The
field is now initialized in Step 1, so delete that line:

```python
    futil.log('build: update feature width display')
    _update_feature_width_display(inputs)
    _update_ratio_display(inputs)
```

becomes:

```python
    futil.log('build: ratio display')
    _update_ratio_display(inputs)
```

- [ ] **Step 5: Syntax-check the Fusion layer**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py`
Expected: no output (compiles clean).

- [ ] **Step 6: Manual verification in Fusion (user)**

Reload the add-in and open the dialog. Confirm all three link directions, with no flicker/loop:
- Edit **Module** → Tooth width updates (Tooth fraction unchanged).
- Edit **Tooth fraction** → Tooth width updates (Module unchanged).
- Edit **Tooth width** → Module updates (Tooth fraction unchanged).
- Reopen the dialog after generating: values persist (module + tooth_fraction restored; width
  shows the matching derived value).
- Generate a gear and confirm geometry is unchanged from before this feature.

- [ ] **Step 7: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "feat(fusion): editable tooth width linked bidirectionally with module"
```

---

### Task 4: Keep docs in sync

**Files:**
- Modify: `README.md`
- Modify: `PerfectPrintGears.manifest` (only if its `description` describes tooth-width behavior)

- [ ] **Step 1: Check how the docs currently describe tooth width**

Run: `git grep -n -i "tooth width\|feature width\|read-only\|derived" README.md PerfectPrintGears.manifest`
Expected: lines describing tooth width as derived/read-only.

- [ ] **Step 2: Update README**

Edit the relevant README passage so it states that **Tooth width is an editable input, mutually
linked with Module** (editing either updates the other), and **Tooth fraction** is the third
coupled field (backlash knob), all tied by `tooth_width = tooth_fraction × π × module`. Replace
any "read-only / derived display" wording for tooth width.

- [ ] **Step 3: Update the manifest description if needed**

If `PerfectPrintGears.manifest`'s `description` mentions tooth width as derived/read-only, update
it to match. If it does not mention tooth-width behavior, leave it unchanged. **Do not** edit the
`version` field (python-semantic-release owns it).

- [ ] **Step 4: Verify the full suite still passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (engine unchanged since Task 1).

- [ ] **Step 5: Commit**

```bash
git add README.md PerfectPrintGears.manifest
git commit -m "docs: tooth width is now an editable, module-linked input"
```

---

## Notes for the implementer

- **mm ↔ cm:** Fusion `ValueInput`/`.value` for lengths are in **cm**; the engine works in **mm**.
  Multiply by `0.1` (mm→cm) when setting a length value input, divide by `0.1` (cm→mm) when
  reading. `toothFraction` is dimensionless — no scaling. This is why the coupling handler scales
  module and tooth width but not tooth fraction.
- **Why the guard:** assigning `ValueInput.value` inside `command_input_changed` triggers another
  `command_input_changed`. Without `_linking`, edit-width→set-module→fires→set-width→… loops.
- **No geometry / persistence change:** `GearInputs`, `derive_geometry`, `build_gear_pair`,
  `test_interference.py`, and `settings.defaults()` are untouched. Tooth width is a UI convenience
  derived from the persisted `(module_mm, tooth_fraction)`.
