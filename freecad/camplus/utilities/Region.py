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
import DraftGeomUtils
import Path.Geom as PathGeom
import math
import Path.Log as PathLog
import Path.Base.Drillable as Drillable
import freecad.camplus.utilities.Edge as Edge
import freecad.camplus.utilities.General as GenUtils
import freecad.camplus.support.Gui_Input as Gui_Input
import freecad.camplus.utilities.MeshTools as MeshTools

if FreeCAD.GuiUp:
    import FreeCADGui

__title__ = "Region Utilities"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Various functions to work with regions."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""
__date__ = ""


IS_MACRO = False  # False  # Set to True to use as macro
SET_SELECTION = False
SELECTIONS = [
    (
        "Body",
        [
            "Face16",
            "Face18",
            "Face17",
            "Face14",
            "Face15",
            "Face7",
            "Face3",
            "Face9",
        ],
    )
]
SELECTIONS2 = [
    (
        "Body",
        [
            "Face8",
            "Face39",
        ],
    )
]
SELECTIONS3 = [
    (
        "Body",
        [
            "Face4",
            "Face8",
            "Face6",
            "Face26",
        ],
    )
]


if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())

translate = FreeCAD.Qt.translate


# Support functions
def _separateFaceWires(faces):
    outerWires = []
    innerWires = []

    def _separateWires(wires):
        tups = [(w.copy(), w.BoundBox.DiagonalLength) for w in wires]
        tups.sort(key=lambda t: t[1], reverse=True)

        outWire = tups[0][0]
        inWires = [w for w, __ in tups[1:]]

        if isConcentricLoopSet(outWire):
            outer, inner = separateLoopSet(outWire)
            outWire = outer
            inWires.insert(0, inner)

        return outWire, inWires

    for face in faces:
        outer, inner = _separateWires(face.Wires)
        outerWires.append(outer)
        innerWires.extend(inner)

    return outerWires, innerWires


def _xyz_to_text(x, y, z):
    return "x{}_y{}_z{}".format(x, y, z)


def _pointToText(p, precision=6):
    factor = 10**precision
    v0x = int(round(p.x, precision) * factor)
    v0y = int(round(p.y, precision) * factor)
    v0z = int(round(p.z, precision) * factor)
    return _xyz_to_text(v0x, v0y, v0z)


def _getXYMinVertex(edge):
    v0 = edge.Vertexes[0].Point

    if len(edge.Vertexes) == 1:
        return v0, None

    v1 = edge.Vertexes[1].Point

    if v0.x < v1.x:
        # v0 is min
        return v0, v1
    elif v0.x > v1.x:
        return v1, v0
    else:
        if v0.y <= v1.y:
            # v0 is min
            return v0, v1
        else:
            return v1, v0


def isConcentricLoopSet(wire):
    if len(wire.Edges) != 3:
        return False
    loopCnt = 0
    for e in wire.Edges:
        if e.Closed:
            loopCnt += 1
    if loopCnt != 2:
        return False
    return True


def separateLoopSet(wire):
    idxs = []
    i = 0
    for e in wire.Edges:
        if e.Closed:
            idxs.append(i)
        i += 1
    e1 = Part.Wire([wire.Edges[idxs[0]]])
    e2 = Part.Wire([wire.Edges[idxs[1]]])
    if e1.Length > e2.Length:
        return e1, e2
    return e2, e1


def _refineOpenWire(wire):
    """_refineOpenWire(wire)"""
    unique = Edge.uniqueEdges(fuseShapes(wire.Edges).Edges)
    clean = Edge.removeUnconnectedEdges(unique)
    return Part.Wire(clean)


def _flattenSingleConeSection(f):
    groups = Part.sortEdges(
        flattenEdges([e.copy() for e in f.Edges if e.Curve.TypeId != "Part::GeomLine"])
    )
    faces = [Part.Face(Part.Wire(g)) for g in groups]
    faces.sort(key=lambda f: f.Area, reverse=True)
    return faces[0].cut(faces[1])


def _flattenWires(wires):
    closedWires = []
    openEdges = []
    for w in wires:
        if not w.isClosed():
            openWires.append(w.copy())
        # Part.show(w, "RawWire_A")
        wBB = w.BoundBox
        if PathGeom.isRoughly(wBB.ZLength, 0.0):
            # flat = Part.Wire([e.copy() for e in w.Edges])
            flat = w.copy()
            flat.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - flat.BoundBox.ZMin))
            closedWires.append(flat)
        else:
            face = PathGeom.makeBoundBoxFace(wBB, 2.0, wBB.ZMin - 10.0)
            flat = face.makeParallelProjection(w, FreeCAD.Vector(0.0, 0.0, 1.0))
            if len(flat.Edges) > 0:
                flat.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - flat.BoundBox.ZMin))
                wire = Part.Wire(flat.Edges)
                if wire.isClosed():
                    closedWires.append(wire)
                else:
                    # Part.show(wire, "FlatOpen")
                    openEdges.extend(wire.Edges)
            else:
                # FreeCAD.Console.PrintMessage(
                #    "No flat edges returned during flattening.\n"
                # )
                pass
        # Eif
    # Efor

    openWires = []
    if openEdges:
        for g in Part.sortEdges(openEdges):
            w = Part.Wire(g)
            if w.isClosed():
                closedWires.append(w)
            else:
                FreeCAD.Console.PrintMessage("Open wire created during flattening.\n")
                openWires.append(w)

    return closedWires, openWires


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


def _makeAdjacentWire_Tups(outerWires):
    # print("_makeAdjacentWire_Tups()")
    allEdgesTups = []
    edgeCount = 0
    # print(f"processing {len(outerWires)} outer wires")
    for wi in range(len(outerWires)):
        w = outerWires[wi]
        # print(f"  {len(w.Edges)} edges")
        edgeCount += len(w.Edges)
        for ei in range(len(w.Edges)):
            e = w.Edges[ei]
            try:
                midpntVert = e.valueAt(e.getParameterByLength(e.Length / 2.0))
                midpntVertTxt = _pointToText(midpntVert, 4)
                minVert, maxVert = _getXYMinVertex(e)
                minVertTxt = _pointToText(minVert, 4)
                if maxVert:
                    maxVertTxt = _pointToText(maxVert, 4)
                else:
                    maxVertTxt = ""
                    # print("___________ No max vertex ___________")
                allEdgesTups.append(
                    (minVertTxt + midpntVertTxt, minVertTxt, maxVertTxt, e)
                )
            except:
                # Part.show(e.copy(), "error_edge")
                print("_makeAdjacentWire_Tups() edge to string error")

    allEdgesTups.sort(key=lambda tup: tup[0])

    # print(f"Raw edge count: {edgeCount}")

    return allEdgesTups


def _removeDuplicateEdges(allEdgesTups):
    # print("_removeDuplicateEdges()")
    # Remove shared edges
    uniqueEdgesTups = [allEdgesTups[0]]
    for t in allEdgesTups[1:]:
        if uniqueEdgesTups:
            if uniqueEdgesTups[-1][0] != t[0]:
                # unique edge
                uniqueEdgesTups.append(t)
            else:
                # remove last edge because it is same as current
                # print("popping last edge")
                uniqueEdgesTups.pop()
                # Part.show(last[3], "LastEdge")
        else:
            uniqueEdgesTups.append(t)

    # print(f"uniqueEdgesTups count: {len(uniqueEdgesTups)}")

    return [(b, c, d) for (a, b, c, d) in uniqueEdgesTups]


def _mergeAdjacentWires(outerWires):
    # print("_mergeAdjacentWires()")
    allEdgesTups = _makeAdjacentWire_Tups(outerWires)
    if not allEdgesTups:
        return []
    uniqueEdgesTups = _removeDuplicateEdges(allEdgesTups)
    # Convert unique edges to wires
    wires = DraftGeomUtils.findWires([e for (__, __, e) in uniqueEdgesTups])
    return wires


def _consolidateAreas(closedWires, saveHoles=True):
    wireCnt = len(closedWires)
    # print(f"_consolidateAreas(closedWires={wireCnt})")

    if wireCnt == 1:
        return [Part.Face(closedWires[0])], []

    # Create face data tups
    faceTups = []
    for i in range(wireCnt):
        w = closedWires[i]
        f = Part.Face(w)
        faceTups.append((i, f, f.Area))

    # Sort large to small by face area
    faceTups.sort(key=lambda tup: tup[2], reverse=True)

    result = []
    cnt = len(faceTups)
    while cnt > 0:
        small = faceTups.pop()
        cnt -= 1
        if cnt:
            for fti in range(len(faceTups)):
                big = faceTups[fti]
                cut = big[1].cut(small[1])
                if PathGeom.isRoughly(cut.Area, big[2]):
                    # small not inside big
                    result.append(small)
                else:
                    # replace big face with cut version
                    # print("found internal loop wire")
                    if saveHoles:
                        faceTups[fti] = (big[0], cut, cut.Area)
                    break
        else:
            result.append(small)
    # Ewhile
    faces = [t[1] for t in result]
    for f in faces:
        f.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - f.BoundBox.ZMin))
    # Part.show(Part.makeCompound(faces), "FacesConsolidate")
    outerFaces = [Part.Face(f.Wires[0]) for f in faces]
    innerFaces = []
    for f in faces:
        for w in f.Wires[1:]:
            innerFaces.append(Part.Face(w))

    return outerFaces, innerFaces


def _fuseFlatWireAreas(flatWires):
    openEdges = []
    closedWires = []

    if len(flatWires) < 2:
        return flatWires

    # separate edges from open wires
    for w in flatWires:
        if w.isClosed():
            closedWires.append(w)
        else:
            openEdges.extend(w.Edges)
    # Attempt to make closed wires from all open edges
    if len(openEdges) > 1:
        closedWires.extend(
            [
                w
                for w in [Part.Wire(edgs) for edgs in Part.sortEdges(openEdges)]
                if w.isClosed()
            ]
        )

    # Process closed wires
    # merge adjacent regions using fuse() method to connect closed wires at common edges
    if len(closedWires) > 1:
        face = Part.Face(closedWires.pop())
        for w in closedWires:
            f = face.fuse(Part.Face(w)).removeSplitter()
            face = f
        return face.Wires
    else:
        return closedWires


def _makeWireText(w):
    """_makeWireText(wire)
    The powers fo 10 used will likely need adjustment depending on face sizes.
    If the values are too restrictive, they may cause the combining of regions
    algorithm to not work correctly."""
    f = Part.Face(w)
    """
    centOfMass = _pointToText(f.CenterOfMass, 3)
    wireLength = "_" + str(int(w.Length * 1000))
    area = "_" + str(int(f.Area / 10.0))
    """
    centOfMass = _pointToText(f.CenterOfMass)
    wireLength = "_" + str(int(w.Length * 10000))
    area = "_" + str(int(f.Area * 100))
    return centOfMass + wireLength + area


def cleanFace(face):
    bbFace1 = PathGeom.makeBoundBoxFace(face.BoundBox, 2.0)
    bbFace2 = PathGeom.makeBoundBoxFace(face.BoundBox, 4.0)
    neg = bbFace2.cut(face)
    clean = bbFace1.cut(neg)
    return clean.copy()


##############
##############
def _flattenSingleFace(face, profile=True, holes=True):
    """_flattenSingleFace(face, profile=True, holes=True)
    Return flattened face, with assumption that face has positive Z exposure."""
    if len(face.Faces) > 1:
        return None

    if profile and holes:
        flat = [_flattenWire(w) for w in face.Wires]
        try:
            f = Part.Face(flat[0])
        except:
            if len(flat[0].Edges) == 1:
                return flat[0].copy()
            refined = _refineOpenWire(flat[0])
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
        return fuseShapes(flat)
    elif profile and not holes:
        flat = _flattenWire(face.Wires[0])
        try:
            f = Part.Face(flat)
        except:
            if len(flat.Edges) == 1:
                return flat.copy()
            refined = _refineOpenWire(flat)
            if refined.isClosed():
                return Part.Face(refined)
            else:
                return None
        else:
            return f
    # Eif
    return None


def _sectionVerticalFace(f, deflection=0.01):
    fused = fuseShapes(
        [
            e.extrude(FreeCAD.Vector(0.0, 0.0, round(f.BoundBox.ZLength * 10.0)))
            for e in f.Wires[0].Edges
        ]
    )
    if len(fused.Faces) < 3:
        pnts = f.Wires[0].discretize(Deflection=deflection)
        lst = pnts[0]
        lines = []
        for p in pnts[1:]:
            lines.append(Part.makeLine(lst, p))
            lst = p
        return _sectionVerticalFace(Part.Face(Part.Wire(lines)))
    section = PathGeom.makeBoundBoxFace(
        f.BoundBox, 5.0, fused.BoundBox.ZMin + fused.BoundBox.ZLength / 2.0
    ).cut(fused)
    section.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - section.BoundBox.ZMin))
    edges = Edge.refineWireEdges(section.Wires[1].Edges)
    return Part.Wire(edges)


def getAllUpfacingRegions(
    faces,
    profile=True,
    holes=True,
    ld=1.0,
    ad=5.0,
    zNormalLimit=0.00001,
    minArea=0.0,
    excludeArea=0.0,
):
    import TechDraw

    regions = []
    openWires = []

    # f.Surface.TypeId: Part::GeomSurfaceOfRevolution
    # group = doc.addObject("App::DocumentObjectGroup", "Group")
    # group2 = doc.addObject("App::DocumentObjectGroup", "Group")
    # owCnt = 0

    for f in faces:
        # print(f"f.Surface.TypeId: {f.Surface.TypeId}")

        if f.Surface.TypeId == "Part::GeomPlane":
            norm = f.normalAt(0.0, 0.0).z
            fsf = _flattenSingleFace(f, profile, holes)
            if norm > zNormalLimit:
                if fsf:
                    if len(fsf.Faces) == 0:
                        openWires.append(fsf)
                    else:
                        regions.append(fsf)
            elif PathGeom.isRoughly(norm, 0.0):
                try:
                    openWires.append(_sectionVerticalFace(f, ld))
                except:
                    openWires.append(fsf)

            elif norm < 0.0:
                # FreeCAD.Console.PrintWarning(
                #    "Ignoring undercut facing planar face.\n"
                # )
                pass
            else:
                FreeCAD.Console.PrintWarning("Unable to categorize planar face.\n")
                Part.show(f, "PlanarFaceError")
        elif f.Surface.TypeId == "Part::GeomCylinder":
            if MeshTools.faceHasUndercut(f):
                mesh = MeshTools.shapeToMesh(
                    f, linearDeflection=ld, angularDeflection=ad
                )
                proj = MeshTools.extractMeshProjection(mesh, zNormalLimit)
                wires = MeshTools.extractMeshPerimeterWires(
                    proj, flatten=True, refine=True, zNormLimit=zNormalLimit
                )
                if len(wires) > 0 and not PathGeom.isRoughly(proj.Area, 0.0):
                    fc = Part.Face([wr for wr in wires if wr.isClosed()])
                    if fc.Area > minArea:
                        regions.append(fc)
                else:
                    # print(f"len(cyl_wires): {len(wires)}")
                    # print(f"cyl_proj.Area: {proj.Area}")
                    pass
            else:
                isVert = PathGeom.isRoughly(f.normalAt(0, 0).z, 0.0)
                if isVert:
                    try:
                        openWires.append(_sectionVerticalFace(f, ld))
                    except:
                        openWires.append(_flattenSingleFace(f))
                else:
                    regions.append(_flattenSingleFace(f, profile, holes))

        elif f.Surface.TypeId == "Part::GeomCone":
            if MeshTools.faceHasUndercut(f):
                mesh = MeshTools.shapeToMesh(
                    f, linearDeflection=ld, angularDeflection=ad
                )
                proj = MeshTools.extractMeshProjection(mesh, zNormalLimit)
                wires = MeshTools.extractMeshPerimeterWires(
                    proj, flatten=True, refine=True, zNormLimit=zNormalLimit
                )
                if len(wires) > 0 and not PathGeom.isRoughly(proj.Area, 0.0):
                    fc = Part.Face([wr for wr in wires if wr.isClosed()])
                    if fc.Area > minArea:
                        regions.append(fc)
                else:
                    # print(f"len(cone_wires): {len(wires)}")
                    # print(f"cone_proj.Area: {proj.Area}")
                    pass
            else:
                if len(f.Wires) == 1 and len(f.Edges) == 3:
                    fsf = _flattenSingleConeSection(f)
                else:
                    fsf = _flattenSingleFace(f, profile, holes)
                if fsf:
                    if len(fsf.Faces) == 0:
                        openWires.append(fsf)
                    else:
                        regions.append(fsf)
        elif f.Surface.TypeId == "Part::GeomBSplineSurface":
            if MeshTools.faceHasUndercut(f):
                # print("Face has undercut portion.")
                mesh = MeshTools.shapeToMesh(
                    f, linearDeflection=ld, angularDeflection=ad
                )
                proj = MeshTools.extractMeshProjection(mesh, zNormalLimit)
                wires = MeshTools.extractMeshPerimeterWires(
                    proj, flatten=True, refine=True, zNormLimit=zNormalLimit
                )
                edges = []
                for w in wires:
                    edges.extend([e.copy() for e in w.Edges])
                fusedEdges = fuseShapes(edges)
                outer = TechDraw.findShapeOutline(
                    fusedEdges, 1, FreeCAD.Vector(0, 0, 1)
                )
                fc = Part.Face(outer)
                if fc.Area > minArea:
                    print("GeomBSplineSurface meshed area > minArea")
                    regions.append(fc)
                else:
                    # print("meshed area NOT greater than minArea")
                    pass
            else:
                fsf = _flattenSingleFace(f, profile, holes)
                isVert = PathGeom.isRoughly(f.normalAt(0, 0).z, 0.0)
                if isVert:
                    print("GeomBSplineSurface. Face is vertical.")
                    openWires.append(fsf)
                else:
                    if len(fsf.Faces) == 0:
                        print("GeomBSplineSurface. No faces for fsf.")
                        openWires.append(fsf)
                    else:
                        regions.append(fsf)
        else:
            if MeshTools.faceHasUndercut(f):
                # print("Face has undercut portion.")
                mesh = MeshTools.shapeToMesh(
                    f, linearDeflection=ld, angularDeflection=ad
                )
                proj = MeshTools.extractMeshProjection(mesh, zNormalLimit)
                wires = MeshTools.extractMeshPerimeterWires(
                    proj, flatten=True, refine=True, zNormLimit=zNormalLimit
                )
                fc = Part.Face([wr for wr in wires if wr.isClosed()])
                if fc.Area > minArea:
                    regions.append(fc)
            else:
                # print("Face has no undercut.")
                # Part.show(f, "SourceFace")

                fsf = _flattenSingleFace(f, profile, holes)
                isVert = PathGeom.isRoughly(f.normalAt(0, 0).z, 0.0)
                if isVert:
                    openWires.append(fsf)
                else:
                    if len(fsf.Faces) == 0:
                        print("No faces for fsf.")
                        openWires.append(fsf)
                    else:
                        regions.append(fsf)

            # Eif
        # Eif

        """if len(openWires) > owCnt:
            owCnt = len(openWires)
            print(f"{owCnt} - f.Surface.TypeId: {f.Surface.TypeId}")
            Part.show(f, f"SourceFace_{owCnt}_")"""
    # Efor

    region = None
    if regions:
        if len(regions) == 1 and regions[0] is not None:
            region = regions[0]
        else:
            region = cleanFace(fuseShapes([r for r in regions if r is not None]))
        # Part.show(region, "Region")

    # print(
    #    f"regions: {len(regions)};  openWires: {len(openWires)}"
    # )

    if region and excludeArea > 0.0:
        shps = []
        for r in region.Faces:
            faces = []
            for w in r.Wires:
                f = Part.Face(w)
                if f.Area > excludeArea:
                    faces.append(f)
            clean = faces[0].copy()
            for f in faces[1:]:
                cut = clean.cut(f)
                clean = cut
            shps.append(clean.copy())
        region = fuseShapes(shps)

    # return region, regions, openWires
    return region, openWires


##############
##############
def _removeSelectedInternals(outerWires, innerWires):
    """_removeSelectedInternals(outerWires, InnerWires)
    Check if any inners are identical to selected outers, and remove both if true.
    Need to save those removed so they can be removed from the inners"""
    outers = []
    inners = []
    data = []

    # Create wire detail tuples for outer and inner wires
    for i in range(len(outerWires)):
        w = outerWires[i]
        data.append((_makeWireText(w), w, 0))
    for i in range(len(innerWires)):
        w = innerWires[i]
        data.append((_makeWireText(w), w, 1))
    data.sort(key=lambda tup: tup[0])

    if len(data) == 0:
        return outers, inners

    # Identify unique wire detail tuples
    unique = [data[0]]
    for d in data[1:]:
        if len(unique) == 0:
            # re-seed unique if empty list
            unique.append(d)
        else:
            if d[0] == unique[-1][0]:
                # remove selected duplicate inner and outer wires
                unique.pop()
            else:
                # Add unique outer and inner tuples
                unique.append(d)

    # Separate wires from tuples into outer and inner
    for __, w, typ in unique:
        if typ == 0:
            outers.append(w)
        else:
            inners.append(w)

    return outers, inners


def _executeAsMacro_1():
    # Get hole settings from user
    guiInput = Gui_Input.GuiInput()
    guiInput.setWindowTitle("Combine Region Details")
    seh = guiInput.addCheckBox("Save Existing Holes")
    seh.setChecked(True)
    shfm = guiInput.addCheckBox("Save Holes From Merge")
    shfm.setChecked(True)
    values = guiInput.execute()
    if values is None:
        return None, None

    (saveExisting, saveMerged) = values
    # return tuple (region, selectedFace)
    # return GenUtils.combineSelectedFaces(saveExisting, saveMerged)
    selectedFaces, __ = GenUtils.getFacesFromSelection()
    if len(selectedFaces) == 0:
        return None

    # combine faces into horizontal regions
    region, outerOpenWires = combineRegions(selectedFaces, saveExisting, saveMerged)

    # fuse faces together for projection of path geometry
    fusedFace = selectedFaces[0]
    if len(selectedFaces) > 1:
        fusedFace = selectedFaces[0]
        for f in selectedFaces[1:]:
            fused = fusedFace.fuse(f)
            fusedFace = fused

    return region, fusedFace


def _executeAsMacro3(selectedFaces, saveExisting, saveMerged):
    # combine faces into horizontal regions
    region, outerOpenWires = combineRegions(selectedFaces, saveExisting, saveMerged)

    # fuse faces together for projection of path geometry
    fusedFace = selectedFaces[0]
    if len(selectedFaces) > 1:
        fusedFace = selectedFaces[0]
        for f in selectedFaces[1:]:
            fused = fusedFace.fuse(f)
            fusedFace = fused

    return region, fusedFace


##################################################
def _refinePlanarFaces_orig(planar):
    """_refinePlanarFaces_orig(planar)
    Returns refined planar faces.
    """

    if len(planar) == 0:
        return Part.Shape()

    normPairs = []
    # group planar faces by Face.Normal() values
    for f in planar:
        n = f.Surface.normal(0.0, 0.0)
        if len(normPairs) > 0:
            add = True
            for nn, ff in normPairs:
                # if same Normal value
                if PathGeom.isRoughly(n.sub(nn).Length, 0.0):
                    ff.append(f)  # add face to list for given Normal value
                    add = False
                    break
            if add:
                normPairs.append((n, [f]))
        else:
            normPairs.append((n, [f]))

    # Fuse and refine planar face groups to remove splitters
    fused = []
    for n, ff in normPairs:
        # all = []
        # for f in fuseShapes(ff).Faces:
        #    all.extend(f.Edges)
        all = [e for f in fuseShapes(ff).Faces for e in f.Edges]
        refined = []
        for grp in Part.sortEdges(Edge.uniqueEdges(all)):
            w = Part.Wire(grp)
            if w.isClosed():
                refined.append(Part.Face(w))

        fused.extend([fc for fc in MeshTools.simplifyFaces(refined).Faces])

    return fuseShapes(fused)


def _refinePlanarFaces(planar):
    """_refinePlanarFaces(planar)
    Returns refined planar faces.
    """

    if len(planar) == 0:
        return Part.Shape()

    normPairs = []
    # group planar faces by Face.Normal() values
    for f in planar:
        n = f.Surface.normal(0.0, 0.0)
        if len(normPairs) > 0:
            add = True
            for nn, ff in normPairs:
                # if same Normal value
                if PathGeom.isRoughly(n.sub(nn).Length, 0.0):
                    ff.append(f)  # add face to list for given Normal value
                    add = False
                    break
            if add:
                normPairs.append((n, [f]))
        else:
            normPairs.append((n, [f]))

    # Fuse and refine planar face groups to remove splitters
    allEdges = []
    for n, ff in normPairs:
        allEdges.extend([e for f in fuseShapes(ff).Faces for e in f.Edges])

    refined = []
    for grp in Part.sortEdges(Edge.uniqueEdges(allEdges)):
        w = Part.Wire(grp)
        if w.isClosed():
            refined.append(Part.Face(w))

    fused = []
    fused.extend([fc for fc in MeshTools.simplifyFaces(refined).Faces])

    return fuseShapes(fused)


def _consolidateFlatFace(face):
    return PathGeom.makeBoundBoxFace(face.BoundBox, 5.0).cut(
        PathGeom.makeBoundBoxFace(face.BoundBox, 10.0).cut(face)
    )


def _separateNonplanarFaces(faceList):
    """_separateNonplanarFaces(faceList)
    Returns tuple of two lists: (planar, nonplanar).
        planar = list of tuples (face_normal, [face_list]).
        nonplanar = list of nonplanar faces.
    """
    planar = []
    non = []
    nonplanar = []
    # Separate planar and nonplanar
    for f in faceList:
        (planar.append(f) if type(f.Surface) == Part.Plane else non.append(f.copy()))

    for np in non:
        wireFace = Part.Face(_flattenWire(np.Wires[0]))
        meshFace = MeshTools.solidToRegion(
            np, linearDeflection=0.75, angularDeflection=7.5
        )
        diff = abs(round(wireFace.Area - meshFace.Area, 8))
        # print(f"wireFace.Area: {wireFace.Area};  meshFace.Area: {meshFace.Area}")
        # print(f"Area diff: {diff}")
        if diff < wireFace.Area / 350.0:
            # proj = makeProjection(np)
            # planar.append(Part.Face(Part.Wire(proj.Edges)))
            planar.append(np)
            print("moving nonplanar to planar")
        else:
            nonplanar.append(np)
            print("maintain nonplanar")

    return planar, nonplanar


def _cleanFace_old(f):
    big = PathGeom.makeBoundBoxFace(f.BoundBox, offset=4.0, zHeight=0.0)
    negative = big.cut(f)
    small = PathGeom.makeBoundBoxFace(f.BoundBox, offset=2.0, zHeight=0.0)
    return small.cut(negative)


def _cleanFace(face):
    if False and len(face.Wires) > 1:
        inner = [w.copy() for w in face.Wires[1:]]
        f = Part.Face(
            PathGeom.makeBoundBoxFace(face.BoundBox, 5.0).cut(face).Faces[0].Wires[1]
        )
        return f
    bbf = PathGeom.makeBoundBoxFace(face.BoundBox, 5.0)
    cut = bbf.cut(face)
    # Part.show(cut, "Cut_x_")
    if len(cut.Faces) > 0:
        f = cut.Faces[0]
        return Part.Face(f.Wires[1])
    print("_cleanFace() No face after cut.")
    return face


##################################################
# Primary function
def openWiresToFaces(obj, openWires):
    openFaces = []
    if not openWires:
        return openFaces
    print(f"RegionUtils.openWiresToFaces() is non-functional.")

    base = fuseShapes([b.Shape.copy() for b, __ in obj.Base])
    bottom = round(base.BoundBox.ZMin - 2.0, 0)
    extLen = round(base.BoundBox.ZLength + 5.0, 0)
    for w in openWires:
        bbf = PathGeom.makeBoundBoxFace(w.BoundBox, 1.0, bottom)
        bbfExt = bbf.extrude(FreeCAD.Vector(0.0, 0.0, extLen))
        cmn = base.common(bbfExt)
        Part.show(w, "OpenWire")
        Part.show(cmn, "OpenBlock")

    return openFaces


def fuseAndRefineRegions(faceList):
    """fuseAndRefineRegions(faceList) return a refined face shape (that may contain multiple independent faces).
    This function is an alternate to the 'removeSplitter()' method of face shapes."""
    # Separate planar and nonplanar
    planarFaces, nonplanar = _separateNonplanarFaces(faceList)
    planar = _refinePlanarFaces(planarFaces)
    # Part.show(planar, "PlanarFaces")

    return planar, nonplanar


def identifyRegions(faceShapes, includeHoles=True, saveMergedHoles=True):
    """identifyRegions(faceShapes, includeHoles=True, saveMergedHoles=True)
    Returns (outer, inner) tuple containing outer faces and inner faces.  A manual cut is
    required to create the complete set of combined faces, or use module method, `combineRegions()`.
    Arguments:
        faceShapes:  List of face shapes to merge
        includeProfile: Set True to include profile of selected face shapes
        includeHoles:  Set True to include existing holes in selected face shapes
        saveMergedHoles:  Set True to save holes created by merger of selected face shapes
    """
    # print("identifyRegions()")
    outerOpenWires = []
    innerFaces = None
    internalFaces = []

    # for fce in faceShapes:
    #    Part.show(fce, "FaceShape")
    #    print(f"len(fce.Faces): {len(fce.Faces)}")

    outerWiresRaw, innerWiresRaw = _separateFaceWires(faceShapes)
    if len(outerWiresRaw) == 0:
        print("No outerWires")
        return [], [], []

    # Flattend all outer wires in case some are 3D
    flatOuterWiresRaw, flatOuterOpenWiresRaw = _flattenWires(outerWiresRaw)
    # PathLog.info(f"len(flatOuterOpenWiresRaw)-A: {len(flatOuterOpenWiresRaw)}")
    outerOpenWires.extend(flatOuterOpenWiresRaw)

    if innerWiresRaw:
        # Flatten inner wires and remove duplicates of outer selections
        # print(f"Found inner {len(innerWiresRaw)} wires")
        flatInnerWiresRaw, flatInnerOpenWiresRaw = _flattenWires(innerWiresRaw)
        returnedOuterWires, rawInnerWires = _removeSelectedInternals(
            flatOuterWiresRaw, flatInnerWiresRaw
        )
        if includeHoles and rawInnerWires:
            # print("Saving rawInnerWires as faces")
            internalFaces.extend([Part.Face(w) for w in rawInnerWires])
        flatOuterWires = returnedOuterWires
    else:
        flatOuterWires = flatOuterWiresRaw

    ########################################################################################

    fusedFlatOuterWires = _fuseFlatWireAreas(flatOuterWires)
    if len(fusedFlatOuterWires) == 0:
        FreeCAD.Console.PrintError("identifyRegions() No fused flat outer wires\n")
        # Part.show(Part.makeCompound(flatOuterWires), "FlatOuterWires")
        return [], [], outerOpenWires

    ########################################################################################

    # Remove duplicate edges
    mergedFlatOuterWires_1 = _mergeAdjacentWires(fusedFlatOuterWires)

    ########################################################################################

    flattenedWires, inFaces1 = _consolidateAreas(
        mergedFlatOuterWires_1, saveHoles=saveMergedHoles
    )
    if inFaces1:
        # print(f"Found inner loop wire(s)")
        internalFaces.extend(inFaces1)

    ########################################################################################

    mergedWires_C = _fuseFlatWireAreas(flattenedWires)

    ########################################################################################

    # Remove duplicate edges from fused regions
    merged = _mergeAdjacentWires(mergedWires_C)

    ########################################################################################

    outFacesRaw, inFaces = _consolidateAreas(merged, saveHoles=saveMergedHoles)
    # outerFaces = Part.makeCompound(outFaces)
    outFaces = [_cleanFace(f) for f in outFacesRaw]
    # for f in outFaces:
    #    Part.show(f, "OutFaces_x_")
    # outerFaces = _cleanFace(fuseShapes(outFaces))
    outerFaces = fuseShapes(outFaces)
    # print(f"Found {len(inFaces)} inner loop wire(s)")
    internalFaces.extend(inFaces)

    if includeHoles and internalFaces:
        innerFaces = Part.makeCompound(internalFaces)
        # Part.show(innerFaces, "innerFaces")

    return outerFaces, innerFaces, outerOpenWires


def facesToRegions(
    faces,
    linearDeflection=1.0,
    angularDeflection=20.0,
    includeProfile=True,
    includeHoles=True,
    saveMergedHoles=True,
):
    if not faces:
        return [], []

    planar, nonplanar = _separateNonplanarFaces(faces)
    planar2 = [
        MeshTools.faceToRegion(f, linearDeflection, math.radians(angularDeflection))
        for f in nonplanar
    ]

    """
    if planar:
        Part.show(Part.makeCompound(planar), "Planar")
    if nonplanar:
        Part.show(Part.makeCompound(nonplanar), "Nonplanar")
    if planar2:
        Part.show(Part.makeCompound(planar2), "Planar2_")
    """

    face, outerOpenWires = combineRegions(
        planar + planar2,
        includeProfile,
        includeHoles,
        saveMergedHoles,
    )

    """
    if outerFaces:
        Part.show(Part.makeCompound(outerFaces), "OuterFaces2_")
    if innerFaces:
        Part.show(Part.makeCompound(innerFaces), "InnerFaces2_")
    """
    if outerOpenWires:
        # Part.show(Part.makeCompound(outerOpenWires), "OuterOpenWires")
        pass

    return face, outerOpenWires


def modelsToRegions(
    shapes, saveHoles=True, linearDeflection=2.0, angularDeflection=20.0
):
    """Objective is to create a cross-section of each shape, including interior holes."""
    # print("modelsToFaces() function is non-functional.")
    modelFaces = []
    # shapeCount = len(shapes)
    if len(shapes) == 0:
        return modelFaces

    if saveHoles:
        for shp in shapes:
            rgn = MeshTools.meshToFlatProjection(
                MeshTools.shapeToMesh(shp, linearDeflection, angularDeflection)
            )
            modelFaces.append(rgn.Faces[0].copy())
    else:
        for shp in shapes:
            rgn = MeshTools.meshToFlatProjection(
                MeshTools.shapeToMesh(shp, linearDeflection, angularDeflection)
            )
            fc = rgn.Faces[0]
            modelFaces.append(Part.Face(fc.Wires[0]))
    return modelFaces


##################################


def holePosition(baseShape, sub):
    """holePosition(baseShape, sub) ... returns a Vector for the position defined by the given features.
    Note that the value for Z is set to 0.
    Copied from"""
    x = None
    y = None
    r = None

    try:
        shape = baseShape.getElement(sub)
        if shape.ShapeType == "Vertex":
            x = shape.X
            y = shape.Y

        if shape.ShapeType == "Edge" and hasattr(shape.Curve, "Center"):
            x = shape.Curve.Center.x
            y = shape.Curve.Center.y

        if shape.ShapeType == "Face":
            if hasattr(shape.Surface, "Center"):
                x = shape.Surface.Center.x
                y = shape.Surface.Center.y
            if len(shape.Edges) == 1 and type(shape.Edges[0].Curve) == Part.Circle:
                x = shape.Edges[0].Curve.Center.x
                y = shape.Edges[0].Curve.Center.y

        r = holeDiameter(baseShape, sub)
        if r is not None:
            return FreeCAD.Vector(x, y, r)

    except Part.OCCError as e:
        PathLog.error(e)

    """PathLog.error(
        translate(
            "Path",
            "Feature %s.%s cannot be processed as a circular hole - please remove from Base geometry list.",
        )
        % (base.Label, sub)
    )"""
    return None


def holeDiameter(baseShape, sub):
    """holeDiameter(obj, base, sub) ... returns the diameter of the specified hole."""
    try:
        shape = baseShape.getElement(sub)
        if shape.ShapeType == "Vertex":
            return 0.0

        if shape.ShapeType == "Edge" and type(shape.Curve) == Part.Circle:
            return shape.Curve.Radius * 2.0

        if shape.ShapeType == "Face":
            for i in range(len(shape.Edges)):
                if (
                    type(shape.Edges[i].Curve) == Part.Circle
                    and shape.Edges[i].Curve.Radius * 2.0 < shape.BoundBox.XLength * 1.1
                    and shape.Edges[i].Curve.Radius * 2.0 > shape.BoundBox.XLength * 0.9
                ):
                    return shape.Edges[i].Curve.Radius * 2.0

        # for all other shapes the diameter is just the dimension in X.
        # This may be inaccurate as the BoundBox is calculated on the tessellated geometry
        PathLog.warning(
            translate(
                "Path",
                "Hole diameter may be inaccurate due to tessellation on face. Consider selecting hole edge.",
            )
        )
        return shape.BoundBox.XLength
    except Part.OCCError as e:
        PathLog.error(e)

    return None


def isHoleEnabled(obj, base, sub):
    """isHoleEnabled(obj, base, sub) ... return true if hole is enabled."""
    name = "%s.%s" % (base.Name, sub)
    return name not in obj.DisabledHoles


def getDrillableTargets(shape, ToolDiameter=None, vector=FreeCAD.Vector(0, 0, 1)):
    """
    Returns a list of tuples for drillable subelements from the given object
    [(obj,'Face1'),(obj,'Face3')]

    Finds cylindrical faces that are larger than the tool diameter (if provided) and
    oriented with the vector.  If vector is None, all drillables are returned

    """

    results = []
    for i in range(1, len(shape.Faces) + 1):
        fname = "Face{}".format(i)
        PathLog.debug(fname)
        candidate = shape.getElement(fname)

        if not isinstance(candidate.Surface, Part.Cylinder):
            continue

        try:
            drillable = Drillable.isDrillable(
                shape, candidate, tooldiameter=ToolDiameter, vector=vector
            )
            PathLog.debug("fname: {} : drillable {}".format(fname, drillable))
        except Exception as e:
            PathLog.debug(e)
            continue

        if drillable:
            results.append(fname)

    return results


def findAllHoles(job, toolDiam):
    """findAllHoles(obj) ... find all holes of all base models and assign as features."""
    PathLog.track()
    features = []
    matchvector = None if job.JobType == "Multiaxis" else FreeCAD.Vector(0, 0, 1)

    for base in job.Model.Group:
        for t in getDrillableTargets(
            base.Shape, ToolDiameter=toolDiam, vector=matchvector
        ):
            features.append((base, t))

    return features


####################################################################
####################################################################
####################################################################
####################################################################


def logText(txt, force=False):
    if DEBUG or force:
        print(txt)


def _edgeValueAtLength(edge, length):
    edgeLen = edge.Length
    # if PathGeom.isRoughly(edgeLen, 0.0):
    if edgeLen == 0.0:
        pnt = edge.Vertexes[0].Point
        return FreeCAD.Vector(pnt.x, pnt.y, pnt.z)

    if hasattr(edge, "Curve"):
        typeId = edge.Curve.TypeId
    elif hasattr(edge, "TypeId"):
        typeId = edge.TypeId

    if typeId == "Part::GeomBSplineCurve":
        return edge.valueAt(length / edgeLen)
    elif typeId == "Part::GeomCircle":
        return edge.valueAt(
            edge.FirstParameter
            + length / edgeLen * (edge.LastParameter - edge.FirstParameter)
        )
    elif typeId == "Part::GeomLine":
        return edge.valueAt(edge.FirstParameter + length)
    elif typeId == "Part::GeomEllipse":
        return edge.valueAt(
            edge.FirstParameter
            + length / edgeLen * (edge.LastParameter - edge.FirstParameter)
        )
    elif typeId == "Part::GeomParabola":
        return edge.valueAt(
            edge.FirstParameter
            + length / edgeLen * (edge.LastParameter - edge.FirstParameter)
        )
    elif typeId == "Part::GeomHyperbola":
        return edge.valueAt(
            edge.FirstParameter
            + length / edgeLen * (edge.LastParameter - edge.FirstParameter)
        )
    else:
        print(f"_edgeValueAtLength() edge.Curve.TypeId, {typeId}, is not available.")
        return None


def makeBoundBoxFace(bBox, offset=0.0, zHeight=0.0):
    """PathGeom.makeBoundBoxFace(bBox, offset=0.0, zHeight=0.0)...
    Function to create boundbox face, with possible extra offset and custom Z-height."""
    p1 = FreeCAD.Vector(bBox.XMin - offset, bBox.YMin - offset, zHeight)
    p2 = FreeCAD.Vector(bBox.XMax + offset, bBox.YMin - offset, zHeight)
    p3 = FreeCAD.Vector(bBox.XMax + offset, bBox.YMax + offset, zHeight)
    p4 = FreeCAD.Vector(bBox.XMin - offset, bBox.YMax + offset, zHeight)

    L1 = Part.makeLine(p1, p2)
    L2 = Part.makeLine(p2, p3)
    L3 = Part.makeLine(p3, p4)
    L4 = Part.makeLine(p4, p1)

    return Part.Face(Part.Wire([L1, L2, L3, L4]))


def makeProjection(shape):
    bfbb = shape.BoundBox
    targetFace = makeBoundBoxFace(bfbb, offset=5.0, zHeight=math.floor(bfbb.ZMin - 5.0))

    direction = FreeCAD.Vector(0.0, 0.0, -1.0)
    #      receiver_face.makeParallelProjection(project_shape, direction)
    proj = targetFace.makeParallelProjection(shape.Wires[0], direction)
    proj.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - proj.BoundBox.ZMin))
    return proj


def flattenEdges(edges):
    flatEdges = []
    comp = Part.makeCompound(edges)
    bfbb = comp.BoundBox
    targetFace = PathGeom.makeBoundBoxFace(
        bfbb, offset=5.0, zHeight=math.floor(bfbb.ZMin - 5.0)
    )

    direction = FreeCAD.Vector(0.0, 0.0, -1.0)
    #      receiver_face.makeParallelProjection(project_shape, direction)
    for e in edges:
        proj = targetFace.makeParallelProjection(e, direction)
        proj.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - proj.BoundBox.ZMin))
        flatEdges.extend(proj.Edges)

    return flatEdges


# Filtering functions
def fuseShapes(shapes, tolerance=0.00001):
    if len(shapes) == 0:
        return None
    if len(shapes) == 1:
        return shapes[0].copy()
    f = shapes[0].copy()
    for fc in shapes[1:]:
        fused = f.generalFuse(fc, tolerance)
        f = fused[0]
    return f


def makeEdgeMidpointTups(edges, precision=5):
    tups = []
    for ei in range(0, len(edges)):
        e = edges[ei].copy()
        # eLen = e.Length / 2.0
        txt = f"L{round(e.Length, precision)}_" + Edge._pointToText(
            _edgeValueAtLength(e, e.Length / 2.0)
        )
        tups.append((txt, ei, e))
    # Sort tups by xyz_length text, so same edges find each other
    tups.sort(key=lambda t: t[0])
    return tups


def isolateUniqueEdges(edges, filterDisconnected=False):
    # Filter out duplicate edges
    # logText("isolateUniqueEdges()")

    if filterDisconnected:
        clean, __ = filterUnconnectedEdges(edges)
        tups = makeEdgeMidpointTups(clean)
    else:
        tups = makeEdgeMidpointTups(edges)
    if len(tups) == 0:
        return tups

    # Remove duplicates
    unique = [tups[0]]
    deleted = []
    multi = False
    for t in tups[1:]:
        if t[0] == unique[-1][0]:
            deleted.append(t)
            multi = True
        else:
            if multi == True:
                unique.pop()
                multi = False
            unique.append(t)
    if multi == True:
        unique.pop()

    return [u[2] for u in unique]


# Path generation functions
def makeEdgeRefTups(edges, touchesZ=None):
    tups = []
    if touchesZ is None:
        # Use all vertexes
        for ei in range(0, len(edges)):
            e = edges[ei]
            for vi in range(0, len(e.Vertexes)):
                v = e.Vertexes[vi]
                txt = Edge._pointToText(v.Point)
                tups.append((txt, ei, vi, e.BoundBox.ZMax))
    else:
        # Use all vertexes
        for ei in range(0, len(edges)):
            e = edges[ei]
            for vi in range(0, len(e.Vertexes)):
                v = e.Vertexes[vi]
                if PathGeom.isRoughly(v.Z, touchesZ):
                    txt = Edge._pointToText(v.Point)
                    # tups.append((txt, ei, vi, e.BoundBox.ZMax))
                    tups.append(
                        (txt, ei, vi, touchesZ)
                    )  # EDIT, added touchesZ parameter to end of tuple

    # Sort tups by xyz text, so same vertexes find each other
    tups.sort(key=lambda t: t[0])
    return tups


def filterUnconnectedEdges(edges):
    # Make reference tups
    tups = []
    for ei in range(0, len(edges)):
        e = edges[ei]
        for vi in range(0, len(e.Vertexes)):
            v = e.Vertexes[vi]
            txt = Edge._pointToText(v.Point)
            tups.append((txt, ei, vi))

    # Sort tups by xyz text, so same vertexes find each other
    tups.sort(key=lambda t: t[0])

    # Identify edges with unconnected vertexes
    keep = []
    other = []
    k = 0
    unique = True
    for t in tups:
        if len(keep) == 0:
            keep.append(t)
            k += 1
        elif keep[-1][0] == t[0]:
            keep.append(t)
            k += 1
            unique = False  # last 2 keep will be same
        else:
            if unique:
                other.append(keep.pop())
                k -= 1
            keep.append(t)
            k += 1
            unique = True
    # Efor

    # identify dirty edge indexes
    idxs = [t[1] for t in other]
    idxs.sort()

    # sort edges into clean and dirty
    clean = []
    dirty = []
    for ei in range(0, len(edges)):
        if ei in idxs:
            dirty.append(edges[ei])
        else:
            clean.append(edges[ei])

    return clean, dirty


def findClosedWireRegions(edgeList):
    edgeGroups = Part.sortEdges(edgeList)
    wires = []
    for g in edgeGroups:
        w = Part.Wire(g)
        if w.isClosed():
            wires.append(w)
            # Part.show(w, "ClosedWire")
        else:
            Part.show(w, "FCWR_OpenWire")
    return wires


def combineAllEdges(faces):
    edgeList = []
    for f in faces:
        for e in f.Edges:
            edgeList.append(e.copy())

    unique = isolateUniqueEdges(edgeList)
    return findClosedWireRegions(unique)


def combineOuterEdges(faces):
    edgeList = []
    for f in faces:
        for e in _getOrderedFaceWires(f)[0].Edges:
            edgeList.append(e.copy())

    unique = isolateUniqueEdges(edgeList)
    # print(f"unique edges: {len(unique)}")
    return findClosedWireRegions(unique)


def combineInnerEdges(faces):
    edgeList = []
    for f in faces:
        if len(f.Wires) > 1:
            for w in _getOrderedFaceWires(f)[1:]:
                for e in w.Edges:
                    edgeList.append(e.copy())

    unique = isolateUniqueEdges(edgeList)
    return findClosedWireRegions(unique)


def closedWiresToHorizontalFaces(wires):
    fcs = []
    open = []
    for cw in wires:
        try:
            f = Part.Face(cw)
        except:
            w = Part.Wire(makeProjection(cw).Edges)
            if w.isClosed():
                f = Part.Face(w)
                fcs.append(f)
            else:
                open.append(w)
        else:
            # ensure face is horizontal
            if PathGeom.isRoughly(f.BoundBox.ZLength, 0.0):
                fcs.append(f)
            else:
                if (
                    len(cw.Edges) == 1
                    and cw.Edges[0].Curve.TypeId == "Part::GeomCircle"
                ):
                    w = Part.Wire([Edge.horizontalCenterChordLine(cw.Edges[0])])
                else:
                    w = Part.Wire(makeProjection(cw).Edges)
                if w.isClosed():
                    f = Part.Face(w)
                    fcs.append(f)
                else:
                    open.append(w)

    for f in fcs:
        f.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - f.BoundBox.ZMin))
    for w in open:
        w.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - w.BoundBox.ZMin))

    return fcs, open


def _removeCommonWires(outerWires, innerWires):
    inner = []
    outer = []
    remove = []
    for inr in innerWires:
        same = False
        vc = inr.BoundBox.Center
        i = -1
        for otr in outerWires:
            i += 1
            fcp = otr.BoundBox.Center
            fc = FreeCAD.Vector(fcp.x, fcp.y, vc.z)
            if not PathGeom.isRoughly(vc.sub(fc).Length, 0.0):
                continue
            if not PathGeom.isRoughly(inr.Length, otr.Length):
                continue
            remove.append(i)
            same = True
            break

        if not same:
            inner.append(inr)

    i = 0
    for w in outerWires:
        if i not in remove:
            outer.append(w)
        i += 1

    return outer, inner


def identifiedMergedHoles(faces):
    """identifiedMergedHoles(faces)()
    Identify independent outer faces and artificial inner holes created by connected outer faces.
    Example: Two halves of donut touch, creating a hole in middle, and artificial inner hole.
    """
    fCnt = len(faces)
    if fCnt == 0:
        return [], []
    if fCnt == 1:
        return [faces[0]], []

    # Sort faces by area, largest to smallest
    faces.sort(key=lambda f: f.Area, reverse=True)
    # print(f"len(faces): {len(faces)}")

    outer = [faces.pop(0)]
    inner = []
    outCnt = 0
    for i in range(0, len(faces)):
        f = faces[i]
        area = f.Area
        outs = []
        for o in range(0, len(outer) - outCnt):
            out = outer[o]
            if PathGeom.isRoughly(out.common(f).Area, area):
                # smaller face entirely in outer face
                inner.append(f)
            else:
                outs.append(f)
                outCnt += 1
        outer.extend(outs)

    return outer, inner


def _getOrderedFaceWires(face):
    """_getOrderedFaceWires(face)
    returns ordered list of face.Wires, with outer in [0] index, and inner as [1]+ index by boundbox diagonal length
    Part.Wire() objects sometimes have the outer wire in non-zero index location within face.Wires list.
    """
    wires = [w.copy() for w in face.Wires]
    wires.sort(key=lambda w: w.BoundBox.DiagonalLength, reverse=True)
    return wires


def combineFacesIntoRegions(faceList):
    """combineFacesIntoRegions(faceList)"""
    # print("combineFacesIntoRegions(faceList)")
    if len(faceList) == 1:
        # outerFaces, mergedHoles, innerFaces, openWires
        wrs = _getOrderedFaceWires(faceList[0])
        outer = [Part.Face(wrs[0])]
        inner = [Part.Face(w) for w in wrs[1:]]
        return (outer, [], inner, [])

    # Identify and separate outer and inner edges, removing shared edges
    outerWires1 = combineOuterEdges(faceList)
    innerWires1 = combineInnerEdges(faceList)
    outerWires, innerWires = _removeCommonWires(outerWires1, innerWires1)
    # print(
    #    f"faceList: {len(faceList)},  outerWires1: {len(outerWires1)},  innerWires1: {len(innerWires1)}"
    # )
    """
    Part.show(Part.makeCompound(outerWires), "OuterWires")
    if innerWires:
        Part.show(Part.makeCompound(innerWires), "InnerWires")
    """

    # Convert closed outer and inner wires to faces at Z=0.0
    rawOuterFaces, outerOpen = closedWiresToHorizontalFaces(outerWires)
    innerFaces, innerOpen = closedWiresToHorizontalFaces(innerWires)

    """
    Part.show(Part.makeCompound(rawOuterFaces), "RawOuterFaces")
    if outerOpen:
        Part.show(Part.makeCompound(outerOpen), "OuterOpen")
    Part.show(Part.makeCompound(innerFaces), "RawInnerFaces")
    if innerOpen:
        Part.show(Part.makeCompound(innerOpen), "InnerOpen")
    """

    # Extract holes created from merging adjacent faces
    outerFaces, mergedHoles = identifiedMergedHoles(rawOuterFaces)

    """
    Part.show(Part.makeCompound(outerFaces), "OuterFaces")
    if mergedHoles:
        Part.show(Part.makeCompound(mergedHoles), "MergedVoids")
    """

    # Combine all open edges/wires
    openWires = []
    openWires.extend(outerOpen)
    openWires.extend(innerOpen)
    # if openWires:
    #    Part.show(Part.makeCompound(openWires), "OpenWires")

    return outerFaces, mergedHoles, innerFaces, openWires


def combineRegions(
    faces, zHeight=0.0, keepProfile=True, keepHoles=True, keepMergedHoles=True
):
    """combineRegions(faces, zHeight=0.0, keepProfile=True, keepHoles=True, keepMergedHoles=True)
    Arguments:
        faces = list of faces at ZMin=0.0
    """
    # print(
    #    f"faces {len(faces)}, kP {keepProfile}, kH {keepHoles}, kMH {keepMergedHoles}"
    # )

    allFaces = fuseShapes(faces)
    # print(
    #    f"combineRegions()\n... faces: {len(faces)}, allFaces.Faces: {len(allFaces.Faces)}"
    # )

    outerFaces, mergedHoles, holeFaces, openWires = combineFacesIntoRegions(
        allFaces.Faces
    )
    # print(
    #    f"combineRegions()\n... outerFaces: {len(outerFaces)}, mergedHoles: {len(mergedHoles)}, holeFaces: {len(holeFaces)}, openWires: {len(openWires)}"
    # )

    if False:
        if outerFaces:
            Part.show(Part.makeCompound(outerFaces), "OuterFaces")
        if holeFaces:
            Part.show(Part.makeCompound(holeFaces), "HoleFaces")
        if mergedHoles:
            Part.show(Part.makeCompound(mergedHoles), "MergedHoles")
        if openWires:
            Part.show(Part.makeCompound(openWires), "OpenWires")

    if openWires:
        # Part.show(Part.makeCompound(openWires), "OpenWires")
        for ow in openWires:
            ow.translate(FreeCAD.Vector(0.0, 0.0, zHeight))

    shape = None
    if keepProfile:
        shape = fuseShapes(outerFaces)
        # if shape:
        #    Part.show(shape, "KeepProfile_Shape")
        if keepMergedHoles and mergedHoles:
            merged = fuseShapes(mergedHoles)
            m = shape.cut(merged)
            shape = m
        if keepHoles and holeFaces:
            holes = fuseShapes(holeFaces)
            h = shape.cut(holes)
            shape = h

    else:
        if keepMergedHoles and mergedHoles:
            shape = fuseShapes(mergedHoles)
        if keepHoles and holeFaces:
            holes = fuseShapes(holeFaces)
            if shape:
                h = shape.fuse(holes)
                shape = h
            else:
                shape = holes

    if shape:
        shape.translate(FreeCAD.Vector(0.0, 0.0, zHeight - shape.BoundBox.ZMin))
        # Part.show(shape, "CombineRegion")
        return shape, openWires

    # print("Region.combineRegions() returning None")
    return None, openWires


def edgesToFaces(edges):
    faces = []
    openWires = []
    if len(edges) == 0:
        return faces, openWires
    projEdges = flattenEdges(edges)  # makeProjection(fuseShapes(edges))
    groups = Part.sortEdges(projEdges)
    for g in groups:
        w = Part.Wire(g)
        if w.isClosed():
            faces.append(Part.Face(w))
            # fc = Part.Face(w)
            # fc.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - fc.BoundBox.ZMin))
            # faces.append(fc)
        else:
            # comp = Part.makeCompound(edges)
            w.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - w.BoundBox.ZMin))
            Part.show(w, "Open_Wire")
            print("Some or all selected edges are not closed.")
            openWires.append(w)
    # Part.show(Part.makeCompound(faces), "Comp_Edges")
    return faces, openWires


def edgesToFaces2(edges):
    faces = []
    openWires = []
    if len(edges) == 0:
        return faces, openWires
    groups = Part.sortEdges(edges)
    for g in groups:
        w = Part.Wire(g)
        if w.isClosed():
            try:
                fc = Part.Face(w)
            except:
                projEdges = flattenEdges(w.Edges)  # makeProjection(fuseShapes(edges))
                fc = Part.Face(Part.Wire(projEdges))
                fc.translate(
                    FreeCAD.Vector(0.0, 0.0, w.BoundBox.ZMax - fc.BoundBox.ZMin)
                )
            faces.append(fc)
        else:
            # comp = Part.makeCompound(edges)
            w.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - w.BoundBox.ZMin))
            Part.show(w, "Open_Wire")
            print("Some or all selected edges are not closed.")
            openWires.append(w)
    # Part.show(Part.makeCompound(faces), "Comp_Edges")
    return faces, openWires


# Selection processing functions for macro
def getFeatureNames(base, subs):
    # Identify input
    edgeNames = []
    faceNames = []
    if len(subs) > 0:
        for s in subs:
            if s.startswith("Face"):
                faceNames.append(s)
            elif s.startswith("Edge"):
                edgeNames.append(s)
            else:
                FreeCAD.Console.PrintError(f"{base.Name}:{s} is unusable.\n")
    else:
        faceNames = [f"Face{i+1}" for i in range(len(base.Shape.Faces))]

    return edgeNames, faceNames


def getSelectedEdgesAndFaces():
    # Get GUI face selection
    # base = FreeCADGui.Selection.getSelection()[0]
    # baseName = base.Name
    sel = FreeCADGui.Selection.getSelectionEx()
    base = sel[0].Object
    # baseName = base.Name
    subs = sel[0].SubElementNames
    # logText("Base Name: {}".format(baseName))
    # logText("len(subs): {}".format(len(subs)))
    # logText("subs: {}".format(subs))

    edgeNames, faceNames = getFeatureNames(base, subs)
    # print(f"{edgeNames}")
    # print(f"{faceNames}")

    return [base.Shape.getElement(n).copy() for n in edgeNames], [
        base.Shape.getElement(n).copy() for n in faceNames
    ]


####################################################################
####################################################################
####################################################################
####################################################################

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
