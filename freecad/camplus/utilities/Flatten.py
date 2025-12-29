# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2023 Russell Johnson (russ4262) <russ4262@gmail.com>    *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD
import Part
import Path.Geom as PathGeom
import Path.Log as PathLog
import freecad.camplus.utilities.Edge as Edge
import freecad.camplus.utilities.MeshTools as MeshTools
import freecad.camplus.utilities.Region as Region
import TechDraw

__title__ = "Flatten Utilities"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Various functions to flatten faces, wires, and edges."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""
__date__ = ""


IS_MACRO = False  # False  # Set to True to use as macro

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())

translate = FreeCAD.Qt.translate


# ###################################################################
def _fuseShapes(shapes, tolerance=0.00001):
    if len(shapes) == 0:
        return None
    if len(shapes) == 1:
        return shapes[0]
    f = shapes[0].copy()
    for fc in shapes[1:]:
        fused = f.generalFuse(fc, tolerance)
        f = fused[0]
    return f


def _closedWiresToFace(wires, profile, holes):
    """_closedWiresToFace(wires, profile, holes)
    Assumes all wires are closed and planar in XY plane.
    return face object per 'profile' and 'holes' arguments."""
    tups = [(w, PathGeom.makeBoundBoxFace(w.BoundBox)) for w in wires]
    tups.sort(key=lambda t: t[1].Area, reverse=True)
    faces = [Part.Face(w) for w, __ in tups]

    if profile:
        if holes:
            f = faces[0]
            for h in faces[1:]:
                cut = f.cut(h)
                f = cut
            return f
        else:
            return faces[0]
    elif holes:
        return _fuseShapes(faces[1:])

    return None


def _flattenWire(w, deflection=0.001):
    wBB = w.BoundBox
    if PathGeom.isRoughly(wBB.ZLength, 0.0):
        flat = w.copy()
        flat.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - flat.BoundBox.ZMin))
        return flat
    elif (
        len(w.Edges) == 1
        and len(w.Edges[0].Vertexes) == 1
        and w.Edges[0].Curve.TypeId == "Part::GeomCircle"
        and PathGeom.isRoughly(Part.Face(w).normalAt(0, 0).z, 0.0)
    ):
        # full circle edge
        flat = Part.Wire([Edge.horizontalCenterChordLine(w.Edges[0])])
        flat.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - flat.BoundBox.ZMin))
        return flat
    else:
        face = PathGeom.makeBoundBoxFace(wBB, 2.0, wBB.ZMin - 10.0)
        flat = face.makeParallelProjection(w, FreeCAD.Vector(0.0, 0.0, 1.0))
        if len(flat.Edges) > 0:
            flat.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - flat.BoundBox.ZMin))
            return Part.Wire(flat.Edges)

    # Part.show(w, "WireToFlatten")
    # FreeCAD.Console.PrintWarning("No flat edges returned during flattening.\n")
    pnts = w.discretize(Deflection=deflection)
    lst = pnts[0]
    lines = []
    for p in pnts[1:]:
        lines.append(Part.makeLine(lst, p))
        lst = p
    wr = Part.Wire(lines)
    # Part.show(wr, "DiscretizedWire")
    return _flattenWire(wr, deflection)


def _flattenSingleFace(face, profile=True, holes=True):
    """_flattenSingleFace(face, profile=True, holes=True)
    Return flattened face, with assumption that face has positive Z exposure."""
    if len(face.Faces) > 1:
        PathLog.error("_flattenSingleFace() len(face.Faces) > 1")
        return None

    def _refine(wire):
        """_refine(wire)"""
        unique = Edge.uniqueEdges(_fuseShapes(wire.Edges).Edges)
        return Part.Wire(Edge.removeUnconnectedEdges(unique))

    if profile and holes:
        flat = [_flattenWire(w) for w in face.Wires]
        try:
            f = Part.Face(flat[0])
        except:
            if len(flat[0].Edges) == 1:
                return flat[0].copy()
            refined = _refine(flat[0])
            if refined.isClosed():
                return Part.Face(refined)
            else:
                return flat[0].copy()  # refined
        else:
            for w in flat[1:]:
                cut = f.cut(Part.Face(w))
                f = cut
        return f
    elif not profile and holes:
        if len(face.Wires) == 1:
            # No holes in face
            return None

        flat = [_flattenWire(w) for w in face.Wires[1:]]
        return _fuseShapes(flat)
    elif profile and not holes:
        flat = _flattenWire(face.Wires[0])
        try:
            f = Part.Face(flat)
        except:
            if len(flat.Edges) == 1:
                return flat.copy()
            refined = _refine(flat)
            if refined.isClosed():
                return Part.Face(refined)
            else:
                return None
        else:
            return f
    # Eif
    PathLog.info("_flattenSingleFace() return None")
    return None


def _sectionExtrudedFace(ext, zLen):
    faces = [f for f in ext.Faces if f.BoundBox.ZLength > zLen * 2.0]
    flat = []
    for f in faces:
        # Part.show(f, "LongFace")
        verts = []
        scan = []
        for e in f.Edges:
            if len(e.Vertexes) == 1:
                scan.append(e.copy())
            else:
                p1 = e.Vertexes[0].Point
                p2 = e.Vertexes[1].Point
                dif = p1.sub(p2)
                if PathGeom.isRoughly(
                    dif.x + dif.y, 0.0
                ):  # and e.Curve.TypeId == "Part::GeomLine":
                    # verts.append(e.copy())
                    pass
                elif e.BoundBox.ZMin > f.BoundBox.ZMin + zLen * 2.0:
                    scan.append(e.copy())

        for s in scan:
            # Part.show(s, "Scan")
            sbb = s.BoundBox
            fc = PathGeom.makeBoundBoxFace(sbb, 2.0, sbb.ZMin - 10.0)
            ft = fc.makeParallelProjection(s, FreeCAD.Vector(0.0, 0.0, 1.0))
            if len(ft.Edges) > 0:
                ft.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - ft.BoundBox.ZMin))
                w = Part.Wire(ft.Edges)
                # Part.show(w, "ScanWire")
                flat.append(w)
    return _fuseShapes(flat)


def _sectionVerticalFace(f, deflection=0.01):
    def _discretize(f, deflection):
        pnts = f.Wires[0].discretize(Deflection=deflection)
        points = [FreeCAD.Vector(p.x, p.y, 0.0) for p in pnts]
        lst = points[0]
        lines = []
        for p in points[1:]:
            if not PathGeom.isRoughly(lst.sub(p).Length, 0.0):
                lines.append(Part.makeLine(lst, p))
                lst = p
        return Part.Wire(_fuseShapes(lines).Edges)

    if f.Surface.TypeId == "Part::GeomPlane":
        # print("GeomPlane....")
        fused = f.extrude(
            FreeCAD.Vector(0.0, 0.0, round(f.BoundBox.DiagonalLength * 1000.0))
        )
        # Part.show(fused, "Ext")
        if fused.Area < 3.0 * f.Area:
            return _discretize(f, deflection)

        vertEdges = []
        for e in fused.Edges:
            if e.Curve.TypeId != "Part::GeomLine":
                continue
            diff = e.Vertexes[0].Point.sub(e.Vertexes[1].Point)
            if abs(diff.x) > 0.00001 or abs(diff.y) > 0.00001:
                continue
            vertEdges.append(e.copy())
        vertEdges.sort(key=lambda e: e.Length, reverse=True)
        # print(f"len(vertEdges): {len(vertEdges)}")
        lines = []
        v0 = vertEdges[0].Vertexes[0].Point
        p0 = FreeCAD.Vector(v0.x, v0.y, 0.0)
        for ve in vertEdges[1:]:
            v1 = ve.Vertexes[0].Point
            p1 = FreeCAD.Vector(v1.x, v1.y, 0.0)
            if not PathGeom.isRoughly(p0.sub(p1).Length, 0.0):
                ln = Part.makeLine(p0, p1)
                lines.append(ln)

        if len(lines) > 0:
            return Part.Wire(_fuseShapes(lines).Edges)
        else:
            return _discretize(f, deflection)
    elif f.Surface.TypeId == "Part::GeomCylinder":
        # print("GeomCylinder....")
        ext = f.extrude(
            FreeCAD.Vector(0.0, 0.0, round(f.BoundBox.DiagonalLength * 100.0))
        )
        if PathGeom.isRoughly(ext.Volume, 0.0):
            # Part.show(ext, "ExtCylFace")
            section = _sectionExtrudedFace(ext, f.BoundBox.DiagonalLength)
            # Part.show(section, "LongFaceFlat")
            return Part.Wire(section.Edges)
        else:
            # print("GeomCyl ext has volume")
            wires = []
            for i in ext.slice(
                FreeCAD.Vector(0, 0, 1), ext.BoundBox.ZMin + ext.BoundBox.ZLength / 2.0
            ):
                wires.append(i)
            f = Part.Face(wires)  # wires[0].copy()
            f.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - f.BoundBox.ZMin))
            return f
    else:
        fused = f.extrude(
            FreeCAD.Vector(0.0, 0.0, round(f.BoundBox.DiagonalLength * 100.0))
        )
        if len(fused.Faces) < 3:
            # print("len faces < 3")
            pnts = f.Wires[0].discretize(Deflection=deflection)
            lst = pnts[0]
            lines = []
            for p in pnts[1:]:
                lines.append(Part.makeLine(lst, p))
                lst = p
            return _sectionVerticalFace(Part.Face(Part.Wire(lines))), deflection

        # Part.show(fused, "Ext")
        # print("len faces > 2")
        bbf = PathGeom.makeBoundBoxFace(
            f.BoundBox, 5.0, fused.BoundBox.ZMin + fused.BoundBox.ZLength / 2.0
        )
        # Part.show(bbf, "Bbf")
        section = bbf.cut(fused)
        # Part.show(section, "SectA")
        section.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - section.BoundBox.ZMin))
        # Part.show(section, "SectB")
        return Part.Wire(section.Edges)


def refineWireEdges(wireEdges):
    """refineWireEdges(w)
    Return wire with consecutive colinear line segments combined into a single, long segment.
    """

    edges = Edge._orientEdgesBasic(wireEdges)
    p = edges.pop(0)
    grp = [p]
    lstDir = p.Vertexes[1].Point.sub(p.Vertexes[0].Point).normalize()
    for o in edges:
        curDir = o.Vertexes[1].Point.sub(o.Vertexes[0].Point).normalize()
        if PathGeom.isRoughly(curDir.sub(lstDir).Length, 0.0):
            # direction of last edge and current edge are within tolerance,
            # so extend previous line to end of current
            p1 = grp.pop().Vertexes[0].Point
            p2 = o.Vertexes[1].Point
            if not PathGeom.isRoughly(p1.sub(p2).Length, 0.0):
                grp.append(Part.makeLine(p1, p2))
        else:
            grp.append(o.copy())
            lstDir = curDir
    # Efor
    return [e.copy() for e in grp]


def _simplifySegmentsInWire(w):
    unChanged = True
    edges = Edge._orientEdgesBasic([ee for ee in Part.__sortEdges__(w.Edges)])
    # print(f"_simplifySegmentsInWire(w) len(edges): {len(edges)}")
    # Part.show(Part.Wire(edges), "OrientedEdges")
    p = edges[0].copy()
    # Part.show(p, "Edge")
    grp = [p]
    lastType = p.Curve.TypeId
    lstDir = p.Vertexes[1].Point.sub(p.Vertexes[0].Point).normalize()
    for eee in edges[1:]:
        # Part.show(eee, "Edge")
        # print(f"lstDir: {lstDir}")
        # print(f"thisType: {eee.Curve.TypeId}")
        curDir = eee.Vertexes[1].Point.sub(eee.Vertexes[0].Point).normalize()
        # print(f"curDir: {curDir}")

        if lastType != "Part::GeomLine":
            FreeCAD.Console.PrintWarning("lastType error\n")
            grp.append(eee.copy())
            lstDir = curDir
            lastType = eee.Curve.TypeId
            continue

        if eee.Curve.TypeId != "Part::GeomLine":
            FreeCAD.Console.PrintWarning("thisType error\n")
            grp.append(eee.copy())
            lstDir = curDir
            lastType = eee.Curve.TypeId
            continue

        if not PathGeom.isRoughly(curDir.sub(lstDir).Length, 0.0):
            FreeCAD.Console.PrintWarning(f"direction error\n")
            grp.append(eee.copy())
            lstDir = curDir
            lastType = eee.Curve.TypeId
            continue

        if len(grp) == 0:
            PathLog.error("grp length is zero.")
            break

        # direction of last edge and current edge are within tolerance,
        # so extend previous line to end of current
        lstEdg = grp[-1]
        p1 = lstEdg.Vertexes[0].Point
        p2 = eee.Vertexes[1].Point
        if not PathGeom.isRoughly(p1.sub(p2).Length, 0.0):
            # print("Merging segments")
            grp.pop()  # remove last group edge
            grp.append(Part.makeLine(p1, p2))  # extend last edge through current
            unChanged = False
        else:
            grp.append(eee.copy())
            lstDir = curDir
            lastType = eee.Curve.TypeId

    # Efor
    if unChanged:
        # print("wire unchanged")
        return w.copy()

    # print(f"len(grp): {len(grp)}")
    # for g in grp:
    #    Part.show(g, "Edge")
    sortedEdges = Part.__sortEdges__(grp)
    # wire = Part.Wire(sortedEdges)
    # Part.show(wire, "Wire")
    return Part.Wire(sortedEdges)


def _flattenGeomBSplineSurface(face, profile, holes, precision):
    openWires = []
    regions = []

    fsf = _flattenSingleFace(face, profile, holes)
    isVert = PathGeom.isRoughly(face.normalAt(0, 0).z, 0.0)
    if isVert:
        print("GeomBSplineSurface. Face is vertical.")
        openWires.append(fsf)
    else:
        if len(fsf.Faces) == 0:
            print("GeomBSplineSurface. No faces for fsf.")
            openWires.append(fsf)
        else:
            regions.append(fsf)

    return regions, openWires


def _flattenGeomCone(face, profile, holes, precision):

    def _flattenConeSection(f):
        groups = Part.sortEdges(
            Region.flattenEdges(
                [e.copy() for e in f.Edges if e.Curve.TypeId != "Part::GeomLine"]
            )
        )
        faces = [Part.Face(Part.Wire(g)) for g in groups]
        faces.sort(key=lambda f: f.Area, reverse=True)
        return faces[0].cut(faces[1])

    openWires = []
    regions = []

    if len(face.Wires) == 1 and len(face.Edges) == 3:
        fsf = _flattenConeSection(face)
    else:
        fsf = _flattenSingleFace(face, profile, holes)
    if fsf:
        if len(fsf.Faces) == 0:
            openWires.append(fsf)
        else:
            regions.append(fsf)

    return regions, openWires


def _flattenGeomCylinder(face, profile, holes, precision):
    openWires = []
    regions = []
    norm = face.normalAt(0, 0)
    # u, v = face.ParameterRange[:2]
    # norm = face.normalAt(u, v)

    isVert = PathGeom.isRoughly(norm.z, 0.0)
    if isVert:
        # Part.show(face, "CylFace_Vert")
        svf = _sectionVerticalFace(face, 0.01)
        # Part.show(svf, "Svf")
        if isinstance(svf, Part.Face):
            regions.append(svf)
        else:
            openWires.append(_sectionVerticalFace(face, 0.01))
    else:
        # Part.show(face, "CylFace")
        regions.append(_flattenSingleFace(face, profile, holes))

    # print(f"len(regions): {len(regions)}")

    return regions, openWires


def _flattenGeomPlane_orig(face, profile, holes, zNormalLimit):
    openWires = []
    regions = []
    zNorm = face.normalAt(0.0, 0.0).z
    # print(f"zNorm: {zNorm}")
    fsf = _flattenSingleFace(face, profile, holes)
    # Part.show(fsf, "Fsf")
    if fsf is None:
        print("_flattenGeomPlane() fsf is None.")

    if zNorm > zNormalLimit:
        if fsf:
            if len(fsf.Faces) == 0:
                openWires.append(fsf)
            else:
                regions.append(fsf)
    elif PathGeom.isRoughly(zNorm, 0.0):
        try:
            openWires.append(_sectionVerticalFace(face, 0.001))
        except:
            openWires.append(fsf)

    elif zNorm < 0.0:
        # FreeCAD.Console.PrintWarning(
        #    "Ignoring undercut facing planar face.\n"
        # )
        pass
    else:
        FreeCAD.Console.PrintError("Unable to categorize planar face.\n")
        Part.show(face, "_flattenGeomPlane_Error")

    return regions, openWires


def _flattenGeomPlane(face, profile, holes, precision):
    openWires = []
    regions = []
    zNorm = round(face.normalAt(0.0, 0.0).z, precision)
    # print(f"zNorm: {zNorm}")
    fsf = _flattenSingleFace(face, profile, holes)
    # Part.show(fsf, "Fsf")
    if fsf is None:
        print("_flattenGeomPlane() fsf is None.")

    if zNorm > 0.0:
        if fsf:
            if len(fsf.Faces) == 0:
                openWires.append(fsf)
            else:
                regions.append(fsf)
    elif PathGeom.isRoughly(zNorm, 0.0):
        try:
            openWires.append(_sectionVerticalFace(face, 0.001))
        except:
            openWires.append(fsf)

    elif zNorm < 0.0:
        # FreeCAD.Console.PrintWarning(
        #    "Ignoring undercut facing planar face.\n"
        # )
        pass
    else:
        FreeCAD.Console.PrintError("Unable to categorize planar face.\n")
        Part.show(face, "_flattenGeomPlane_Error")

    return regions, openWires


def _flattenGeomSphere(face, profile, holes, precision):
    openWires = []
    regions = []

    if len(face.Wires) == 1:
        if len(face.Edges) == 2:
            for e in face.Edges:
                if e.Curve.TypeId == "Part::GeomCircle" and len(e.Vertexes) == 1:
                    flat = _flattenWire(Part.Wire([e.copy()]))
                    regions.append(Part.Face(flat))
                    break
        elif len(face.Edges) == 3:
            for e in face.Edges:
                if e.Curve.TypeId == "Part::GeomCircle" and len(e.Vertexes) == 1:
                    flat = _flattenWire(Part.Wire([e.copy()]))
                    regions.append(Part.Face(flat))
                    break

    """
    norm = face.normalAt(0.0, 0.0).z
    fsf = _flattenSingleFace(face, profile, holes)
    if fsf is None:
        print("_flattenGeomPlane() fsf is None.")
    else:
        Part.show(fsf, "SphereFace")

    if norm > zNormalLimit or True:
        if fsf:
            if len(fsf.Faces) == 0:
                openWires.append(fsf)
            else:
                regions.append(fsf)
    elif PathGeom.isRoughly(norm, 0.0):
        try:
            openWires.append(_sectionVerticalFace(face, 0.001))
        except:
            openWires.append(fsf)

    elif norm < 0.0:
        # FreeCAD.Console.PrintWarning(
        #    "Ignoring undercut facing planar face.\n"
        # )
        pass
    else:
        FreeCAD.Console.PrintError("Unable to categorize planar face.\n")
        Part.show(face, "_flattenGeomPlane_Error")
    """

    return regions, openWires


def _flattenGeomSurfaceOfRevolution(face, profile, holes, precision):
    openWires = []
    regions = []
    PathLog.error("_flattenGeomSurfaceOfRevolution() is INCOMPLETE")
    return regions, openWires


def _flattenGeomTEMPLATE(face, profile, holes, precision):
    openWires = []
    regions = []
    return regions, openWires


# ###################################################################
def flattenFace(
    face,
    profile=True,
    holes=True,
    ld=1.0,
    ad=5.0,
    precision=8,
):
    if len(face.Faces) > 1:
        PathLog.error("flattenFace() Multiple Face shapes within 'face'.")
        return None

    openWires = []
    regions = []
    other = []
    surfaceType = face.Surface.TypeId[6:]
    # PathLog.info(f"flattenFace() Suface type: {surfaceType}")

    # Handle face with undercut exposure using meshes
    if MeshTools.faceHasUndercut(face, ld, ad, roundTo=precision):
        # PathLog.warning("Face has undercut...")
        mesh = MeshTools.shapeToMesh(face, linearDeflection=ld, angularDeflection=ad)
        proj = MeshTools.extractMeshProjection(mesh, precision)
        # MeshTools.meshToObject(proj, "ProjRaw")
        if len(proj.Facets) > 0:
            wires = MeshTools.extractMeshPerimeterWires(
                proj, flatten=True, refine=True, precision=precision
            )
            if len(wires) > 0:
                edges = []
                for wr in wires:
                    # Part.show(wr, "PerimWire")
                    edges.extend([e.copy() for e in wr.Edges])
                fusedEdges = _fuseShapes(edges)
                grps = Part.sortEdges(fusedEdges.Edges)
                useAlt = False
                for g in grps:
                    if not Part.Wire(g).isClosed():
                        useAlt = True
                        break

                if useAlt:
                    PathLog.warning(
                        "Unable to apply 'profile' and 'holes' requests. Providing 'profile'."
                    )
                    outer = TechDraw.findShapeOutline(
                        fusedEdges, 1, FreeCAD.Vector(0, 0, 1)
                    )
                    regions.append(Part.Face(outer))
                else:
                    fc = _closedWiresToFace(wires, profile, holes)
                    if fc:
                        # PathLog.info("_closedWiresToFace() returned")
                        # Part.show(fc, "ClosedWireFace")
                        regions.append(fc)
            else:
                PathLog.error("Unable to extract meshed region from face.")
                # PathLog.info(f"Proj.Facets: {len(proj.Facets)}")
                MeshTools.meshToObject(proj, "ErrorProj")
        else:
            # PathLog.warning("No mesh Z+ projection facets.")
            # Part.show(face, "ErrorFace")
            other.append(face.copy())
        # Eif
        return regions, openWires, other

    # PathLog.warning("No undercut on Face.")
    # Part.show(face, "Source")

    faceType = f"_flatten{surfaceType}"
    if faceType not in globals().keys():
        Part.show(face, faceType)
        print(f"No {faceType}() function")
        return [], [], []

    # Process face without undercut using other methods
    flattenFunction = globals()[faceType]
    rgns, ow = flattenFunction(face, profile, holes, precision)
    # ows = [Part.Wire(Edge.refineWireEdges(w.Edges)) for w in ow]
    # print(f"len(ow): {len(ow)}")
    ows = []
    for w in ow:
        if len(w.Edges) == 0:
            continue

        # Part.show(w, "OW")

        if len(w.Edges) == 1:
            ows.append(w.copy())
            continue

        ows.append(_simplifySegmentsInWire(w))

    # if len(rgns) > 0:
    #    Part.show(Part.makeCompound(rgns), "FaceRegion")

    return rgns, ows, other


def flattenFaces(
    faces,
    profile=True,
    holes=True,
    ld=1.0,
    ad=5.0,
    precision=6,
    excludeArea=0.0,
):
    allRegions = []
    allOpenWires = []
    for f in faces:
        if len(f.Faces) > 1:
            PathLog.error(
                "flattenFaces() Multiple Face shapes within 'face'. Skipping 'face'."
            )
            continue

        regions, openWires, __ = flattenFace(f, profile, holes, ld, ad, precision)
        allRegions.extend(regions)
        allOpenWires.extend(openWires)
    # Efor

    if allRegions:
        # Part.show(Part.makeCompound(allRegions), "AllRegionsRaw")
        region = Region.cleanFace(_fuseShapes(allRegions))
        # Part.show(region, "Region")
    else:
        region = None
    if region and excludeArea > 0.0:
        shps = []
        for r in region.Faces:
            faces = []
            for w in r.Wires:
                f = Part.Face(w)
                if f.Area > excludeArea:
                    faces.append(f)

            if not faces:
                continue

            trim = faces[0].copy()
            for f in faces[1:]:
                cut = trim.cut(f)
                trim = cut
            shps.append(trim.copy())
        return _fuseShapes(shps), allOpenWires

    # return region, _fuseShapes(allOpenWires)
    return region, allOpenWires


# ###################################################################
# ###################################################################


def _executeAsMacro_1():
    return None, None


if IS_MACRO and FreeCAD.GuiUp:
    region, selectedFaces = _executeAsMacro_1()
    if region is not None:
        r = Part.show(region, "Face")
        r.Label = "Combined Region"
    else:
        print("No combine region returned.")
    FreeCAD.ActiveDocument.recompute()
else:
    # print("Imported Region utilities")
    pass
