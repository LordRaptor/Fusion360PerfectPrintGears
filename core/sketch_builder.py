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


def _add_circle_diameters(sketch, cx_cm, cy_cm, items):
    """Add driving diameter dimensions to circles. `items` is a list of
    (circle, radius_cm, text_angle_rad); the text sits on the circle at that angle.
    Defensive: a solver rejection on one dimension must not abort the build."""
    dims = sketch.sketchDimensions
    for circle, r_cm, ang in items:
        tp = adsk.core.Point3D.create(cx_cm + r_cm * math.cos(ang),
                                      cy_cm + r_cm * math.sin(ang), 0.0)
        try:
            dims.addDiameterDimension(circle, tp, True)
        except Exception:
            futil.handle_error('addDiameterDimension')


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
               thickness_mm: float, name: str,
               lock_center: bool = False, mesh_to_pitch=None):
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
        circles = sketch.sketchCurves.sketchCircles
        # Root circle REAL (bounds the disk profile + serves as the pattern axis);
        # pitch/addendum drawn as construction references.
        root_circle = circles.addByCenterRadius(_pt(cx, cy), profile.root_radius * MM_TO_CM)
        pitch_circle = circles.addByCenterRadius(_pt(cx, cy), profile.pitch_radius * MM_TO_CM)
        pitch_circle.isConstruction = True
        add_circle = circles.addByCenterRadius(_pt(cx, cy), profile.addendum_radius * MM_TO_CM)
        add_circle.isConstruction = True
        tooth = gear_math.array_tooth(profile.tooth_segments, 1, profile.base_angle)
        _draw_outline(sketch, tooth, cx, cy)
    finally:
        sketch.isComputeDeferred = False

    # Constraints step 1: lock the three circle diameters (driving dimensions).
    _add_circle_diameters(sketch, cx * MM_TO_CM, cy * MM_TO_CM, [
        (root_circle, profile.root_radius * MM_TO_CM, math.radians(45)),
        (pitch_circle, profile.pitch_radius * MM_TO_CM, math.radians(90)),
        (add_circle, profile.addendum_radius * MM_TO_CM, math.radians(135)),
    ])

    gc = sketch.geometricConstraints
    # Constraints step 2a: make the three circles concentric.
    if lock_center:
        # lock the common centre to the sketch origin (wheel sits at the origin)
        for c in (root_circle, pitch_circle, add_circle):
            try:
                gc.addCoincident(c.centerSketchPoint, sketch.originPoint)
            except Exception:
                futil.handle_error('addCoincident(center, origin)')
        futil.log(f'build_gear {name}: centres coincident with origin')
    else:
        # tie root + addendum centres to the pitch centre (concentric); the pitch
        # circle itself is located by the mesh tangent below
        for c in (root_circle, add_circle):
            try:
                gc.addCoincident(c.centerSketchPoint, pitch_circle.centerSketchPoint)
            except Exception:
                futil.handle_error('addCoincident(center, pitch center)')
        futil.log(f'build_gear {name}: circles concentric')

    # Constraints step 2b: locate this gear by meshing -- reference an external
    # pitch circle (e.g. the wheel's) and make this gear's pitch circle tangent
    # to it (pitch circles tangent == meshing center distance).
    if mesh_to_pitch is not None:
        try:
            ref = sketch.include(mesh_to_pitch).item(0)
            # MUST be construction, else the big projected circle adds profiles and
            # breaks the extrude.
            try:
                ref.isConstruction = True
            except Exception:
                futil.handle_error('set referenced pitch circle to construction')
            gc.addTangent(pitch_circle, ref)
            # line of centers: keep this gear's centre horizontal with the wheel's,
            # removing the rotate-around-the-wheel DOF (-> pinion fully located).
            try:
                gc.addHorizontalPoints(pitch_circle.centerSketchPoint, ref.centerSketchPoint)
            except Exception:
                futil.handle_error('addHorizontalPoints(pinion center, wheel center)')
            futil.log(f'build_gear {name}: pitch tangent + centre horizontal with wheel')
        except Exception:
            futil.handle_error('mesh tangent to wheel pitch circle')

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
    return sketch, pitch_circle


def build_pair(component: adsk.fusion.Component, pair: gear_math.GearPair,
               thickness_mm: float = 5.0) -> None:
    """Build both gears into `component` in meshing layout. The wheel is built
    first with its circle centres locked to the origin; the pinion then references
    the wheel's pitch circle and is constrained tangent to it (the mesh)."""
    _, wheel_pitch = build_gear(component, pair.wheel, thickness_mm,
                                f'PPG Wheel {pair.wheel.teeth}T', lock_center=True)
    build_gear(component, pair.pinion, thickness_mm,
               f'PPG Pinion {pair.pinion.teeth}T', mesh_to_pitch=wheel_pitch)
