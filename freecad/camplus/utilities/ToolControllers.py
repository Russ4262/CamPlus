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
import Path
import Part
import PathScripts.PathUtils as PathUtils
import Path.Base.Util as PathUtil
import Path.Geom as PathGeom
from PySide.QtCore import QT_TRANSLATE_NOOP

__title__ = "Clearing Operation"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Creates a clearing operation."
__usage__ = "Import this module.  Run the 'Create()' function."
__url__ = ""
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate
isDebug = True if Path.Log.getLevel(Path.Log.thisModule()) == 4 else False
showDebugShapes = False


# Support functions
class PathNoTCException(Exception):
    """PathNoTCException is raised when no TC was selected or matches the input
    criteria. This can happen intentionally by the user when they cancel the TC
    selection dialog."""

    def __init__(self):
        super().__init__("No Tool Controller found")


def toolControllerProperties():
    return [
        (
            "App::PropertyLink",
            "ToolController",
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The tool controller that will be used to calculate the path",
            ),
        ),
        (
            "App::PropertyDistance",
            "OpToolDiameter",
            "Op Values",
            QT_TRANSLATE_NOOP("App::Property", "Holds the diameter of the tool"),
        ),
    ]


def setDefaultToolController(job, obj, proxy):
    tc = None
    opCnt = len(job.Operations.Group)
    if opCnt > 1:
        # Check
        idx = 0
        while opCnt > 0:
            opCnt -= 1
            idx -= 1
            tc = PathUtil.toolControllerForOp(job.Operations.Group[idx])
            if tc:
                break
    if not tc:
        tc = PathUtils.findToolController(obj, proxy)
    if not tc:
        raise PathNoTCException()
    obj.ToolController = tc
    obj.OpToolDiameter = obj.ToolController.Tool.Diameter
    return tc


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


def getShankBottomHeight(tool):
    # Exclude horizontal faces
    faces = [f.copy() for f in tool.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    # Sort highest to lowest
    faces.sort(key=lambda f: f.BoundBox.ZMax, reverse=True)
    # Identify first cylinder with tool diameter
    for f in faces:
        if PathGeom.isRoughly(f.Edges[0].Curve.Radius, tool.ShankDiameter.Value / 2.0):
            return f.BoundBox.ZMin
    FreeCAD.Console.PrintError("getShankBottomHeight() Failed")
    Part.show(tool.Shape.copy(), "FailedToolShape")
    return None


def getHalfTool(tc, keepShank=True):
    toolShape = tc.Tool.Shape
    bbf = PathGeom.makeBoundBoxFace(toolShape.BoundBox, 2.0)
    bbf.translate(FreeCAD.Vector(0.0 - bbf.BoundBox.XMin, 0.0, -1.0))
    ext = bbf.extrude(FreeCAD.Vector(0.0, 0.0, toolShape.BoundBox.ZLength + 2.0))

    if keepShank:
        return toolShape.cut(ext).removeSplitter()

    half = toolShape.cut(ext)
    shankBottom = getShankBottomHeight(tc.Tool)
    bbf2 = PathGeom.makeBoundBoxFace(toolShape.BoundBox, 2.0, shankBottom)
    ext2 = bbf2.extrude(
        FreeCAD.Vector(0.0, 0.0, round(toolShape.BoundBox.ZLength + 2.0, 0))
    )
    return half.cut(ext2).removeSplitter()


def getToolHalfAndProfile(tc, keepShank=True):
    half = getHalfTool(tc, keepShank)

    for f in half.Faces:
        if PathGeom.isRoughly(f.BoundBox.XMin, 0.0):
            return (half, f.copy())

    FreeCAD.Console.PrintError("getToolHalfAndProfile() No tool profile identified.\n")

    return None, None


def getToolHalfProfileOthers(tc, keepShank=True):
    half = getHalfTool(tc, keepShank)
    others = []
    profile = None
    for f in half.Faces:
        if PathGeom.isRoughly(f.BoundBox.XMin, 0.0):
            profile = f.copy()
        else:
            others.append(f.copy())

    return half, profile, others
