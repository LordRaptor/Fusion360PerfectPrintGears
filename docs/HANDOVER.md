# Perfect Print Gears — Handover / Context Summary

**Date:** 2026-06-27
**Branch:** `feat/perfect-print-gears`
**Status:** Add-in scaffolding, engine plumbing, Fusion layer, and UI are all built and
committed (26 pytest tests pass). **The one unsolved problem is the wheel-tooth tip
geometry** — generating the correct *conjugate* profile for Perfect Print constant-width
gears. Next step (user's decision): **reconstruct Peterson's envelope method from scratch.**

---

## 1. What this project is

A Fusion 360 Python add-in that generates Steve Peterson's **"Perfect Print" gears** — a
3D-print-optimized cycloidal gear profile — as **sketches** (not bodies): a matched
**wheel + pinion** pair drawn into a user-selected component.

- **Spec:** `docs/superpowers/specs/2026-06-26-perfect-print-gears-design.md`
- **Plan:** `docs/superpowers/plans/2026-06-26-perfect-print-gears.md` (18 tasks)
- **Source PDF:** `tmp/Clock_Design_Guidelines_2025_Nov.pdf`, pp. 61–66 (the Perfect Print
  method). Rendered diagrams at `tmp/pdfimg/page62.png … page65.png`.
- **Reference add-ins studied:**
  - FusionCycloidalGears (Keveney) — `C:\Users\Raptor\AppData\Roaming\Autodesk\FusionAddins\FusionCycloidalGears` — modern template, working cycloidal math (`radiusAtAngle`).
  - SpurGear (Autodesk) — `…\webdeploy\production\…\Python\Samples\SpurGear` — settings persistence, spline drawing, `isComputeDeferred`.

### The gear definition (important)
- **Both** wheel and pinion teeth are **constant width**: each working flank is a straight
  line **parallel to a gear radial, offset by ±half the "feature width"** (Peterson uses
  0.094″ = 2.388 mm). This decouples tooth thickness from pitch (tuned to the printer).
- **Pinion tip:** free **rounded semicircle of radius = half_width, centered ON the pinion
  pitch circle** (Peterson's diagram; user-confirmed). Never contacts the wheel.
- **Wheel tip:** the **conjugate-generated** curve that meshes with the straight pinion
  flank. **This is the hard part that is not yet correct.**

---

## 2. Plan execution status (subagent-driven)

| Plan tasks | What | Status |
|---|---|---|
| 1 | Scaffold (manifest, config, packages, ported utils, tests) | ✅ committed |
| 2–9 | Pure-Python engine (`core/gear_math.py`), TDD | ✅ committed, 21 tests |
| 10–11 | `core/sketch_builder.py` (draws sketches, tangent-arc tips) | ✅ committed — **NOT yet verified in Fusion** |
| 12–13 | `core/settings.py` (persistence + length resolution) | ✅ committed, 5 tests |
| 14–17 | `commands/generateGears/entry.py` (command, dialog, validation, execute, persistence) | ✅ committed — **NOT yet verified in Fusion** |
| 18 | README + manual Fusion acceptance | ❌ not done |

**The add-in is structurally runnable** (you can load it in Fusion), **but the generated
wheel tip is geometrically wrong** (interferes with the pinion), so it is not yet usable for
real gears. Task 18 (load in Fusion, acceptance checklist) has never been run.

### Verification environment
- `.venv` has **pytest 9.1.1**, **matplotlib 3.11**, **pymupdf** installed.
- Run engine tests: `python -m pytest tests/ -q` → **26 passed**.
- Fusion code (`sketch_builder.py`, `entry.py`) can only be `py_compile`d here, never executed (no headless Fusion). Final verification is manual in Fusion (the user's job).

---

## 3. Git state

Branch `feat/perfect-print-gears`, commits (newest first):
```
ae14a44 feat(ui): generateGears command, dialog, validation, and execute
8cb967a feat(settings): pure dialog-settings serialization and length resolution
ad35a33 feat(fusion): sketch builder with tangent-arc tips
7d59558 fix(engine): center pinion tip arc on the pitch circle
3970b5c Port validated cycloidal wheel-tooth geometry into the gear engine
5c8da58 fix(engine): bridge tooth roots into a single closed gear outline
bd8ecc4 test(engine): Peterson 50/10 golden check and second ratio
2817766 feat(engine): array teeth and assemble GearPair
2683ed6 feat(engine): pinion tooth with constant-width flanks and rounded tip
bbc7046 feat(engine): assemble one wheel tooth from mirrored tip + flanks
4d08c91 feat(engine): conjugate wheel-tip envelope
e748e74 feat(engine): 2d rotate and line-intersection helpers
ed73653 feat(engine): input validation
3c9da84 feat(engine): gear inputs and derived geometry
(30fc20f scaffold — first commit)
```
**Remote:** `origin` → `https://github.com/LordRaptor/Fusion360PerfectPrintGears.git`
(repo-local `http.sslBackend=schannel` was set to fix a cert error). `main` was pushed
once early; the feature branch has **not** been pushed.

### ⚠ Uncommitted working-tree changes
`core/gear_math.py` is **modified but not committed** — it contains an experiment that
sizes each gear's **root depth from the mating tooth's addendum + clearance**
(functions `_wheel_addendum_height`, `_pinion_addendum_height`, and a `foot_x = sqrt(root² −
half_w²)` fix in `build_pinion_tooth` so the pinion foot sits on the root circle). 26 tests
still pass. **Decision needed:** keep these (they're a genuine improvement over the old
fixed `1.25·module`) or revert. The `.idea/*` and `main.py` changes are incidental.

---

## 4. The engine (`core/gear_math.py`) — current API

Pure Python, **no `adsk` import**, all lengths in **mm**. Public symbols:
- `GearInputs(wheel_teeth, pinion_teeth, module_mm, feature_width_mm, clearance_mm, addendum_factor=1.0, dedendum_factor=1.0, resolution=24)`
- `DerivedGeometry`, `derive_geometry(inp)` → pitch radii, center_distance, ratio, circular_pitch
- `validate_inputs(inp)` → meshing constraint `2·feature_width − clearance < circular_pitch`, teeth minimums, etc.
- `rotate_point(p, center, angle)`, `line_intersection(...)`
- `radius_at_angle(a, pinion_teeth, wheel_teeth)` — cycloidal epicycloid (ported from Keveney)
- `wheel_tip_envelope(inp, geo, ...)` — the OLD consecutive-intersection envelope (preserved)
- `build_wheel_tooth(inp, geo, method='cycloidal')` → `_build_wheel_tooth_cycloidal` (default) / `_build_wheel_tooth_envelope`
- `build_pinion_tooth(inp, geo)` — straight flanks + semicircle cap on pitch circle
- `Segment(kind, points)` where kind ∈ `'line'|'spline'|'arc3'`
- `array_tooth(tooth, teeth, base_angle)`, `close_gear_loop(...)` (root-bridge arcs → closed loop)
- `GearProfile(role, teeth, center, pitch_radius, root_radius, addendum_radius, segments)`
- `GearPair(wheel, pinion, center_distance, circular_pitch)`
- `build_gear_pair(inp)` → validates, builds both teeth, arrays + closes loops, meshing layout (wheel at origin; pinion at `(center_distance, 0)`; pinion phased `base_angle = π + π/Np` so a GAP faces the wheel tooth)

**The committed default wheel tip is `method='cycloidal'`** (epicycloid). It is NOT truly
conjugate to our offset flank — see §6.

### Fusion layer (untested in Fusion)
- `core/sketch_builder.py` — `draw_gear(component, profile, name)`, `build_pair(component, pair)`. mm→cm (`MM_TO_CM=0.1`). Draws center point, construction circles (pitch/root/addendum), the outline (lines/fitted-splines/3-pt arcs). **Pinion rounded tips drawn as tangent arcs** with tangent constraints to both flank lines (defensive try/except). Per the user, after the add-in runs, the whole sketch generation should be **reworked to use as many proper Fusion constraints as possible** (currently mostly placed geometry; only tip tangency is constrained) — see memory `sketch-constraints-rework`.
- `commands/generateGears/entry.py` — Solid→Create button, dialog inputs (target component selection; wheel/pinion teeth; module mm; switchable absolute/% feature width & clearance; advanced group with addendum/dedendum factors + resolution), `inputChanged` mode toggles, `validateInputs` inline errors, `command_execute` builds the pair + draws + persists settings to a document attribute.
- `core/settings.py` — `defaults()` (module 1.5, feature_width 2.388, clearance 0.1, etc.), `to_json`, `from_json`, `resolve_length(is_percent, abs_mm, pct, basis_mm)`.

---

## 5. Key parameters / decisions (the agreed test case)

- **Module m = 1.5 mm**, **Nw = 50**, **Np = 10**, **feature width w = 2.388 mm** (half_w = 1.194), **clearance = 0.1 mm**, ratio = 5.
- Derived: **Rw = 37.5, Rp = 7.5, center distance C = 45**, circular pitch ≈ 4.712 mm, pitch point at **(37.5, 0)** on the line of centers.
- Why module 1.5 (not 0.8): the meshing constraint needs `w < ~CP/2`. Peterson's 2.388 mm implies module ≈ 1.5, not a small module. The original default (module 0.8 + width 2.388) was physically impossible — see memory `perfect-print-feature-width-constraint`.
- Defaults the user chose: "Peterson-like" module 1.5 + width 2.388.
- Output decisions (from the spec): sketches only (no bodies), two sketches (wheel + pinion) into a **user-selected component**, full toothed outline + center point + construction circles, **fitted splines** for tip curves, switchable absolute/% for width & clearance, rounded pinion tip, meshing layout, settings persistence.

---

## 6. THE GEOMETRY SAGA (read this before touching the tip)

**The problem:** find the wheel-tooth tip curve that is the exact **conjugate** to the
straight, constant-width (offset-from-radial) **pinion flank**, so the pair meshes with
zero interference. Standard cycloidal math doesn't apply directly because our pinion flank
is *straight and offset*, not the classic radial/cycloidal flank.

### Methods tried and their results (all on the m=1.5, 50/10 case)
1. **Cycloidal epicycloid** (`radius_at_angle`, the committed default): apex ≈ (40, 0),
   addendum ≈ 2.44. It is the conjugate to a **radial** flank, not our offset flank →
   **~0.22 mm flank interference**. Best so far but not correct.
2. **Consecutive-intersection envelope** (`wheel_tip_envelope`): noisy/unreliable
   extraction; apex ≈ 40 but **~0.41 mm** interference.
3. **Law of gearing** (contact = **foot of perpendicular from the pitch point to the
   straight flank**): apex ≈ 40.25; measured **~0.41 mm** — but likely contaminated by a
   generation-vs-test **phase mismatch** (see pitfalls). This is the most principled method
   and probably close to correct once kinematics are made consistent.
4. **User's "parallel-line" method:** intersect a line **parallel to the line of centers**
   (offset `o(θ)` from it) with the pinion flank, then de-rotate by **+θ** into the wheel
   frame. Offset `o(θ) = half_w·cos θ` or constant `half_w` are nearly identical because the
   whole tip is generated over only **~1.7° of wheel rotation** (so cos θ ≈ 1). Produces a
   clean ogive, apex ≈ 40 — essentially the **same curve as law-of-gearing**. Sign
   convention that works: pinion rotates **+5θ**, de-rotate by **+θ**; physically the wheel
   rotates **−θ** (opposite sense, external gears).
5. **Pinion-pitch-circle method:** intersect the pinion flank with the **pinion pitch
   circle**. **Clearly wrong** — tooth too tall (addendum ≈ 3.0), heavy overlap.

### KEY INSIGHTS (hard-won — don't relearn these)
- **The wheel∩pinion-flank intersection lies *on* the wheel flank**, so de-rotating it into
  the wheel frame can only ever slide along the flank → **degenerate** (flat line or
  radial). The traced point must be something else (a contact point, or a point carried by
  the pinion), not the raw two-flank crossing.
- **The contact point starts at the pitch point and moves *inward*** (toward the pinion
  center) as the flank rotates. It does **NOT** stay on the pinion pitch circle — that only
  happens if the pinion is *cycloidal*. For our straight/offset flank the contact follows
  the **foot-of-perpendicular (law-of-gearing) path**, which moves inward. (User's
  observation, confirmed.)
- **Root depth must be sized from the MATING tooth's addendum + clearance**, not a fixed
  `1.25·module`. And the flank **foot** must be placed at `sqrt(root_radius² − half_w²)` so
  it sits on the root circle (the pinion had a bug where it sat farther out). These fixes
  are in the **uncommitted** `gear_math.py` changes.
- Methods 3 and 4 **converge on the same tip** (apex ≈ 40), which is good corroboration that
  that curve is close to right — the remaining interference is most likely a **kinematic
  phase/sign mismatch in the verification**, not the curve.

### ⚠ Verification pitfalls (these caused several FALSE results)
The interference numbers were repeatedly wrong due to bugs in throwaway scripts. A
trustworthy interference test requires **all** of:
- **Closed polygons** — each gear's outline must include the **root-bridge arcs** between
  teeth (an open zig-zag makes `point_in_polygon` garbage → false 0 or false huge).
- **Correct transforms** — build the pinion in **local** coords (centered at origin) then
  place via `xf(poly, spin, C, 0)`. Do NOT pre-add `C` and then `xf` with `C` again (double
  translation flings it off-screen → false "0.0000 interference").
- **Point-in-polygon containment + penetration depth**, NOT nearest-point distance
  (nearest-distance can't tell "touching" from "overlapping" — it reported ~0.003 mm while
  the wheel tip was 0.6 mm into the pinion root).
- **Arc sampling through the mid point** — `arc3` is `[start, mid, end]`; sampling only
  start→end the "short way" produced *inverted (concave) pinion tips* and corrupted the
  polygon. `tmp/ghelpers.py::arc3_polyline` does this correctly.
- **Consistent kinematics** — generate the tip and test the mesh with the **same** pinion
  phase (`base = π + π/Np`) and the **same** rolling sign. A generation-vs-test phase
  mismatch is the leading suspect for the residual ~0.4 mm in methods 3/4.
- Penetration **counts** are not comparable across runs if the tip sampling density differs
  (a 1082-point tip inflates the count vs a 59-point tip). Use penetration **depth**.

---

## 7. Verification tooling in `tmp/` (gitignored, not committed)

- **`tmp/ghelpers.py`** — shared, *correct* helpers: `arc3_polyline` (through mid),
  `polygon`, `xf`, `point_in_poly`, `dist_to_poly`. **Reuse these.**
- `tmp/interference.py` — penetration sweep (max depth over the mesh cycle).
- `tmp/mesh_anim.py` — N-frame mesh animation with penetration highlight + pinion pitch
  circle (magenta).
- `tmp/construction.py` / `construction2.py` — step-by-step construction diagrams
  (pinion flank, parallel line / pitch circle, wheel flank −θ, centerline −θ, traced point).
- `tmp/lawgear.py` — law-of-gearing (foot-of-perpendicular) locus, 4 sign combos.
- `tmp/envtooth.py` — builds a wheel tooth from a tip + runs the (trustworthy) interference test.
- `tmp/mymethod.py` / `mymethod2.py` — user's parallel-line and pitch-circle methods.
- Others: `cycloidal.py`, `envelope_explore.py`, `conj.py`, `flanktrace.py`, `usermethod.py`,
  `one_tooth.py`, `pinion_check.py`, `plot_gears.py`, `where.py`, `verify_engine.py`.

These are all gitignored. If you clear context, the **methods and results are summarized
above** — you don't strictly need the scripts, but `ghelpers.py` is worth keeping.

---

## 8. NEXT STEP — reconstruct Peterson's envelope method from scratch

> ### ‼ WORKING MODE (read first)
> The geometry rebuild MUST be done **step by step, collaboratively with the user**. The
> agent must **NOT** go off and implement the whole method on its own. Propose one small
> step (a definition, a single construction element, a sign convention, a diagram), **show
> it / confirm it with the user, and wait** before proceeding to the next. The user is
> driving the derivation; the agent supplies math, code, and visualizations on request. Do
> not run the interference test or build the full tooth until the user asks. (This is why
> the previous long session worked — the user caught real errors the agent missed.)

User's decision: **go back to Peterson's method and rebuild it cleanly.** Peterson's literal
construction (PDF pp. 63–64):
1. Draw the pinion working flank as a line.
2. Copy it rotated about the **pinion center** in steps across **one pinion tooth pitch**
   (e.g. 10 copies, 3.6° each for a 10-tooth pinion).
3. Rotate each copy **up about the wheel center** by the **ratio-scaled** amount
   (0.72° each for 5:1) — i.e. line *k* gets `k·Δ` about the pinion and `k·Δ/ratio` about
   the wheel.
4. The **envelope** tangent to that family of lines is the wheel tip, drawn **from the
   pinion pitch circle to the tooth centerline**; mirror about the centerline; the wheel
   flanks below are straight.

### Recommendations for the rebuild
- Get the **reference flank phase right**: the meshing pinion presents a **gap** to the
  wheel tooth (teeth offset ±half-pitch). Generate the tip from the **actual contacting
  flank** at the meshing phase, and test against a pinion at the **same** phase/rolling sign
  (one consistent kinematic model — eliminates the §6 phase-mismatch suspect).
- Extract the envelope **robustly** (not raw consecutive-intersection): consider the
  **foot-of-perpendicular / law-of-gearing** characterization (the contact is the foot of
  the perpendicular from the pitch point to the straight flank) — it's exact for a straight
  flank and matches the "contact moves inward" observation. Methods 3 & 4 already produce
  the likely-correct curve (apex ≈ 40); the rebuild is mostly about **proving** it with a
  clean, consistent interference test.
- **Validate with the trustworthy interference test** (§6 pitfalls). Target: penetration
  depth ≈ 0 (within sampling noise) over the full mesh cycle, then a manual Fusion check.
- Keep the tip generator **pluggable** (the engine already has `method=` on
  `build_wheel_tooth`); add the new method alongside `cycloidal`/`envelope`.

### After the geometry is correct
- Wire the correct method as the default in `build_wheel_tooth`.
- Run **Task 18**: load the add-in in Fusion, walk the acceptance checklist (two sketches,
  correct meshing layout, extrude one wheel tooth to confirm closed profile, re-run pre-fills
  settings, invalid inputs disable OK), write the README.
- Then the planned **sketch-constraints rework** (memory `sketch-constraints-rework`).

---

## 9. Memory files written (in the agent memory store)
- `perfect-print-feature-width-constraint` — feature width < ~half circular pitch; module
  1.5 + width 2.388; wheel tooth is also constant-width with a conjugate tip.
- `sketch-constraints-rework` — after the add-in runs, rework sketch generation to use
  proper Fusion constraints.

---

## 10. TL;DR for resuming
The add-in is fully built except the **wheel tip is geometrically wrong** (cycloidal default
≈ 0.22 mm flank interference). The correct conjugate for our offset flank is almost
certainly the **law-of-gearing / Peterson-envelope** curve (apex ≈ 40 for the test case),
which methods 3 and 4 already produce; the blocker has been **buggy verification** and a
**generation-vs-test phase/sign mismatch**, not the curve itself. **Rebuild Peterson's
envelope cleanly with one consistent kinematic model, validate with the trustworthy
interference test (§6), then finish Task 18 (Fusion acceptance) and the constraints rework.**
Decide what to do with the **uncommitted root-depth changes** in `core/gear_math.py` first.
