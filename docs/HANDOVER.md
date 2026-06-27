# Perfect Print Gears — Handover / Context Summary

**Date:** 2026-06-27
**Status:** **v1 complete and validated** — merged to `main` via **PR #1**
(https://github.com/LordRaptor/Fusion360PerfectPrintGears/pull/1).
The hard problem (the conjugate wheel-tip geometry) is **solved**; the add-in generates solid
gears with **fully parametric, fully constrained** sketches. 38 pytest tests pass.

**Post-v1 refinements:** the dialog now shows a live **gear-ratio readout**
(decimal + GCD-reduced integer, e.g. `3.33 : 1 (10 : 3)`) and a read-only **Tooth width** field
(renamed from "Feature width"). The default `tooth_fraction` is now **0.45** (was 0.5) for
meshing backlash. Two sketch-constraint over/degenerate-constraint errors were cleared — see the
notes in §3 (wheel tip apex) and §5 (pinion cap). Both gears build with a **clean log**.

**Placement & targeting (this session, branch `feat/placement-targeting`):** three optional
dialog inputs, each defaulting to today's behaviour — see the spec/plan dated 2026-06-27:
- **Wheel component / Pinion component** — build the two gears into separate components. Each
  resolves to `(component, occurrence)`; sketches are created with `occurrenceForCreation` on a
  root-level shared plane, and the pinion projects the wheel's pitch circle via a
  `createForAssemblyContext` proxy for the cross-component mesh. An empty pinion field defaults to
  the wheel's component (Fusion blocks picking the same entity in two selection inputs).
- **Sketch plane** — a construction plane *or planar face* (shared by both gears, default root XY).
  A picked **face is converted to a coincident construction plane** (`setByOffset` 0) before
  sketching, so the face's edges can't fragment the disk / add a leftover region (this bit us with
  a small concentric axle-top face). `build_gear` now also draws each gear **at its final location**
  (wheel at the picked point, pinion at wheel+center-distance) rather than drawing-then-moving — the
  `isFixed` tip spline tears if the centre is moved by constraint.
- **Wheel center** — a point (sketch point / construction point / vertex) the wheel centre sits on
  (`project2`, linked); the tip-mirror match reflects about the actual centerline (`y=2*cy-y`), not
  the global X axis, so an off-origin centre still solves.

> This supersedes the older handover (which described the geometry as unsolved). That saga is
> over — see §3.

---

## 1. What this project is

A Fusion 360 Python add-in that generates Steve Peterson's **"Perfect Print" gears** — a
3D-print-optimized constant-width cycloidal profile — as a matched **wheel + pinion** pair.
Output is now **solids** (extrude + circular pattern), drawn into a user-selected component.

- **Credit:** the Perfect Print gear concept is Steve Peterson's (*Clock Design Guidelines*,
  pp. 61–66). The README credits him; keep that.
- **Spec:** `docs/superpowers/specs/2026-06-26-perfect-print-gears-design.md` (revised for the
  validated geometry).
- **Plan:** `docs/superpowers/plans/2026-06-26-perfect-print-gears.md` (revised; has REVISED
  callouts pointing at the validated approach).
- **Source PDF:** `tmp/Clock_Design_Guidelines_2025_Nov.pdf` pp. 61–66 (gitignored).

---

## 2. Architecture & key files

Pure-Python engine (no `adsk`, no numpy) → thin Fusion layer. mm in the engine; the Fusion
layer converts mm→cm (`MM_TO_CM = 0.1`).

| File | Responsibility |
|---|---|
| `core/gear_math.py` | **Pure** geometry engine: inputs, derived geometry, validation, the conjugate wheel-tip envelope, tooth builders, arraying, `closed_gear_polygon` (for the interference test). No `adsk`. |
| `core/sketch_builder.py` | Fusion layer: sketch one tooth → extrude (disk + tooth) → circular pattern → solid gear; **applies all the parametric constraints**. |
| `core/settings.py` | Pure (de)serialization of dialog settings + length resolution. |
| `commands/generateGears/entry.py` | Command, dialog inputs, validation, persistence, execute. |
| `lib/fusionAddInUtils/general_utils.py` | Logging (file + Text Commands palette + Fusion log) and error handling. |
| `tests/test_gear_math.py`, `tests/test_settings.py`, `tests/test_interference.py` | pytest (engine + settings + conjugacy/interference guard). |
| `PerfectPrintGears.py` | `run`/`stop`; shows a load message box (with the log path). |

**Run tests:** `.venv/Scripts/python.exe -m pytest tests/ -q` → **38 passed**. The Fusion
layer can only be `py_compile`d here; final verification is manual in Fusion (user's job).

**Logs (for debugging the add-in in Fusion):**
- `PerfectPrintGears.log` next to the add-in (gitignored).
- Fusion app log: `C:\Users\Raptor\AppData\Local\Autodesk\Autodesk Fusion 360\<id>\logs\AppLogFile*.log`.
- Live: View → Show Text Commands palette.

---

## 3. The geometry (SOLVED — do not re-derive)

The wheel tip is the **conjugate** of the straight, constant-width pinion flank, built by
Peterson's envelope with **one consistent kinematic model** used for both generation and the
interference test (this consistency is what fixed the long-running failure):
- pinion rotates `+tau` about `O_p`; wheel rotates `-tau/ratio` about `O_w`.
- The contact point is the **foot of the perpendicular from the pitch point onto the flank**
  (exact for a straight flank), carried into the wheel frame. Cross-checked against
  consecutive-line intersection (agree ~0.01 mm).
- Tip trimmed from the flank join to the centerline apex; mirrored; emitted as a **fitted
  spline of ~4 fit points/half** (the `resolution` input). Apex is a **sharp point** (printer
  smooths it).
- **Tooth width is derived from the module:** `w = TOOTH_FRACTION · π·module`. There are
  **no user parameters** for regeneration — Peterson's tip can't be regenerated parametrically;
  changing any input requires re-running the add-in. `TOOTH_FRACTION` (**default 0.45**) is the
  circumferential-backlash knob (0.5 = zero play; 0.45 ≈ 10% play); `clearance` is radial
  tip/root play. (The dialog field is now labelled **Tooth width**, shown read-only; the engine
  identifier is still `feature_width_mm`.)

**Validation:** `tests/test_interference.py` rolls closed gear polygons through a full mesh
cycle (point-in-poly + penetration depth, geometry-derived mesh zone) — ~0 µm at realistic
`TOOTH_FRACTION` across ratios 3/5/7. Earlier (wrong) methods were 220–410 µm.

**IMPORTANT geometry facts (don't "fix" these):**
- The wheel tip is **NOT tangent to the flank** — there's a real ~12° corner at the flank/tip
  join. Verified against a Fusion DXF export: the spline through the raw envelope points
  tracks the ideal envelope to ~6.4 µm and correctly reproduces that corner. Forcing tangency
  smooths a real feature and deviates *more* (~19 µm). Decision: keep it faithful (non-tangent).
- Pinion flanks end exactly **on the pinion pitch circle**; cap is a tangent semicircle.
- Roots sized from the **mating** tooth's tip height + clearance.

Memory store has the durable facts: `peterson-geometry-validated`, `fusion-addin-gotchas`,
`pinion-cap-flanks-end-on-pitch-circle`, `perfect-print-feature-width-constraint`,
`v1-status-and-followons`.

---

## 4. Fusion build pipeline (sketch → solid)

Matches the **FusionCycloidalGears** reference add-in
(`C:\Users\Raptor\AppData\Roaming\Autodesk\FusionAddins\FusionCycloidalGears`):
- Draw the **root circle (real)** + pitch/addendum (construction) + **one tooth**.
- Extrude the **disk** as a new body; extrude the **tooth** as a **Join** scoped via
  `participantBodies=[disk_body]` (so it never joins a pre-existing body like an axle — this was
  an explicit user requirement).
- **Circular-pattern only the tooth extrude** `teeth` times, using the **sketch circle as the
  axis** (no construction axis, no combine). One clean gear body.

### Fusion API gotchas (researched the hard way — see `fusion-addin-gotchas` memory)
- `ButtonRowCommandInput.listItems.add(name, sel)` **fails** ("Invalid argument icon") — items
  need a per-item icon. Use a **text-list `DropDownCommandInput`** instead.
- No native sketch pattern; use `sketch.copy(entities, Matrix3D)` if ever needed.
- **Spline symmetry is per-fit-point**, not curve-level (curve-level `addSymmetry` on splines
  is a no-op). Mirror a spline by symmetry-constraining each fit point.
- Button icons must be named `16x16.png`/`32x32.png`/`64x64.png` (+ `-dark`); `*-normal.png`
  isn't picked up. Icons live in `commands/generateGears/resources/`. (Icon cache: a full
  Fusion restart may be needed to see new icons.)
- A referenced (`sketch.include`) circle used only as a constraint reference must be set
  `isConstruction = True`, or it adds a profile and breaks the extrude.
- Attach command handlers FIRST in `command_created`, then build inputs in try/except that
  logs + message-boxes, so a failed input can't leave a dead dialog.

---

## 5. The parametric sketch constraints (v1, both gears fully constrained)

Built **collaboratively, one step at a time** with the user (this is the required working
mode — see §7). Every constraint/dimension call is wrapped in try/except + log.

**Wheel** (at origin):
- 3 circles concentric, centres coincident to the sketch origin; driving **diameter dims**.
- Construction **centerline** (centre → tip), coincident-to-origin + **horizontal** + end on
  the addendum circle.
- Flanks: bases coincident to root circle; f1 **parallel** to centerline; f2 **symmetric**
  about centerline; **equal** length (symmetry doesn't equalise length); **width** offset dim;
  **length** dim on f1.
- Tip: lower spline apex coincident to centerline end; **`isFixed`** on the lower spline (the
  conjugate shape can't be dimensioned); upper spline mirrored **per fit point** via symmetry —
  **except the apex fit point**, which lies on the centerline (its mirror is itself, so the
  symmetry there is degenerate and threw `VCS_SKETCH_SOLVING_FAILED`); it is skipped and the
  apex stays pinned by the centerline-end coincidence + the closed tooth loop.

**Pinion** (located by the mesh):
- 3 circles concentric (root/add centres coincident to pitch centre); diameter dims.
- Located relative to the wheel: the wheel pitch circle is **`include`d** (construction) and
  the pinion pitch circle is **tangent** to it; pinion centre **horizontal** with the wheel
  centre; **phase** pinned by an **angular dimension** between the pinion centerline and the
  line of centers.
- Flanks: bases on root; f1 parallel to centerline; f2 symmetric; width offset dim; flank
  **tops coincident to the pitch circle** (instead of a length dim — pinion flanks end there).
- Cap: arc endpoints **coincident with the flank tops**, then arc **tangent to ONE flank**.
  Both endpoints are pinned and the flanks are parallel, so a single tangent fixes the cap
  radius — a second tangent over-constrains (`VCS_SKETCH_OVER_CONSTRAINTS`), so only one is added.

---

## 6. NEXT — the follow-ons (not in v1)

The user will start these next (collaboratively, step by step):
1. ~~**Split wheel and pinion into their own components**~~ — **DONE** (branch
   `feat/placement-targeting`; see the Placement & targeting note at the top). Also done in that
   branch: selectable sketch plane / planar face, and a selectable wheel centre point.
2. **Rotate-the-arrangement option** — deliberately set up: the wheel centerline is
   horizontal-constrained and flanks are parallel to it, so rotating only needs to swap that
   horizontal for an **angle dimension**; the pinion phase already references the line of
   centers.
3. Optionally **wire phase/rotation (and maybe thickness/factors) into the dialog** as inputs.
4. (Lower priority) the original Task 18 acceptance checklist / extrude-one-tooth checks are
   effectively satisfied; tidy README/screenshots if desired.

---

## 7. Working mode (IMPORTANT — keep doing this)

- **Collaborative, step by step.** Propose ONE constraint/step, the user tests it in Fusion
  and confirms before the next. The user catches real errors (e.g. they corrected that symmetry
  doesn't equalise length, and that the tip corner is real). Don't batch many changes.
- **Research the Fusion API before using it** (WebFetch the help pages). Several plausible-but-
  wrong API calls cost cycles; verify signatures first.
- **Verify before claiming done:** run `pytest`; for Fusion, ask the user to test or to export
  a **DXF** to `tmp/fusion_sketches/` — `tmp/render_dxf.py` and `tmp/check_tangency.py` parse
  DXFs (needs `ezdxf`, installed in `.venv`).
- `.venv` has pytest, matplotlib, numpy, pymupdf, ezdxf. `tmp/` is gitignored (scratch +
  the original `peterson_*.py` derivation scripts + verification helpers).

---

## 8. TL;DR for resuming
v1 is done and in PR #1 (merging to main): validated conjugate geometry + a Fusion add-in that
builds **solid** wheel+pinion gears with **fully constrained parametric sketches**. The geometry
is solved — don't touch it (the ~12° flank/tip corner is intentional). Next work is the
**follow-ons** in §6 (split into components; rotate-the-arrangement option), done **step by step
with the user**. Read the memory files first.
