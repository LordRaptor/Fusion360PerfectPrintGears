# Perfect Print Gears — Fusion 360 Add-in

A Fusion 360 add-in that generates **Perfect Print gears** as solid bodies: a
matched **driving + driven gear** pair built into a component you select.

Perfect Print gears are a 3D-print-optimized gear profile. Instead of an involute
or a classic cycloid, both gears have **constant-width teeth** — each working flank
is a straight line parallel to a gear radial — and the **driving** gear's tip is the
exact **conjugate** of the **driven** gear's straight flank. The result meshes with
constant velocity, low friction, and prints cleanly without fine involute detail.

> ### Credit
> The **Perfect Print gear** concept is the work of **[Steve Peterson](https://www.stevesclocks.com)**,
> documented in his *[Clock Design Guidelines](https://www.myminifactory.com/object/3d-print-clock-design-guidelines-pdf-714119)*
> (pp. 61–66, "Perfect Print Gears"). This add-in is an independent implementation of that method;
> all credit for the gear design itself belongs to Steve Peterson. Please refer to his guidelines for
> the background and rationale behind the approach.

---

## What it does

- Generates a **driving** and a matching **driven** gear as **solid bodies** — each tooth is
  extruded and circular-patterned from a parametric sketch (the driving gear fully
  constrained; the driven gear left with one alignment DOF, see below).
- Builds them in **meshing layout**: driving gear at the origin, driven gear at the center
  distance, pitch circles tangent.
- Leaves the **driven gear free to swing** around the driving gear (its pitch stays tangent, so
  the center distance is fixed) so you can **align it with existing features** — add
  your own constraint (coincident to an axle point, an angle dimension, collinear to
  an edge) to lock it where you want. A target at the wrong spacing simply won't solve.
- Supports **reductions** (driving < driven, output slower), **step-ups** (driving > driven),
  and **1:1** — any tooth counts ≥ 6 on both, including clock motion-work style reductions.
  Very low driving-gear tooth counts mesh more tightly; use `tooth_fraction` ≈ 0.40–0.45 for
  extra backlash in those cases.
- Persists your last-used settings on the document and pre-fills them next run.
- Also ships a separate **[Gear Train Calculator](#gear-train-calculator)** — a display-only
  palette that finds compound gear trains hitting an exact target ratio (it creates no geometry).

Because the driving gear tip is conjugate to one specific driven gear, **every driving/driven
pair is unique** and must be generated together for its mating partner.

---

## Installation

1. Download/clone this repository to a local folder.
2. In Fusion 360: **Utilities → Add-Ins → Scripts and Add-Ins**.
3. On the **Add-Ins** tab, click the green **+**, select this folder, and **Run**
   (tick *Run on Startup* if you want it loaded automatically).
4. Two commands appear: **Solid → Create → Generate Perfect Print Gears**, and
   **Utilities → Add-Ins → Gear Train Calculator** (the palette).

---

## Usage

Open **Solid → Create → Generate Perfect Print Gears** and set:

| Input | Meaning |
|---|---|
| **Driving gear component** | Component to build the driving gear into (defaults to the active component). |
| **Driven gear component** | Component to build the driven gear into (defaults to the **same as the driving gear**). Select different components to split the pair across components — the driven gear still meshes to the driving gear across components. To put both in one specific component, set it here as the driving gear and leave this empty (Fusion won't allow the same component in both pickers). |
| **Sketch plane** *(optional)* | Construction plane or planar face the gear sketches are drawn on (defaults to the root XY plane). Shared by both gears so they stay coplanar and mesh. A picked face is used via a coincident construction plane, so even a small axle-top face works. |
| **Driving gear center** *(optional)* | Point (sketch point, construction point, or vertex) to place the driving gear center on (defaults to the sketch origin). The driven gear meshes relative to the driving gear. |
| **Driving / Driven gear teeth** | Tooth counts, each ≥ 6. The driving gear carries the conjugate tip; either may be larger, so the pair can be a **reduction** (driving < driven), **step-up** (driving > driven), or **1:1**. |
| **Gear ratio** *(read-only)* | Displays the resulting ratio as a decimal and reduced integer form, e.g. `3.33 : 1 (10 : 3)`. Updates live as tooth counts change. |
| **Sizes** *(read-only)* | Previews each gear's **pitch diameter** (`module × teeth`) and the **center distance** between them (sum of pitch radii). Updates live as tooth counts or module change. |
| **Tooth sizing → Module (mm)** | Sets the tooth size / pitch. `circular pitch = π · module`. Mutually linked with tooth width (editing one updates the other). |
| **Tooth sizing → Tooth width (mm)** | The physical tooth width — **editable and mutually linked with module**. Editing it back-solves the module at the current tooth fraction (`module = tooth_width / (tooth_fraction · π)`); editing module or tooth fraction recomputes it (`tooth_width = tooth_fraction · π · module`). Lets you dial in a specific width for 3D printing. |
| **Tooth sizing → Tooth fraction** | Tooth width as a fraction of the circular pitch (0–0.5). **This is the backlash knob:** 0.5 = equal tooth and space; below 0.5 thins the teeth for circumferential play. Editing it recomputes tooth width (module pinned). |
| **Clearance** | Radial tip-to-root play (absolute mm or % of tooth width). Independent of tooth fraction. |
| **Advanced → Dedendum factor** | Optional root-depth scaling. |
| **Advanced → Tip control points** | Control points per driving-gear tip half: **4** (degree-3 Bézier, default) or **5–6** (degree-5). The tip is a control-point spline, so it is fully constrained and the driving gear can be rotated by editing its orientation dimension. |
| **Advanced → Tangent tip join** | Make the tip leave the flank join **tangent** (smoother) instead of the faithful conjugate corner. Fits the envelope less well — a warning recommends 5+ control points when this is enabled. |

Click **OK** to draw the pair. Invalid combinations disable OK and show an inline
message.

### The two kinds of play
- **Tooth fraction → circumferential backlash** (flank-to-flank): `backlash = CP · (1 − 2 · fraction)`.
- **Clearance → radial clearance** (tip-to-root bottoming).

---

## Gear Train Calculator

A second command adds a non-modal **Palette** (UTILITIES tab → ADD-INS panel → *Gear Train
Calculator*) that searches for **compound clock gear trains** hitting an **exact** target
ratio. It is a pure calculator — it creates no geometry.

Enter a target ratio as `input : output` — turns of the input per turn of the output, any
positive rational (e.g. `12 : 1` for a minutes-to-hours reduction, where the input turns 12×
for each output turn) — plus a stage-count range and a single tooth-count range that every
gear draws from. Each stage is one driving/driven mesh and may step the speed up or down, so
the search covers both directions. Options:

- **Rotation** — filter to trains whose output turns the *same* as, or *opposite* to, the
  input (this is a stage-count parity filter, independent of speed).
- **Coaxial input/output** — require the input and output to share one shaft. This forces
  every stage to share one tooth sum (equal center distance at one module) and at least two
  stages.
- **End gears (optional)** — independently bound the **input gear** (the first stage's
  driving gear) and/or the **output gear** (the last stage's driven gear) with their own
  min/max, each a narrowing within the general tooth range. Enable either with its checkbox
  (both min and max are required when checked). Useful when the end gears sit in tighter
  spots than the middle gears. When a bound is set, each result's stages are listed in
  **input → output** order so you can read off which gear is which.

Results list each train's stages (`driving ÷ driven` tooth counts), the exact achieved ratio
(shown `input : output` to match the target you entered), gear count, rotation direction, and
per-stage tooth sum. Following Steve Peterson's convention, the tooth
sum (∝ center distance) helps you judge gear sizes when picking a solution. Results are exact
by construction and ordered fewest-stages-then-most-compact, capped at 200. Gear-train ratio
search is combinatorially large, so for loose targets over wide ranges the search is bounded
for responsiveness and returns a **partial** list (flagged in the palette) — narrow the tooth
range or stage count for a complete result. You read a result and set up the gears yourself
(e.g. with the generator command).

---

## How the geometry works

The driving gear tip is generated as the **conjugate** of the straight driven gear flank, using
one consistent kinematic model (the driven gear rotates `+τ` about its center while the
driving gear rotates `−τ/ratio` about its). For a straight flank the contact point is the
**foot of the perpendicular from the pitch point onto the flank**; sweeping `τ`
traces the tip locus. It is trimmed from the flank join up to the centerline apex,
mirrored, and represented as a **control-point (Bézier) spline** — a degree-3
(4 control points) or degree-5 (6) curve fitted to the envelope (~3 µm at degree 3).
A control-point spline has no tangent handles, so its control points can be fully
constrained — which is what lets the driving gear sketch be **rotated** by editing an angle
dimension. By default the join to the flank is **not** tangent — there is a real
~12° corner; forcing tangency (the optional *Tangent tip join*) deviates from the
true envelope more, so the faithful non-tangent shape is the default. The apex is a
sharp point (your printer rounds it).

The **driven** gear tip is a small **elliptical cap** (Steve Peterson's refinement):
an oval whose tangential (major) axis spans the tooth width and whose radial (minor)
axis is shorter (75% aspect), so the tip is flatter than a plain semicircle and is
centered slightly **inside** the pitch circle. This rounds off the leading corners
that would otherwise touch before the line of centers, cutting tip interference and
friction — with little effect on the rolling, since the previous tooth is still
engaged. The tip is **free** (non-working); only the flanks carry load. Because the
cap is an ellipse, the driven flanks end just inside the pitch circle (at the
ellipse's co-vertices, where the cap meets them tangentially) rather than on it.

The engine (`core/gear_math.py`) is **pure Python** (no Fusion, no third-party
deps), so the conjugation math is unit-tested without Fusion — including a
**conjugacy/interference test** that rolls the closed gear outlines through a full
mesh cycle and checks the penetration depth stays at the approximation noise floor
(validated to ~0 across several ratios).

---

## Development

```bash
python -m pytest tests/ -q      # pure-engine + interference tests (no Fusion needed)
```

The Fusion layer (`core/sketch_builder.py`, `commands/generateGears/entry.py`)
cannot be driven headless; it is verified by loading the add-in in Fusion.

### Project layout

| Path | Responsibility |
|---|---|
| `core/gear_math.py` | Pure conjugation engine — no `adsk` import. |
| `core/gear_train.py` | Pure gear-train search engine (exact ratios) — no `adsk` import. |
| `core/sketch_builder.py` | Renders engine output into Fusion sketches, then extrudes + patterns them into solids. |
| `core/settings.py` | Pure (de)serialization of dialog settings. |
| `commands/generateGears/entry.py` | Gear generator: command, dialog, validation, persistence. |
| `commands/calcGearTrain/entry.py` | Gear train calculator: palette launcher + engine bridge. |
| `tests/` | pytest for the engines, settings, and interference guard. |

---

## Scope

Solid gear bodies (extrude + circular pattern) — no fillets, bores, or motion
links; one driving + driven gear mesh per run (the pair can be split across two
components or built into one); spur gears only (non-helical/bevel/internal).

## License & attribution

The Perfect Print gear method is credited to **Steve Peterson** (*Clock Design
Guidelines*). This repository is an independent add-in implementing it.

This add-in is licensed under the **[Apache License 2.0](LICENSE)**. The license
covers the add-in's source code only, not the underlying gear design method. See
[`NOTICE`](NOTICE) for third-party attributions (the add-in scaffolding derives
from Autodesk's Fusion 360 sample template).
