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
import Part
import math
import Path
import time
import PathScripts.PathUtils as PathUtils
import freecad.camplus.utilities.Slice as SliceUtils
import freecad.camplus.utilities.Edge as EdgeUtils
import freecad.camplus.inlay.Filters as Filters
import freecad.camplus.inlay.FiltersUp as FiltersUp
import freecad.camplus.inlay.Support as InlaySupport
import freecad.camplus.inlay.InlayClosed as InlayClosed
import freecad.camplus.inlay.InlayClosedUp as InlayClosedUp
import freecad.camplus.utilities.AlignToFeature as AlignToFeature
import freecad.camplus.features.Features as Features
import freecad.camplus.utilities.ObjectTools as ObjectTools
from PySide.QtCore import QT_TRANSLATE_NOOP


__title__ = "Inlay Operation"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__url__ = ""
__doc__ = "Class and implementation of Inlay operation."
__contributors__ = ""
__files__ = "_Inlay_test_2_current.FCStd"
__resources__ = "https://www.youtube.com/watch?v=l4VMo9DCzO8"


translate = FreeCAD.Qt.translate
isDebug = True if Path.Log.getLevel(Path.Log.thisModule()) == 4 else False
DEBUG = False
DEBUG_SHP = False


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


FEATURES_DICT = {
    "ToolController": ["NoTaskPanel"],
    "Coolant": ["NoTaskPanel"],
    "HeightsDepths": [
        "NoClearanceHeight",
        "NoSafeHeight",
        "NoFinishDepth",
        "NoStepDown",
    ],
    # "BaseGeometry": [],
    # "Extensions": [],
    # "Locations": [],
    # "HoleGeometry": ["AllowVertexes"],
    # "Rotation": [],
}


def _debugText(txt, force=False):
    if DEBUG or force:
        print(txt)


def _debugShape(shape, name, force=False):
    obj = None
    if shape is not None and (DEBUG_SHP or force):
        # if FreeCAD.ActiveDocument.getObject(name):
        #    FreeCAD.ActiveDocument.removeObject(name)
        obj = Part.show(shape, name)
    return obj


def _updateDepths(job, obj, ignoreErrors=False):
    """_updateDepths(job, obj, ignoreErrors=False) ... base implementation calculating depths depending on base geometry."""

    stockBB = job.Stock.Shape.BoundBox
    zmin = stockBB.ZMin
    zmax = stockBB.ZMax

    obj.OpStockZMin = zmin
    obj.OpStockZMax = zmax

    if hasattr(obj, "Base") and obj.Base:
        # _debugText(f"_updateDepths() obj.Base")
        for base, sublist in obj.Base:
            baseShape = base.Shape

            bb = baseShape.BoundBox
            zmax = max(zmax, bb.ZMax)
            for sub in sublist:
                try:
                    if sub:
                        fbb = baseShape.getElement(sub).BoundBox
                    else:
                        fbb = baseShape.BoundBox
                    zmin = max(zmin, fbb.ZMin)
                    zmax = max(zmax, fbb.ZMax)
                except Part.OCCError as e:
                    Path.Log.error(e)

    else:
        # _debugText(f"_updateDepths() using stock boundaries")
        # clearing with stock boundaries
        zmax = stockBB.ZMax
        zmin = job.Proxy.modelBoundBox(job).ZMin

    if not Path.Geom.isRoughly(obj.OpFinalDepth.Value, zmin):
        obj.OpFinalDepth = zmin
    zmin = obj.OpFinalDepth.Value

    def minZmax(z):
        if hasattr(obj, "StepDown") and not Path.Geom.isRoughly(obj.StepDown.Value, 0):
            return z + obj.StepDown.Value
        else:
            return z + 1.0

    # ensure zmax is higher than zmin
    if (zmax - 0.0001) <= zmin:
        zmax = minZmax(zmin)

    # update start depth if requested and required
    if not Path.Geom.isRoughly(obj.OpStartDepth.Value, zmax):
        obj.OpStartDepth = zmax


class ObjectInlay(object):
    @classmethod
    def propertyDefinitions(cls):
        Path.Log.track()
        # Standard properties
        definitions = [
            (
                "App::PropertyBool",
                "Active",
                "Base",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Make False, to prevent dressup from generating code",
                ),
            ),
            (
                "App::PropertyBool",
                "ShowShape",
                "Base",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Make True to display inlay shape.",
                ),
            ),
            (
                "App::PropertyBool",
                "TestMode",
                "Base",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Make True to use test mode, testing all orientations",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "InlayGeometry",
                "Shapes",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Shape of the inlay face",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "PathGeometry",
                "Shapes",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Wires representing inlay path geometry.",
                ),
            ),
            (
                "App::PropertyLink",
                "BaseShape",
                "Base",
                QT_TRANSLATE_NOOP(
                    "App::Property", "The target shape for path creation."
                ),
            ),
            (
                "App::PropertyEnumeration",
                "WireType",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property", "Select the type of wire to generate."
                ),
            ),
            (
                "App::PropertyEnumeration",
                "CutDirection",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The direction that the toolpath should go around the part: CounterClockwise or Clockwise.",
                ),
            ),
            (
                "App::PropertyBool",
                "MakePaths",
                "Operation",
                QT_TRANSLATE_NOOP("App::Property", "Set to True to make paths."),
            ),
            (
                "App::PropertyBool",
                "MakeBottom",
                "Operation",
                QT_TRANSLATE_NOOP("App::Property", "Enable make bottom wire of inlay."),
            ),
            (
                "App::PropertyEnumeration",
                "CutMode",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The clearing mode to be used: Single-pass or Multi-pass.",
                ),
            ),
            (
                "App::PropertyDistance",
                "DiscretizeValue",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Discretize value to use when discretizing curves.",
                ),
            ),
            (
                "App::PropertyDistance",
                "InlayThickness",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Thickness of the inlay.",
                ),
            ),
            (
                "App::PropertyDistance",
                "GlueGap",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Thickness of the inlay.",
                ),
            ),
            (
                "App::PropertyDistance",
                "InlayWasteHeight",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Height of inlay above working surface, cut off as waste.",
                ),
            ),
            (
                "App::PropertyBool",
                "StackComponents",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property", "Stack bottom and top components of inlay."
                ),
            ),
            (
                "App::PropertyBool",
                "Sqr_Corners_Btm",
                "Operation",
                QT_TRANSLATE_NOOP("App::Property", "Square bottom corners."),
            ),
            (
                "App::PropertyBool",
                "Sqr_Corners_Top",
                "Operation",
                QT_TRANSLATE_NOOP("App::Property", "Square top corners."),
            ),
            (
                "App::PropertyAngle",
                "AngularDeflection",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Smaller values yield a finer, more accurate mesh. Smaller values increase processing time a lot.",
                ),
            ),
            (
                "App::PropertyDistance",
                "LinearDeflection",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Smaller values yield a finer, more accurate mesh. Smaller values do not increase processing time much.",
                ),
            ),
            (
                "App::PropertyDistance",
                "DepthOffset",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Set the Z-axis pocketDepth offset from the target surface.",
                ),
            ),
            (
                "App::PropertyEnumeration",
                "CutSide",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property", "Side of selected faces that tool should cut"
                ),
            ),
            (
                "App::PropertyEnumeration",
                "CutUpDown",
                "Operation",
                QT_TRANSLATE_NOOP(
                    "App::Property", "Cut direction in Z axis: Up, Down, Both"
                ),
            ),
        ]

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getProps = getattr(Features, f + "PropertyDefinitions")
            definitions.extend(getProps(flags))

        return definitions

    @classmethod
    def propertyEnumerations(cls, dataType="data"):
        """propertyEnumerations(dataType="data")... return property enumeration lists of specified dataType.
        Args:
            dataType = 'data', 'raw', 'translated'
        Notes:
        'data' is list of internal string literals used in code
        'raw' is list of (translated_text, data_string) tuples
        'translated' is list of translated string literals
        """
        Path.Log.track()

        enums = {
            "WireType": (
                (translate("Path", "None"), "None"),
                (translate("Path", "Inlay"), "Inlay"),
                (translate("Path", "Bottom"), "Bottom"),
                (translate("Path", "Midline"), "Midline"),
            ),
            "CutDirection": (
                (translate("Path", "Clockwise"), "Clockwise"),
                (translate("Path", "CounterClockwise"), "CounterClockwise"),
            ),
            "CutMode": (
                (translate("Path", "Single-pass"), "Single-pass"),
                (translate("Path", "Multi-pass"), "Multi-pass"),
            ),
            "CutSide": (
                (translate("Path", "Both"), "Both"),
                (translate("Path", "Outside"), "Outside"),
                (translate("Path", "Inside"), "Inside"),
            ),
            "CutUpDown": (
                (translate("Path", "Both"), "Both"),
                (translate("Path", "Up"), "Up"),
                (translate("Path", "Down"), "Down"),
            ),
            # "ZZZZZZZZ": (
            #    (translate("Path", "None"), "None"),
            #    (translate("Path", "After"), "After"),
            #    (translate("Path", "Before"), "Before"),
            #    (translate("Path", "Single Only"), "Only"),
            #    (translate("Path", "Compound Only"), "Compound"),
            # ),
            # "CoolantMode": (
            #    (translate("Path_Operation", "None"), "None"),
            #    (translate("Path_Operation", "Flood"), "Flood"),
            #    (translate("Path_Operation", "Mist"), "Mist"),
            # ),
        }

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getValues = getattr(Features, f + "Enumerations")
            vals = getValues(flags)
            if vals:
                for k, v in vals.items():
                    enums[k] = v

        if dataType == "raw":
            return enums

        data = []
        idx = 0 if dataType == "translated" else 1

        Path.Log.debug(enums)

        for k, v in enumerate(enums):
            data.append((v, [tup[idx] for tup in enums[v]]))
        Path.Log.debug(data)

        return data

    @classmethod
    def propertyDefaults(cls, obj, job):
        """propertyDefaults(obj, job) ... returns a dictionary of default values
        for the operation's properties."""

        defaults = {
            "Active": True,
            "WireType": "Bottom",  # None, Inlay, Bottom, Midline
            "CutDirection": "Clockwise",  # Clockwise, CounterClockwise
            "MakePaths": True,
            "MakeBottom": True,
            "CutMode": "Single-pass",  # Single-pass, Multi-pass
            "DiscretizeValue": 0.5,
            "InlayThickness": 5.0,
            "GlueGap": 1.0,
            "InlayWasteHeight": 1.0,
            "StackComponents": True,
            "Sqr_Corners_Btm": True,
            "Sqr_Corners_Top": True,
            "AngularDeflection": 30.0,
            "LinearDeflection": 1.0,
            "DepthOffset": 0.0,
            "CutSide": "Inside",  # Both, Outside, Inside
            "CutUpDown": "Both",  # Both, Down, Up
            "TestMode": False,
        }

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getValues = getattr(Features, f + "DefaultValues")
            vals = getValues(job, obj, flags)
            if vals:
                for k, v in vals.items():
                    defaults[k] = v

        return defaults

    def __init__(self, obj, baseObj, parentJob=None):
        # Path.Log.info("ObjectInlay.__init__()")
        self.obj = obj
        self.rotations = None
        if parentJob is None:
            self.job = PathUtils.findParentJob(baseObj)
        else:
            self.job = parentJob
        self.job.Proxy.addOperation(obj, baseObj, True)

        definitions = ObjectInlay.propertyDefinitions()
        enumerations = ObjectInlay.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(obj, definitions, enumerations)
        self._setEditorModes(obj)

        # Set default values
        propDefaults = ObjectInlay.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)
        obj.BaseShape = baseObj

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setEditorModes(self, obj):
        # obj.setEditorMode("OpStartDepth", 1)  # read-only
        # obj.setEditorMode("OpFinalDepth", 1)  # read-only
        pass

    #########################

    def _getRotationsList(self, obj, mapped=False):
        return AlignToFeature.getRotationsList(obj, mapped)

    def isToolSupported(self, obj, tool):
        if not hasattr(tool, "CuttingEdgeAngle"):
            return False
        return True

    #########################
    #########################

    def onDelete(self, obj, args):
        if obj.BaseShape:
            job = PathUtils.findParentJob(obj)
            if job:
                job.Proxy.addOperation(obj.BaseShape, obj)
            if obj.BaseShape.ViewObject:
                obj.BaseShape.ViewObject.Visibility = True
                if hasattr(obj.BaseShape, "Active"):
                    obj.BaseShape.Active = True
            obj.BaseShape = None
        return True

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.job = PathUtils.findParentJob(obj)
        definitions = ObjectInlay.propertyDefinitions()
        enumerations = ObjectInlay.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(
            obj, definitions, enumerations, warn=True
        )
        propDefaults = ObjectInlay.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)
        self._setEditorModes(obj)

    def onChanged(self, obj, prop):
        """onChanged(obj, prop) ... method called when objECT is changed,
        with source propERTY of the change."""

        def sanitizeBase(obj):
            """sanitizeBase(obj) ... check if Base is valid and clear on errors."""
            if hasattr(obj, "Base"):
                try:
                    for o, sublist in obj.Base:
                        for sub in sublist:
                            if sub != "":
                                o.Shape.getElement(sub)
                except Part.OCCError:
                    Path.Log.error(
                        "{} - stale base geometry detected - clearing.".format(
                            obj.Label
                        )
                    )
                    obj.Base = []
                    return True
            return False

        # there's a bit of cycle going on here, if sanitizeBase causes the transaction to
        # be cancelled we end right here again with the unsainitized Base - if that is the
        # case, stop the cycle and return immediately
        if prop == "Base" and sanitizeBase(obj):
            return

        if "Restore" in obj.State:
            pass
        elif prop in [
            "Base",
            "StartDepth",
            "FinalDepth",
        ]:
            _updateDepths(self.job, obj, True)
        # _debugText("onChange() finished")

    def acceptAddBase(self, obj, base, sub):
        """acceptAddBase(base, sub) ... This method is used to apply filters to Base additions."""
        return True

    def addBase(self, obj, base, sub, prop="Base"):
        Path.Log.track(obj, base, sub)
        base = Path.Base.Util.getPublicObject(base)

        for model in self.job.Model.Group:
            if base == self.job.Proxy.baseObject(self.job, model):
                base = model
                break

        if prop == "Base":
            baselist = obj.Base
        elif prop == "Hole":
            baselist = obj.Holes
        else:
            Path.Log.error(f"addBase() prop '{prop}' unknown.")
            return
        if baselist is None:
            baselist = []

        for p, el in baselist:
            if p == base and sub in el:
                Path.Log.notice(
                    (translate("Path", "Base object %s.%s already in the list") + "\n")
                    % (base.Label, sub)
                )
                return

        if self.acceptAddBase(obj, base, sub):
            baselist.append((base, sub))
            if prop == "Base":
                obj.Base = baselist
            elif prop == "Hole":
                obj.Holes = baselist

        else:
            Path.Log.notice(
                (translate("Path", "Base object %s.%s rejected by operation") + "\n")
                % (base.Label, sub)
            )

    def showShape(self, obj):
        if hasattr(obj, "Shape"):
            _debugShape(obj.Shape, f"{obj.Name}__Shape", True)
        _debugShape(obj.InlayGeometry, f"{obj.Name}__Inlay", True)
        _debugShape(obj.PathGeometry, f"{obj.Name}__Path", True)

    def execute(self, obj):
        if not obj.Active:
            return

        startTime = time.time()

        _updateDepths(self.job, obj, True)
        # obj.recompute()
        # _debugText(f"self.rotations: {self.rotations}")

        """
        _debugText(f"obj.ExpressionEngine: {obj.ExpressionEngine}")
        _debugText(
            f"obj.OpStartDepth: {obj.OpStartDepth};  obj.OpFinalDepth: {obj.OpFinalDepth}"
        )
        _debugText(f"obj.StartDepth: {obj.StartDepth};  obj.FinalDepth: {obj.FinalDepth}")
        _debugText(
            f"StartDepth.Value: {obj.StartDepth.Value},  FinalDepth.Value: {obj.FinalDepth.Value}"
        )
        """
        Path.Log.track()
        # _debugText(f"ClearingObj.execute() Base: {obj.BaseShape.Label}")
        if not obj.BaseShape:
            Path.Log.info("No base object.")
            return

        t = obj.ToolController.Tool
        if not hasattr(t, "CuttingEdgeAngle"):
            FreeCAD.Console.PrintMessage(
                f"Current Tool Controller: {obj.ToolController.Name}.\n"
            )
            FreeCAD.Console.PrintError(
                "Tool Controller is missing 'CuttingEdgeAngle' property.\n"
            )
            return
        if not hasattr(t, "TipDiameter"):
            FreeCAD.Console.PrintMessage(
                f"Current Tool Controller: {obj.ToolController.Name}.\n"
            )
            FreeCAD.Console.PrintError(
                "Current Tool Controller is missing 'TipDiameter' property.\n"
            )
            return

        commands = []
        solids = []
        wires = []
        wireType = obj.WireType
        inlayDepth = obj.InlayThickness.Value
        pocketDepth = _calculatePocketDepth(obj)
        wasteHeight = _calculateAdjustedWasteHeight(obj)
        _debugText(f"execute() wireType: {wireType}, pocketDepth: {pocketDepth}")
        _debugText(f"execute() inlayDepth: {inlayDepth}, wasteHeight: {wasteHeight}")
        wT = wireType
        pD = pocketDepth
        iD = inlayDepth
        wH = wasteHeight

        Path.Log.debug(f"Processing '{obj.BaseShape.ShapeType}' shape type.")

        i = 0
        if obj.BaseShape.ShapeType == "Wire":
            for w in obj.BaseShape.Shape.Wires:
                _debugText(f"Wire_{i}")
                sol, wir = _wireToInlay(obj, w, wT, pD, iD, wH)
                solids.extend(sol)
                wires.extend(wir)
                i += 1
        elif obj.BaseShape.ShapeType == "Region":
            for f in obj.BaseShape.Shape.Faces:
                _debugText(f"Face_{i}")
                sol, wir = _wireToInlay(obj, f, wT, pD, iD, wH)
                solids.extend(sol)
                wires.extend(wir)
                i += 1
        else:
            Path.Log.warning(
                f"No clearing support for '{obj.BaseShape.ShapeType}' shapes."
            )

        # Debug & Test Mode feedback
        _debugText(f"len(solids): {len(solids)}", obj.TestMode)
        # for s in solids:
        #    _debugShape(s, "InlayComponent", obj.TestMode)
        for w in wires:
            _debugShape(w, "PathWire", obj.TestMode)

        obj.InlayGeometry = Part.makeCompound(solids)

        if len(wires) > 0:
            w = Part.makeCompound(wires)
            obj.PathGeometry = w
        else:
            obj.PathGeometry = Part.Shape()

        # iObj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "InlaySolid")
        # iObj.Shape = Part.makeCompound(solids)

        # self.commandlist = commands

        timeStr = time.strftime("%H:%M:%S", time.gmtime(time.time() - startTime))
        Path.Log.info("Processing time: " + timeStr)

        if obj.ShowShape:
            self.showShape(obj)


# Eclass


# Support functions
def _calculatePocketDepth(obj):
    tool = obj.ToolController.Tool
    halfToolAngle = tool.CuttingEdgeAngle.Value / 2.0
    tipRad = tool.TipDiameter.Value / 2.0
    tipHeight = tipRad / math.tan(math.radians(halfToolAngle))
    _debugText(f"tipHeight: {tipHeight}")
    # return obj.InlayThickness.Value
    pocketDepth = obj.InlayThickness.Value + tipHeight + obj.GlueGap.Value
    return pocketDepth


def _calculateAdjustedWasteHeight(obj):
    tool = obj.ToolController.Tool
    halfToolAngle = tool.CuttingEdgeAngle.Value / 2.0
    tipRad = tool.TipDiameter.Value / 2.0
    tipHeight = tipRad / math.tan(math.radians(halfToolAngle))
    wasteHeight = obj.InlayWasteHeight.Value + tipHeight
    return wasteHeight


def _getDepthForMidline(shp, cutAngle):
    length = max(shp.BoundBox.XLength, shp.BoundBox.YLength) * 1.1 / 2.0
    # tan ANG = o/a
    # a = o/tan ANG
    return length / math.tan(math.radians(cutAngle))


def _getInlayDependencies(shape, obj):
    tool = obj.ToolController.Tool
    halfToolAngle = -1.0 * tool.CuttingEdgeAngle.Value / 2.0
    # Only process outside wire
    wire = EdgeUtils.orientWire(shape.Wires[0], True)
    proj = InlaySupport._makeProjection(wire)
    dataTup = (
        InlaySupport._discretizeEdgeList(proj.Edges, obj.DiscretizeValue.Value),
        shape.BoundBox.ZMin,
    )
    w = EdgeUtils.orientWire(dataTup[0], True)  # dataTup[0]
    h = dataTup[1]
    return (w, halfToolAngle, h)


def _wireToInlay(obj, shp, wireType, pocketDepth, inlayDepth, wasteHeight):
    solids = []
    wires = []

    # get Wire, Angle, and Height
    (cleanWire, cutAngle, height) = _getInlayDependencies(shp, obj)

    dfm = abs(_getDepthForMidline(shp, cutAngle))
    depth = pocketDepth if wireType != "Midline" else dfm
    _debugText(
        f"_wireToInlay()  cutAngle: {cutAngle}, height: {height}, depth: {depth}"
    )

    # rw2 = InlayClosed.rotateShape180(cleanWire)  # Wire flipped horizontally

    if obj.TestMode:
        slds, pthWrs = buildInlayWalls(
            obj,
            cleanWire,
            cutAngle,
            height,
            depth,
        )
    else:
        slds, pthWrs = buildInlay(
            cleanWire, cutAngle, height, depth, inlayDepth, wasteHeight, wireType
        )
    if slds:
        solids.extend(slds)
        _debugText(f"len(slds): {len(slds)}", obj.TestMode)
    if pthWrs:
        wires.extend(pthWrs)
        _debugText(f"len(pthWrs): {len(pthWrs)}", obj.TestMode)

    return solids, wires


def buildInlayWalls(obj, w, a, h, pocketDepth):
    solids = []
    wires = []
    rndInCorn = not obj.Sqr_Corners_Btm
    rndOutCorn = not obj.Sqr_Corners_Top
    cutSide = obj.CutSide
    upDown = obj.CutUpDown
    wireType = obj.WireType

    if cutSide in ["Both", "Inside"] and upDown in ["Both", "Down"]:
        inlay, inWire = makeInlayDown(rndInCorn, w, a, h, pocketDepth, wireType)
        if inlay is not None:
            solids.append(inlay)
            _debugShape(inlay, "Inside_Down", obj.TestMode)
        if inWire is not None:
            wires.append(inWire)

    if cutSide in ["Both", "Outside"] and upDown in ["Both", "Down"]:
        outlay, outWire = makeOutlayDown(rndOutCorn, w, a, h, pocketDepth, wireType)
        if outlay is not None:
            solids.append(outlay)
            _debugShape(outlay, "Outside_Down", obj.TestMode)
        if outWire is not None:
            wires.append(outWire)

    if cutSide in ["Both", "Inside"] and upDown in ["Both", "Up"]:
        inlayUp, inWireUp = makeInlayUp(rndInCorn, w, a, h, pocketDepth, wireType)
        if inlayUp is not None:
            solids.append(inlayUp)
            _debugShape(inlayUp, "Inside_Up", obj.TestMode)
        if inWireUp is not None:
            wires.append(inWireUp)

    if cutSide in ["Both", "Outside"] and upDown in ["Both", "Up"]:
        outlayUp, outWireUp = makeOutlayUp(rndOutCorn, w, a, h, pocketDepth, wireType)
        if outlayUp is not None:
            solids.append(outlayUp)
            _debugShape(outlayUp, "Outside_Up", obj.TestMode)
        if outWireUp is not None:
            wires.append(outWireUp)

    return solids, wires


def buildInlay(w, a, h, pocketDepth, inlayDepth, wasteHeight, wireType):
    solids = []
    wires = []

    # Make inlay pocket
    inlay, inWire = makeInlayDown(True, w, a, h, pocketDepth, wireType)
    if inlay:
        _debugShape(inlay, "MakeInlayDown_Inlay")
    if inWire:
        _debugShape(inWire, "MakeInlayDown_InWire")
    if inlay is not None:
        solids.append(inlay)
        if inWire is not None:
            wires.append(inWire)

    # Make inlay base
    """
    inlayBase, baseWire = makeInlayDown(False, w, a, h, inlayDepth)
    if inlayBase is not None:
        baseFlipped = InlayClosed.rotateShape180(inlayBase)  # flipped horizontally
        # solids.append(baseFlipped)
        # if baseWire is not None:
        #    wires.append(baseWire)

        # Make waste material on top of inlay base
        if wasteHeight > 0.0:
            waste, wasteWire = makeOutlayUp(False, w, a, h, wasteHeight, wireType="Top")
            if waste is not None:
                wasteFlipped = InlayClosed.rotateShape180(waste)  # flipped horizontally
                # Stack waste under flipped inlay base
                wasteFlipped.translate(
                    FreeCAD.Vector(
                        0.0, 0.0, baseFlipped.BoundBox.ZMin - wasteFlipped.BoundBox.ZMax
                    )
                )
                solids.append(
                    EdgeUtils.fuseShapes([baseFlipped, wasteFlipped]).removeSplitter()
                )
                if wasteWire is not None:
                    wasteWireFlipped = InlayClosed.rotateShape180(
                        wasteWire
                    )  # flipped horizontally
                    wires.append(wasteWireFlipped)
        else:
            solids.append(baseFlipped)
    """

    return solids, wires


def _makePointFlag(p):
    p1 = FreeCAD.Vector(p.x, p.y, p.z + 10.0)
    line = Part.makeLine(p, p1)
    _debugShape(line, "PointFlag")


def _showWireEdges(w):
    i = 0
    for e in w.Edges:
        _debugShape(e, f"Wire_Edge_{i}_")
        i += 1


def makeInlayDown(rndCrnrs, w, a, h, pocketDepth, wireType="None"):
    _debugText(f"makeInlayDown({rndCrnrs}, wire, {a}, {h}, {pocketDepth}, {wireType})")
    _debugShape(w, "MakeInlayDown_Raw_Wire")
    wire = None

    # _debugText("Inlay.makeInlayDown() setting InlayClosed.DEBUG to True")
    # InlayClosed.DEBUG = True
    # InlayClosed.DEBUG_SHP = True

    # _showWireEdges(w)

    # InlayClosed.ROUND_CORNERS = rndCrnrs
    rawInlayFace, obtusePoints = InlayClosed.clockwiseWireToRawInlay(
        w, a, pocketDepth, rndCrnrs
    )
    if rawInlayFace:
        _debugShape(rawInlayFace, "RawInlayFace")
    # inlayFace = Filters.filterInlay(rawInlayFace, False, True, extra=rndCrnrs)
    # Filters.filterInlay(rawInlay, outside, isClosed, extra=False)

    # _debugText("Inlay.makeInlayDown() setting InlayClosed.DEBUG to True", True)
    # Filters.DEBUG = True
    # Filters.DEBUG_SHP = True

    # inlayFace = Filters.filterInlay(rawInlayFace, False, True, extra=True)
    inlayFace = Filters.filterInlay(rawInlayFace, False, True, extra=False)
    if inlayFace is None:
        _debugText("makeInlayDown() inlayFace is None")
        return None, None

    # for op in obtusePoints:
    #    _makePointFlag(op)
    # _debugShape(inlayFace, "InlayDownFace_A")

    inlayFace.translate(FreeCAD.Vector(0.0, 0.0, h - inlayFace.BoundBox.ZMax))

    # _debugShape(inlayFace, "InlayDownFace_B")

    if wireType != "None":
        # _debugText("Inlay.makeInlayDown() setting Filters.DEBUG to True")
        # Filters.DEBUG = True
        # Filters.DEBUG_SHP = True

        iwr = Filters.identifyInsideInlayPathWires(inlayFace, wireType, obtusePoints)
        if iwr is not None:
            _debugShape(iwr, "InlayWire_DownRegular")
            wire = iwr

    return inlayFace, wire


def makeOutlayDown(rndCrnrs, w, a, h, pocketDepth, wireType="None"):
    _debugText(f"makeOutlayDown({rndCrnrs}, wire, {a}, {h}, {pocketDepth}, {wireType})")
    wire = None
    # InlayClosed.DEBUG = True
    # InlayClosed.DEBUG_SHP = True

    # InlayClosed.ROUND_CORNERS = rndCrnrs
    rawOutlayFace, obtusePoints = InlayClosed.clockwiseWireToRawOutlay(
        w, a, pocketDepth, rndCrnrs
    )
    outlayFace = Filters.filterInlay(rawOutlayFace, False, True)
    if outlayFace is None:
        return None, None

    # for op in obtusePoints:
    #    _makePointFlag(op)

    outlayFace.translate(FreeCAD.Vector(0.0, 0.0, h - outlayFace.BoundBox.ZMax))
    # shpObj = _debugShape(outlayFace, "OutlayFace_DownRegular")
    if wireType != "None":
        wire = Filters.identifyOutsideInlayPathWires(outlayFace, wireType, obtusePoints)
        if wire is not None:
            _debugShape(wire, "OutlayWire_DownRegular")

    return outlayFace, wire


def makeInlayUp(rndCrnrs, w, a, h, pocketDepth, wireType="None"):
    _debugText("makeInlayUp()")
    wire = None
    # InlayClosedUp.DEBUG = True
    # InlayClosedUp.DEBUG_SHP = True
    # FiltersUp.DEBUG = True
    # FiltersUp.DEBUG_SHP = True

    # InlayClosedUp.ROUND_CORNERS = rndCrnrs
    rawInlayFace, obtusePoints = InlayClosedUp.clockwiseWireToRawInlay(
        w, a, pocketDepth, rndCrnrs
    )
    inlayFace = FiltersUp.filterInlay(rawInlayFace, False, True, extra=rndCrnrs)
    if inlayFace is None:
        _debugText("makeInlayUp() inlayFace is None")
        return None, None

    inlayFace.translate(FreeCAD.Vector(0.0, 0.0, h - inlayFace.BoundBox.ZMax))
    shpObj = _debugShape(inlayFace, "InlayFace_UpRegular")
    if wireType != "None":
        wire = FiltersUp.identifyInsideInlayPathWires(inlayFace, wireType, obtusePoints)
        if wire is not None:
            # _debugShape(wire, "InlayWire_UpRegular")
            pass

    return inlayFace, wire


def makeOutlayUp(rndCrnrs, w, a, h, pocketDepth, wireType="None"):
    _debugText("makeOutlayUp()")
    shapes = []
    wire = None
    # InlayClosedUp.DEBUG = True
    # InlayClosedUp.DEBUG_SHP = True
    # FiltersUp.DEBUG = True
    # FiltersUp.DEBUG_SHP = True

    # InlayClosedUp.ROUND_CORNERS = rndCrnrs
    rawOutlayFace, obtusePoints = InlayClosedUp.clockwiseWireToRawOutlay(
        w, a, pocketDepth, rndCrnrs
    )
    outlayFace = FiltersUp.filterInlay(rawOutlayFace, True, True)
    if outlayFace is None:
        _debugText("makeOutlayUp() outlayFace is None")
        return None, None

    outlayFace.translate(FreeCAD.Vector(0.0, 0.0, h - outlayFace.BoundBox.ZMax))
    shapes.append(outlayFace)
    # shpObj = _debugShape(outlayFace, "OutlayFace_UpRegular")
    if wireType != "None":
        wire = FiltersUp.identifyOutsideInlayPathWires(
            outlayFace, wireType, obtusePoints
        )
        if wire is not None:
            # _debugShape(wire, "OutlayWire_UpRegular")
            pass

    return outlayFace, wire


def showSlices(slices, name):
    group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "Group")
    group.Label = f"_{name}"
    slices.reverse()
    for s in slices:
        group.addObject(_debugShape(s, name))


def getDepthParams(obj):
    clearance_height = obj.StartDepth.Value + 10.0
    safe_height = obj.StartDepth.Value + 5.0
    start_depth = obj.StartDepth.Value
    step_down = (
        obj.StepDown.Value
        if hasattr(obj, "StepDown")
        else (obj.FinalDepth.Value - obj.StartDepth.Value) / 5.0
    )
    z_finish_step = 0.0
    final_depth = obj.FinalDepth.Value

    depthParams = PathUtils.depth_params(
        clearance_height,
        safe_height,
        start_depth,
        step_down,
        z_finish_step,
        final_depth,
        user_depths=None,
        equalstep=False,
    )

    return [d for d in depthParams]


def sliceShape(obj):
    if obj.ShapeType not in ["ExtrudedRegion", "3DSolid"]:
        return None
    depths = [obj.StartDepth.Value] + getDepthParams(obj)
    # Path.Log.info(f"depths: {depths}")
    if obj.ShapeType == "3DSolid":
        shape = obj.Shape
    else:
        shape = obj.Shape.copy()
        shape.translate(FreeCAD.Vector(0.0, 0.0, -1.0 * obj.FinalDepth.Value))

    slices = SliceUtils.sliceSolid(shape, depths)
    # showSlices(slices, "Solid")
    sections = SliceUtils._slicesToCrossSections(slices)
    showSlices(sections, "Section")
    regions = SliceUtils._slicesToCutRegions(slices)
    showSlices(regions, "CutRegions")
    return slices


def listPropertyDetails():
    """listPropertyDetails() ... print details for all properties"""
    for prtyp, nm, grp, tt in ObjectInlay.opPropertyDefinitions():
        _debugText(f"type: {prtyp};  name: {nm}")


def SetupProperties():
    """SetupProperties() ... Return list of properties required for operation."""
    return [tup[1] for tup in ObjectInlay.propertyDefinitions()]


def Create(baseObj, obj=None, name="Inlay", parentJob=None):
    """Create(name) ... Creates and returns a Clearing operation."""
    if obj is None:
        # obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
        obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
    obj.Proxy = ObjectInlay(obj, baseObj, parentJob)
    return obj
