# Editable, module-linked tooth width — design

**Date:** 2026-06-27
**Status:** design, approved for spec review

## Problem

Tooth width is currently a **derived, read-only** display: `tooth_width = tooth_fraction ×
π × module`. For 3D printing the user sometimes needs to dial in a specific physical tooth
width directly, rather than back-solving the module by hand.

## Goal

Make **tooth width an editable input**, mutually linked with module:

- edit **module** → tooth width updates
- edit **tooth width** → module recalculates

Keep the **tooth fraction** (backlash knob) as a third editable field. All three are tied by
the single equation above, so only two are ever independent; the edited field plus one pinned
field determine the third.

## The coupling rule

`tooth_width = tooth_fraction × π × module`

| User edits | Held constant | Recomputed |
|---|---|---|
| Module | tooth_fraction | tooth width |
| Tooth fraction | module | tooth width |
| Tooth width | tooth_fraction | module |

Rationale: tooth_fraction is the *backlash* knob — a property of the tooth relative to its
pitch — so it is the natural quantity to pin while converting between module and width. Editing
tooth_fraction itself is a deliberate backlash change at a fixed gear size (module pinned),
which thins/thickens the tooth (width recomputed).

## UI

A new **"Tooth sizing"** `GroupCommandInput` (expanded by default) replaces the three
standalone module-area controls, holding:

- **Module (mm)** — `ValueInput` (id `module`, moved into the group)
- **Tooth width (mm)** — `ValueInput` (id `toothWidth`, was the read-only `featureWidthInfo`
  text box; now editable)
- **Tooth fraction** — `ValueInput` (id `toothFraction`, moved into the group)

The read-only `featureWidthInfo` text box is removed.

## Implementation

### Pure engine (`core/gear_math.py`) — testable

Add two one-line helpers (and reuse them where the equation already appears):

- `tooth_width_from_module(module_mm, tooth_fraction) -> float`  → `tooth_fraction * π * module_mm`
- `module_from_tooth_width(width_mm, tooth_fraction) -> float`   → `width_mm / (tooth_fraction * π)`

`module_from_tooth_width` raises `ValueError` on non-positive `tooth_fraction` (guards a
divide-by-zero from an in-progress dialog edit; callers already wrap in try/except).

### Fusion layer (`commands/generateGears/entry.py`)

- Build the group and add the three `ValueInput`s to `group.children`; initialize `toothWidth`
  from `tooth_width_from_module(module, tooth_fraction)`.
- All existing references to `module` / `toothFraction` change to go through the group's
  `.children.itemById(...)` (the same pattern the Advanced group already uses — `itemById` is
  treated as non-recursive in this codebase). Affected: `_read_inputs`, `_persist_settings`,
  the changed-handler, and the build-time initializers.
- Replace `_update_feature_width_display` with the coupling handler in `command_input_changed`:
  - guard with a module-level `_linking` flag (setting `ValueInput.value` re-fires
    `command_input_changed`);
  - dispatch on `changed.id` per the table above, using the engine helpers and the
    cm↔mm scale (`* 0.1` / `/ 0.1`).

### Persistence & engine — unchanged

Source of truth stays `(module_mm, tooth_fraction)`. Tooth width is always derivable, so:

- no settings migration; `settings.defaults()` is untouched;
- `GearInputs`, `derive_geometry`, `build_gear_pair`, and `test_interference.py` are untouched;
- `_read_inputs` still reads module + tooth_fraction and computes `feature_width_mm` as today.

### Validation — unchanged

`validate_inputs` already enforces `module > 0` and `0 < tooth_fraction ≤ 0.5`. A width edit
only changes module (tooth_fraction pinned), so it cannot push tooth_fraction out of range.

## Tests

`tests/test_gear_math.py`:

- `tooth_width_from_module` matches `tooth_fraction · π · module` at known values;
- round-trip: `module_from_tooth_width(tooth_width_from_module(m, tf), tf) == m`;
- `module_from_tooth_width` raises on `tooth_fraction = 0`.

Full suite must stay green: `.venv/Scripts/python.exe -m pytest tests/ -q`. The dialog layer
is verified manually in Fusion by the user (it imports `adsk`).

## Docs to keep in sync

- `README.md` — tooth width is now an editable, module-linked input (not read-only).
- `PerfectPrintGears.manifest` `description` — only if it mentions tooth width behavior.

## Out of scope

No geometry change. No new persisted setting. The ~12° flank/tip corner and all conjugate
math are untouched.