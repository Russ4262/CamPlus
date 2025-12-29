# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2022 Russell Johnson (russ4262) <russ4262@gmail.com>    *
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
import math
import freecad.camplus.utilities.Edge as EdgeUtils
import freecad.camplus.inlay.Support as InlaySupport

DEBUG = False
DEBUG_SHP = False
ROUND_CORNERS = True  # value changes in code


def _debugText(txt, force=False):
    if DEBUG or force:
        print(txt)


def _debugShape(shape, name, force=False):
    obj = None
    if shape is not None and (DEBUG_SHP or force):
        obj = Part.show(shape, name)
    return obj


# Face creation and support functions
def _makeRectangularFace(edge, halfToolAngle, depthOfCut, isInside):
    # _debugText(
    #    f"_makeRectangularFace() HTA: {halfToolAngle};  DOC: {depthOfCut};  isInside: {isInside}"
    # )
    # __showShape(edge.copy(), "LineEdge")

    origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    v0x = edge.Vertexes[0].X
    v0y = edge.Vertexes[0].Y
    # Make simple, rectagular face
    l = edge.Length
    w = depthOfCut / math.cos(math.radians(halfToolAngle))
    p1 = FreeCAD.Vector(0.0, 0.0, 0.0)
    p2 = FreeCAD.Vector(l, 0.0, 0.0)
    p3 = FreeCAD.Vector(l, w, 0.0)
    p4 = FreeCAD.Vector(0.0, w, 0.0)
    l1 = Part.makeLine(p1, p2)
    l2 = Part.makeLine(p2, p3)
    l3 = Part.makeLine(p3, p4)
    l4 = Part.makeLine(p4, p1)
    face = Part.Face(Part.Wire([l1, l2, l3, l4]))
    refEdge = face.Edge1

    # __showShape(face.copy(), "Face")
    # __showShape(face.Edge1.copy(), "RefEdge1")
    eP0 = edge.Vertexes[0].Point
    eP1 = edge.Vertexes[1].Point
    edgeDir = eP1.sub(eP0)
    # _debugText(f"eP1-eP0 {eP1} - {eP0}")
    # _debugText(f"edgeDir {edgeDir}")
    rP0 = refEdge.Vertexes[0].Point
    rP1 = refEdge.Vertexes[1].Point
    faceDir = rP0.sub(rP1)
    # _debugText(f"rP0-rP1 {rP0} - {rP1}")
    # _debugText(f"faceDir {faceDir}")

    # rotate face down over X axis to tool angle
    if isInside:
        tiltAngle = -90.0 - halfToolAngle + 90.0  # DIFFERENT
    else:
        tiltAngle = -90.0 + halfToolAngle - 90.0  # DIFFERENT
    # _debugText(f"tiltAngle {tiltAngle}")
    face.rotate(origin, FreeCAD.Vector(1.0, 0.0, 0.0), tiltAngle)
    # __showShape(face.copy(), "FaceTilt")

    # rotate face around Z axis to orient same as source edge
    xyRotationAngle = InlaySupport._vector_to_degrees(
        edgeDir
    ) - InlaySupport._vector_to_degrees(faceDir)
    # _debugText(f"xyRotationAngle {xyRotationAngle}")
    face.rotate(origin, FreeCAD.Vector(0.0, 0.0, 1.0), xyRotationAngle)
    # __showShape(face.copy(), "FaceRot")

    # move face into position at source edge
    xMove = v0x - face.Edge1.Vertexes[1].X
    yMove = v0y - face.Edge1.Vertexes[1].Y
    # _debugText(f"xMove {xMove},   yMove {yMove}")
    face.translate(FreeCAD.Vector(xMove, yMove, 0.0))
    angle = InlaySupport._vector_to_degrees(
        face.Vertexes[0].Point.sub(face.Vertexes[1].Point)
    )
    # _debugText(f"angle {angle}")
    # __showShape(face.copy(), "FaceRect")

    return face, angle, xyRotationAngle


def _makeConicalFaceUp(edge, halfToolAngle, depthOfCut, isInside):
    _debugText(
        f"_makeConicalFaceUp() HTA: {halfToolAngle}  DOC: {depthOfCut}  isInside: {isInside}"
    )

    if depthOfCut <= 0.0:
        FreeCAD.Console.PrintMessage("ERROR: _makeConicalFaceUp() depthOfCut <= 0.0\n")
        return None

    # plungeRadius is based on physical tool dimensions
    plungeRadius = math.tan(math.radians(halfToolAngle)) * depthOfCut
    edgeRadius = edge.Curve.Radius
    angle = (edge.Length / (2.0 * math.pi * edge.Curve.Radius)) * 360.0

    # _debugText(
    #    f"making cone: PlunRad{plungeRadius}, ArcRad{edgeRadius}, DOC{depthOfCut}, Ang{angle}"
    # )
    if plungeRadius >= edgeRadius:
        # _debugText(f"plungeRadius: {plungeRadius} >= edgeRadius: {edgeRadius}")
        # Set depth of cut as needed, raising cutter such that cutter only plunges to fit arc radius
        bottomRadius = 0.0
        depth = edgeRadius / math.tan(math.radians(halfToolAngle))
    else:
        # _debugText(f"plungeRadius: {plungeRadius} < edgeRadius: {edgeRadius}")
        if isInside:
            bottomRadius = edgeRadius + plungeRadius
        else:
            bottomRadius = edgeRadius - plungeRadius
        depth = depthOfCut

    edgeIdx = 0
    if bottomRadius < 0.0:
        # _debugText(
        #    f"    bottom radius of {bottomRadius} changed to 0.0 with DOC at {depth}"
        # )
        bottomRadius = 0.0
        depth = abs(edgeRadius / math.tan(math.radians(halfToolAngle)))
        edgeIdx = 2

    _debugText(
        f"    CF: BRad:{bottomRadius}, TRad:{edgeRadius}, Dep:{depth}, Ang:{angle}"
    )
    cone = Part.makeCone(
        edgeRadius,  # DIFFERENT - swapped
        bottomRadius,  # DIFFERENT - swapped
        depth,
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, 1.0),
        angle,
    )
    face = cone.Faces[0].copy()
    face.translate(
        FreeCAD.Vector(
            edge.Curve.Center.x,
            edge.Curve.Center.y,
            edge.Curve.Center.z,
        )
    )
    _debugShape(face, "RawConicalFace")

    edgeMidpoint = EdgeUtils.valueAtEdgeLength(edge, edge.Length / 2.0)
    edgeDirRaw = edgeMidpoint.sub(edge.Curve.Center)
    edgeDir = FreeCAD.Vector(edgeDirRaw.x, edgeDirRaw.y, 0.0)
    # eLine = Part.makeLine(edge.Curve.Center, edgeMidpoint)
    # __showShape(eLine, "ELine")

    faceEdge = face.Edges[edgeIdx]  # DIFFERENT [0]
    faceMidpoint = EdgeUtils.valueAtEdgeLength(faceEdge, faceEdge.Length / 2.0)
    faceDirRaw = faceMidpoint.sub(faceEdge.Curve.Center)
    faceDir = FreeCAD.Vector(faceDirRaw.x, faceDirRaw.y, 0.0)
    # fLine = Part.makeLine(edge.Curve.Center, faceMidpoint)
    # __showShape(fLine, "FLine")

    rotationAngle = InlaySupport._vector_to_degrees(
        edgeDir
    ) - InlaySupport._vector_to_degrees(faceDir)
    face.rotate(faceEdge.Curve.Center, FreeCAD.Vector(0.0, 0.0, 1.0), rotationAngle)
    face.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - face.BoundBox.ZMin))  # .ZMax
    # _debugText(f"    edgeDir:{edgeDir}, faceDir:{faceDir}, RotAng:{rotationAngle}")

    return face, angle, rotationAngle


def _coneConnectionToSquareUp(face, sweepAngle):
    """_coneConnectionToSquareUp(face, sweepAngle)
    Convert cone face section to fusion of two triangular faces, making rectangular corner instead of arc.
    """
    fbb = face.BoundBox
    zMax = fbb.ZMax  # DIFFERENT zMin;  ZMin
    tip = face.Vertexes[2].Point  # DIFFERENT [0]
    cent = FreeCAD.Vector(tip.x, tip.y, zMax)  # DIFFERENT zMin
    midPnt = EdgeUtils.valueAtEdgeLength(
        face.Edges[0], face.Edges[0].Length / 2.0
    )  # DIFFERENT [2]; [2]
    vect = midPnt.sub(cent).normalize()
    rad = face.Vertexes[0].Point.sub(cent).Length  # DIFFERENT [1]
    dist = rad / math.cos(math.radians(sweepAngle) / 2.0)
    vect.multiply(dist)
    midLine = cent.add(vect)

    # __showShape(Part.makeLine(cent, midLine), "MidLine")

    seg1 = Part.makeLine(tip, face.Vertexes[0].Point)  # DIFFERENT [1]
    seg2 = Part.makeLine(face.Vertexes[0].Point, midLine)  # DIFFERENT [1]
    seg3 = Part.makeLine(midLine, tip)
    f1 = Part.Face(Part.Wire([seg1, seg2, seg3]))
    _debugShape(f1, "Face1")

    seg4 = Part.makeLine(tip, face.Vertexes[1].Point)  # DIFFERENT [2]
    seg5 = Part.makeLine(face.Vertexes[1].Point, midLine)  # DIFFERENT [2]
    seg6 = Part.makeLine(midLine, tip)
    f2 = Part.Face(Part.Wire([seg4, seg5, seg6]))
    _debugShape(f2, "Face2")

    return f1.fuse(f2)


def _makeConnectionFaceUp(
    edge, halfToolAngle, depthOfCut, arcAngle, prevPoint, isInside
):
    """_makeConnectionFaceUp(edge, halfToolAngle, depthOfCut, arcAngle, prevPoint, isClockwise)
    Return section of cone as arc connection coneFace."""
    # This function assumes counterclockwise wire direction
    if depthOfCut <= 0.0:
        FreeCAD.Console.PrintMessage(
            "ERROR: _makeConnectionFaceUp() depthOfCut <= 0.0\n"
        )
        return None

    # plungeRadius = math.tan(math.radians(halfToolAngle)) * depthOfCut
    plungeRadius = math.tan(math.radians(abs(halfToolAngle))) * depthOfCut
    commonPoint = edge.Vertexes[0].Point
    coneAngle = arcAngle

    cone = Part.makeCone(
        0.0,  # DIFFERENT - swapped
        plungeRadius,  # DIFFERENT - swapped
        depthOfCut,
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, 1.0),
        coneAngle,
    )
    # __showShape(cone.copy(), "RawConnectCone")
    cone.translate(
        FreeCAD.Vector(
            commonPoint.x - cone.Vertexes[2].X,  # DIFFERENT
            commonPoint.y - cone.Vertexes[2].Y,  # DIFFERENT
            commonPoint.z - cone.Vertexes[2].Z,  # DIFFERENT
        )
    )

    coneFace = cone.Face1.copy()
    centToPrev = prevPoint.sub(commonPoint)

    if isInside:
        faceIdx = 2
    else:
        faceIdx = 0  # 1

    centToConeFaceVert2 = coneFace.Vertexes[faceIdx].Point.sub(commonPoint)
    rotationAngle = InlaySupport._vector_to_degrees(
        centToPrev
    ) - InlaySupport._vector_to_degrees(centToConeFaceVert2)
    # _debugText(f"rotationAngle: {rotationAngle}")

    coneFace.rotate(commonPoint, FreeCAD.Vector(0.0, 0.0, 1.0), rotationAngle)

    _debugShape(coneFace, "ConnectFace")
    return coneFace


def _calculateArcStartAngle(e, flip=False):
    p0 = e.Curve.Center
    p1 = e.Vertexes[0].Point
    ang = InlaySupport._vector_to_degrees(p1.sub(p0)) - 90.0
    if flip:
        ang += 180.0
    if ang < 0.0:
        ang += 360.0
    if ang >= 360.0:
        ang -= 360.0
    return ang


def _calculateArcEndAngle(e, flip=False):
    p0 = e.Curve.Center
    p1 = e.Vertexes[1].Point
    ang = InlaySupport._vector_to_degrees(p1.sub(p0)) - 90.0
    if flip:
        ang += 180.0
    if ang < 0.0:
        ang += 360.0
    if ang >= 360.0:
        ang -= 360.0
    return ang


def _makeInlayFace(e, halfToolAngle, depthOfCut, wireFace, isInside):
    """_makeInlayFace(e, halfToolAngle, depthOfCut, wireFace, isOutside)"""
    # _debugText(f"getFace_CCW(e, halfToolAngle, depthOfCut, outside={outside})")
    _debugShape(e, "ClosedFaceEdge")
    eType = e.Curve.TypeId
    if eType == "Part::GeomCircle":
        # _debugText("Processing Part::GeomCircle  . . . . . . . . . .")
        f0, ang0, rotAng0 = _makeConicalFaceUp(e, halfToolAngle, depthOfCut, isInside)
        if InlaySupport._isCommon(wireFace, f0, isInside):
            _debugText("  InlaySupport._isCommon is True")
            edgeStartAng0 = _calculateArcStartAngle(e)
            edgeEndAng0 = _calculateArcEndAngle(e)
            return "GC", f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0
        _debugText("  InlaySupport._isCommon is False - recalculating conical face")
        f, ang, rotAng = _makeConicalFaceUp(e, halfToolAngle, depthOfCut, not isInside)
        edgeStartAng = _calculateArcStartAngle(e, True)
        edgeEndAng = _calculateArcEndAngle(e, True)
        return "GC", f, ang, rotAng, edgeStartAng, edgeEndAng
    elif eType == "Part::GeomLine":
        # _debugText("Processing Part::GeomLine . . . . . . . . . .")
        f, ang, rotAng = _makeRectangularFace(e, halfToolAngle, depthOfCut, isInside)
        edgeStartAng = InlaySupport._normalizeDegrees(ang)
        edgeEndAng = edgeStartAng
        return "GL", f, ang, rotAng, edgeStartAng, edgeEndAng

    FreeCAD.Console.PrintMessage(f"makeInlay...() Ignoring '{eType}' edge\n")
    # return None, None, None, None, None, None
    return None  # Throw error


# Public functions
def clockwiseWireToRawInlay(w, halfToolAngle, depthOfCut, roundCorners):
    _debugText("InlayClosedUp.clockwiseWireToRawInlay()")
    wireFace = Part.Face(w)
    wireFace.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - wireFace.BoundBox.ZMin))
    lastEdge = w.Edges[0]
    lastFace = None
    lastEndAng = 0.0
    obtusePoints = []

    # Process first edge
    eType0, f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0 = _makeInlayFace(
        lastEdge, halfToolAngle, depthOfCut, wireFace, True
    )
    lastFace = f0
    lastEndAng = edgeEndAng0
    faces = [f0]
    # _visualizeStartAngle(lastEdge, edgeStartAng0)
    _debugShape(f0, "PathFace")
    # _visualizeEndAngle(lastEdge, edgeEndAng0)

    for e in [e for e in w.Edges[1:]] + [w.Edges[0]]:
        eType, f, ang, rotAng, edgeStartAng, edgeEndAng = _makeInlayFace(
            e, halfToolAngle, depthOfCut, wireFace, True
        )
        # _visualizeStartAngle(e, edgeStartAng)
        _debugShape(f, "PathFace")
        # _visualizeEndAngle(e, edgeEndAng)
        # print(f"  edgeStartAng: {edgeStartAng}  minus lastEndAng: {lastEndAng}")
        angDiff = edgeStartAng - lastEndAng
        if (0.0 < angDiff and angDiff < 180.0) or (
            -360.0 < angDiff and angDiff < -180.0
        ):
            # make connect face
            if angDiff < 0.0:
                angDiff += 360.0
            arcAng = abs(angDiff)
            obtusePoints.append(e.Vertexes[0].Point)
            coneFace = _makeConnectionFaceUp(
                e,
                halfToolAngle,
                depthOfCut,
                arcAng,
                InlaySupport._getLowConnectPoint(lastFace, e.Vertexes[0].Point),
                True,
            )
            # if ROUND_CORNERS:
            if roundCorners:
                faces.append(coneFace)
            else:
                faces.append(_coneConnectionToSquareUp(coneFace, arcAng))
        lastEdge = e
        lastFace = f
        lastEndAng = edgeEndAng
        faces.append(f)

    # Remove last edge
    firstFace = faces.pop()

    return EdgeUtils.fuseShapes(faces), obtusePoints


def clockwiseWireToRawOutlay(w, halfToolAngle, depthOfCut, roundCorners):
    _debugText("InlayClosedUp.clockwiseWireToRawOutlay()")
    wireFace = Part.Face(w)
    wireFace.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - wireFace.BoundBox.ZMin))
    lastEdge = w.Edges[0]
    lastFace = None
    lastEndAng = 0.0
    obtusePoints = []

    # Process first edge
    eType0, f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0 = _makeInlayFace(
        lastEdge, halfToolAngle, depthOfCut, wireFace, False
    )
    lastFace = f0
    lastEndAng = edgeEndAng0
    faces = [f0]
    # InlaySupport._visualizeStartAngle(lastEdge, edgeStartAng0)
    _debugShape(f0, "PathFace")
    # InlaySupport._visualizeEndAngle(lastEdge, edgeEndAng0)

    for e in [e for e in w.Edges[1:]] + [w.Edges[0]]:
        eType, f, ang, rotAng, edgeStartAng, edgeEndAng = _makeInlayFace(
            e, halfToolAngle, depthOfCut, wireFace, False
        )
        # InlaySupport._visualizeStartAngle(e, edgeStartAng)
        _debugShape(f, "PathFace")
        # InlaySupport._visualizeEndAngle(e, edgeEndAng)
        angDiff = edgeStartAng - lastEndAng
        # _debugText(
        #    f"  angDiff: {angDiff}  =  edgeStartAng: {edgeStartAng}  minus lastEndAng: {lastEndAng}"
        # )
        if angDiff > 180.0 or (-180.0 < angDiff and angDiff < 0.0):
            # make connect face
            # print("  --MAKING CONNECTION --")
            if angDiff > 180.0:
                arcAng = 360.0 - angDiff
            else:
                arcAng = abs(angDiff)
            # lowPoint = InlaySupport._getLowConnectPoint(lastFace, e.Vertexes[0].Point)
            # _debugText(f"arcAng: {arcAng};  lowPoint: {lowPoint}")
            obtusePoints.append(e.Vertexes[0].Point)
            coneFace = _makeConnectionFaceUp(
                e,
                halfToolAngle,
                depthOfCut,
                arcAng,
                InlaySupport._getLowConnectPoint(lastFace, e.Vertexes[0].Point),
                False,
            )
            # if ROUND_CORNERS:
            if roundCorners:
                faces.append(coneFace)
            else:
                faces.append(_coneConnectionToSquareUp(coneFace, arcAng))
        # Eif

        lastEdge = e
        lastFace = f
        lastEndAng = edgeEndAng
        faces.append(f)

    # Remove last edge
    firstFace = faces.pop()

    return EdgeUtils.fuseShapes(faces), obtusePoints


#################################################
def rotateShape180(shape, offset=FreeCAD.Vector(0.0, 0.0, 0.0)):
    origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    rotated = shape.copy()
    vBB = rotated.BoundBox
    rotated.translate(FreeCAD.Vector(0.0 - vBB.XMin, 0.0 - vBB.YMin, 0.0 - vBB.ZMin))
    rotated.rotate(origin, FreeCAD.Vector(0.0, 1.0, 0.0), 180.0)
    vBB = rotated.BoundBox
    sBB = shape.BoundBox
    rotated.translate(
        FreeCAD.Vector(
            sBB.XMin - vBB.XMin + offset.x,
            sBB.YMin - vBB.YMin + offset.y,
            sBB.ZMin - vBB.ZMin + offset.z,
        )
    )
    return rotated
