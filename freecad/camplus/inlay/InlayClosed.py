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
        if FreeCAD.ActiveDocument.getObject(name):
            FreeCAD.ActiveDocument.removeObject(name)
        obj = Part.show(shape, name)
    return obj


# Face creation and support functions
def _makeRectangularFace(edge, halfToolAngle, depthOfCut, isInside):
    # _debugText(f"_makeRectangularFace() DOC: {depthOfCut}  CW: {isInside}")
    _debugShape(edge.copy(), "Edge")

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

    # _debugShape(face.copy(), "Face")
    # _debugShape(face.Edge1.copy(), "RefEdge1")
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
        tiltAngle = -90.0 - halfToolAngle
    else:
        tiltAngle = -90.0 + halfToolAngle
    # _debugText(f"tiltAngle {tiltAngle}")
    face.rotate(origin, FreeCAD.Vector(1.0, 0.0, 0.0), tiltAngle)
    # _debugShape(face.copy(), "FaceTilt")

    # rotate face around Z axis to orient same as source edge
    xyRotationAngle = InlaySupport._vector_to_degrees(
        edgeDir
    ) - InlaySupport._vector_to_degrees(faceDir)
    # _debugText(f"xyRotationAngle {xyRotationAngle}")
    face.rotate(origin, FreeCAD.Vector(0.0, 0.0, 1.0), xyRotationAngle)
    # _debugShape(face.copy(), "FaceRot")

    # move face into position at source edge
    xMove = v0x - face.Edge1.Vertexes[1].X
    yMove = v0y - face.Edge1.Vertexes[1].Y
    # _debugText(f"xMove {xMove},   yMove {yMove}")
    face.translate(FreeCAD.Vector(xMove, yMove, 0.0 - face.BoundBox.ZMax))
    angle = InlaySupport._vector_to_degrees(
        face.Vertexes[0].Point.sub(face.Vertexes[1].Point)
    )
    # _debugText(f"angle {angle}")
    # _debugShape(face.copy(), "FaceRect")

    return face, angle, xyRotationAngle


def _makeConicalFace(edge, halfToolAngle, depthOfCut, isInside):
    debugLocal = False
    _debugText(
        f"_makeConicalFace() HalfToolAng: {halfToolAngle}  DOC: {depthOfCut}  isInside: {isInside}",
        debugLocal,
    )

    if depthOfCut <= 0.0:
        FreeCAD.Console.PrintError("ERROR: _makeConicalFace() depthOfCut <= 0.0\n")
        return None

    # plungeRadius is based on physical tool dimensions
    plungeRadius = math.tan(math.radians(halfToolAngle)) * depthOfCut
    edgeRadius = edge.Curve.Radius
    angle = (edge.Length / (2.0 * math.pi * edge.Curve.Radius)) * 360.0

    _debugText(
        f"making cone: PlunRad:{plungeRadius}, ArcRad:{edgeRadius}, DOC:{depthOfCut}, Ang:{angle}",
        debugLocal,
    )
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

    if bottomRadius < 0.0:
        # _debugText(
        #    f"    bottom radius of {bottomRadius} changed to 0.0 with DOC at {depth}"
        # )
        bottomRadius = 0.0
        depth = abs(edgeRadius / math.tan(math.radians(halfToolAngle)))

    _debugText(
        f"    CF: BRad:{bottomRadius}, TRad:{edgeRadius}, Dep:{depth}, Ang:{angle}",
        debugLocal,
    )

    cone = Part.makeCone(
        bottomRadius,
        edgeRadius,
        depth,
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, 1.0),
        angle,
    )
    _debugShape(cone, "RawCone", debugLocal)

    face = cone.Faces[0].copy()
    face.translate(
        FreeCAD.Vector(edge.Curve.Center.x, edge.Curve.Center.y, edge.Curve.Center.z)
    )

    edgeMidpoint = EdgeUtils.valueAtEdgeLength(edge, edge.Length / 2.0)
    edgeDirRaw = edgeMidpoint.sub(edge.Curve.Center)
    edgeDir = FreeCAD.Vector(edgeDirRaw.x, edgeDirRaw.y, 0.0)
    # eLine = Part.makeLine(edge.Curve.Center, edgeMidpoint)
    # _debugShape(eLine, "ELine")

    faceEdge = face.Edges[0]
    faceMidpoint = EdgeUtils.valueAtEdgeLength(faceEdge, faceEdge.Length / 2.0)
    faceDirRaw = faceMidpoint.sub(faceEdge.Curve.Center)
    faceDir = FreeCAD.Vector(faceDirRaw.x, faceDirRaw.y, 0.0)
    # fLine = Part.makeLine(edge.Curve.Center, faceMidpoint)
    # _debugShape(fLine, "FLine")

    rotationAngle = InlaySupport._vector_to_degrees(
        edgeDir
    ) - InlaySupport._vector_to_degrees(faceDir)
    face.rotate(faceEdge.Curve.Center, FreeCAD.Vector(0.0, 0.0, 1.0), rotationAngle)
    face.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - face.BoundBox.ZMax))
    # _debugText(f"    edgeDir:{edgeDir}, faceDir:{faceDir}, RotAng:{rotationAngle}")

    return face, angle, rotationAngle


def _coneConnectionToSquare(face, sweepAngle):
    """_coneConnectionToSquare(face, sweepAngle)
    Convert cone face section to fusion of two triangular faces, making rectangular corner instead of arc.
    """
    fbb = face.BoundBox
    zMin = fbb.ZMin
    tip = face.Vertexes[0].Point
    cent = FreeCAD.Vector(tip.x, tip.y, zMin)
    midPnt = EdgeUtils.valueAtEdgeLength(face.Edges[2], face.Edges[2].Length / 2.0)
    vect = midPnt.sub(cent).normalize()
    rad = face.Vertexes[1].Point.sub(cent).Length
    dist = rad / math.cos(math.radians(sweepAngle) / 2.0)
    vect.multiply(dist)
    midLine = cent.add(vect)

    # _debugShape(Part.makeLine(cent, midLine), "MidLine")

    seg1 = Part.makeLine(tip, face.Vertexes[1].Point)
    seg2 = Part.makeLine(face.Vertexes[1].Point, midLine)
    seg3 = Part.makeLine(midLine, tip)
    f1 = Part.Face(Part.Wire([seg1, seg2, seg3]))
    # _debugShape(f1, "Face1")

    seg4 = Part.makeLine(tip, face.Vertexes[2].Point)
    seg5 = Part.makeLine(face.Vertexes[2].Point, midLine)
    seg6 = Part.makeLine(midLine, tip)
    f2 = Part.Face(Part.Wire([seg4, seg5, seg6]))
    # _debugShape(f2, "Face2")

    return f1.fuse(f2)


def _makeConnectionFace(edge, halfToolAngle, depthOfCut, arcAngle, prevPoint, isInside):
    """_makeConnectionFace(edge, halfToolAngle, depthOfCut, arcAngle, prevPoint, isInside)
    Return section of cone as arc connection coneFace."""
    # This function assumes counterclockwise wire direction
    if depthOfCut <= 0.0:
        FreeCAD.Console.PrintError("ERROR: _makeConnectionFace() depthOfCut <= 0.0\n")
        return None

    # plungeRadius = math.tan(math.radians(halfToolAngle)) * depthOfCut
    plungeRadius = math.tan(math.radians(abs(halfToolAngle))) * depthOfCut
    commonPoint = edge.Vertexes[0].Point
    coneAngle = arcAngle
    if isInside:
        faceIdx = 2
    else:
        faceIdx = 1

    cone = Part.makeCone(
        plungeRadius,
        0.0,
        depthOfCut,
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, 1.0),
        coneAngle,
    )
    cone.translate(
        FreeCAD.Vector(
            commonPoint.x - cone.Vertexes[0].X,
            commonPoint.y - cone.Vertexes[0].Y,
            commonPoint.z - cone.Vertexes[0].Z,
        )
    )

    coneFace = cone.Face1.copy()

    centToPrev = prevPoint.sub(commonPoint)
    centToConeFaceVert2 = coneFace.Vertexes[faceIdx].Point.sub(commonPoint)
    rotationAngle = InlaySupport._vector_to_degrees(
        centToPrev
    ) - InlaySupport._vector_to_degrees(centToConeFaceVert2)

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


def _makeInlayFaceCW(e, halfToolAngle, depthOfCut, wireFace, isInside):
    """_makeInlayFaceCW(e, halfToolAngle, depthOfCut, wireFace, isOutside)
    Make clockwise inlay face."""
    # _debugText(f"getFace_CCW(e, halfToolAngle, depthOfCut, outside={outside})")
    # _debugShape(e, "ClosedFaceEdge")
    eType = e.Curve.TypeId
    if eType == "Part::GeomCircle":
        _debugText("Processing Part::GeomCircle  . . . . . . . . . .")
        f0, ang0, rotAng0 = _makeConicalFace(e, halfToolAngle, depthOfCut, isInside)
        if InlaySupport._isCommon(wireFace, f0, isInside) or True:
            _debugText("  InlaySupport._isCommon is True")
            edgeStartAng0 = _calculateArcStartAngle(e)
            edgeEndAng0 = _calculateArcEndAngle(e)
            return "GC", f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0
        _debugText("  InlaySupport._isCommon is False - recalculating conical face")
        f, ang, rotAng = _makeConicalFace(e, halfToolAngle, depthOfCut, not isInside)
        edgeStartAng = _calculateArcStartAngle(e, True)
        edgeEndAng = _calculateArcEndAngle(e, True)
        return "GC", f, ang, rotAng, edgeStartAng, edgeEndAng
    elif eType == "Part::GeomLine":
        _debugText("Processing Part::GeomLine . . . . . . . . . .")
        f, ang, rotAng = _makeRectangularFace(e, halfToolAngle, depthOfCut, isInside)
        edgeStartAng = InlaySupport._normalizeDegrees(ang)
        edgeEndAng = edgeStartAng
        return "GL", f, ang, rotAng, edgeStartAng, edgeEndAng

    FreeCAD.Console.PrintError(f"makeInlay...() Ignoring '{eType}' edge\n")
    # return None, None, None, None, None, None
    return None  # Throw error


def _makeInlayFace(e, halfToolAngle, depthOfCut, wireFace, isInside):
    """_makeInlayFace(e, halfToolAngle, depthOfCut, wireFace, isOutside)"""
    # _debugText(f"getFace_CCW(e, halfToolAngle, depthOfCut, outside={outside})")
    # _debugShape(e, "ClosedFaceEdge")
    eType = e.Curve.TypeId
    if eType == "Part::GeomCircle":
        _debugText("Processing Part::GeomCircle  . . . . . . . . . .")
        f0, ang0, rotAng0 = _makeConicalFace(e, halfToolAngle, depthOfCut, isInside)
        if InlaySupport._isCommon(wireFace, f0, isInside):
            _debugText("  InlaySupport._isCommon is True")
            edgeStartAng0 = _calculateArcStartAngle(e)
            edgeEndAng0 = _calculateArcEndAngle(e)
            return "GC", f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0
        _debugText("  InlaySupport._isCommon is False - recalculating conical face")
        f, ang, rotAng = _makeConicalFace(e, halfToolAngle, depthOfCut, not isInside)
        edgeStartAng = _calculateArcStartAngle(e, True)
        edgeEndAng = _calculateArcEndAngle(e, True)
        return "GC", f, ang, rotAng, edgeStartAng, edgeEndAng
    elif eType == "Part::GeomLine":
        # _debugText("Processing Part::GeomLine . . . . . . . . . .")
        f, ang, rotAng = _makeRectangularFace(e, halfToolAngle, depthOfCut, isInside)
        edgeStartAng = InlaySupport._normalizeDegrees(ang)
        edgeEndAng = edgeStartAng
        return "GL", f, ang, rotAng, edgeStartAng, edgeEndAng

    FreeCAD.Console.PrintError(f"makeInlay...() Ignoring '{eType}' edge\n")
    # return None, None, None, None, None, None
    return None  # Throw error


def _facesNotAligned(lastFace, f, common):
    # Check if two faces share two common vertexes
    cnt = 0
    for v in lastFace.Vertexes:
        p = v.Point
        for v2 in f.Vertexes:
            if EdgeUtils.PathGeom.isRoughly(p.sub(v2.Point).Length, 0.0):
                cnt += 1
                break
    if cnt == 2:
        return False

    # Check if fusion of faces introduces new vertex, indicating common edge
    fusion = lastFace.fuse(f)
    if len(fusion.Wires[0].Vertexes) > len(lastFace.Vertexes):
        return False

    # Check if wire length of lastFace changed, indicating two faces connect
    if not EdgeUtils.PathGeom.isRoughly(
        fusion.Wires[0].Length, lastFace.Wires[0].Length
    ):
        return False

    fp = f.Vertexes[-1].Point  # f.Vertexes[3].Point
    lp = lastFace.Vertexes[-1].Point  # lastFace.Vertexes[3].Point
    if lp.sub(fp).Length > common.sub(lp).Length:
        return False

    return True


# Public functions
def clockwiseWireToRawInlay(w, halfToolAngle, depthOfCut, roundCorners):
    _debugText("InlayClosed.clockwiseWireToRawInlay()")
    wireFace = Part.Face(w)
    wireFace.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - wireFace.BoundBox.ZMin))
    lastEdge = w.Edges[0]
    lastFace = None
    lastEndAng = 0.0
    pfi = 0
    obtusePoints = []
    # Part.show(wireFace, "WireFace")

    # Process first edge
    eType0, f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0 = _makeInlayFaceCW(
        lastEdge, halfToolAngle, depthOfCut, wireFace, True
    )
    lastFace = f0
    lastEndAng = edgeEndAng0
    faces = [f0]
    # _visualizeStartAngle(lastEdge, edgeStartAng0)

    # _debugShape(f0, f"PathFace_{pfi}_")
    _debugText(f"pfi: {pfi}")

    # _visualizeEndAngle(lastEdge, edgeEndAng0)

    for e in [e for e in w.Edges[1:]] + [w.Edges[0].copy()]:
        pfi += 1
        _debugText(f"pfi: {pfi}")
        eType, f, ang, rotAng, edgeStartAng, edgeEndAng = _makeInlayFaceCW(
            e, halfToolAngle, depthOfCut, wireFace, True
        )
        # _visualizeStartAngle(e, edgeStartAng)
        # _debugShape(f, f"PathFace_{pfi}_")
        # print(f"eType: {eType}")
        # _visualizeEndAngle(e, edgeEndAng)
        # print(
        #    f"zzz_{pfi}_  edgeStartAng: {edgeStartAng}  minus lastEndAng: {lastEndAng}"
        # )
        angDiff = edgeStartAng - lastEndAng
        # print(f"zzz_{pfi}_  angDiff: {angDiff}")
        if eType == "GC" and _facesNotAligned(lastFace, f, e.Vertexes[1].Point):
            altIsInside = True  # original was False, but known direction allows for correct value = True
            _debugText("*** Faces NOT aligned ..............")
            eType, f, ang, rotAng, edgeStartAng, edgeEndAng2 = _makeInlayFaceCW(
                e, halfToolAngle, depthOfCut, wireFace, altIsInside
            )
            angDiff = edgeStartAng - lastEndAng
            # print(
            #    f"zzz_{pfi}_  edgeStartAng: {edgeStartAng}  minus lastEndAng: {lastEndAng}"
            # )
            # print(f"zzz_{pfi}_  angDiff: {angDiff}")
            # _debugShape(f, f"PathFace_{pfi}_2_")
            if angDiff < 0.0:
                angDiff += 180.0
                edgeEndAng += 180.0

        # if pfi == 13:
        #    Part.show(lastFace, "LastFace_13_")
        #    # Part.show(f, "LastFace_13_")
        # print(f"zzz_{pfi}_  angDiff: {angDiff}")
        # _debugShape(lastFace, f"LastFace_{pfi}_", force=True)

        if (0.0 < angDiff and angDiff < 180.0) or (
            -360.0 < angDiff and angDiff < -180.0
        ):
            _debugText("Making CONNECT face for last two faces.")
            # make connect face
            if angDiff < 0.0:
                angDiff += 360.0
            arcAng = abs(angDiff)
            obtusePoints.append(e.Vertexes[0].Point)

            # print(f"zzz_{pfi}_ topPoint: {e.Vertexes[0].Point}")
            coneFace = _makeConnectionFace(
                e,
                halfToolAngle,
                depthOfCut,
                arcAng,
                InlaySupport._getLowConnectPoint(
                    lastFace, e.Vertexes[0].Point, error=0.0001
                ),
                True,
            )
            # if ROUND_CORNERS:
            if roundCorners:
                faces.append(coneFace)
            else:
                faces.append(_coneConnectionToSquare(coneFace, arcAng))
        else:
            _debugText("No connecting face needed.")

        lastEdge = e
        lastFace = f
        lastEndAng = edgeEndAng
        faces.append(f)

    # Remove last edge
    firstFace = faces.pop()

    return EdgeUtils.fuseShapes(faces), obtusePoints


def clockwiseWireToRawOutlay(w, halfToolAngle, depthOfCut, roundCorners):
    _debugText("InlayClosed.clockwiseWireToRawOutlay()")
    wireFace = Part.Face(w)
    wireFace.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - wireFace.BoundBox.ZMin))
    lastEdge = w.Edges[0]
    lastFace = None
    lastEndAng = 0.0
    pfi = 0
    obtusePoints = []

    # Process first edge
    eType0, f0, ang0, rotAng0, edgeStartAng0, edgeEndAng0 = _makeInlayFace(
        lastEdge, halfToolAngle, depthOfCut, wireFace, False
    )
    lastFace = f0
    lastEndAng = edgeEndAng0
    faces = [f0]
    # InlaySupport._visualizeStartAngle(lastEdge, edgeStartAng0)
    # _debugShape(f0, f"PathFace_{pfi}_")
    # InlaySupport._visualizeEndAngle(lastEdge, edgeEndAng0)

    for e in [e for e in w.Edges[1:]] + [w.Edges[0]]:
        pfi += 1
        eType, f, ang, rotAng, edgeStartAng, edgeEndAng = _makeInlayFace(
            e, halfToolAngle, depthOfCut, wireFace, False
        )
        # InlaySupport._visualizeStartAngle(e, edgeStartAng)
        # _debugShape(f, f"PathFace_{pfi}_")
        # InlaySupport._visualizeEndAngle(e, edgeEndAng)
        angDiff = edgeStartAng - lastEndAng
        # _debugText(
        #    f"  angDiff: {angDiff}  =  edgeStartAng: {edgeStartAng}  minus lastEndAng: {lastEndAng}"
        # )
        # print(f"zzz_{pfi}_  angDiff: {angDiff}")
        if eType == "GC" and _facesNotAligned(lastFace, f, e.Vertexes[1].Point):
            eType, f, ang, rotAng, edgeStartAng, edgeEndAng2 = _makeInlayFace(
                e, halfToolAngle, depthOfCut, wireFace, True
            )
            angDiff = edgeStartAng - lastEndAng
            # print(f"zzz_{pfi}_  angDiff: {angDiff}")
            if angDiff < 0.0:
                angDiff += 180.0
                edgeEndAng += 180.0

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

            coneFace = _makeConnectionFace(
                e,
                halfToolAngle,
                depthOfCut,
                arcAng,
                InlaySupport._getLowConnectPoint(
                    lastFace, e.Vertexes[0].Point, error=0.0001
                ),
                False,
            )
            # if ROUND_CORNERS:
            if roundCorners:
                faces.append(coneFace)
            else:
                faces.append(_coneConnectionToSquare(coneFace, arcAng))
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
