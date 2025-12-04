# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2024 Russell Johnson (russ4262) <russ4262@gmail.com>    *
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
import Sketcher

if FreeCAD.GuiUp:
    import FreeCADGui

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate


def _getPathBoundBox(obj):
    """_getPathBoundBox(obj)
    Returns the BoundBox of a wire object representing all move non-rapid
    commands found in the given path.
    This function is a modified derivative of Path.Geom.wireForPath()."""
    edges = []
    rapid = []
    startPoint = FreeCAD.Vector(0, 0, 0)
    path = PathUtils.getPathWithPlacement(obj)

    if hasattr(path, "Commands"):
        for cmd in path.Commands:
            edge = Path.Geom.edgeForCmd(cmd, startPoint)
            if edge:
                if cmd.Name in Path.Geom.CmdMoveRapid:
                    rapid.append(edge)
                else:
                    edges.append(edge)
                startPoint = Path.Geom.commandEndPoint(cmd, startPoint)

    if not edges:
        return None

    return Part.makeCompound(edges).BoundBox


def _sketchAddCircle(sketch, center, radius):
    # center = FreeCAD.Vector(0.0, 0.0, 0.0)
    # radius = 25.0
    if radius <= 0.0:
        return

    # lastGeoId = len(sketch.Geometry)
    geoList = []
    geoList.append(Part.Circle(center, FreeCAD.Vector(0.0, 0.0, 1.0), radius))
    sketch.addGeometry(geoList, False)
    # constraintList = []
    # sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 3, -1, 1))


def _addBody(baseFeature=None, name="BoundaryBody"):
    """Create(baseFeature=None, name="BoundaryBody") ... Creates a Boundary Shape for a Boundary Dressup."""

    doc = FreeCAD.ActiveDocument
    body = doc.addObject("PartDesign::Body", name)
    body.Label = "BoundaryBody"
    if baseFeature:
        body.BaseFeature = baseFeature
    # body.recompute()
    if FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", body)
    return body


def _addSketch(body):
    if FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", body)
    # Create a Sketch within the Body object
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    # sketch.AttachmentSupport = (doc.getObject('XY_Plane001'),[''])
    sketch.AttachmentSupport = [(body.Origin.OriginFeatures[3], [""])]
    sketch.MapMode = "FlatFace"
    if FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", None)
    return sketch


def _padSketch(sketch, padValue):
    body = None
    for o in sketch.InList:
        if o.Name.startswith("BoundaryBody"):
            body = o
            break
    if body is None:
        FreeCAD.Console.PrintMessage("No Body object identified for Pad.\n")
        return None

    #  Pad the Sketch
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sketch
    pad.Length = padValue
    pad.TaperAngle = 0.0
    pad.UseCustomVector = 0
    pad.Direction = (0, 0, 1)
    pad.ReferenceAxis = (sketch, ["N_Axis"])
    pad.AlongSketchNormal = 1
    pad.Type = 0
    pad.UpToFace = None
    pad.Reversed = 0
    pad.Midplane = 0
    pad.Offset = 0
    # doc.recompute()
    # Gui.getDocument('trash_3').resetEdit()
    sketch.Visibility = False

    return pad


def createForDressup(obj, base=None):
    body = _addBody(base)
    sketch = _addSketch(body)
    center = FreeCAD.Vector(0.0, 0.0, 0.0)
    radius = 25.0
    _sketchAddCircle(sketch, center, radius)
    padValue = 50.0
    pad = _padSketch(sketch, padValue)

    sBB = _getPathBoundBox(obj.Base)
    body.Placement.Base = FreeCAD.Vector(0.0, 0.0, sBB.ZMin)
    mode = 0  # 0=Absolute, 1=Relative
    # Constrain diameter of circle to diagonal of obj.Path boundbox
    diameter = round(sBB.DiagonalLength + 1.0, 0)
    body.Group[0].addConstraint(Sketcher.Constraint("Diameter", 0, diameter))
    # Move circle center to center of obj.Path boundbox
    pathCenter = FreeCAD.Vector(
        sBB.XMin + sBB.XLength / 2.0, sBB.YMin + sBB.YLength / 2.0, 0
    )
    body.Group[0].movePoint(0, 3, pathCenter, mode)

    if FreeCAD.GuiUp:
        body.ViewObject.Visibility = False

    return body


def Create(base=None):
    body = _addBody(base)
    sketch = _addSketch(body)
    center = FreeCAD.Vector(0.0, 0.0, 0.0)
    radius = 25.0
    _sketchAddCircle(sketch, center, radius)
    padValue = 50.0
    pad = _padSketch(sketch, padValue)

    if FreeCAD.GuiUp:
        body.ViewObject.Visibility = False
    return body


FreeCAD.Console.PrintMessage("Imported BoundaryBody module\n")
