# Gear Ratio Readout — Design

**Date:** 2026-06-27
**Status:** Approved, ready for implementation plan
**Scope:** Small, informational dialog enhancement. No geometry or output changes.

## Goal

Show the user the reduction ratio implied by their current wheel/pinion tooth counts,
directly in the Generate dialog, updating live as either count changes.

## Display format

"Both" the decimal and the GCD-reduced integer ratio — the two pieces of information not
already visible on screen (the raw tooth counts are shown in the two spinners above):

| Wheel / Pinion | Readout |
|---|---|
| 60 / 12 | `5.00 : 1 (5 : 1)` |
| 50 / 15 | `3.33 : 1 (10 : 3)` |
| 20 / 20 | `1.00 : 1 (1 : 1)` |

Decimal is `wheel / pinion` to 2 decimal places. The reduced pair divides both counts by
their GCD.

## Components

### `core/gear_math.py` — `format_ratio(wheel_teeth, pinion_teeth) -> str`

Pure helper, no `adsk`. Computes the 2-dp decimal and the GCD-reduced integer pair and
returns the formatted string (e.g. `"3.33 : 1 (10 : 3)"`). Lives in the engine so it is
unit-testable without Fusion. Uses `math.gcd`.

### `commands/generateGears/entry.py` — wiring

- **`_build_inputs`**: add a disabled `TextBoxCommandInput` for the ratio, placed directly
  under the two teeth spinners (after entry.py:81-82, before the module input). A text box
  (not a value input like `featureWidthInfo`) because the content is a formatted string,
  not a single scalar. Call `_update_ratio_display(inputs)` once at build time.
- **`_update_ratio_display(inputs)`**: new helper. Reads the two spinner values, calls
  `gear_math.format_ratio`, writes the result into the text box. Wrapped in try/except like
  `_update_feature_width_display`.
- **`command_input_changed`**: call `_update_ratio_display` when `wheelTeeth` or
  `pinionTeeth` changes (extend the existing `if changed.id in (...)` branch or add a new
  one).

## Data flow

`wheelTeeth` / `pinionTeeth` spinner change → `command_input_changed` →
`_update_ratio_display` → `gear_math.format_ratio` → formatted string written into the
disabled text box. One-directional, read-only; the field never feeds back into generation.

## Error handling

`_update_ratio_display` swallows exceptions (matching `_update_feature_width_display`) so a
transient bad state during dialog construction can't kill the dialog. `format_ratio` itself
is pure arithmetic on integers already constrained to ≥ 6 by the spinners, so it cannot
raise in practice.

## Testing

Add `test_format_ratio` to `tests/test_gear_math.py`:
- integer reduction: `60, 12` → `"5.00 : 1 (5 : 1)"`
- non-integer: `50, 15` → `"3.33 : 1 (10 : 3)"`
- equal counts: `20, 20` → `"1.00 : 1 (1 : 1)"`

The Fusion-layer wiring is verified manually in Fusion (user's job), as usual.

## Docs

Mention the ratio readout in `README.md`'s dialog description. Check the `manifest`
`description` field; it is high-level and likely does not need changing.

## Out of scope

No change to generated geometry or output. No new dialog inputs that affect the gear. No
new dependencies.
