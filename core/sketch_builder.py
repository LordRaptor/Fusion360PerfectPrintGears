"""Builds Perfect Print gears in Fusion: one tooth on the root disk -> extrude
-> model circular pattern. Converts mm (engine) -> cm (Fusion).

Per the chosen workflow: draw the full root circle plus ONE tooth (a "driving gear with a
single tooth"), extrude the resulting profiles (disk + tooth) to the given
thickness, then circular-pattern the extrude feature `teeth` times about a
construction axis through the gear centre. The concentric disks coincide so the
pattern reads as a solid gear. Everything goes into the one target component for
now (splitting driving/driven into separate components is a planned extension).
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
    """Draw a connected segment list (lines / 3-pt arcs / control-point splines).
    Returns a list of (segment, created_curve) for downstream constraints."""
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    cpsplines = sketch.sketchCurves.sketchControlPointSplines
    earcs = sketch.sketchCurves.sketchEllipticalArcs
    drawn = []
    for seg in segments:
        pts = [(p[0] + cx_mm, p[1] + cy_mm) for p in seg.points]
        if seg.kind == 'line':
            ent = lines.addByTwoPoints(_pt(*pts[0]), _pt(*pts[-1]))
        elif seg.kind == 'arc3':
            ent = arcs.addByThreePoints(_pt(*pts[0]), _pt(*pts[1]), _pt(*pts[-1]))
        elif seg.kind == 'cpspline':
            # Control-point (Bezier) spline -- the control points ARE the input
            # (off-curve). No tangent handles, so it can be fully constrained and
            # rotated. Fusion accepts only degree 3 or 5. add() wants a plain LIST
            # of Point3D (a std::vector<Base>), NOT an ObjectCollection.
            ctrl = [_pt(*p) for p in pts]
            deg = (adsk.fusion.SplineDegrees.SplineDegreeFive if seg.degree == 5
                   else adsk.fusion.SplineDegrees.SplineDegreeThree)
            ent = cpsplines.add(ctrl, deg)
        elif seg.kind == 'earc':
            # Elliptical-arc cap (the driven 'Perfect Print blue' tip). points are
            # [center, start, apex, end]; major axis = center->end (tangential,
            # radius hw), minor axis = center->apex (radial, radius 0.75*hw). The two
            # axis args are Vector3D whose MAGNITUDE is the radius (in cm). addByEndPoints
            # sweeps CCW from its 1st to its 2nd point; passing (end, start) sweeps the
            # OUTWARD half (through the apex). Passing (start, end) takes the inward half.
            center, start, apex, end = pts          # mm, already offset by (cx_mm, cy_mm)
            major = adsk.core.Vector3D.create((end[0] - center[0]) * MM_TO_CM,
                                              (end[1] - center[1]) * MM_TO_CM, 0.0)
            minor = adsk.core.Vector3D.create((apex[0] - center[0]) * MM_TO_CM,
                                              (apex[1] - center[1]) * MM_TO_CM, 0.0)
            ent = earcs.addByEndPoints(_pt(*center), major, minor, _pt(*end), _pt(*start))
        else:
            continue
        drawn.append((seg, ent))
    return drawn


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


def _constrain_flanks(sketch, flank_lines, root_circle, gcx_cm, gcy_cm,
                      centerline=None, pitch_circle=None):
    """Constrain the two tooth flank lines, symmetric about the centerline.

    Common to both gears: both flank bases (the ends nearest the root) coincident
    with the root circle; f1 parallel to the centerline; f2 symmetric to f1 about
    the centerline; a width offset dimension between the flanks.

    Length is fixed differently per gear:
      - driven (pitch_circle given): the flank TOPS are coincident with the pitch
        circle (the driven flanks end on the pitch circle) -- no length dimension.
      - driving (pitch_circle None): a length dimension on f1 plus an EQUAL
        constraint on f2 (its top is at the spline join, not on a clean circle;
        and symmetry does not equalise length).

    No centerline / <2 flanks: just pin each base to the root circle."""
    gc = sketch.geometricConstraints
    dims = sketch.sketchDimensions

    def ends(line):
        sp, ep = line.startSketchPoint, line.endSketchPoint
        ds = math.hypot(sp.geometry.x - gcx_cm, sp.geometry.y - gcy_cm)
        de = math.hypot(ep.geometry.x - gcx_cm, ep.geometry.y - gcy_cm)
        return (sp, ep) if ds < de else (ep, sp)        # (foot, top)

    if centerline is None or len(flank_lines) < 2:
        for line in flank_lines:
            try:
                gc.addCoincident(ends(line)[0], root_circle)
            except Exception:
                futil.handle_error('flank base coincident with root circle')
        return

    f1, f2 = flank_lines[0], flank_lines[1]
    foot1, top1 = ends(f1)
    foot2, top2 = ends(f2)
    for foot in (foot1, foot2):
        try:
            gc.addCoincident(foot, root_circle)
        except Exception:
            futil.handle_error('flank base coincident with root circle')
    try:
        gc.addParallel(f1, centerline)
    except Exception:
        futil.handle_error('flank parallel to centerline')
    try:
        gc.addSymmetry(f1, f2, centerline)
    except Exception:
        futil.handle_error('flank symmetry about centerline')
    try:
        s1, s2 = f1.startSketchPoint.geometry, f2.startSketchPoint.geometry
        wtp = adsk.core.Point3D.create((s1.x + s2.x) / 2.0, (s1.y + s2.y) / 2.0, 0.0)
        dims.addOffsetDimension(f1, f2, wtp, True)
    except Exception:
        futil.handle_error('flank width offset dimension')

    if pitch_circle is not None:
        # driven: the flanks now end at the elliptical cap's co-vertices, 0.25*hw
        # INSIDE the pitch circle -- NOT on it. So we no longer pin the flank tops to
        # the pitch circle (that would drag them off the ellipse and break the oval
        # cap). The driven flank length is fixed by the cap instead (the elliptical
        # arc's co-vertices + its center offset; constraints TBD live in Fusion).
        # Left intentionally length-free here for the first draw test.
        pass
    else:
        # driving: length dimension on f1 + equal on f2.
        try:
            ltp = adsk.core.Point3D.create((foot1.geometry.x + top1.geometry.x) / 2.0,
                                           (foot1.geometry.y + top1.geometry.y) / 2.0 - 0.3, 0.0)
            dims.addDistanceDimension(
                foot1, top1, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                ltp, True)
        except Exception:
            futil.handle_error('flank length dimension')
        try:
            gc.addEqual(f1, f2)
        except Exception:
            futil.handle_error('flank equal length')


def _lock_control_points_to_frame(sketch, spline, center_pt, apex_pt):
    """Lock each INTERIOR control point of a control-point spline relative to the
    centerline frame with two point-to-point distance dimensions: to the centre and
    to the apex (both on the centerline, so each point rotates with the frame). The
    two END control points are the curve ends and are skipped: Fusion auto-coincides
    the drawn segment joins, so the start is already coincident with the flank top
    and the end with the centerline end / upper spline -- adding dims there would
    over-constrain. A control-point spline has no tangent handles, so locking the
    control points fully constrains the curve."""
    dims = sketch.sketchDimensions
    aligned = adsk.fusion.DimensionOrientations.AlignedDimensionOrientation
    cps = spline.controlPoints                         # SketchPointVector (len/index)
    n = len(cps)
    for i in range(1, n - 1):                          # interior only
        cp = cps[i]
        g = cp.geometry
        for ref in (center_pt, apex_pt):
            tp = adsk.core.Point3D.create(g.x, g.y, 0.0)
            try:
                dims.addDistanceDimension(cp, ref, aligned, tp, True)
            except Exception:
                futil.handle_error(f'tip control-point distance dim {i}')


def _orient_driving(sketch, gc, centerline, center_anchor, add_circle,
                    cx_mm, cy_mm, addendum_radius_mm, use_angle_dim=True):
    """Fix the driving gear tooth's orientation.

    use_angle_dim (default): add an ANGULAR dimension between the centerline and a
    vertical construction reference through the centre, so the driving gear can be
    rotated later by editing it. Home reads 90deg -- a 0deg dim against a horizontal
    reference is degenerate (collinear lines sharing a vertex). The reference line
    is itself fully constrained (start at centre, vertical, end on the addendum
    circle).

    Otherwise: simply constrain the centerline HORIZONTAL -- not rotatable, but
    cleaner. Kept for the rotate-the-arrangement work, where a rotation of 0 can
    use the plain horizontal instead of a 90deg angle dim (per the chosen rotation
    scheme)."""
    if not use_angle_dim:
        try:
            gc.addHorizontal(centerline)
        except Exception:
            futil.handle_error('centerline horizontal')
        return
    try:
        ref = sketch.sketchCurves.sketchLines.addByTwoPoints(
            _pt(cx_mm, cy_mm), _pt(cx_mm, cy_mm + addendum_radius_mm))
        ref.isConstruction = True
        gc.addCoincident(ref.startSketchPoint, center_anchor)
        gc.addVertical(ref)
        # pin the free endpoint (length) so the reference line is constrained too
        gc.addCoincident(ref.endSketchPoint, add_circle)
        atp = adsk.core.Point3D.create(cx_mm * MM_TO_CM + 0.5, cy_mm * MM_TO_CM + 0.5, 0.0)
        sketch.sketchDimensions.addAngularDimension(centerline, ref, atp, True)
    except Exception:
        futil.handle_error('driving gear orientation angle dimension')


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


def build_gear(component: adsk.fusion.Component, occurrence, profile: gear_math.GearProfile,
               thickness_mm: float, name: str, plane,
               lock_center: bool = False, mesh_to_pitch=None, center_point=None,
               draw_offset=(0.0, 0.0), mesh_occ=None):
    """Sketch (root circle + one tooth) -> extrude the disk (new body) and the
    tooth (join) -> circular-pattern ONLY the tooth extrude `teeth` times about
    the root circle. Yields a single clean gear body (disk + N teeth).

    Mirrors FusionCycloidalGears: sketch circle as the pattern axis, profiles
    picked by centroid, tooth joined onto the disk via participantBodies, no
    construction axis, no combine. (We skip its dedendum Cut -- our tooth profile
    already runs to the root.)

    The gear is DRAWN at its final location, never drawn-then-moved: the lower tip
    spline is isFixed in absolute sketch coords, so moving the centre by constraint
    afterwards tears the tooth. `draw_offset` (mm) shifts the whole gear (used to
    place the driven gear at driving_centre + center_distance). When `center_point`
    is given (the driving gear), the gear is drawn at the projected point instead.

    Returns (sketch, pitch_circle, (cx_mm, cy_mm)) -- the centre actually used."""
    cx, cy = profile.center
    cx, cy = cx + draw_offset[0], cy + draw_offset[1]
    th_cm = thickness_mm * MM_TO_CM

    # Create the sketch in this component's context. When the target is a placed
    # occurrence, occurrenceForCreation supplies the assembly context (the same thing
    # Fusion does when you activate a component and sketch in the UI).
    if occurrence is not None:
        sketch = component.sketches.add(plane, occurrence)
    else:
        sketch = component.sketches.add(plane)
    sketch.name = name

    # Anchor the driving gear to a picked point BEFORE drawing: project it, then
    # draw the gear at its location (cx, cy) so the isFixed tip spline is born in place.
    center_anchor = None
    if lock_center and center_point is not None:
        try:
            center_anchor = sketch.project2([center_point], True)[0]
            cx = center_anchor.geometry.x / MM_TO_CM
            cy = center_anchor.geometry.y / MM_TO_CM
        except Exception:
            futil.handle_error('project driving gear centre point')
            center_anchor = None

    futil.log(f'build_gear {name}: center=({cx:.3f},{cy:.3f})mm teeth={profile.teeth} '
              f'root_r={profile.root_radius:.3f} add_r={profile.addendum_radius:.3f} '
              f'thickness={thickness_mm}mm')

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
        drawn = _draw_outline(sketch, tooth, cx, cy)
    finally:
        sketch.isComputeDeferred = False

    # Constraints step 1: lock the three circle diameters (driving dimensions).
    _add_circle_diameters(sketch, cx * MM_TO_CM, cy * MM_TO_CM, [
        (root_circle, profile.root_radius * MM_TO_CM, math.radians(45)),
        (pitch_circle, profile.pitch_radius * MM_TO_CM, math.radians(90)),
        (add_circle, profile.addendum_radius * MM_TO_CM, math.radians(135)),
    ])

    gc = sketch.geometricConstraints
    # center_anchor was set above (the projected picked point) if any; otherwise the
    # gear was drawn at the origin and we anchor its centre there.
    if center_anchor is None:
        center_anchor = sketch.originPoint

    # Constraints step 2a: make the three circles concentric.
    if lock_center:
        # lock the common centre to the chosen anchor (origin, or the picked point)
        for c in (root_circle, pitch_circle, add_circle):
            try:
                gc.addCoincident(c.centerSketchPoint, center_anchor)
            except Exception:
                futil.handle_error('addCoincident(center, anchor)')
        futil.log(f'build_gear {name}: centres coincident with anchor')
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
    # pitch circle (e.g. the driving gear's) and make this gear's pitch circle tangent
    # to it (pitch circles tangent == meshing center distance).
    driving_center_pt = None      # the driving gear centre projected into this sketch (set below)
    if mesh_to_pitch is not None:
        try:
            # When the driving gear lives in a different component, the pitch circle
            # must be taken in the driving gear's assembly context (a proxy) before it
            # can be projected into this (driven) sketch.
            ref_pitch = mesh_to_pitch
            if mesh_occ is not None:
                try:
                    ref_pitch = mesh_to_pitch.createForAssemblyContext(mesh_occ)
                except Exception:
                    futil.handle_error('proxy driving gear pitch circle for assembly context')
            ref = sketch.include(ref_pitch).item(0)
            # MUST be construction, else the big projected circle adds profiles and
            # breaks the extrude.
            try:
                ref.isConstruction = True
            except Exception:
                futil.handle_error('set referenced pitch circle to construction')
            gc.addTangent(pitch_circle, ref)
            # The included pitch circle's centre IS the driving gear centre in this
            # sketch; the line of centers / phase reference anchors to it (NOT the
            # sketch origin -- they differ when the driving gear centre is an
            # off-origin point).
            driving_center_pt = ref.centerSketchPoint
            # The tangent fixes the meshing centre distance but deliberately leaves
            # ONE DOF: the driven gear can swing around the driving gear on the locus
            # of valid centres. The user adds their own constraint (coincident to an
            # axle point, an angle dim, collinear to an edge) to align the driven gear
            # with existing features; a wrong-spacing target simply won't solve. The
            # driven gear's tooth phase is dimensioned relative to the line of centres
            # below, so its teeth follow as it swings.
            futil.log(f'build_gear {name}: pitch tangent (centre free to swing)')
        except Exception:
            futil.handle_error('mesh tangent to driving gear pitch circle')

    # Constraints step 3: a construction CENTERLINE (gear centre -> tooth tip) for
    # both gears; flanks are symmetric about it. The driving gear's is horizontal
    # (pins the tooth orientation); the driven gear's angle (phase) is left free.
    flank_lines = [e for (s, e) in drawn if s.kind == 'line']
    ax = profile.base_angle
    apex_mm = (cx + profile.addendum_radius * math.cos(ax),
               cy + profile.addendum_radius * math.sin(ax))
    centerline = sketch.sketchCurves.sketchLines.addByTwoPoints(_pt(cx, cy), _pt(*apex_mm))
    centerline.isConstruction = True
    try:
        if lock_center:
            gc.addCoincident(centerline.startSketchPoint, center_anchor)
        else:
            gc.addCoincident(centerline.startSketchPoint, pitch_circle.centerSketchPoint)
    except Exception:
        futil.handle_error('centerline start coincident with gear centre')
    try:
        gc.addCoincident(centerline.endSketchPoint, add_circle)
    except Exception:
        futil.handle_error('centerline end coincident with addendum circle')
    if lock_center:
        # Orientation: angle dimension (rotatable) by default; the horizontal
        # alternative is preserved in _orient_driving for the rotate-the-arrangement
        # work (rotation 0 can use plain horizontal).
        _orient_driving(sketch, gc, centerline, center_anchor, add_circle,
                        cx, cy, profile.addendum_radius, use_angle_dim=True)

    _constrain_flanks(sketch, flank_lines, root_circle, cx * MM_TO_CM, cy * MM_TO_CM,
                      centerline=centerline,
                      pitch_circle=(None if lock_center else pitch_circle))

    if lock_center:
        # Driving gear tip: a control-point (Bezier) spline locked RELATIVE to the
        # centerline frame, so it rotates with the centerline. A control-point
        # spline has no tangent handles, so locking its control points fully
        # constrains it (a fitted spline could not be). Apex control point on the
        # centerline end; interior lower control points dimensioned to centre +
        # apex; the upper half's interior control points follow by symmetry.
        # (cpspline segments carry no clamp flags, so pick lower/upper by order:
        # build_driving_tooth emits lower [join->apex] then upper [apex->join].)
        cpsplines = [e for (s, e) in drawn if s.kind == 'cpspline']
        lower_spline = cpsplines[0] if len(cpsplines) >= 1 else None
        upper_spline = cpsplines[1] if len(cpsplines) >= 2 else None
        if lower_spline is not None:
            try:
                gc.addCoincident(lower_spline.endSketchPoint, centerline.endSketchPoint)
            except Exception:
                futil.handle_error('tip apex coincident with centerline end')
            # Lock the lower spline's INTERIOR control points to the frame (centre +
            # apex, both on the centerline). The end control points are the curve
            # ends (auto-coincided joins + apex->centerline end).
            _lock_control_points_to_frame(sketch, lower_spline,
                                          center_anchor, centerline.endSketchPoint)
            if upper_spline is not None:
                # The lower spline's join auto-coincides to the lower flank on draw,
                # but the upper spline's join does not (draw order); pin it to the
                # nearest flank endpoint so the sketch is fully constrained.
                try:
                    je = upper_spline.endSketchPoint        # upper: apex -> join
                    best, bestd = None, 1e18
                    for fl in flank_lines:
                        for ep in (fl.startSketchPoint, fl.endSketchPoint):
                            d = math.hypot(ep.geometry.x - je.geometry.x,
                                           ep.geometry.y - je.geometry.y)
                            if d < bestd:
                                bestd, best = d, ep
                    if best is not None and bestd < 1e-3:    # cm: the genuine join
                        gc.addCoincident(je, best)
                except Exception:
                    futil.handle_error('upper tip join coincident with upper flank')
                try:
                    lcp, ucp = lower_spline.controlPoints, upper_spline.controlPoints
                    futil.log(f'build_gear {name}: tip control points '
                              f'lower={len(lcp)} upper={len(ucp)}')
                    # Mirror only the INTERIOR control points about the centerline
                    # (endpoints are curve ends, pinned by coincidence; mirroring
                    # them too would be redundant/over-constrained). The mirror of a
                    # point across the centerline at y = cy is (x, 2*cy - y).
                    cy_cm = cy * MM_TO_CM
                    n = len(lcp)
                    for i in range(1, n - 1):
                        lp = lcp[i]
                        tx, ty = lp.geometry.x, 2.0 * cy_cm - lp.geometry.y
                        best, bestd = None, 1e18
                        for j in range(len(ucp)):
                            up = ucp[j]
                            d = math.hypot(up.geometry.x - tx, up.geometry.y - ty)
                            if d < bestd:
                                bestd, best = d, up
                        if best is not None:
                            try:
                                gc.addSymmetry(lp, best, centerline)
                            except Exception:
                                futil.handle_error(f'tip control-point symmetry {i}')
                except Exception:
                    futil.handle_error('mirror tip control points')
    else:
        # Driven gear cap: coincident the arc endpoints with the flank tops, then make
        # the arc tangent to ONE flank. Both endpoints are pinned to the flank tops
        # and the flanks are parallel, so a single tangent already fixes the arc's
        # radius and orientation -- a second tangent over-constrains the sketch.
        cap = next((e for (s, e) in drawn if s.kind == 'arc3'), None)
        if cap is not None and len(flank_lines) >= 2:
            gcx, gcy = cx * MM_TO_CM, cy * MM_TO_CM

            def _flank_top(line):
                sp, ep = line.startSketchPoint, line.endSketchPoint
                ds = math.hypot(sp.geometry.x - gcx, sp.geometry.y - gcy)
                de = math.hypot(ep.geometry.x - gcx, ep.geometry.y - gcy)
                return ep if ds < de else sp        # end farther from centre

            tops = [_flank_top(f) for f in flank_lines[:2]]
            for cap_end in (cap.startSketchPoint, cap.endSketchPoint):
                best, bestd = None, 1e18
                for t in tops:
                    d = math.hypot(cap_end.geometry.x - t.geometry.x,
                                   cap_end.geometry.y - t.geometry.y)
                    if d < bestd:
                        bestd, best = d, t
                if best is not None:
                    try:
                        gc.addCoincident(cap_end, best)
                    except Exception:
                        futil.handle_error('cap endpoint coincident with flank top')
            try:
                gc.addTangent(cap, flank_lines[0])
            except Exception:
                futil.handle_error('cap tangent to flank')

        # Phase: pin the driven gear's rotation with an angular dimension between its
        # centerline and the line of centers (driven centre -> driving centre). The
        # driving centre is `driving_center_pt` (the projected driving gear pitch
        # centre), which is the sketch origin ONLY when the driving gear sits at the
        # origin -- anchor to it, not the origin, so an off-origin driving gear centre
        # still gives the true line of centers. (Falls back to the origin if the mesh
        # reference is unavailable.)
        wc_pt = driving_center_pt if driving_center_pt is not None else sketch.originPoint
        try:
            loc = sketch.sketchCurves.sketchLines.addByTwoPoints(_pt(cx, cy),
                                                                 _pt(*draw_offset))
            loc.isConstruction = True
            gc.addCoincident(loc.startSketchPoint, pitch_circle.centerSketchPoint)
            gc.addCoincident(loc.endSketchPoint, wc_pt)
            atp = adsk.core.Point3D.create(cx * MM_TO_CM - 1.0, cy * MM_TO_CM - 1.0, 0.0)
            sketch.sketchDimensions.addAngularDimension(centerline, loc, atp, True)
        except Exception:
            futil.handle_error('driven gear phase angular dimension')

    futil.log(f'build_gear {name}: profiles={sketch.profiles.count}')
    disk_prof, tooth_profs = _nearest_profile(sketch.profiles, cx * MM_TO_CM, cy * MM_TO_CM)

    extrudes = component.features.extrudeFeatures
    dist = adsk.core.ValueInput.createByReal(th_cm)

    # Disk -> new body.
    disk_in = extrudes.createInput(disk_prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    disk_in.setDistanceExtent(False, dist)
    disk_ext = extrudes.add(disk_in)
    base_body = disk_ext.bodies.item(0)
    # Name the body after the sketch; the tooth join + pattern merge into this body,
    # so it is the final gear body (e.g. "PPG Driving 50T").
    try:
        base_body.name = name
    except Exception:
        futil.handle_error('name gear body')

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
    return sketch, pitch_circle, (cx, cy)


def build_pair(driving_component: adsk.fusion.Component, driving_occurrence,
               driven_component: adsk.fusion.Component, driven_occurrence,
               pair: gear_math.GearPair, thickness_mm: float = 5.0,
               plane=None, driving_center=None) -> None:
    """Build the driving and driven gears into their (possibly separate) components
    in a meshing layout. Each `*_occurrence` is the selected instance (or None for
    the root/active component); it provides the assembly context to create the sketch
    in that component and to proxy the driving gear's pitch circle into the driven
    gear's sketch for the mesh. The driving gear is built first (centre locked to the
    chosen point or origin); the driven gear then references the driving gear's pitch
    circle tangent (the mesh).

    `plane` is the shared planar entity both sketches are drawn on; defaults to the
    ROOT XY construction plane (a root-level plane works with occurrenceForCreation
    for both components). A selected planar FACE is converted to a coincident
    construction plane in the root first -- sketching directly on a face drags the
    face's edges into profile detection (fragmenting the disk, adding a leftover
    region); a construction plane has no edges, so the gear profiles stay clean."""
    root = driving_component.parentDesign.rootComponent
    if plane is None:
        plane = root.xYConstructionPlane
    elif isinstance(plane, adsk.fusion.BRepFace):
        # Coincident construction plane = the face offset by zero, created in the
        # root so it is shared/usable from both components' contexts. (Associative to
        # the face; ConstructionPlaneInput has no setByPlanarFace.)
        ci = root.constructionPlanes.createInput()
        ci.setByOffset(plane, adsk.core.ValueInput.createByReal(0.0))
        plane = root.constructionPlanes.add(ci)
        try:
            plane.name = f'PPG Gear Plane {pair.driving.teeth}T-{pair.driven.teeth}T'
        except Exception:
            futil.handle_error('name gear construction plane')
    _, driving_pitch, driving_xy = build_gear(driving_component, driving_occurrence,
                                              pair.driving, thickness_mm,
                                              f'PPG Driving {pair.driving.teeth}T',
                                              plane, lock_center=True,
                                              center_point=driving_center)
    # Draw the driven gear at driving_centre + center_distance so it is born where
    # the mesh places it (the driven gear has no fixed geometry, but drawing it in
    # place keeps the profile picker accurate and minimises solver movement).
    # mesh_occ carries the driving gear's context so its pitch circle can be proxied
    # into the driven gear sketch.
    build_gear(driven_component, driven_occurrence, pair.driven, thickness_mm,
               f'PPG Driven {pair.driven.teeth}T', plane, mesh_to_pitch=driving_pitch,
               draw_offset=driving_xy, mesh_occ=driving_occurrence)
