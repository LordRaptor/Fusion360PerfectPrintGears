"""Builds Perfect Print gears in Fusion: one tooth on the root disk -> extrude
-> model circular pattern. Converts mm (engine) -> cm (Fusion).

Per the chosen workflow: draw the full root circle plus ONE tooth (a "wheel with a
single tooth"), extrude the resulting profiles (disk + tooth) to the given
thickness, then circular-pattern the extrude feature `teeth` times about a
construction axis through the gear centre. The concentric disks coincide so the
pattern reads as a solid gear. Everything goes into the one target component for
now (splitting wheel/pinion into separate components is a planned extension).
"""
import math

import adsk.core
import adsk.fusion

from . import gear_math
from ..lib import fusionAddInUtils as futil

MM_TO_CM = 0.1


def _pt(x_mm: float, y_mm: float) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x_mm * MM_TO_CM, y_mm * MM_TO_CM, 0.0)


def _draw_outline(sketch, segments, cx_mm, cy_mm):
    """Draw a connected segment list (lines / 3-pt arcs / fitted splines)."""
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    splines = sketch.sketchCurves.sketchFittedSplines
    for seg in segments:
        pts = [(p[0] + cx_mm, p[1] + cy_mm) for p in seg.points]
        if seg.kind == 'line':
            lines.addByTwoPoints(_pt(*pts[0]), _pt(*pts[-1]))
        elif seg.kind == 'arc3':
            arcs.addByThreePoints(_pt(*pts[0]), _pt(*pts[1]), _pt(*pts[-1]))
        elif seg.kind == 'spline':
            coll = adsk.core.ObjectCollection.create()
            for p in pts:
                coll.add(_pt(*p))
            splines.add(coll)


def _nearest_profile(profiles, cx_cm, cy_cm):
    """Return (disk_profile, [other_profiles]) split by centroid distance to the
    gear centre. The disk profile's centroid is at the centre; the tooth tab's is
    out by the tooth."""
    ranked = []
    for p in profiles:
        c = p.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).centroid
        ranked.append((math.hypot(c.x - cx_cm, c.y - cy_cm), p))
    ranked.sort(key=lambda t: t[0])
    return ranked[0][1], [p for _, p in ranked[1:]]


def build_gear(component: adsk.fusion.Component, profile: gear_math.GearProfile,
               thickness_mm: float, name: str):
    """Sketch (root circle + one tooth) -> extrude the disk (new body) and the
    tooth (join) -> circular-pattern ONLY the tooth extrude `teeth` times about
    the root circle. Yields a single clean gear body (disk + N teeth).

    Mirrors FusionCycloidalGears: sketch circle as the pattern axis, profiles
    picked by centroid, tooth joined onto the disk via participantBodies, no
    construction axis, no combine. (We skip its dedendum Cut -- our tooth profile
    already runs to the root.)
    """
    cx, cy = profile.center
    th_cm = thickness_mm * MM_TO_CM
    futil.log(f'build_gear {name}: center=({cx:.3f},{cy:.3f})mm teeth={profile.teeth} '
              f'root_r={profile.root_radius:.3f} add_r={profile.addendum_radius:.3f} '
              f'thickness={thickness_mm}mm')

    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = name

    sketch.isComputeDeferred = True
    try:
        sketch.sketchPoints.add(_pt(cx, cy))
        circles = sketch.sketchCurves.sketchCircles
        # Root circle REAL (bounds the disk profile + serves as the pattern axis);
        # pitch/addendum drawn as construction references.
        root_circle = circles.addByCenterRadius(_pt(cx, cy), profile.root_radius * MM_TO_CM)
        for r in (profile.pitch_radius, profile.addendum_radius):
            c = circles.addByCenterRadius(_pt(cx, cy), r * MM_TO_CM)
            c.isConstruction = True
        tooth = gear_math.array_tooth(profile.tooth_segments, 1, profile.base_angle)
        _draw_outline(sketch, tooth, cx, cy)
    finally:
        sketch.isComputeDeferred = False

    futil.log(f'build_gear {name}: profiles={sketch.profiles.count}')
    disk_prof, tooth_profs = _nearest_profile(sketch.profiles, cx * MM_TO_CM, cy * MM_TO_CM)

    extrudes = component.features.extrudeFeatures
    dist = adsk.core.ValueInput.createByReal(th_cm)

    # Disk -> new body.
    disk_in = extrudes.createInput(disk_prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    disk_in.setDistanceExtent(False, dist)
    disk_ext = extrudes.add(disk_in)
    base_body = disk_ext.bodies.item(0)

    # Tooth -> join onto the disk body.
    tooth_coll = adsk.core.ObjectCollection.create()
    for p in tooth_profs:
        tooth_coll.add(p)
    tooth_in = extrudes.createInput(tooth_coll, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    tooth_in.setDistanceExtent(False, dist)
    tooth_in.participantBodies = [base_body]
    tooth_ext = extrudes.add(tooth_in)

    # Circular-pattern ONLY the tooth extrude about the root circle (its axis).
    coll = adsk.core.ObjectCollection.create()
    coll.add(tooth_ext)
    circ = component.features.circularPatternFeatures
    cp_input = circ.createInput(coll, root_circle)
    cp_input.quantity = adsk.core.ValueInput.createByReal(float(profile.teeth))
    circ.add(cp_input)

    futil.log(f'build_gear {name}: disk+tooth extruded, pattern x{profile.teeth} done')
    return sketch


def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair,
               thickness_mm: float = 5.0) -> None:
    """Build both gears into `component` in meshing layout."""
    build_gear(component, pair.wheel, thickness_mm, f'PPG Wheel {pair.wheel.teeth}T')
    build_gear(component, pair.pinion, thickness_mm, f'PPG Pinion {pair.pinion.teeth}T')
