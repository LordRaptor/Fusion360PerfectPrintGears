"""Draws gear_math output into Fusion sketches. Converts mm (engine) -> cm (Fusion).

This is the only module besides entry.py that imports adsk. It does no geometry
math: it consumes the plain Segment/GearProfile data from gear_math and renders it.

Pinion (and any) rounded tips are drawn as tangent arcs: the arc is created through
its three points, then tangent constraints are added to the two adjacent flank lines
so the tip meets the flanks smoothly and the sketch is properly constrained.
"""
import adsk.core
import adsk.fusion

from . import gear_math

MM_TO_CM = 0.1


def _pt(x_mm: float, y_mm: float) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x_mm * MM_TO_CM, y_mm * MM_TO_CM, 0.0)


def _draw_outline(sketch: adsk.fusion.Sketch, segments, cx_mm: float, cy_mm: float):
    """Draw the connected outline. Returns a list of (kind, curve) in segment order
    so tangency between an arc tip and its neighbouring flank lines can be added."""
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    splines = sketch.sketchCurves.sketchFittedSplines

    drawn = []
    for seg in segments:
        pts = [(p[0] + cx_mm, p[1] + cy_mm) for p in seg.points]
        if seg.kind == 'line':
            curve = lines.addByTwoPoints(_pt(*pts[0]), _pt(*pts[-1]))
            drawn.append(('line', curve))
        elif seg.kind == 'arc3':
            s, m, e = pts[0], pts[1], pts[-1]
            curve = arcs.addByThreePoints(_pt(*s), _pt(*m), _pt(*e))
            drawn.append(('arc3', curve))
        elif seg.kind == 'spline':
            coll = adsk.core.ObjectCollection.create()
            for p in pts:
                coll.add(_pt(*p))
            curve = splines.add(coll)
            drawn.append(('spline', curve))
    return drawn


def _add_tip_tangencies(sketch: adsk.fusion.Sketch, drawn):
    """For each arc tip flanked by line segments, constrain the arc tangent to both
    neighbouring lines (a tangent arc with a tangent constraint on the other side).
    Wrapped defensively: a solver rejection on one tooth must not abort generation."""
    constraints = sketch.geometricConstraints
    n = len(drawn)
    for i, (kind, curve) in enumerate(drawn):
        if kind != 'arc3':
            continue
        prev_kind, prev_curve = drawn[(i - 1) % n]
        next_kind, next_curve = drawn[(i + 1) % n]
        for nb_kind, nb_curve in ((prev_kind, prev_curve), (next_kind, next_curve)):
            if nb_kind == 'line':
                try:
                    constraints.addTangent(curve, nb_curve)
                except Exception:
                    # Over-constrained / solver rejection on a tooth: skip, keep going.
                    pass


def draw_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
              name: str) -> adsk.fusion.Sketch:
    """Create one sketch in `component` with: a center point, construction circles
    (pitch/root/addendum), and the full toothed outline. Rounded tips are tangent."""
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = name
    cx, cy = profile.center

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

    # Tangencies added after the solver is live so it can apply them.
    _add_tip_tangencies(sketch, drawn)
    return sketch


def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair) -> None:
    """Draw both gears of `pair` into `component` as two sketches in meshing layout
    (wheel at origin, pinion at the center distance on +x)."""
    draw_gear(component, pair.wheel, f'PPG Wheel {pair.wheel.teeth}T')
    draw_gear(component, pair.pinion, f'PPG Pinion {pair.pinion.teeth}T')
