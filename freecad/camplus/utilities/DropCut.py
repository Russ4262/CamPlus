# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2021 Russell Johnson (russ4262) <russ4262@gmail.com>    *
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
import PathScripts.PathUtils as PathUtils
import Path.Log as PathLog
import freecad.camplus.utilities.Edge as EdgeUtils

__title__ = "Drop Cut Generator"
__author__ = "russ4262 (Russell Johnson)"
__url__ = "https://github.com/Russ4262/PathRed"
__doc__ = (
    "Produces wires representative of a toolbit following a projected path on a face."
)

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


isDebug = True if PathLog.getLevel(PathLog.thisModule()) == 4 else False
showDebugShapes = False


LINEARDEFLECTION = FreeCAD.Units.Quantity("0.0001 mm")
MAX_DROPS = 25
moveCnt = 0


def _toolShapeCenter(toolShape):
    tBB = toolShape.BoundBox
    return FreeCAD.Vector(
        round(tBB.Center.x, 7), round(tBB.Center.y, 7), round(tBB.ZMin, 7)
    )


def _bsplineValue(__, sampleInterval, cnt, edgeLen):
    # print(".. _bsplineValue")
    return (sampleInterval * cnt) / edgeLen


def _arcValue(e, sampleInterval, cnt, edgeLen):
    # print(".. _arcValue")
    rate = (sampleInterval * cnt) / edgeLen
    return e.FirstParameter + rate * (e.LastParameter - e.FirstParameter)


def _ellipseValue(e, sampleInterval, cnt, edgeLen):
    # print(".. _ellipseValue")
    rate = (sampleInterval * cnt) / edgeLen
    return e.FirstParameter + rate * (e.LastParameter - e.FirstParameter)


def _lineValue(e, sampleInterval, cnt, __):
    # print(".. _lineValue")
    return e.FirstParameter + (sampleInterval * cnt)


def _parabolaValue(e, sampleInterval, cnt, edgeLen):
    # This method is experimental, a copy of the _ellipseValue() method
    # print(".. _parabolaValue")
    rate = (sampleInterval * cnt) / edgeLen
    return e.FirstParameter + rate * (e.LastParameter - e.FirstParameter)


def _getValueAtArgumentFunction(typeId):
    if typeId == "Part::GeomBSplineCurve":
        return _bsplineValue
    elif typeId == "Part::GeomCircle":
        return _arcValue
    elif typeId == "Part::GeomLine":
        return _lineValue
    elif typeId == "Part::GeomEllipse":
        return _ellipseValue
    elif typeId == "Part::GeomParabola":
        return _parabolaValue

    print(f"_followEdge() e.Curve.TypeId, {typeId}, is not available.")
    return None


def _dropShapeToFace_orig(
    toolShape, face, location, destination, startDepth, dropTolerance
):
    drops = 0
    deltaX = destination.x - location.x
    deltaY = destination.y - location.y
    deltaZ = startDepth - location.z
    trans = FreeCAD.Vector(deltaX, deltaY, deltaZ)
    toolShape.translate(trans)
    dist = toolShape.distToShape(face)[0]
    while dist > dropTolerance:
        drops += 1
        trans = FreeCAD.Vector(0.0, 0.0, dist * -0.8)
        toolShape.translate(trans)
        dist = toolShape.distToShape(face)[0]
        if drops > MAX_DROPS:
            print(
                f"_dropShapeToFace() Breaking at {MAX_DROPS} at distance of {dist} mm"
            )
            # print(f"_dropShapeToFace() dtf {dtf}")
            break
    return toolShape, _toolShapeCenter(toolShape), drops


def _dropShapeToFace(toolShape, face, location, destination, startDepth, dropTolerance):
    drops = 0
    # trans = FreeCAD.Vector(destination.x - location.x, destination.y - location.y, startDepth - location.z)
    # toolShape.translate(trans)
    toolShape.translate(
        FreeCAD.Vector(
            destination.x - location.x,
            destination.y - location.y,
            startDepth - location.z,
        )
    )
    dist = toolShape.distToShape(face)[0]
    while dist > dropTolerance:
        drops += 1
        trans = FreeCAD.Vector(0.0, 0.0, dist * -0.8)
        toolShape.translate(trans)
        dist = toolShape.distToShape(face)[0]
        if drops > MAX_DROPS:
            print(
                f"_dropShapeToFace() Breaking at {MAX_DROPS} at distance of {dist} mm"
            )
            # print(f"_dropShapeToFace() dtf {dtf}")
            break
    return toolShape, _toolShapeCenter(toolShape), drops


def _followEdge(
    e, toolShape, face, startDepth, sampleInterval, dropTolerance, lastEdge
):
    global moveCnt

    points = []
    tool = toolShape
    eLen = e.Length
    edgeLen = e.Length
    dropCnt = 0
    moveCnt += 1
    loopCnt = 0

    typeId = e.Curve.TypeId
    valueAtArgument = _getValueAtArgumentFunction(typeId)

    location = _toolShapeCenter(tool)
    # follow edge
    while eLen > sampleInterval:
        moveCnt += 1
        # move to next point along edge
        valueAtParam = valueAtArgument(e, sampleInterval, loopCnt, edgeLen)
        dest = e.valueAt(valueAtParam)
        tool, center, drpCnt = _dropShapeToFace(
            tool, face, location, dest, startDepth, dropTolerance
        )
        dropCnt += drpCnt
        if center.z < dest.z:
            # print("Vertically adjusting tool")
            center.z = dest.z
        points.append(center)
        location = center
        eLen -= sampleInterval
        loopCnt += 1

    if loopCnt == 0 or lastEdge:
        # experimental section for edges of length less than sampleInterval
        dest = e.valueAt(e.LastParameter)
        tool, center, drpCnt = _dropShapeToFace(
            tool, face, location, dest, startDepth, dropTolerance
        )
        dropCnt += drpCnt
        if center.z < dest.z:
            # print("Vertically adjusting tool")
            center.z = dest.z
        points.append(FreeCAD.Vector(center.x, center.y, center.z))

    return points, dropCnt


def _dropCutEdges(
    edges, toolShape, faceShape, startDepth, sampleInterval, dropTolerance
):
    wirePoints = []
    dropCnt = 0
    distance = 0.0
    for e in edges[:-1]:
        if distance + e.Length > sampleInterval:
            distance = 0.0
            points, drpCnt = _followEdge(
                e,
                toolShape,
                faceShape,
                startDepth,
                sampleInterval,
                dropTolerance,
                False,
            )
            wirePoints.extend(points)
            dropCnt += drpCnt
        else:
            distance += e.Length

    # Process last edge
    e = edges[-1]
    points, drpCnt = _followEdge(
        e, toolShape, faceShape, startDepth, sampleInterval, dropTolerance, True
    )
    wirePoints.extend(points)
    dropCnt += drpCnt

    return wirePoints, dropCnt


def _isSameStartEnd(w, wire):
    v1 = w.Edges[0].Vertexes[0].Point
    v2 = w.Edges[-1].Vertexes[-1].Point
    v1p = FreeCAD.Vector(v1.x, v1.y, 0.0)
    v2p = FreeCAD.Vector(v2.x, v2.y, 0.0)

    p1 = wire.Edges[0].Vertexes[0].Point
    p2 = wire.Edges[-1].Vertexes[-1].Point
    p1p = FreeCAD.Vector(p1.x, p1.y, 0.0)
    p2p = FreeCAD.Vector(p2.x, p2.y, 0.0)

    if PathGeom.isRoughly(p1p.sub(v1p).Length, 0.0) and PathGeom.isRoughly(
        p2p.sub(v2p).Length, 0.0
    ):
        return True
    return False


def getToolShape(toolController):
    """getToolShape(toolController) Return tool shape with shank removed."""
    full = toolController.Tool.Shape.copy()
    vertEdges = [
        e
        for e in full.Edges
        if len(e.Vertexes) == 2
        and PathGeom.isRoughly(e.Vertexes[0].X, e.Vertexes[1].X)
        and PathGeom.isRoughly(e.Vertexes[0].Y, e.Vertexes[1].Y)
    ]
    vertEdges.sort(key=lambda e: e.BoundBox.ZMax)
    topVertEdge = vertEdges.pop()
    top = full.BoundBox.ZMax + 2.0
    face = PathGeom.makeBoundBoxFace(full.BoundBox, 5.0, top)
    dist = -1.0 * (top - topVertEdge.BoundBox.ZMin)
    faceExt = face.extrude(FreeCAD.Vector(0.0, 0.0, dist))
    # Part.show(full, "Full")
    # Part.show(faceExt, "FaceExt")
    return full.cut(faceExt)


###################################################
def _dropCutAtPoints(
    dropPoints,
    toolShape,
    faceShape,
    startDepth,
    dropTolerance,
):
    points = []
    tool = toolShape
    dropCnt = 0
    location = _toolShapeCenter(tool)
    for dest in dropPoints:
        tool, center, drops = _dropShapeToFace(
            tool, faceShape, location, dest, startDepth, dropTolerance
        )
        if center.z < dest.z:
            # print("Vertically adjusting tool")
            center.z = dest.z
        dropCnt += drops
        location = center
        points.append(center)

    return points, dropCnt


def _dropCutWire(
    horizWire,
    faceShape,
    toolShape,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    # print(
    #    f"_dropCutWire() dropTolerance: {dropTolerance};  MAX_DROPS: {MAX_DROPS};  optimizeLines: {optimizeLines}"
    # )
    pointsLists = []
    dropCnt = 0
    startDepth = faceShape.BoundBox.ZMax + 1.0
    wCnt = 0

    # Part.show(faceShape, "GDC_FaceShape")

    wCnt += 1
    # Must create new toolShape object for each wire, otherwise FreeCAD crash will occur
    toolShp = toolShape.copy()
    if horizWire.Length >= sampleInterval:
        dropPoints = horizWire.discretize(Distance=sampleInterval)
    else:
        # Make sure wires less than sample interval are cut
        dropPoints = [
            horizWire.Edges[0].Vertexes[0].Point,
            horizWire.Edges[-1].Vertexes[-1].Point,
        ]

    (wirePoints, drops) = _dropCutAtPoints(
        dropPoints,
        toolShp,
        faceShape,
        startDepth,
        dropTolerance,
    )
    dropCnt += drops
    # Optimize points list
    if len(wirePoints) > 0:
        if optimizeLines:
            pointsLists.append(
                PathUtils.simplify3dLine(wirePoints, LINEARDEFLECTION.Value)
            )
        else:
            pointsLists.append(wirePoints)
    else:
        print(f"no drop cut wire points from wire {wCnt}")

    # Part.show(toolShape, "ToolShape")
    # print(f"Total dropcut count: {dropCnt}")

    return pointsLists


def _dropCutWires_orig(
    pathWires,
    faceShape,
    toolShape,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    print(
        f"_dropCutWires_orig() sampleInterval: {sampleInterval};  dropTolerance: {dropTolerance};  MAX_DROPS: {MAX_DROPS};  optimizeLines: {optimizeLines}"
    )
    pointsLists = []
    dropCnt = 0
    startDepth = faceShape.BoundBox.ZMax + 1.0
    wCnt = 0

    # Part.show(faceShape, "GDC_FaceShape")

    for w in pathWires:
        wCnt += 1
        # Must create new toolShape object for each wire, otherwise FreeCAD crash will occur
        toolShp = toolShape.copy()
        if w.Length >= sampleInterval:
            # print("w.Length >= sampleInterval")
            dropPoints = w.discretize(Distance=sampleInterval)
        else:
            # Make sure wires less than sample interval are cut
            dropPoints = [w.Edges[0].Vertexes[0].Point, w.Edges[-1].Vertexes[-1].Point]

        print(f"Breaking at wire {wCnt}")
        break

        (wirePoints, drops) = _dropCutAtPoints(
            dropPoints,
            toolShp,
            faceShape,
            startDepth,
            dropTolerance,
        )
        dropCnt += drops
        # Optimize points list
        if len(wirePoints) > 0:
            if optimizeLines:
                pointsLists.append(
                    PathUtils.simplify3dLine(wirePoints, LINEARDEFLECTION.Value)
                )
            else:
                pointsLists.append(wirePoints)
        else:
            print(f"no drop cut wire points from wire {wCnt}")

    # Part.show(toolShape, "ToolShape")
    # print(f"Total dropcut count: {dropCnt}")

    return pointsLists


def _dropCutWires(
    pathWires,
    faceShape,
    toolShape,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    # print(
    #    f"_dropCutWires() sampleInterval: {sampleInterval};  dropTolerance: {dropTolerance};  MAX_DROPS: {MAX_DROPS};  optimizeLines: {optimizeLines}"
    # )
    pointsLists = []
    dropCnt = 0
    startDepth = faceShape.BoundBox.ZMax + 1.0
    wCnt = 0

    # Part.show(faceShape, "GDC_FaceShape")

    dropPointsLists = []
    for w in pathWires:
        if w.Length >= sampleInterval:
            # print("w.Length >= sampleInterval")
            # pnts = w.discretize(Distance=sampleInterval)
            dropPointsLists.append(w.discretize(Distance=sampleInterval))
        else:
            # Make sure wires less than sample interval are cut
            dropPointsLists.append(
                [w.Edges[0].Vertexes[0].Point, w.Edges[-1].Vertexes[-1].Point]
            )
        # print("Breaking after first dropPoints list")
        # break

    for dp in dropPointsLists:
        wCnt += 1
        # Must create new toolShape object for each wire, otherwise FreeCAD crash will occur
        toolShp = toolShape.copy()

        (wirePoints, drops) = _dropCutAtPoints(
            dp,
            toolShp,
            faceShape,
            startDepth,
            dropTolerance,
        )
        dropCnt += drops

        # Optimize points list
        if len(wirePoints) > 0:
            if optimizeLines:
                pointsLists.append(
                    PathUtils.simplify3dLine(wirePoints, LINEARDEFLECTION.Value)
                )
            else:
                pointsLists.append(wirePoints)
        else:
            print(f"no drop cut wire points from wire {wCnt}")

    # Part.show(toolShape, "ToolShape")
    # print(f"Total dropcut count: {dropCnt}")

    return pointsLists


###################################################
# Public functions
def getProjectedGeometry(face, pathGeomList):
    """getProjectedGeometry(face, pathGeomList) Return list of wires resulting from projection onto face"""
    # Project 2D wires onto 3D face(s)
    faceCopy = face.copy()
    # print(f"   paths: {paths}")
    compPathGeom = Part.makeCompound(pathGeomList)
    # Part.show(compPathGeom, "PathGeom")  #  path projected to original face
    faceCopy.translate(
        FreeCAD.Vector(
            0.0, 0.0, (compPathGeom.BoundBox.ZMin - 10.0) - faceCopy.BoundBox.ZMin
        )
    )
    transDiff = face.BoundBox.ZMin - faceCopy.BoundBox.ZMin
    projWires = []
    for w in pathGeomList:
        p = faceCopy.makeParallelProjection(w, FreeCAD.Vector(0.0, 0.0, -1.0))
        p.translate(FreeCAD.Vector(0.0, 0.0, transDiff))
        wire = Part.Wire(Part.__sortEdges__(p.Edges))  # sort edges properly
        projWires.append(wire)

    return projWires


def getProjectedGeometry2(face, pathGeomList):
    """getProjectedGeometry2(face, pathGeomList)
    Return list of wires resulting from projection onto face"""
    # Project 2D wires onto 3D face(s)
    projWires = []
    zMin = face.BoundBox.ZMin
    canvas = face.copy()
    compPathGeom = Part.makeCompound(pathGeomList)
    canvas.translate(
        FreeCAD.Vector(
            0.0,
            0.0,
            round((compPathGeom.BoundBox.ZMin - 100.0), 0) - face.BoundBox.ZMin,
        )
    )
    if isDebug:
        Part.show(compPathGeom, "PathGeom")  #  path projected to original face
        Part.show(canvas, "Dropcut_FaceCopy")
    transDiff = zMin - canvas.BoundBox.ZMin

    for w in pathGeomList:
        # Part.show(w, "Dropcut_OrigWire")
        p = canvas.makeParallelProjection(w, FreeCAD.Vector(0.0, 0.0, -1.0))
        if len(p.Edges) == 0:
            wire = w.copy()
            # Part.show(w, "Dropcut_UseOrigWire")
        else:
            p.translate(FreeCAD.Vector(0.0, 0.0, transDiff))
            edges = Part.__sortEdges__(p.Edges)  # sort edges properly
            wire = Part.Wire(edges)
            if isDebug:
                Part.show(wire, "ProjWire")

        if _isSameStartEnd(w, wire):
            projWires.append(wire)
        else:
            flipped = EdgeUtils.flipWire(wire)
            projWires.append(flipped)

    return projWires


'''
def getProjectedWire(face, inWire):
    """getProjectedWire(face, inWire) Return wire resulting from projection of inWire onto face"""
    # Part.show(inWire, "PathGeom")  #  path projected to original face
    # Save ZMin value of face
    zMinFace = face.BoundBox.ZMin
    # Move face below inWire
    face.translate(
        FreeCAD.Vector(0.0, 0.0, (inWire.BoundBox.ZMin - 10.0) - face.BoundBox.ZMin)
    )
    # Save difference
    transDiff = zMinFace - face.BoundBox.ZMin
    # Project wire
    p = face.makeParallelProjection(inWire, FreeCAD.Vector(0.0, 0.0, -1.0))
    p.translate(FreeCAD.Vector(0.0, 0.0, transDiff))

    # Restore vertical face position
    face.translate(FreeCAD.Vector(0.0, 0.0, zMinFace - face.BoundBox.ZMin))

    return Part.Wire(Part.__sortEdges__(p.Edges))  # sort edges properly

'''


"""
def dropCutWire(
    wire,
    face,
    toolShape,
    depthOffset,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    projWire = getProjectedWire(face, wire)
    # Apply drop cut to 3D projected wires to get point set
    pointsLists = _dropCutWire(
        projWire,
        face,
        toolShape,
        sampleInterval,
        dropTolerance,
        optimizeLines,
    )

    # return pointsToLines(pointsLists, depthOffset)
    lineSegs = pointsToLines(pointsLists, depthOffset)
    return Part.Wire(lineSegs)


def dropCutWires_orig(
    wires,
    fusedFace,
    toolShape,
    depthOffset,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    projWires = getProjectedGeometry(fusedFace, wires)
    # Apply drop cut to 3D projected wires to get point set
    pointsLists = _dropCutWires(
        projWires,
        fusedFace,
        toolShape,
        sampleInterval,
        dropTolerance,
        optimizeLines,
    )

    # return pointsToLines(pointsLists, depthOffset)
    lineSegs = pointsToLines(pointsLists, depthOffset)
    return Part.Wire(lineSegs)

"""


def pointsToLines(pointsLists, high, low, depthOffset=0.0):
    print(f"pointsToLines(pointsLists, {high}, {low}, {depthOffset})")
    wires = []

    def pntsToLine(pnts):
        lines = []
        p0 = pnts[0]
        for p1 in pnts[1:]:
            if p0.z <= high:
                if p1.z <= high:
                    # raise z value if below 'low' value
                    if p0.z <= low:
                        p0 = FreeCAD.Vector(p0.x, p0.y, low)
                    # raise z value if below 'low' value
                    if p1.z < low:
                        p1 = FreeCAD.Vector(p1.x, p1.y, low)
                    if p0.sub(p1).Length > 0.00001:
                        lines.append(Part.makeLine(p0, p1))
                else:
                    # segment starts below high, and ends above high
                    print("IF ELSE INCOMPLETE DropCut.pointsToLines()")
                    print("IF ELSE INCOMPLETE")
                    pass
            elif p1.z <= high:
                print("ELIF INCOMPLETE DropCut.pointsToLines()")
                print("ELIF INCOMPLETE")
                pass

            p0 = p1
        return lines

    if depthOffset == 0.0:
        for pnts in pointsLists:
            # print(f"len(pnts): {len(pnts)}")
            if len(pnts) == 1:
                lines = []
                p0 = pnts[0]
                p1 = FreeCAD.Vector(p0.x, p0.y, p0.z + 0.001)
                if p0.z > high and p1.z > high:
                    pass
                else:
                    ln = Part.Edge(Part.LineSegment(p1, p0))
                    lines.append(ln)
                    wires.append(Part.Wire(lines))
            elif len(pnts) > 1:
                lines = pntsToLine(pnts)
                if len(lines) > 0:
                    # wires.append(Part.Wire(Part.__sortEdges__(lines)))
                    # wires.append(Part.Wire(lines))
                    wires.extend([Part.Wire(w) for w in Part.sortEdges(lines)])
    else:
        trans = FreeCAD.Vector(0.0, 0.0, depthOffset)
        for pnts in pointsLists:
            if len(pnts) == 1:
                lines = []
                p0 = pnts[0]
                p1 = FreeCAD.Vector(p0.x, p0.y, p0.z + 0.001)
                line = Part.Edge(Part.LineSegment(p1, p0))
                line.translate(trans)
                lines.append(line)
                wires.append(Part.Wire(lines))
            elif len(pnts) > 1:
                lines = pntsToLine(pnts)
                if len(lines) > 0:
                    for l in lines:
                        l.translate(trans)
                    # wires.append(Part.Wire(lines))
                    wires.extend([Part.Wire(w) for w in Part.sortEdges(lines)])

    return wires


def dropCutWires(
    wires,
    fusedFace,
    toolShape,
    sampleInterval,
    dropTolerance,
    optimizeLines=False,
):
    # fusedFaceCopy = fusedFace.copy()
    # projWires = getProjectedGeometry2(fusedFace, fusedFaceCopy, wires)
    projWires = getProjectedGeometry2(fusedFace, wires)
    if isDebug:
        Part.show(Part.makeCompound(projWires), "ProjectedWires")
    # Apply drop cut to 3D projected wires to get point set
    return _dropCutWires(
        projWires,
        fusedFace,
        toolShape,
        sampleInterval,
        dropTolerance,
        optimizeLines,
    )


# FreeCAD.Console.PrintMessage("Imported Generator_DropCut\n")
