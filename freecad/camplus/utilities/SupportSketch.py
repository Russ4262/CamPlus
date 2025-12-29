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
import Part
import Path
import freecad.camplus.utilities.Region as Region


__title__ = "Support Sketch"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "."
__usage__ = "."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate


# Support functions
def _addBoundarySketch(obj):
    if not hasattr(obj, "BoundarySketch"):
        s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", "BoundarySketch")
        s.Placement = FreeCAD.Placement(
            FreeCAD.Vector(),
            FreeCAD.Rotation(0.0, 0.0, 0.0, 1.0),
        )
        """
        support = None
        if support:
            zShift2 = obj.FeatureShape.FinalDepth.Value
            s.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, 0.0, zShift2),
                FreeCAD.Rotation(0.0, 0.0, 0.0),
            )
            s.AttachmentSupport = support
            s.MapReversed = False
            s.MapPathParameter = 0
            s.MapMode = "ObjectXY"
        else:
            s.MapMode = "Deactivated"
        """
        s.MapMode = "Deactivated"

        if s.ViewObject:
            s.ViewObject.Visibility = False
            s.ViewObject.LineColor = (110, 165, 0)
            s.ViewObject.PointColor = (110, 165, 0)  # (255, 255, 255)

        # Add property to sketch to identify external geometry intent
        s.addProperty(
            "App::PropertyBool",
            "UseExternalEdges",
            "Custom",
            translate(
                "App::Property",
                "Set True to include external sketch geometry in region identification.",
            ),
        )

        obj.addProperty(
            "App::PropertyLink",
            "BoundarySketch",
            "Shape",
            translate(
                "App::Property",
                "Sketch container for defining a boundary shape.",
            ),
        )
        setattr(obj, "BoundarySketch", s)
        s.recompute()
        s.purgeTouched()
        obj.recompute()
        # FreeCAD.ActiveDocument.recompute()

    return getattr(obj, "BoundarySketch").Name


def _addSupportSketch_orig(obj, name="Extend"):
    if name not in ["Extend", "Trim"]:
        FreeCAD.Console.PrintError(f"{name} not in ['Extend', 'Trim']")
        return None

    propName = f"Feature{name}"

    if not hasattr(obj, propName):
        s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", propName)
        s.Placement = FreeCAD.Placement(
            FreeCAD.Vector(),
            FreeCAD.Rotation(0.0, 0.0, 0.0, 1.0),
        )
        support = obj.FeatureShape
        if support:
            # shpBB = obj.FeatureShape.Shape.BoundBox
            # zShift0 = obj.FeatureShape.Placement.Base.z
            # zShift1 = obj.FeatureShape.Shape.BoundBox.ZMax
            zShift2 = obj.FeatureShape.FinalDepth.Value
            # print(f"{name} zShift0: {zShift0}")
            # print(f"{name} zShift1: {zShift1}")
            # print(f"{name} zShift2: {zShift2}")
            # print(f"support.Name: {support.Name}")
            s.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, 0.0, zShift2),
                FreeCAD.Rotation(0.0, 0.0, 0.0),
            )
            s.AttachmentSupport = support
            s.MapReversed = False
            s.MapPathParameter = 0
            s.MapMode = "ObjectXY"
        else:
            s.MapMode = "Deactivated"

        if s.ViewObject:
            s.ViewObject.Visibility = False
            if name == "Extend":
                s.ViewObject.LineColor = (110, 165, 0)
                s.ViewObject.PointColor = (110, 165, 0)  # (255, 255, 255)
            elif name == "Trim":
                s.ViewObject.LineColor = (170, 0, 0)
                s.ViewObject.PointColor = (170, 0, 0)  # (255, 255, 255)

        # Add property to sketch to identify external geometry intent
        s.addProperty(
            "App::PropertyBool",
            "UseExternalEdges",
            "Custom",
            translate(
                "App::Property",
                "Set True to include external sketch geometry in region identification.",
            ),
        )

        obj.addProperty(
            "App::PropertyLink",
            propName,
            "Shape",
            translate(
                "App::Property",
                "Sketch container for extending the target shape.",
            ),
        )
        setattr(obj, propName, s)
        s.recompute()
        s.purgeTouched()
        obj.recompute()
        # FreeCAD.ActiveDocument.recompute()


def _addSupportSketch(obj, name="Extend"):
    if name not in ["Extend", "Trim"]:
        FreeCAD.Console.PrintError(f"{name} not in ['Extend', 'Trim']")
        return None

    propName = f"Feature{name}"

    if not hasattr(obj, propName):
        s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", propName)
        s.Placement = FreeCAD.Placement(
            FreeCAD.Vector(),
            FreeCAD.Rotation(0.0, 0.0, 0.0, 1.0),
        )
        support = obj.FeatureShape
        if support:
            # zShift = obj.FeatureShape.Shape.BoundBox
            # zShift0 = obj.FeatureShape.Placement.Base.z
            # zShift1 = obj.FeatureShape.Shape.BoundBox.ZMax
            zShift2 = obj.FeatureShape.FinalDepth.Value
            # print(f"{name} zShift: {zShift}")
            # print(f"{name} zShift0: {zShift0}")
            # print(f"{name} zShift1: {zShift1}")
            # print(f"{name} zShift2: {zShift2}")
            # print(f"support.Name: {support.Name}")
            s.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, 0.0, zShift2),
                FreeCAD.Rotation(0.0, 0.0, 0.0),
            )
            s.AttachmentSupport = support
            s.MapReversed = False
            s.MapPathParameter = 0
            s.MapMode = "ObjectXY"
        else:
            s.MapMode = "Deactivated"

        if s.ViewObject:
            s.ViewObject.Visibility = False
            if name == "Extend":
                s.ViewObject.LineColor = (110, 165, 0)
                s.ViewObject.PointColor = (110, 165, 0)  # (255, 255, 255)
            elif name == "Trim":
                s.ViewObject.LineColor = (170, 0, 0)
                s.ViewObject.PointColor = (170, 0, 0)  # (255, 255, 255)

        # Add property to sketch to identify external geometry intent
        s.addProperty(
            "App::PropertyBool",
            "UseExternalEdges",
            "Custom",
            translate(
                "App::Property",
                "Set True to include external sketch geometry in region identification.",
            ),
        )

        obj.addProperty(
            "App::PropertyLink",
            propName,
            "Shape",
            translate(
                "App::Property",
                "Sketch container for extending the target shape.",
            ),
        )
        setattr(obj, propName, s)
        s.recompute()
        s.purgeTouched()
        obj.recompute()
        # FreeCAD.ActiveDocument.recompute()


def _getSketchRegion(sketchName):
    extend = []
    regions = []
    sketch = FreeCAD.ActiveDocument.getObject(sketchName)
    for base, subs in sketch.ExternalGeometry:
        for s in subs:
            if sketch.UseExternalEdges and s.startswith("Edge"):
                extend.append(base.Shape.getElement(s).copy())
    for e in sketch.Shape.Edges:
        extend.append(e.copy())
    for grp in Part.sortEdges(extend):
        w = Part.Wire(grp)
        if w.isClosed():
            # Part.show(w, f"{sketchName}_Wire")
            regions.append(Part.Face(w))

    if not regions:
        return None

    # return Region.fuseAndRefineRegions(regions)[0]
    return Region.fuseShapes(regions)


def _processTriggers(obj):
    recompute = False
    if obj.UseFeatureExtend:
        _addSupportSketch(obj, "Extend")
    elif hasattr(obj, "FeatureExtend"):
        sName = obj.FeatureExtend.Name
        obj.FeatureExtend = None
        obj.removeProperty("FeatureExtend")
        FreeCAD.ActiveDocument.removeObject(sName)
        obj.recompute()
        recompute = True

    if obj.UseFeatureTrim:
        _addSupportSketch(obj, "Trim")
    elif hasattr(obj, "FeatureTrim"):
        sName = obj.FeatureTrim.Name
        obj.FeatureTrim = None
        obj.removeProperty("FeatureTrim")
        FreeCAD.ActiveDocument.removeObject(sName)
        obj.recompute()
        recompute = True
    return recompute


#####################################
def addSketch(parentObj, name="Extend"):
    if name not in ["Extend", "Trim", "Boundary"]:
        FreeCAD.Console.PrintError(f"{name} not in ['Extend', 'Trim', 'Boundary']")
        return None

    support = None
    propName = f"{name}Features"

    s = FreeCAD.ActiveDocument.addObject("Sketcher::SketchObject", propName)
    s.Placement = FreeCAD.Placement(
        FreeCAD.Vector(),
        FreeCAD.Rotation(0.0, 0.0, 0.0, 1.0),
    )
    if parentObj.ModelFeatures and parentObj.ModelFeatures.Shape.SubShapes:
        support = parentObj.ModelFeatures
    if support:
        # print(f"support.Name: {support.Name}")
        zShift2 = parentObj.ModelFeatures.ZMin
        s.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0, 0.0, zShift2),
            FreeCAD.Rotation(0.0, 0.0, 0.0),
        )
        s.AttachmentSupport = support
        s.MapReversed = False
        s.MapPathParameter = 0
        s.MapMode = "ObjectXY"
    else:
        s.MapMode = "Deactivated"

    if s.ViewObject:
        s.ViewObject.Visibility = False
        if name == "Extend":
            s.ViewObject.LineColor = (110, 165, 0)
            s.ViewObject.PointColor = (110, 165, 0)  # (255, 255, 255)
        elif name == "Trim":
            s.ViewObject.LineColor = (170, 0, 0)
            s.ViewObject.PointColor = (170, 0, 0)  # (255, 255, 255)
        elif name == "Boundary":
            s.ViewObject.LineColor = (25, 25, 110)
            s.ViewObject.PointColor = (25, 25, 110)  # (255, 255, 255)

    # Add property to sketch to identify external geometry intent, and parent object
    s.addProperty(
        "App::PropertyBool",
        "UseExternalEdges",
        "Custom",
        translate(
            "App::Property",
            "Set True to include external sketch geometry in region identification.",
        ),
    )
    s.addProperty(
        "App::PropertyString",
        "ParentName",
        "Base",
        translate(
            "App::Property",
            "Set True to include external sketch geometry in region identification.",
        ),
    )

    s.ParentName = parentObj.Name
    s.setEditorMode("ParentName", 1)  # read-only

    s.recompute()
    # s.purgeTouched()
    # FreeCAD.ActiveDocument.recompute()
    return s


def addSketchSupport(sketch, supportObj, zHeight):
    if not sketch:
        return
    # print(f"addSketchSupport() {sketch.Name}, {supportObj.ZMin}")
    sketch.MapMode = "ObjectXY"
    sketch.AttachmentSupport = supportObj
    sketch.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, zHeight),
        FreeCAD.Base.Rotation(),
    )
    sketch.MapReversed = False
    sketch.MapPathParameter = 0
    sketch.recompute()
    sketch.purgeTouched()


def addSketchSupportAlt(sketch, supportObj, vector):
    if not sketch:
        return
    # print(f"addSketchSupport() {sketch.Name}, {supportObj.ZMin}")
    sketch.MapMode = "ObjectXY"
    sketch.AttachmentSupport = supportObj
    sketch.AttachmentOffset = FreeCAD.Placement(
        vector,
        FreeCAD.Base.Rotation(),
    )
    sketch.MapReversed = False
    sketch.MapPathParameter = 0
    sketch.recompute()
    sketch.purgeTouched()


def addSketchSupportNew(sketch, supportObj, placement):
    if not sketch:
        return
    # print(f"addSketchSupport() {sketch.Name}, {supportObj.ZMin}")
    sketch.MapMode = "ObjectXY"
    sketch.AttachmentSupport = supportObj
    sketch.AttachmentOffset = placement
    sketch.MapReversed = False
    sketch.MapPathParameter = 0
    sketch.recompute()
    sketch.purgeTouched()


def clearSketchSupport(sketch, zHeight=0.0):
    if not sketch:
        return
    # print(f"clearSketchSupport() {sketch.Name}, {zMin}")
    # sketch.AttachmentOffset = FreeCAD.Placement(
    #    FreeCAD.Vector(0.0, 0.0, zMin),
    #    FreeCAD.Rotation(0.0, 0.0, 0.0),
    # )
    sketch.MapMode = "Deactivated"
    sketch.AttachmentSupport = []
    sketch.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, zHeight), FreeCAD.Base.Rotation()
    )
    sketch.recompute()
    sketch.purgeTouched()


# FreeCAD.Console.PrintMessage("Imported SupportSketch module.\n")
