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
  extruded and circular-patterned from a fully-constrained parametric sketch.
- Builds them in **meshing layout**: wheel at the origin, pinion at the center
  distance, pitch circles tangent.
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
| **Module (mm)** | Sets the tooth size / pitch. `circular pitch = π · module`. |
| **Tooth fraction** | Tooth width as a fraction of the circular pitch (0–0.5). **This is the backlash knob:** 0.5 = equal tooth and space; below 0.5 thins the teeth for circumferential play. The resulting **tooth width** is shown read-only. |
| **Clearance** | Radial tip-to-root play (absolute mm or % of tooth width). Independent of tooth fraction. |
| **Advanced → Addendum / Dedendum factor** | Optional root-depth scaling. |
| **Advanced → Tip spline points** | Number of fit points per wheel-tip half (default 4). |

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
mirrored, and represented as a fitted spline. The join to the flank is **not**
tangent — there is a real ~12° corner; forcing tangency deviates from the true
envelope more, so the faithful (non-tangent) shape is kept. The apex is a sharp
point (your printer rounds it).

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
| `docs/` | Design spec and implementation plan. |

---

## Scope (v1)

Solid gear bodies (extrude + circular pattern) — no fillets, bores, or motion
links; both gears are drawn into one selected component (not auto-split); single
mesh per run; spur (non-helical/bevel/internal) gears.

## License & attribution

The Perfect Print gear method is credited to **Steve Peterson** (*Clock Design
Guidelines*). This repository is an independent add-in implementing it.
