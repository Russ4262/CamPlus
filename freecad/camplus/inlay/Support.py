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
import Path.Geom as PathGeom
import math
import freecad.camplus.utilities.Edge as EdgeUtils

DEBUG = False
DEBUG_SHP = False
DEBUG_ALL = True


# Face creation and support functions
def _vector_to_degrees(vector):
    ang = round(math.degrees(math.atan2(vector.y, vector.x)), 6)
    if ang < 0.0:
        ang += 360.0
    return ang


def _normalizeDegrees(a):
    if a >= 360.0:
        a -= 360.0
    elif a < 0.0:
        a += 360.0
    return a


def _makeProjection(face):
    bfbb = face.BoundBox
    targetFace = PathGeom.makeBoundBoxFace(
        bfbb, offset=5.0, zHeight=math.floor(bfbb.ZMin - 5.0)
    )

    direction = FreeCAD.Vector(0.0, 0.0, -1.0)
    #      receiver_face.makeParallelProjection(project_shape, direction)
    proj = targetFace.makeParallelProjection(face.Wires[0], direction)
    proj.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - proj.BoundBox.ZMin))
    return proj


def _discretizeEdgeList(edgeList, discretizeValue, force=False):
    """Return Part.Wire object only consisting of lines and arcs."""
    if len(edgeList) == 1 and not force:
        # Likely a circle
        return Part.Wire(edgeList[0].copy())

    edges = []
    for e in edgeList:
        if e.Curve.TypeId == "Part::GeomCircle":
            edges.append(e.copy())
        elif e.Curve.TypeId == "Part::GeomLine":
            edges.append(e.copy())
        else:
            # print("Discretizing '{}' edge".format(e.Curve.TypeId))
            # pnts = e.discretize(Distance=discretizeValue)
            pnts = e.discretize(Deflection=discretizeValue)
            for i in range(0, len(pnts) - 1):
                edges.append(Part.makeLine(pnts[i], pnts[i + 1]))
    return EdgeUtils.orientWire(Part.Wire(Part.__sortEdges__(edges)))


def _getLowConnectPoint(face, topPoint, error=0.0001):
    for e in face.Edges:
        # Part.show(e, "FEdge")
        if len(e.Vertexes) > 1:
            # Look for non-horizontal edges
            if not PathGeom.isRoughly(e.Vertexes[0].Z, e.Vertexes[1].Z):
                # Part.show(e, "FEdge")
                # Find topPoint on edge
                if PathGeom.isRoughly(
                    e.Vertexes[0].Point.sub(topPoint).Length, 0.0, error
                ):
                    return e.Vertexes[1].Point
                if PathGeom.isRoughly(
                    e.Vertexes[1].Point.sub(topPoint).Length, 0.0, error
                ):
                    return e.Vertexes[0].Point
                # print(f".. {e.Vertexes[0].Point} .. {e.Vertexes[1].Point}")
                # print(
                #    f".. {e.Vertexes[0].Point.sub(topPoint).Length} .. {e.Vertexes[1].Point.sub(topPoint).Length}"
                # )
        else:
            # return e.Vertexes[0].Point
            pass
    return None


def _isCommon(canvas, testFace, isInside):
    proj = _makeProjection(testFace)
    region = Part.Face(Part.Wire(proj.Edges))
    regionArea = region.Area
    # This 0.25 common percentage may need adjustment
    if isInside:
        if canvas.common(region).Area > regionArea * 0.25:
            return True
        return False
    else:
        if canvas.common(region).Area > regionArea * 0.25:
            return False
        return True


def _visualizeEndAngle(e, angle):
    p0 = e.Vertexes[1].Point
    x = math.cos(math.radians(angle))
    y = math.sin(math.radians(angle))
    move = FreeCAD.Vector(p0.x, p0.y, 0.0)
    p = FreeCAD.Vector(x, y, p0.z)
    p.multiply(10.0)
    p1 = p.add(move)
    seg = Part.Edge(Part.LineSegment(p0, p1))
    Part.show(seg, "EndAngle")


def _visualizeStartAngle(e, angle):
    p0 = e.Vertexes[0].Point
    x = math.cos(math.radians(angle))
    y = math.sin(math.radians(angle))
    move = FreeCAD.Vector(p0.x, p0.y, 0.0)
    p = FreeCAD.Vector(x, y, p0.z)
    p.multiply(10.0)
    p1 = p.add(move)
    seg = Part.Edge(Part.LineSegment(p0, p1))
    Part.show(seg, "StartAngle")
