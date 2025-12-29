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
from freecad.camplus.utilities.Edge import valueAtEdgeLength
from freecad.camplus.utilities.Edge import isWireClockwise
from freecad.camplus.utilities.Edge import PathGeom
from freecad.camplus.utilities.Edge import _pointToText
import Part
import Path.Log as PathLog

# from freecad.camplus.utilities.Edge import Part

# import Path.Geom as PathGeom


__title__ = "Wire Utilities"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Various functions to work with wires."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""
__date__ = ""


IS_MACRO = False  # False  # Set to True to use as macro
DEBUG_SHAPES = False

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())

translate = FreeCAD.Qt.translate


# Support functions
def _makeEdgeRefTups(edges):
    tups = []
    # Use all vertexes
    for ei in range(len(edges)):
        e = edges[ei]
        for vi in range(len(e.Vertexes)):
            v = e.Vertexes[vi]
            txt = _pointToText(v.Point)
            tups.append((txt, ei, vi, e))
    tups.sort(key=lambda t: t[0])
    return tups


def _popNodeTups(tups, nodePoint):
    send = []
    keep = []
    txt = _pointToText(nodePoint)
    # print(f"_popNodeTups({txt})")
    found = False
    for _ in range(len(tups)):
        t = tups.pop()
        if t[0] == txt:
            send.append(t)
            found = True
        else:
            keep.append(t)
            if found:
                break
    keep.sort(key=lambda t: t[0])
    tups.extend(keep)

    # Remove partner edge reference tuples
    # partners = []
    sendIndexes = [t[1] for t in send]
    # print(f"sending indexes: {sendIndexes}")
    remove = [i for i in range(len(tups)) if tups[i][1] in sendIndexes]
    remove.sort(reverse=True)
    # for ri in remove:
    #    partners.append(tups.pop(ri))

    return send  # , partners


def _showSegment(p1, p2, name):
    if DEBUG_SHAPES:
        Part.show(Part.makeLine(p1, p2), name)


def _getDegreesBetween(vertex, base, target, clockwise=True):
    """_getDegreesBetween(vertex, base, target)
    Returns
    Arguments:
        vertex: vertex point of angle formed
        base: point from vertex to form BASE segment to be measured from
        target: point from vertex to form TARGET segment to be measured to
           t
          .
         .   return this angle in degrees, 0.0 - 360.0
        v..........b
    """
    degrees = PathGeom.math.degrees(base.sub(vertex).getAngle(target.sub(vertex)))
    if degrees < 180.0:
        w = Part.Wire(
            [
                Part.makeLine(base, target),
                Part.makeLine(target, vertex),
                Part.makeLine(vertex, base),
            ]
        )
        if clockwise:
            if isWireClockwise(w):
                degrees += 180.0
        else:
            if not isWireClockwise(w):
                degrees += 180.0
    return degrees


def _getSeedTup(tups):
    """_getSeedTup(tups)
    Expects to find two tuples that have the same edge index (second tuple item)."""
    seed = tups.pop(0)
    i = 0
    for t in tups:
        if t[1] == seed[1]:
            break
        i += 1
    tups.pop(i)
    return seed


def _findNextTuple(tup, tuples, clockwise=True):
    nodeIndex = 1 if tup[2] == 0 else 0
    nodeEdge = tup[3]
    nodePoint = nodeEdge.Vertexes[nodeIndex].Point
    refPoint = (
        valueAtEdgeLength(nodeEdge, nodeEdge.Length * 0.9)
        if tup[2] == 0
        else valueAtEdgeLength(nodeEdge, nodeEdge.Length * 0.1)
    )
    # _showSegment(nodePoint, refPoint, f"Base{tup[1]+1}_")

    candidates = []
    for t in _popNodeTups(tuples, nodePoint):
        if t[1] != tup[1]:
            candidates.append(
                (
                    _getDegreesBetween(
                        nodePoint,
                        refPoint,
                        (
                            valueAtEdgeLength(t[3], t[3].Length * 0.1)
                            if t[2] == 0
                            else valueAtEdgeLength(t[3], t[3].Length * 0.9)
                        ),
                        clockwise,
                    ),
                    t,
                )
            )

    if len(candidates) == 0:
        return None

    candidates.sort(key=lambda t: t[0])
    return candidates.pop()[1]


# Public functions
def findOuterWire(edges, showError=False, alternate=False):
    """findOuterWire(edges)
    All edges should be coplanar.  Returns outer wire, if available."""

    edgeCnt = len(edges)
    clockwise = True if alternate else False
    tups = _makeEdgeRefTups(edges)
    seedTup = _getSeedTup(tups)
    seedPoint = seedTup[3].Vertexes[seedTup[2]].Point
    profileEdges = [seedTup[3].copy()]
    nodeIndex = 1 if seedTup[2] == 0 else 0
    nodePoint = seedTup[3].Vertexes[nodeIndex].Point
    Part.show(profileEdges[-1], "pEdge")

    while not PathGeom.isRoughly(nodePoint.sub(seedPoint).Length, 0.0) and edgeCnt > 0:
        nextTup = _findNextTuple(seedTup, tups, clockwise)
        if nextTup is None:
            FreeCAD.Console.PrintMessage("No refTups candidates.\n")
            break
        nodeIndex = 1 if nextTup[2] == 0 else 0
        nodePoint = nextTup[3].Vertexes[nodeIndex].Point
        profileEdges.append(nextTup[3].copy())
        # Part.show(profileEdges[-1], "pEdge")
        seedTup = nextTup
        edgeCnt -= 1

    w = Part.Wire(profileEdges)
    if w.isClosed():
        return w
    if showError:
        FreeCAD.Console.PrintWarning("Wire.findOuterWire() failed.\n")
        Part.show(w, "OuterWireFail")
    FreeCAD.Console.PrintMessage(
        "Wire.findOuterWire() attempting alternate direction.\n"
    )
    if alternate:
        return None

    return findOuterWire(edges, showError, True)


print("Imported Wire Utilities")
