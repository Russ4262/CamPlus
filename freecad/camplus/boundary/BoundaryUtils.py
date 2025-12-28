# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2025 Russell Johnson <russ4262> russ4262@gmail.com      *
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

__title__ = "Boundary Utils Macro"
__author__ = "Russell Johnson <russ4262>"
__doc__ = "Macro to create a boundary dressup with a Body object as the 'Stock' property and boundary shape."
__date__ = "2025-12-22"
__version__ = "1.0"

import FreeCAD as App
import Part
import Sketcher
from PySide.QtCore import QT_TRANSLATE_NOOP


IS_MACRO = False  # Set to True if using file as FreeCAD Macro.
GUI_ACTIVE = False

if App.GuiUp:
    import FreeCADGui as Gui

    GUI_ACTIVE = True


def _addBody(doc):
    body = doc.addObject("PartDesign::Body", "Body")
    body.AllowCompound = True

    if GUI_ACTIVE:
        Gui.ActiveDocument.ActiveView.setActiveObject("pdbody", body)
        Gui.Selection.clearSelection()
        body.ViewObject.ShapeAppearance = App.Material(
            DiffuseColor=4289331455,
            AmbientColor=1431655935,
            SpecularColor=0,
            EmissiveColor=0,
            Shininess=0.9,
            Transparency=0.50,
        )
        body.ViewObject.update()
    return body


def _addSketchToBody(body):
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    sketch.AttachmentSupport = (body.Origin, ["XY_Plane"])
    sketch.MapMode = "FlatFace"
    return sketch


def _addSquareToSketch(sketch, sideLength):
    # Add four line segments, two vertical and two horizontal, for sides of square
    geoList = []
    geoList.append(
        Part.LineSegment(
            App.Vector(-sideLength, sideLength, 0.0),
            App.Vector(-sideLength, -sideLength, 0.0),
        )
    )
    geoList.append(
        Part.LineSegment(
            App.Vector(-sideLength, -sideLength, 0.0),
            App.Vector(sideLength, -sideLength, 0.0),
        )
    )
    geoList.append(
        Part.LineSegment(
            App.Vector(sideLength, -sideLength, 0.0),
            App.Vector(sideLength, sideLength, 0.0),
        )
    )
    geoList.append(
        Part.LineSegment(
            App.Vector(sideLength, sideLength, 0.0),
            App.Vector(-sideLength, sideLength, 0.0),
        )
    )
    sketch.addGeometry(geoList, False)
    del geoList

    # Use constraints to:
    constraintList = []
    ##   connect end points of each side to make closed four-sided polygon.
    constraintList.append(Sketcher.Constraint("Coincident", 0, 2, 1, 1))
    constraintList.append(Sketcher.Constraint("Coincident", 1, 2, 2, 1))
    constraintList.append(Sketcher.Constraint("Coincident", 2, 2, 3, 1))
    constraintList.append(Sketcher.Constraint("Coincident", 3, 2, 0, 1))
    ##   set left and right sides to vertical
    constraintList.append(Sketcher.Constraint("Vertical", 0))
    constraintList.append(Sketcher.Constraint("Vertical", 2))
    ##   set top and bottom sides to horizontal
    constraintList.append(Sketcher.Constraint("Horizontal", 1))
    constraintList.append(Sketcher.Constraint("Horizontal", 3))
    sketch.addConstraint(constraintList)
    del constraintList

    # Add constraint to make rectangle a square by setting two adjacent sides equal in length.
    sketch.addConstraint(Sketcher.Constraint("Equal", 3, 0))

    # Lock upper left corner to (-100, 100)
    sketch.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, -sideLength))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", 0, 1, sideLength))

    # Set distance of bottom side of square to 200 mm
    sketch.addConstraint(Sketcher.Constraint("DistanceX", 1, 1, 1, 2, 2.0 * sideLength))
    sketch.setDatum(11, App.Units.Quantity(f"{2.0 * sideLength} mm"))

    # constraintList = []
    sketch.recompute()


def _padSketch(body, sketch, padValue):
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = (
        sketch,
        [
            "",
        ],
    )

    #####################
    # pad.ViewObject.ShapeAppearance=getattr(body.getLinkedObject(True).ViewObject, 'ShapeAppearance', pad.ViewObject.ShapeAppearance)
    # pad.ViewObject.LineColor=getattr(body.getLinkedObject(True).ViewObject, 'LineColor', pad.ViewObject.LineColor)
    # pad.ViewObject.PointColor=getattr(body.getLinkedObject(True).ViewObject, 'PointColor', pad.ViewObject.PointColor)
    # pad.ViewObject.Transparency=getattr(body.getLinkedObject(True).ViewObject, 'Transparency', pad.ViewObject.Transparency)
    # pad.ViewObject.DisplayMode=getattr(body.getLinkedObject(True).ViewObject, 'DisplayMode', pad.ViewObject.DisplayMode)
    # Gui.getDocument('Unnamed').setEdit(body, 0, 'Pad.')

    pad.Length = padValue
    pad.TaperAngle = 0.0
    pad.UseCustomVector = 0
    pad.Direction = (0, 0, 1)
    pad.ReferenceAxis = (sketch, ["N_Axis"])
    pad.AlongSketchNormal = 1
    pad.SideType = 0
    pad.Type = 0
    pad.Type2 = 0
    pad.UpToFace = None
    pad.UpToFace2 = None
    pad.Reversed = 0
    pad.Offset = 0
    pad.Offset2 = 0

    if GUI_ACTIVE:
        sketch.Visibility = False

    return pad


def clearBoundaryGroup(body):
    if hasattr(body, "Group"):
        for grpObj in body.Group:
            body.Document.removeObject(grpObj.Name)


def createBoundaryBodyForJob(job, initializeWithSquare=True):
    doc = App.ActiveDocument
    body = _addBody(doc)
    body.setExpression('.Placement.Base.z', f'{job.Stock.Name}.Shape.BoundBox.ZMin')
    sketch = _addSketchToBody(body)
    if initializeWithSquare:
        _addSquareToSketch(sketch, 0.20 * job.Stock.Shape.BoundBox.DiagonalLength)
        pad = _padSketch(body, sketch, job.Stock.Shape.BoundBox.ZLength)
    doc.recompute()
    return body


def createBodyWithSketch(initializeWithSquare=False):
    doc = App.ActiveDocument
    body = _addBody(doc)
    sketch = _addSketchToBody(body)
    if initializeWithSquare:
        _addSquareToSketch(sketch, 100.0)
        pad = _padSketch(body, sketch, 10.0)
    doc.recompute()
    return body


if IS_MACRO:
    createBodyWithSketch()
    App.ActiveDocument.recompute()
