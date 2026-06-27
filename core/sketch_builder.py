"""Draws gear_math output into Fusion sketches. Converts mm (engine) -> cm (Fusion).

This is the only module besides entry.py that imports adsk. It does no geometry
math: it consumes the plain Segment/GearProfile data from gear_math and renders it.

Pinion rounded tips are drawn as tangent arcs (tangent to both adjacent flanks).
Wheel tip halves are fitted splines that carry clamp_start/clamp_end flags marking
which end must leave the adjoining flank tangentially; a tangent constraint is added
at that end so the drawn sketch matches the smooth (corner-free) flank/tip join.
"""
import adsk.core
import adsk.fusion

from . import gear_math
from ..lib import fusionAddInUtils as futil

MM_TO_CM = 0.1

# Auto tangent constraints are OFF for now: applying ~100+ constraints with the
# solver live distorts the (already-correct) placed geometry and is very slow.
# Proper parametric constraints are a planned later rework.
DRAW_TANGENT_CONSTRAINTS = False


def _pt(x_mm: float, y_mm: float) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x_mm * MM_TO_CM, y_mm * MM_TO_CM, 0.0)


def _draw_outline(sketch: adsk.fusion.Sketch, segments, cx_mm: float, cy_mm: float):
    """Draw the connected outline. Returns a list of (seg, curve) in segment order
    so tangency between a tip (arc or spline) and its neighbouring flank lines can
    be added afterwards."""
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    splines = sketch.sketchCurves.sketchFittedSplines

    drawn = []
    for seg in segments:
        pts = [(p[0] + cx_mm, p[1] + cy_mm) for p in seg.points]
        if seg.kind == 'line':
            curve = lines.addByTwoPoints(_pt(*pts[0]), _pt(*pts[-1]))
        elif seg.kind == 'arc3':
            s, m, e = pts[0], pts[1], pts[-1]
            curve = arcs.addByThreePoints(_pt(*s), _pt(*m), _pt(*e))
        elif seg.kind == 'spline':
            coll = adsk.core.ObjectCollection.create()
            for p in pts:
                coll.add(_pt(*p))
            curve = splines.add(coll)
        else:
            continue
        drawn.append((seg, curve))
    return drawn


def _add_tangencies(sketch: adsk.fusion.Sketch, drawn):
    """Constrain tips tangent to their neighbouring flank lines:
      - arc3 tips (pinion cap): tangent to both adjacent lines;
      - spline tips (wheel): tangent to the previous line if clamp_start, and/or
        the next line if clamp_end (the smooth flank/tip joins).
    Wrapped defensively: a solver rejection on one tooth must not abort generation."""
    constraints = sketch.geometricConstraints
    n = len(drawn)

    def tangent(a, b):
        try:
            constraints.addTangent(a, b)
        except Exception:
            # Over-constrained / solver rejection on a tooth: skip, keep going.
            pass

    for i, (seg, curve) in enumerate(drawn):
        prev_seg, prev_curve = drawn[(i - 1) % n]
        next_seg, next_curve = drawn[(i + 1) % n]
        if seg.kind == 'arc3':
            if prev_seg.kind == 'line':
                tangent(curve, prev_curve)
            if next_seg.kind == 'line':
                tangent(curve, next_curve)
        elif seg.kind == 'spline':
            if seg.clamp_start and prev_seg.kind == 'line':
                tangent(curve, prev_curve)
            if seg.clamp_end and next_seg.kind == 'line':
                tangent(curve, next_curve)


def draw_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
              name: str) -> adsk.fusion.Sketch:
    """Create one sketch in `component` with: a center point, construction circles
    (pitch/root/addendum), and the full toothed outline. Rounded tips are tangent."""
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = name
    cx, cy = profile.center

    # Diagnostics: counts + bounding box (mm) so the log cross-checks scale/placement.
    kinds = {}
    xs, ys = [], []
    for s in profile.segments:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
        for (x, y) in s.points:
            xs.append(x + cx); ys.append(y + cy)
    futil.log(f'draw_gear {name}: center=({cx:.3f},{cy:.3f})mm segments={len(profile.segments)} '
              f'kinds={kinds} pitch_r={profile.pitch_radius:.3f} root_r={profile.root_radius:.3f} '
              f'add_r={profile.addendum_radius:.3f}')
    if xs:
        futil.log(f'  bbox mm: x[{min(xs):.3f},{max(xs):.3f}] y[{min(ys):.3f},{max(ys):.3f}] '
                  f'(drawn in cm = mm*{MM_TO_CM})')

    sketch.isComputeDeferred = True
    try:
        sketch.sketchPoints.add(_pt(cx, cy))

        circles = sketch.sketchCurves.sketchCircles
        for r in (profile.pitch_radius, profile.root_radius, profile.addendum_radius):
            c = circles.addByCenterRadius(_pt(cx, cy), r * MM_TO_CM)
            c.isConstruction = True

        drawn = _draw_outline(sketch, profile.segments, cx, cy)
    finally:
        sketch.isComputeDeferred = False

    futil.log(f'draw_gear {name}: drew {len(drawn)} curves, '
              f'tangent_constraints={"on" if DRAW_TANGENT_CONSTRAINTS else "off"}')
    if DRAW_TANGENT_CONSTRAINTS:
        # Tangencies added after the solver is live so it can apply them.
        _add_tangencies(sketch, drawn)
    return sketch


def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair) -> None:
    """Draw both gears of `pair` into `component` as two sketches in meshing layout
    (wheel at origin, pinion at the center distance on +x)."""
    draw_gear(component, pair.wheel, f'PPG Wheel {pair.wheel.teeth}T')
    draw_gear(component, pair.pinion, f'PPG Pinion {pair.pinion.teeth}T')
