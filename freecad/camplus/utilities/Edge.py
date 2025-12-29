# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2016 sliptonic <shopinthewoods@gmail.com>               *
# *   Copyright (c) 2018 sliptonic <shopinthewoods@gmail.com>               *
# *   Copyright (c) 2021 Schildkroet                                        *
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
import Path.Log as PathLog
import Path.Geom as PathGeom
import Part
import math

if FreeCAD.GuiUp:
    import FreeCADGui


__title__ = "Edge Utilities"
__author__ = "sliptonic (Brad Collette), Schildkroet, Russell Johnson (russ4262) <russ4262@gmail.com>"
__url__ = "https://github.com/Russ4262/PathRed"
__doc__ = "Utilities for manipulating edges. Some functions are modified derivatives of functions in the Path.Geom.py and Path.Op.Util modules."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


# Private functions
def _flipLine(edge):
    """_flipLine(edge)
    Reverses direction of a line by reversing the order of the vertexes, while maintaining the geometric shape.
    Copied from Path.Geom.flipEdge()."""

    if not edge.Vertexes:
        return Part.Edge(
            Part.Line(
                edge.valueAt(edge.LastParameter), edge.valueAt(edge.FirstParameter)
            )
        )

    return Part.Edge(Part.LineSegment(edge.Vertexes[-1].Point, edge.Vertexes[0].Point))


def _flipLineSegment(edge):
    """_flipLineSegment(edge)
    Reverses direction of a line segment by reversing the order of the vertexes, while maintaining the geometric shape.
    Copied from Path.Geom.flipEdge()."""

    return Part.Edge(Part.LineSegment(edge.Vertexes[-1].Point, edge.Vertexes[0].Point))


def _flipCircle(edge):
    """_flipCircle(edge)
    Reverses direction of an arc or circle by reversing the order of the vertexes, while maintaining the geometric shape.
    Copied from Path.Geom.flipEdge()."""

    # Create an inverted circle
    circle = Part.Circle(edge.Curve.Center, -edge.Curve.Axis, edge.Curve.Radius)
    # Rotate the circle appropriately so it starts at edge.valueAt(edge.LastParameter)
    circle.rotate(
        FreeCAD.Placement(
            circle.Center,
            circle.Axis,
            180.0 - math.degrees(edge.LastParameter + edge.Curve.AngleXU),
        )
    )
    # Now the edge always starts at 0 and LastParameter is the value range
    return Part.Edge(circle, 0, edge.LastParameter - edge.FirstParameter)


def _flipBSplineBezier(edge):
    """_flipBSplineBezier(edge)
    Reverses direction of a B-Spline or Bezier curve by reversing the order of the vertexes, while maintaining the geometric shape.
    Modified form of Path.Geom.flipEdge()."""
    if type(edge.Curve) == Part.BSplineCurve:
        spline = edge.Curve
    else:
        spline = edge.Curve.toBSpline()

    mults = spline.getMultiplicities()
    weights = spline.getWeights()
    knots = spline.getKnots()
    poles = spline.getPoles()
    perio = spline.isPeriodic()
    ratio = spline.isRational()
    degree = spline.Degree

    ma = max(knots)
    mi = min(knots)
    knotsRev = [ma + mi - k for k in knots]

    mults.reverse()
    weights.reverse()
    poles.reverse()
    knotsRev.reverse()

    flipped = Part.BSplineCurve()
    flipped.buildFromPolesMultsKnots(
        poles, mults, knotsRev, perio, degree, weights, ratio
    )

    firstParam = 0.0
    lastParam = 1.0
    if not PathGeom.isRoughly(edge.LastParameter, 1.0):
        firstParam = 1.0 - edge.LastParameter
    if not PathGeom.isRoughly(edge.FirstParameter, 0.0):
        lastParam = 1.0 - edge.FirstParameter

    e = Part.Edge(flipped, firstParam, lastParam)
    return e


def _flipEllipse(edge):
    """_flipEllipse(edge)
    Reverses direction of an ellipse by reversing the order of the vertexes.
    Note: This method converts the edge to a B-Spline during the process."""

    # Additional research needs to be done to reverse an elliptical edge without making projection of the original edge.
    """
    # ALTERNATE version. Used 'deflection' as argument.
    edges = []
    points = edge.discretize(Deflection=deflection)
    prev = points[0]
    for i in range(1, len(points)):
        now = points[i]
        edges.append(Part.makeLine(now, prev))
        prev = now
    edges.reverse()
    return edges
    """

    bbFace = PathGeom.makeBoundBoxFace(
        edge.BoundBox, 5.0, round(edge.BoundBox.ZMax + 10.0, 0)
    )
    proj = bbFace.makeParallelProjection(edge, FreeCAD.Vector(0.0, 0.0, 1.0))
    proj.translate(FreeCAD.Vector(0.0, 0.0, edge.BoundBox.ZMin - proj.BoundBox.ZMin))
    flipped = proj.Edges[0]
    return flipped.copy()


def _flipHyperbola(edge):
    """_flipHyperbola(edge)
    Reverses direction of a hyperbola by reversing the order of the vertexes.
    Note: This method converts the edge to a B-Spline during the process."""

    # Additional research needs to be done to reverse a hyperbolic edge without discretizing the original edge.
    """
    # ALTERNATE version. Used 'deflection' as argument.
    edges = []
    points = edge.discretize(Deflection=deflection)
    prev = points[0]
    for i in range(1, len(points)):
        now = points[i]
        edges.append(Part.makeLine(now, prev))
        prev = now
    edges.reverse()
    return edges
    """

    bbFace = PathGeom.makeBoundBoxFace(
        edge.BoundBox, 5.0, round(edge.BoundBox.ZMax + 10.0, 0)
    )
    proj = bbFace.makeParallelProjection(edge, FreeCAD.Vector(0.0, 0.0, 1.0))
    proj.translate(FreeCAD.Vector(0.0, 0.0, edge.BoundBox.ZMin - proj.BoundBox.ZMin))
    flipped = proj.Edges[0]
    return flipped.copy()


def _flipEdge(e):
    """_flipEdge(e)
    Returns a reversed-direction edge with same geometry, except for ellipses and hyperbolas.
    """
    if hasattr(e, "Curve"):
        typ = type(e.Curve)
    else:
        typ = type(e)
    # print(f"_flipEdge() type: {typ}")

    if typ == Part.Line:
        return _flipLine(e)
    elif typ == Part.LineSegment:
        return _flipLineSegment(e)
    elif typ == Part.Circle:
        return _flipCircle(e)
    elif typ in [Part.BSplineCurve, Part.BezierCurve]:
        return _flipBSplineBezier(e)
    elif typ == Part.OffsetCurve:
        return e.reversed()
    elif typ == Part.Ellipse:
        return _flipEllipse(e)
    elif typ == Part.Hyperbola:
        return _flipHyperbola(e)

    PathLog.warning(f"{typ} not supported for flipping")
    return None


def _orientEdges(inEdges):
    """_orientEdges(inEdges) ... internal worker function to orient edges so the last vertex of one edge connects to the first vertex of the next edge.
    Assumes the edges are in an order so they can be connected.
    Modified version of Path.Op.Util._orientEdges() to utilize _flipEdge() in this module.
    """
    PathLog.track()
    # orient all edges of the wire so each edge's last value connects to the next edge's first value
    e0 = inEdges[0]
    # well, even the very first edge could be misoriented, so let's try and connect it to the second
    if 1 < len(inEdges):
        last = e0.valueAt(e0.LastParameter)
        e1 = inEdges[1]
        if not PathGeom.pointsCoincide(
            last, e1.valueAt(e1.FirstParameter)
        ) and not PathGeom.pointsCoincide(last, e1.valueAt(e1.LastParameter)):
            # debugEdge("#  _orientEdges - flip first", e0)
            e0 = _flipEdge(e0)

    edges = [e0]
    last = e0.valueAt(e0.LastParameter)
    for e in inEdges[1:]:
        edge = (
            e
            if PathGeom.pointsCoincide(last, e.valueAt(e.FirstParameter))
            else _flipEdge(e)
        )
        edges.append(edge)
        last = edge.valueAt(edge.LastParameter)
    return edges


def _orientEdgesBasic(inEdges):
    """_orientEdges(inEdges) ... internal worker function to orient edges so the last vertex of one edge connects to the first vertex of the next edge.
    Assumes the edges are in an order so they can be connected.
    Modified version of Path.Op.Util._orientEdges(), removing initial flip of inEdges[0].
    """
    PathLog.track()
    # orient all edges of the wire so each edge's last value connects to the next edge's first value
    e0 = inEdges[0]
    edges = [e0]

    last = e0.valueAt(e0.LastParameter)
    for e in inEdges[1:]:
        edge = (
            e
            if PathGeom.pointsCoincide(last, e.valueAt(e.FirstParameter))
            # else PathGeom.flipEdge(e)
            else _flipEdge(e)
        )
        edges.append(edge)
        last = edge.valueAt(edge.LastParameter)
    return edges


def _wireMidpoint(wire):
    wireLength = wire.Length
    halfLength = wireLength / 2.0

    if len(wire.Edges) == 1:
        return valueAtEdgeLength(wire.Edges[0], halfLength)

    dist = 0.0
    for e in wire.Edges:
        eLen = e.Length
        newDist = dist + eLen
        if PathGeom.isRoughly(newDist, halfLength):
            return e.valueAt(e.LastParameter)
        elif newDist > halfLength:
            return valueAtEdgeLength(e, halfLength - dist)
        dist = newDist


def _wireQuartilePoint(wire):
    wireLength = wire.Length
    quartileLength = wireLength / 4.0

    if len(wire.Edges) == 1:
        return valueAtEdgeLength(wire.Edges[0], quartileLength)

    dist = 0.0
    for e in wire.Edges:
        eLen = e.Length
        newDist = dist + eLen
        if PathGeom.isRoughly(newDist, quartileLength):
            return e.valueAt(e.LastParameter)
        elif newDist > quartileLength:
            return valueAtEdgeLength(e, quartileLength - dist)
        dist = newDist


def _pointToText(p, digits=4):
    """vertexToText(p) Return text reference string from point or vector object."""
    x = round(p.x, digits)
    y = round(p.y, digits)
    z = round(p.z, digits)
    txt = f"{z},{y},{x},"
    return txt.replace("-0.0,", "0.0,")


def _pointToTextAlt(p, digits=4):
    """vertexToText(p) Return text reference string from point or vector object."""
    x = round(p.x, digits)
    y = round(p.y, digits)
    z = round(p.z, digits)
    txt = f"z{z}y{y}x{x}"
    return txt.replace("-0.0,", "0.0,")


def _makeEdgeMidpointTups(edges, precision=4):
    tups = []
    for ei in range(0, len(edges)):
        e = edges[ei]
        # eLen = e.Length / 2.0
        txt = f"L{round(e.Length, precision)}_" + _pointToText(
            valueAtEdgeLength(e, e.Length / 2.0), precision
        )
        tups.append((txt, ei, e))
    # Sort tups by xyz_length text, so same edges find each other
    tups.sort(key=lambda t: t[0])
    return tups


def _isWireClockwise(w):
    """_isWireClockwise(w) ... return True if wire is oriented clockwise.
    Assumes the edges of w are already properly oriented - for generic access use isWireClockwise(w).
    Copied from Path.Op.Util module."""
    # handle wires consisting of a single circle or 2 edges where one is an arc.
    # in both cases, because the edges are expected to be oriented correctly, the orientation can be
    # determined by looking at (one of) the circle curves.
    if 2 >= len(w.Edges) and Part.Circle == type(w.Edges[0].Curve):
        return 0 > w.Edges[0].Curve.Axis.z
    if 2 == len(w.Edges) and Part.Circle == type(w.Edges[1].Curve):
        return 0 > w.Edges[1].Curve.Axis.z

    # for all other wires we presume they are polygonial and refer to Gauss
    # https://en.wikipedia.org/wiki/Shoelace_formula
    area = 0
    for e in w.Edges:
        v0 = e.valueAt(e.FirstParameter)
        v1 = e.valueAt(e.LastParameter)
        area = area + (v0.x * v1.y - v1.x * v0.y)
    PathLog.track(area)
    return area < 0


# Public functions
def flipEdge(e):
    """flipEdge(e) Public proxy for _flipEdge() function to return flipped version of edge provided.
    Copied from Path.Geom module, but references _flipEdge() in this module, rather than Path.Geom.
    """
    return _flipEdge(e)


def flipWire(wire):
    """flipWire(wire) Returns a reversed-direction wire.
    Copied with slight modification from Path.Geom module."""
    edges = [_flipEdge(e) for e in wire.Edges]
    edges.reverse()
    PathLog.debug(edges)
    return Part.Wire(Part.__sortEdges__(edges))


def isWireClockwise(w):
    """isWireClockwise(w) ... returns True if the wire winds clockwise.
    Modified version of Path.Op.Util.isWireClockwise(), utilizing _orientEdges() in this module.
    """
    return _isWireClockwise(Part.Wire(_orientEdges(w.Edges)))


def orientWire(w, forward=True):
    """orientWire(w, forward=True) ... orients given wire in a specific direction.
    If forward = True (the default) the wire is oriented clockwise, looking down the negative Z axis.
    If forward = False the wire is oriented counter clockwise.
    If forward = None the orientation is determined by the order in which the edges appear in the wire.
    Modified version of Path.Op.Util.orientWire(), utilizing _orientEdges() and flipWire() in this module.
    """
    PathLog.debug("orienting forward: {}: {} edges".format(forward, len(w.Edges)))
    wire = Part.Wire(_orientEdges(w.Edges))
    if forward is not None:
        if forward != _isWireClockwise(wire):
            PathLog.track("orientWire - needs flipping")
            # return PathGeom.flipWire(wire)
            return flipWire(wire)
        PathLog.track("orientWire - ok")
    return wire


def orientWireBasic(w, forward=True):
    """orientWire(w, forward=True) ... orients given wire in a specific direction.
    If forward = True (the default) the wire is oriented clockwise, looking down the negative Z axis.
    If forward = False the wire is oriented counter clockwise.
    If forward = None the orientation is determined by the order in which the edges appear in the wire.
    Modified version of Path.Op.Util.orientWire(), utilizing _orientEdges() and flipWire() in this module.
    """
    PathLog.debug("orienting forward: {}: {} edges".format(forward, len(w.Edges)))
    wire = Part.Wire(_orientEdgesBasic(w.Edges))
    if forward is not None:
        if forward != _isWireClockwise(wire):
            PathLog.track("orientWire - needs flipping")
            # return PathGeom.flipWire(wire)
            return flipWire(wire)
        PathLog.track("orientWire - ok")
    return wire


def valueAtMidpoint(edge):
    """valueAtMidpoint(edge)
    Returns the midpoint of the edge."""

    return valueAtEdgeLength(edge, edge.Length / 2.0)


def valueAtEdgeLength(edge, length):
    """valueAtEdgeLength(edge, length)
    Returns the point along the given edge at the given length."""

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
    elif typeId == "Part::GeomLine":
        return edge.valueAt(edge.FirstParameter + length)
    elif typeId in [
        "Part::GeomCircle",
        "Part::GeomEllipse",
        "Part::GeomParabola",
        "Part::GeomHyperbola",
    ]:
        return edge.valueAt(
            edge.FirstParameter
            + length / edgeLen * (edge.LastParameter - edge.FirstParameter)
        )
    else:
        PathLog.warning(
            f"valueAtEdgeLength() edge.Curve.TypeId, {typeId}, is not available."
        )
        return None


def valueAtPercentEdgeLength(edge, percent=0.5):
    """valueAtEdgeLength(edge, percent=0.5)
    Returns the point along the given edge at the given percent of overall edge length.
    """

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
        return edge.valueAt(percent * edgeLen)
    elif typeId == "Part::GeomLine":
        return edge.valueAt(edge.FirstParameter + (percent * edgeLen))
    elif typeId in [
        "Part::GeomCircle",
        "Part::GeomEllipse",
        "Part::GeomParabola",
        "Part::GeomHyperbola",
    ]:
        return edge.valueAt(
            edge.FirstParameter + percent * (edge.LastParameter - edge.FirstParameter)
        )
    else:
        PathLog.warning(
            f"valueAtEdgeLength() edge.Curve.TypeId, {typeId}, is not available."
        )
        return None


def fuseShapes(shapes, tolerance=0.00001):
    if len(shapes) == 0:
        return None
    if len(shapes) == 1:
        return shapes[0]
    f = shapes[0].copy()
    for fc in shapes[1:]:
        fused = f.generalFuse(fc, tolerance)
        f = fused[0]
    return f


def getAngle(pnt, centerOfPattern):
    p = pnt.sub(centerOfPattern)
    angle = math.degrees(math.atan2(p.y, p.x))
    if angle < 0.0:
        angle += 360.0
    return angle


def isOrientedTheSame(directionVector, wire):
    v1 = wire.Edges[0].Vertexes[0].Point
    v2 = wire.Edges[-1].Vertexes[-1].Point
    p1 = FreeCAD.Vector(v1.x, v1.y, 0.0)
    p2 = FreeCAD.Vector(v2.x, v2.y, 0.0)
    drctn = p2.sub(p1).normalize()
    if PathGeom.isRoughly(directionVector.x, drctn.x) and PathGeom.isRoughly(
        directionVector.y, drctn.y
    ):
        return True
    return False


def isEdgeSame(e1, e2, orientation=True, tolerance=0.000001):
    """isEdgeSame(e1, e2, orientation=True, tolerance=0.000001)
    Returns True if edge1 and edge2 are the same type, length, position and orientation.
    """

    # Check edge types
    if e1.Curve.TypeId != e2.Curve.TypeId:
        return False
    # Check edge lengths
    if not PathGeom.isRoughly(e1.Length, e2.Length, tolerance):
        return False
    # Check vertex count
    if len(e1.Vertexes) != len(e2.Vertexes):
        return False
    # Check position
    if len(e1.Vertexes) == 1:
        if not PathGeom.isRoughly(
            e1.Vertexes[0].Point.sub(e2.Vertexes[0].Point).Length, 0.0, tolerance
        ):
            return False
    else:
        if orientation:
            if not PathGeom.isRoughly(
                e1.Vertexes[0].Point.sub(e2.Vertexes[0].Point).Length, 0.0, tolerance
            ):
                return False
            if not PathGeom.isRoughly(
                e1.Vertexes[1].Point.sub(e2.Vertexes[1].Point).Length, 0.0, tolerance
            ):
                return False
        else:
            e1a = e1.Vertexes[0].Point
            e2a = e2.Vertexes[0].Point
            e1b = e1.Vertexes[1].Point
            e2b = e2.Vertexes[1].Point
            if not PathGeom.isRoughly(
                e1a.sub(e2a).Length, 0.0, tolerance
            ) and not PathGeom.isRoughly(e1a.sub(e2b).Length, 0.0, tolerance):
                return False
            if not PathGeom.isRoughly(
                e1b.sub(e2a).Length, 0.0, tolerance
            ) and not PathGeom.isRoughly(e1b.sub(e2b).Length, 0.0, tolerance):
                return False

    return True


def isArcClockwise(wire, centerOfPattern):
    """isArcClockwise(wire) Return True if arc is oriented clockwise.
    Incomming wire is assumed to be an arc shape (single arc edge, or discretized version).
    """
    if wire.isClosed():
        # This method is not reliable for open wires
        p1 = wire.Edges[0].valueAt(wire.Edges[0].FirstParameter)
        p2 = _wireQuartilePoint(wire)

        a1 = getAngle(p1, centerOfPattern)
        if PathGeom.isRoughly(a1, 360.0):
            a1 = 0.0
        a2 = getAngle(p2, centerOfPattern) - a1
        if a2 < 0.0:
            a2 += 360.0

        if PathGeom.isRoughly(a2, 90.0):
            return True

        return False

    p1 = wire.Edges[0].valueAt(wire.Edges[0].FirstParameter)
    p2 = _wireQuartilePoint(wire)  # _wireMidpoint(wire)
    p3 = wire.Edges[-1].valueAt(wire.Edges[-1].LastParameter)

    a1 = getAngle(p1, centerOfPattern)
    if PathGeom.isRoughly(a1, 360.0):
        a1 = 0.0
    a2 = getAngle(p2, centerOfPattern)
    a3 = getAngle(p3, centerOfPattern)

    a2 -= a1
    if a2 < 0.0:
        a2 += 360.0
    a3 -= a1
    if a3 < 0.0:
        a3 += 360.0

    if a3 > a2 and a2 > 0.0:
        return False

    if a3 < a2 and a2 < 360.0:
        return True

    FreeCAD.Console.PrintError(
        f"ERROR isArcClockwise() a1: {round(a1, 2)},  a2: {round(a2, 2)},  a3: {round(a3, 2)}\n"
    )

    return None


def uniqueEdges(edges, precision=4):
    """uniqueEdges(edges)
    Return edges that only touch a single face - removing edges that are shared between multiple faces.
    """
    # Filter out all edges touching multiple faces, leaving edges that are truly unique

    tups = _makeEdgeMidpointTups(edges, precision)
    if len(tups) == 0:
        return tups

    # Remove duplicates
    unique = [tups[0]]
    uCnt = 1
    for t in tups[1:]:
        removeLast = False
        if uCnt > 0:
            if t[0] == unique[-1][0]:
                removeLast = True
            else:
                unique.append(t)
                uCnt += 1

            if removeLast:
                __ = unique.pop()
                uCnt -= 1
        else:
            unique.append(t)
            uCnt += 1

    return [u[2] for u in unique]


def removeUnconnectedEdges(edges):
    data = {}
    ei = 0
    for e in edges:
        for v in e.Vertexes:
            t = _pointToTextAlt(v.Point)
            if t in data.keys():
                data[t].append(ei)
            else:
                data[t] = [ei]
        ei += 1
    remove = []
    for k, v in data.items():
        print(f"{k}.{v}")
        if len(v) == 1:
            remove.append(v[0])
    remove.sort(reverse=True)
    rmv = []
    for r in remove:
        if r not in rmv:
            rmv.append(r)
    edgs = [e.copy() for e in edges]
    print(f"remove edge idxs: {rmv};  len(edgs): {len(edgs)}")
    for r in rmv:
        edgs.pop(r)
    return edgs


def getPlaneFaceFromEdge(edge):
    if edge.Curve.TypeId == "Part::GeomLine":
        FreeCAD.Console.PrintError(
            "getPlaneFaceFromEdge() edge is a LINE. Cannot create plane face.\n"
        )
        return None

    # ERROR will occur with complete circle

    p1 = edge.Vertexes[0].Point
    mp = valueAtMidpoint(edge)
    p2 = edge.Vertexes[1].Point
    return Part.Face(
        Part.Wire([Part.makeLine(p1, mp), Part.makeLine(mp, p2), Part.makeLine(p2, p1)])
    )


def horizontalCenterChordLine(e):
    if not isinstance(e, Part.Edge):
        return None

    if e.Curve.TypeId != "Part::GeomCircle":
        return None

    c = e.Curve.Center
    p0 = valueAtPercentEdgeLength(e, 0.01)
    p1 = valueAtPercentEdgeLength(e, 0.33)
    p2 = valueAtPercentEdgeLength(e, 0.66)

    diffs = [(abs(c.z - p0.z), p0), (abs(c.z - p1.z), p1), (abs(c.z - p2.z), p2)]
    diffs.sort(key=lambda t: t[0])
    p = diffs[0][1]
    # print(f"c: {c};  p: {p}")
    v1 = e.Curve.Center.sub(FreeCAD.Vector(p.x, p.y, c.z))
    v1.normalize()
    v1.multiply(e.Curve.Radius)
    v2 = e.Curve.Center.sub(FreeCAD.Vector(p.x, p.y, c.z))
    v2.normalize()
    v2.multiply(-1.0 * e.Curve.Radius)
    ln = Part.makeLine(v1, v2)
    ln.translate(FreeCAD.Vector(e.Curve.Center.x, e.Curve.Center.y, 0.0))
    # Part.show(ln, "CircleDiameter")
    return ln


def refineWireEdges(edges):
    """refineWireEdges(w)
    Return wire with consecutive colinear line segments combined into a single, long segment.
    """

    if len(edges) == 0:
        return None
    if len(edges) == 1:
        return edges

    orientedEdges = _orientEdgesBasic(edges)
    idxEnd = 1
    idxStart = 0
    # Swap index values based on orientation of orientedEdges
    if not PathGeom.isRoughly(
        orientedEdges[0]
        .Vertexes[idxEnd]
        .Point.sub(orientedEdges[1].Vertexes[idxStart].Point)
        .Length,
        0.0,
    ):
        idxEnd = 0
        idxStart = 1

    p = orientedEdges.pop(0)
    grp = [p]
    lstDir = p.Vertexes[idxEnd].Point.sub(p.Vertexes[idxStart].Point).normalize()
    for o in orientedEdges:
        curDir = o.Vertexes[idxEnd].Point.sub(o.Vertexes[idxStart].Point).normalize()
        if len(grp) > 0:
            if PathGeom.isRoughly(curDir.sub(lstDir).Length, 0.0):
                # direction of last edge and current edge are within tolerance,
                # so extend previous line to end of current
                p1 = grp.pop().Vertexes[idxStart].Point
                p2 = o.Vertexes[idxEnd].Point
                if not PathGeom.isRoughly(p1.sub(p2).Length, 0.0):
                    grp.append(Part.makeLine(p1, p2))
            else:
                grp.append(o.copy())
                lstDir = curDir
    # Efor
    return grp
