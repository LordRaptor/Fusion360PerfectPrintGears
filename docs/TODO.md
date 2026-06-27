# Add-in TODO

Pending changes to the Fusion add-in (dialog + settings). Captured during the
Peterson geometry rebuild (2026-06-27). Geometry math is being rebuilt first in
`tmp/peterson_step1.py`; these wire the results into the add-in UI afterward.

## Parameters / inputs

- [ ] **Feature width → read-only info display.** Feature width is no longer a
  user input. It is **derived from the module**: `w = TOOTH_FRACTION * CP`,
  where `CP = π · module`. Show it in the dialog as an informational
  (read-only) value so the user can see the resulting tooth width, but they
  cannot edit it directly.
  - Touch: `commands/generateGears/entry.py` (dialog), `core/settings.py`
    (stop persisting feature width as an input; compute on the fly).

- [ ] **Expose `TOOTH_FRACTION` as a user parameter** (default `0.5`).
  - Controls **circumferential backlash**: `backlash = CP · (1 − 2·TOOTH_FRACTION)`
    (flank-to-flank rotational play). `0.5` = equal tooth & space (zero
    circumferential backlash); lower = thinner teeth, more backlash.
  - This is the rotational/backlash knob.

- [ ] **Keep `clearance` as the radial play knob** (tip-to-root). Distinct from
  `TOOTH_FRACTION`. Two independent play controls:
  - `TOOTH_FRACTION` → rotational backlash (flank-to-flank)
  - `clearance` → radial clearance (tip-to-root bottoming)

## Notes / rationale

- Coupling feature width to the module means it can never violate the meshing
  constraint (`2w − c = CP − c < CP` always holds at `TOOTH_FRACTION = 0.5`),
  removing a class of invalid input. Printer minimum-feature limits are not a
  concern for this user.
- For the test case (module 1.5, Nw 50, Np 10): `CP = 4.7124`,
  `w = 2.3562`, `half_w = 1.1781`.

## Related (from HANDOVER.md, still pending)

- [ ] **Sketch constraints rework** — once the add-in runs, rework
  `core/sketch_builder.py` to use proper Fusion parametric constraints rather
  than placed geometry (see memory `sketch-constraints-rework`).
- [ ] **Task 18 — Fusion acceptance** — load the add-in, walk the acceptance
  checklist, write the README (see HANDOVER.md §8).
