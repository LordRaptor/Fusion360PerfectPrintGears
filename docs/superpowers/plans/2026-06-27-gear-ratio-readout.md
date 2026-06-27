# Gear Ratio Readout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the reduction ratio (decimal + GCD-reduced integer) implied by the current wheel/pinion tooth counts in the Generate dialog, updating live as either count changes.

**Architecture:** A pure `format_ratio(wheel_teeth, pinion_teeth) -> str` helper in the engine (`core/gear_math.py`) does all formatting and is unit-tested without Fusion. The Fusion layer (`commands/generateGears/entry.py`) adds a disabled `TextBoxCommandInput` under the teeth spinners and refreshes it from `command_input_changed`, mirroring the existing `featureWidthInfo` pattern.

**Tech Stack:** Python 3, pytest, Fusion 360 `adsk` API (Fusion layer not unit-testable here — `compileall` + manual test in Fusion).

---

### Task 1: `format_ratio` engine helper (TDD)

**Files:**
- Modify: `core/gear_math.py`
- Test: `tests/test_gear_math.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_gear_math.py` (after the imports / near the other top-level tests):

```python
# ------------------------------------------------------------------ ratio format
def test_format_ratio_integer_reduction():
    assert gm.format_ratio(60, 12) == "5.00 : 1 (5 : 1)"


def test_format_ratio_non_integer():
    assert gm.format_ratio(50, 15) == "3.33 : 1 (10 : 3)"


def test_format_ratio_equal_counts():
    assert gm.format_ratio(20, 20) == "1.00 : 1 (1 : 1)"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gear_math.py -q -k "format_ratio"`
Expected: FAIL — `AttributeError: module 'core.gear_math' has no attribute 'format_ratio'`

- [ ] **Step 3: Write the minimal implementation**

Add to `core/gear_math.py` (after the `GearInputs`/geometry section is fine; `math` is already imported at the top of the module). Place it as a standalone top-level function:

```python
def format_ratio(wheel_teeth: int, pinion_teeth: int) -> str:
    """Human-readable reduction ratio: decimal to 2 dp plus the GCD-reduced
    integer pair, e.g. format_ratio(50, 15) == "3.33 : 1 (10 : 3)"."""
    decimal = wheel_teeth / pinion_teeth
    g = math.gcd(int(wheel_teeth), int(pinion_teeth))
    rw, rp = int(wheel_teeth) // g, int(pinion_teeth) // g
    return f"{decimal:.2f} : 1 ({rw} : {rp})"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gear_math.py -q -k "format_ratio"`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/gear_math.py tests/test_gear_math.py
git commit -m "feat(engine): add format_ratio helper for dialog ratio readout"
```

---

### Task 2: Wire the ratio readout into the dialog

**Files:**
- Modify: `commands/generateGears/entry.py`

This task is Fusion-layer code that imports `adsk`, so it cannot be unit-tested here. Verification is `compileall` (Step 4) plus a manual check in Fusion by the user (Step 6).

- [ ] **Step 1: Add the disabled text box under the teeth spinners**

In `_build_inputs`, immediately after the two teeth spinner lines (currently entry.py:81-82):

```python
    inputs.addIntegerSpinnerCommandInput('wheelTeeth', 'Wheel teeth', 6, 2000, 1, int(s['wheel_teeth']))
    inputs.addIntegerSpinnerCommandInput('pinionTeeth', 'Pinion teeth', 6, 2000, 1, int(s['pinion_teeth']))

    futil.log('build: ratioInfo')
    # Read-only readout of the reduction ratio implied by the tooth counts.
    rinfo = inputs.addTextBoxCommandInput('ratioInfo', 'Gear ratio', '', 1, True)
    rinfo.isFullWidth = False
```

- [ ] **Step 2: Add the `_update_ratio_display` helper**

Add a new helper next to `_update_feature_width_display` (after it, around entry.py:142):

```python
def _update_ratio_display(inputs):
    """Recompute the reduction-ratio readout from the current tooth counts."""
    try:
        wt = inputs.itemById('wheelTeeth').value
        pt = inputs.itemById('pinionTeeth').value
        inputs.itemById('ratioInfo').text = gear_math.format_ratio(wt, pt)
    except Exception:
        pass
```

- [ ] **Step 3: Call it at build time and on input change**

In `_build_inputs`, where it currently calls `_update_feature_width_display(inputs)` at the end (entry.py:130), add the ratio update right after:

```python
    futil.log('build: update feature width display')
    _update_feature_width_display(inputs)
    _update_ratio_display(inputs)
    futil.log('build: inputs done')
```

In `command_input_changed`, extend the dispatch so tooth-count changes refresh the ratio. Replace the existing branch (entry.py:148-153):

```python
    if changed.id in ('module', 'toothFraction'):
        _update_feature_width_display(inputs)
    elif changed.id in ('wheelTeeth', 'pinionTeeth'):
        _update_ratio_display(inputs)
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct
```

- [ ] **Step 4: Syntax-check the Fusion layer**

Run: `.venv/Scripts/python.exe -m compileall -q commands/generateGears/entry.py`
Expected: no output (success; non-zero exit only on a syntax error).

- [ ] **Step 5: Run the full test suite (nothing should regress)**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all tests pass (35 prior + 3 new from Task 1 = 38 passed).

- [ ] **Step 6: Manual verification in Fusion (user)**

Ask the user to load/reload the add-in in Fusion, open **Generate Perfect Print Gears**, and confirm:
- A "Gear ratio" field appears under the two teeth spinners.
- It reads `5.00 : 1 (5 : 1)` at the defaults (wheel 50 / pinion 10).
- Changing Wheel teeth to 50 and Pinion teeth to 15 updates it live to `3.33 : 1 (10 : 3)`.

- [ ] **Step 7: Commit**

```bash
git add commands/generateGears/entry.py
git commit -m "feat(fusion): show live gear ratio readout in the generate dialog"
```

---

### Task 3: Update docs

**Files:**
- Modify: `README.md`
- Check (likely no change): `PerfectPrintGears.manifest`

- [ ] **Step 1: Inspect the README dialog/usage section and the manifest description**

Read `README.md` and locate where the dialog inputs are described. Read the `description` field in `PerfectPrintGears.manifest`.

- [ ] **Step 2: Add the ratio readout to the README**

In the README's dialog/inputs description, add a line noting the dialog displays the resulting gear ratio (decimal plus reduced integer form, e.g. `3.33 : 1 (10 : 3)`) live as the tooth counts change. Match the surrounding wording/format.

- [ ] **Step 3: Decide on the manifest**

The `manifest` `description` is a one-line high-level summary; this informational readout does not change what the add-in produces, so leave it unchanged unless it enumerates dialog fields (it does not). Make no edit if so.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: note the gear ratio readout in the dialog"
```

---

## Self-Review

- **Spec coverage:** `format_ratio` helper (Task 1) ✓; disabled text box under spinners + live update via `command_input_changed` (Task 2) ✓; tests for integer/non-integer/equal counts (Task 1) ✓; README mention + manifest check (Task 3) ✓. All spec sections covered.
- **Placeholder scan:** No TBD/TODO; all code shown in full; commands have expected output.
- **Type consistency:** `format_ratio(wheel_teeth, pinion_teeth) -> str` is defined in Task 1 and called identically in `_update_ratio_display` (Task 2). The input id `ratioInfo` is created in Task 2 Step 1 and referenced in Task 2 Steps 2-3. `gear_math` is already imported in `entry.py` (entry.py:8).
