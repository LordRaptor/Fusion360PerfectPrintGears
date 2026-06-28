# Perfect Print Gears — Fusion 360 Add-in

A Fusion 360 add-in that generates **Perfect Print gears** as solid bodies: a
matched **wheel + pinion** pair built into a component you select.

Perfect Print gears are a 3D-print-optimized gear profile. Instead of an involute
or a classic cycloid, both gears have **constant-width teeth** — each working flank
is a straight line parallel to a gear radial — and the wheel's tip is the exact
**conjugate** of the pinion's straight flank. The result meshes with
constant velocity, low friction, and prints cleanly without fine involute detail.

> ### Credit
> The **Perfect Print gear** concept is the work of **[Steve Peterson](https://www.stevesclocks.com)**,
> documented in his *[Clock Design Guidelines](https://www.myminifactory.com/object/3d-print-clock-design-guidelines-pdf-714119)*
> (pp. 61–66, "Perfect Print Gears"). This add-in is an independent implementation of that method;
> all credit for the gear design itself belongs to Steve Peterson. Please refer to his guidelines for
> the background and rationale behind the approach.

---

## What it does

- Generates a **wheel** and a matching **pinion** as **solid bodies** — each tooth is
  extruded and circular-patterned from a parametric sketch (the wheel fully
  constrained; the pinion left with one alignment DOF, see below).
- Builds them in **meshing layout**: wheel at the origin, pinion at the center
  distance, pitch circles tangent.
- Leaves the **pinion free to swing** around the wheel (its pitch stays tangent, so
  the center distance is fixed) so you can **align it with existing features** — add
  your own constraint (coincident to an axle point, an angle dimension, collinear to
  an edge) to lock it where you want. A target at the wrong spacing simply won't solve.
- Persists your last-used settings on the document and pre-fills them next run.

Because the wheel tip is conjugate to one specific pinion, **every wheel/pinion
combination is unique** and must be generated together for its mating partner.

---

## Installation

1. Download/clone this repository to a local folder.
2. In Fusion 360: **Utilities → Add-Ins → Scripts and Add-Ins**.
3. On the **Add-Ins** tab, click the green **+**, select this folder, and **Run**
   (tick *Run on Startup* if you want it loaded automatically).
4. The command appears under **Solid → Create → Generate Perfect Print Gears**.

---

## Usage

Open **Solid → Create → Generate Perfect Print Gears** and set:

| Input | Meaning |
|---|---|
| **Wheel component** | Component to build the wheel into (defaults to the active component). |
| **Pinion component** | Component to build the pinion into (defaults to the **same as the wheel**). Select different components to split the pair across components — the pinion still meshes to the wheel across components. To put both in one specific component, set it here as the wheel and leave this empty (Fusion won't allow the same component in both pickers). |
| **Sketch plane** *(optional)* | Construction plane or planar face the gear sketches are drawn on (defaults to the root XY plane). Shared by both gears so they stay coplanar and mesh. A picked face is used via a coincident construction plane, so even a small axle-top face works. |
| **Wheel center** *(optional)* | Point (sketch point, construction point, or vertex) to place the wheel center on (defaults to the sketch origin). The pinion meshes relative to the wheel. |
| **Wheel teeth / Pinion teeth** | Tooth counts (pinion ≥ 6, wheel ≥ pinion). |
| **Gear ratio** *(read-only)* | Displays the resulting ratio as a decimal and reduced integer form, e.g. `3.33 : 1 (10 : 3)`. Updates live as tooth counts change. |
| **Tooth sizing → Module (mm)** | Sets the tooth size / pitch. `circular pitch = π · module`. Mutually linked with tooth width (editing one updates the other). |
| **Tooth sizing → Tooth width (mm)** | The physical tooth width — **editable and mutually linked with module**. Editing it back-solves the module at the current tooth fraction (`module = tooth_width / (tooth_fraction · π)`); editing module or tooth fraction recomputes it (`tooth_width = tooth_fraction · π · module`). Lets you dial in a specific width for 3D printing. |
| **Tooth sizing → Tooth fraction** | Tooth width as a fraction of the circular pitch (0–0.5). **This is the backlash knob:** 0.5 = equal tooth and space; below 0.5 thins the teeth for circumferential play. Editing it recomputes tooth width (module pinned). |
| **Clearance** | Radial tip-to-root play (absolute mm or % of tooth width). Independent of tooth fraction. |
| **Advanced → Dedendum factor** | Optional root-depth scaling. |
| **Advanced → Tip control points** | Control points per wheel-tip half: **4** (degree-3 Bézier, default) or **5–6** (degree-5). The tip is a control-point spline, so it is fully constrained and the wheel can be rotated by editing its orientation dimension. |
| **Advanced → Tangent tip join** | Make the tip leave the flank join **tangent** (smoother) instead of the faithful conjugate corner. Fits the envelope less well — a warning recommends 5+ control points when this is enabled. |

Click **OK** to draw the pair. Invalid combinations disable OK and show an inline
message.

### The two kinds of play
- **Tooth fraction → circumferential backlash** (flank-to-flank): `backlash = CP · (1 − 2 · fraction)`.
- **Clearance → radial clearance** (tip-to-root bottoming).

---

## How the geometry works

The wheel tip is generated as the **conjugate** of the straight pinion flank, using
one consistent kinematic model (the pinion rotates `+τ` about its center while the
wheel rotates `−τ/ratio` about its). For a straight flank the contact point is the
**foot of the perpendicular from the pitch point onto the flank**; sweeping `τ`
traces the tip locus. It is trimmed from the flank join up to the centerline apex,
mirrored, and represented as a **control-point (Bézier) spline** — a degree-3
(4 control points) or degree-5 (6) curve fitted to the envelope (~3 µm at degree 3).
A control-point spline has no tangent handles, so its control points can be fully
constrained — which is what lets the wheel sketch be **rotated** by editing an angle
dimension. By default the join to the flank is **not** tangent — there is a real
~12° corner; forcing tangency (the optional *Tangent tip join*) deviates from the
true envelope more, so the faithful non-tangent shape is the default. The apex is a
sharp point (your printer rounds it).

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
| `core/sketch_builder.py` | Renders engine output into Fusion sketches, then extrudes + patterns them into solids. |
| `core/settings.py` | Pure (de)serialization of dialog settings. |
| `commands/generateGears/entry.py` | Command, dialog, validation, persistence. |
| `tests/` | pytest for the engine, settings, and interference guard. |

---

## Scope

Solid gear bodies (extrude + circular pattern) — no fillets, bores, or motion
links; one wheel + pinion mesh per run (the pair can be split across two
components or built into one); spur gears only (non-helical/bevel/internal).

## License & attribution

The Perfect Print gear method is credited to **Steve Peterson** (*Clock Design
Guidelines*). This repository is an independent add-in implementing it.

This add-in is licensed under the **[Apache License 2.0](LICENSE)**. The license
covers the add-in's source code only, not the underlying gear design method. See
[`NOTICE`](NOTICE) for third-party attributions (the add-in scaffolding derives
from Autodesk's Fusion 360 sample template).
