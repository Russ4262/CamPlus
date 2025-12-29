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
import PathScripts.PathUtils as PathUtils
import Part

# import Path

__title__ = "Features List"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Simple catalogue of feature hex codes."
__usage__ = ""
__url__ = ""
__Wiki__ = ""
__date__ = "2023.07.14"

translate = FreeCAD.Qt.translate

"""
HeightsDepths = 0x0001  # Heights and Depths combined
BaseVertexes = 0x0002  # Base geometry
BaseEdges = 0x0004  # Base geometry
BaseFaces = 0x0008  # Base geometry
FeatureLocations = 0x0010  # Locations
FeatureExtensions = 0x0020  # Extensions
FeatureHoleGeometry = 0x0040
FeatureNoClearanceHeight = 0x0080
FeatureNoSafeHeight = 0x0100
FeatureNoFinalDepth = 0x0200
FeatureStepDown = 0x0400
FeatureFinishDepth = 0x0800
FeatureCoolant = 0x1000
FeatureTool = 0x2000
FeatureBasePanels = 0x4000  # Base
BaseGeometry = BaseVertexes | BaseFaces | BaseEdges
"""


class PathNoTCException(Exception):
    """PathNoTCException is raised when no TC was selected or matches the input
    criteria. This can happen intentionally by the user when they cancel the TC
    selection dialog."""

    def __init__(self):
        super().__init__("No Tool Controller found")


def getToolControllers(obj, proxy=None):
    """returns all the tool controllers"""
    if proxy is None:
        proxy = obj.Proxy
    try:
        job = PathUtils.findParentJob(obj)
    except Exception:
        job = None

    if job:
        return [
            tc
            for tc in job.Tools.Group
            if (
                hasattr(proxy, "isToolSupported")
                and proxy.isToolSupported(obj, tc.Tool)
            )
            or not hasattr(proxy, "isToolSupported")
        ]
    return []


# Property Definition Functions
def OpBasePropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyBool",
            "Active",
            "Path",
            translate(
                "App::Property", "Make False, to prevent operation from generating code"
            ),
        ),
        (
            "App::PropertyString",
            "Comment",
            "Path",
            translate("App::Property", "An optional comment for this Operation"),
        ),
        (
            "App::PropertyString",
            "UserLabel",
            "Path",
            translate("App::Property", "User Assigned Label"),
        ),
        (
            "App::PropertyString",
            "CycleTime",
            "Path",
            translate("App::Property", "Operations Cycle Time Estimation"),
        ),
        (
            "App::PropertyDistance",
            "OpStockZMax",
            "Op Values",
            translate("App::Property", "Holds the max Z value of Stock"),
        ),
        (
            "App::PropertyDistance",
            "OpStockZMin",
            "Op Values",
            translate("App::Property", "Holds the min Z value of Stock"),
        ),
        (
            "App::PropertyDistance",
            "OpToolDiameter",
            "Op Values",
            translate("App::Property", "Holds the diameter of the tool"),
        ),
    ]


def ToolControllerPropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyLink",
            "ToolController",
            "Path",
            translate(
                "App::Property",
                "The tool controller that will be used to calculate the path",
            ),
        ),
        (
            "App::PropertyDistance",
            "OpToolDiameter",
            "Op Values",
            translate("App::Property", "Holds the diameter of the tool"),
        ),
    ]


def CoolantPropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            translate("App::Property", "Coolant mode for this operation"),
        )
    ]


def StartPointPropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyVectorDistance",
            "StartPoint",
            "Start Point",
            translate("App::Property", "The start point of this path"),
        ),
        (
            "App::PropertyBool",
            "UseStartPoint",
            "Start Point",
            translate("App::Property", "Make True, if specifying a Start Point"),
        ),
    ]


def BaseGeometryPropertyDefinitions(flags=[]):
    """BaseGeometryPropertyDefinitions(flags=[])
    Flags:
        Faces
        Edges
        Vertexes
    """
    return [
        (
            "App::PropertyLinkSubListGlobal",
            "Base",
            "BaseFeatures",
            translate("PathOp", "The base geometry for this operation"),
        ),
        (
            "App::PropertyBool",
            "ModelOnly",
            "BaseFeatures",
            translate(
                "PathOp",
                "If set True, only the base model will be used, no features.",
            ),
        ),
    ]


def HoleGeometryPropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyLinkSubListGlobal",
            "Holes",
            "Holes",
            translate("PathOp", "The hole geometry for this operation"),
        ),
        (
            "App::PropertyStringList",
            "DisabledHoles",
            "Holes",
            translate("App::Property", "List of disabled features"),
        ),
        (
            "App::PropertyDistance",
            "MinDiameter",
            "Diameter",
            translate("PathOp", "Lower limit of the turning diameter"),
        ),
        (
            "App::PropertyDistance",
            "MaxDiameter",
            "Diameter",
            translate("PathOp", "Upper limit of the turning diameter."),
        ),
    ]


def LocationsPropertyDefinitions(flags=[]):
    return [
        (
            "App::PropertyVectorList",
            "Locations",
            "Locations",
            translate("PathOp", "Base locations for this operation"),
        )
    ]


def HeightsDepthsPropertyDefinitions(flags=[]):
    definitions = [
        (
            "App::PropertyDistance",
            "StartDepth",
            "HeightsAndDepths",
            translate("PathOp", "Starting Depth of Tool- first cut depth in Z"),
        ),
        (
            "App::PropertyDistance",
            "OpStartDepth",
            "Op Values",
            translate("PathOp", "Holds the calculated value for the StartDepth"),
        ),
        (
            "App::PropertyDistance",
            "OpFinalDepth",
            "Op Values",
            translate("PathOp", "Holds the calculated value for the FinalDepth"),
        ),
        (
            "App::PropertyDistance",
            "OpStockZMax",
            "Op Values",
            translate("App::Property", "Holds the max Z value of Stock"),
        ),
        (
            "App::PropertyDistance",
            "OpStockZMin",
            "Op Values",
            translate("App::Property", "Holds the min Z value of Stock"),
        ),
    ]
    if "NoClearanceHeight" not in flags:
        definitions.append(
            (
                "App::PropertyDistance",
                "ClearanceHeight",
                "HeightsAndDepths",
                translate(
                    "PathOp", "The height needed to clear clamps and obstructions"
                ),
            )
        )
    if "NoSafeHeight" not in flags:
        definitions.append(
            (
                "App::PropertyDistance",
                "SafeHeight",
                "HeightsAndDepths",
                translate("PathOp", "Rapid Safety Height between locations."),
            )
        )
    if "NoStepDown" not in flags:
        definitions.append(
            (
                "App::PropertyDistance",
                "StepDown",
                "HeightsAndDepths",
                translate("App::Property", "Incremental Step Down of Tool"),
            )
        )
    if "NoFinishDepth" not in flags:
        definitions.append(
            (
                "App::PropertyDistance",
                "FinishDepth",
                "HeightsAndDepths",
                translate("App::Property", "Maximum material removed on final pass."),
            )
        )
    if "NoFinalDepth" not in flags:
        definitions.append(
            (
                "App::PropertyDistance",
                "FinalDepth",
                "HeightsAndDepths",
                translate("PathOp", "Final Depth of Tool- lowest value in Z"),
            ),
        )
    return definitions


def ExtensionsPropertyDefinitions(flags=[]):
    """extensionsPropertyDefinitions()... Adds feature properties to object argument"""
    return [
        (
            "App::PropertyDistance",
            "ExtensionLengthDefault",
            "Extensions",
            translate("PathPocketShape", "Default length of extensions."),
        ),
        (
            "App::PropertyLinkSubListGlobal",
            "ExtensionFeature",
            "Extensions",
            translate("PathPocketShape", "List of features to extend."),
        ),
        (
            "App::PropertyBool",
            "ExtensionCorners",
            "Extensions",
            translate(
                "PathPocketShape",
                "When enabled connected extension edges are combined to wires.",
            ),
        ),
    ]


'''def RotationPropertyDefinitions(flags=[]):
    """RotationPropertyDefinitions(flags=[])"""
    return [
        (
            "App::PropertyBool",
            "UseRotation",
            "Rotation",
            translate("Features", "Use rotation for shape."),
        ),
        (
            "App::PropertyLinkSubListGlobal",
            "RotationBase",
            "Rotation",
            translate("Features", "The base geometry for this operation"),
        ),
        (
            "App::PropertyVector",
            "CenterOfRotation",
            "Rotation",
            translate(
                "Features",
                "Center of rotation for rotations applied.",
            ),
        ),
        (
            "App::PropertyBool",
            "InvertRotation",
            "Rotation",
            translate("Features", "Invert direction of rotation."),
        ),
        (
            "App::PropertyVector",
            "RotationsValues",
            "Rotation",
            translate(
                "Features",
                "Rotations applied to the model to access this target shape. Values",
            ),
        ),
        (
            "App::PropertyString",
            "RotationsOrder",
            "Rotation",
            translate(
                "Features",
                "Rotations applied to the model to access this target shape. Order",
            ),
        ),
    ]

'''


def RotationPropertyDefinitions(flags=[]):
    """RotationPropertyDefinitions(flags=[])"""
    return [
        # (
        #    "App::PropertyBool",
        #    "UseRotation",
        #    "Rotation",
        #    translate("Features", "Use rotation for shape."),
        # ),
        (
            "App::PropertyVector",
            "CenterOfRotation",
            "Rotation",
            translate(
                "Features",
                "Center of rotation for rotations applied.",
            ),
        ),
        (
            "App::PropertyBool",
            "InvertRotation",
            "Rotation",
            translate("Features", "Invert direction of rotation."),
        ),
        (
            "App::PropertyVector",
            "RotationsValues",
            "Rotation",
            translate(
                "Features",
                "Rotations applied to the model to access this target shape. Values",
            ),
        ),
        (
            "App::PropertyString",
            "RotationsOrder",
            "Rotation",
            translate(
                "Features",
                "Rotations applied to the model to access this target shape. Order",
            ),
        ),
    ]


# Default Value Functions
def OpBaseDefaultValues(job, obj, flags=[]):
    # obj.Active = True
    return {"Active": True}


def ToolControllerDefaultValues(job, obj, flags=[]):
    tc = None
    for o in job.Operations.Group[:-1]:
        if hasattr(o, "ToolController") and o.ToolController is not None:
            tc = o.ToolController
    if tc:
        if hasattr(obj.Proxy, "isToolSupported") and obj.Proxy.isToolSupported(
            obj, tc.Tool
        ):
            pass
        else:
            tc = None
    if tc is None:
        tc = PathUtils.findToolController(obj, obj.Proxy)
    if not tc:
        raise PathNoTCException()
    # obj.ToolController = tc
    # obj.OpToolDiameter = obj.ToolController.Tool.Diameter
    return {"ToolController": tc, "OpToolDiameter": tc.Tool.Diameter}


def CoolantDefaultValues(job, obj, flags=[]):
    # Path.Log.track()
    # Path.Log.debug(obj.getEnumerationsOfProperty("CoolantMode"))
    # obj.CoolantMode = job.SetupSheet.CoolantMode
    return {"CoolantMode": job.SetupSheet.CoolantMode}


def StartPointDefaultValues(job, obj, flags=[]):
    # obj.UseStartPoint = False
    return {"UseStartPoint": False}


def BaseGeometryDefaultValues(job, obj, flags=[]):
    return {}


def HoleGeometryDefaultValues(job, obj, flags=[]):
    # obj.MinDiameter = "0 mm"
    # obj.MaxDiameter = "0 mm"
    # if job and job.Stock:
    #    obj.MaxDiameter = job.Stock.Shape.BoundBox.XLength
    minDiam = 0.0
    maxDiam = 0.0
    if job and job.Stock:
        maxDiam = job.Stock.Shape.BoundBox.XLength
    return {"MinDiameter": minDiam, "MaxDiameter": maxDiam}


def LocationsDefaultValues(job, obj, flags=[]):
    return {}


def HeightsDepthsDefaultValues(job, obj, flags=[]):
    values = {}
    if job:
        allModels = Part.makeCompound([m.Shape for m in job.Model.Group])
        modMax = allModels.BoundBox.ZMax
        modMin = allModels.BoundBox.ZMin
        jobMin = job.Stock.Shape.BoundBox.ZMin
        jobMax = job.Stock.Shape.BoundBox.ZMax
    else:
        modMax = 1.0
        modMin = 0.0
        jobMin = 2.0
        jobMax = -1.0

    values["OpStockZMax"] = jobMax
    values["OpStockZMin"] = jobMin

    if "NoFinalDepth" not in flags:
        if job and job.SetupSheet.FinalDepthExpression:
            obj.setExpression("FinalDepth", job.SetupSheet.FinalDepthExpression)
            values["OpFinalDepth"] = modMin
        elif hasattr(obj, "OpFinalDepth"):
            obj.setExpression("FinalDepth", "OpFinalDepth")
            values["OpFinalDepth"] = modMin
        else:
            values["FinalDepth"] = 0.0

    if "NoStartDepth" not in flags:
        if job and job.SetupSheet.StartDepthExpression:
            obj.setExpression("StartDepth", job.SetupSheet.StartDepthExpression)
            values["OpStartDepth"] = modMax
        elif hasattr(obj, "OpStartDepth"):
            obj.setExpression("StartDepth", "OpStartDepth")
            values["OpStartDepth"] = modMax
        else:
            values["StartDepth"] = 0.0

    if "NoSafeHeight" not in flags:
        if job and job.SetupSheet.SafeHeightExpression:
            obj.setExpression("SafeHeight", job.SetupSheet.SafeHeightExpression)
        else:
            values["SafeHeight"] = jobMax + 3.0

    if "NoClearanceHeight" not in flags:
        if job and job.SetupSheet.ClearanceHeightExpression:
            obj.setExpression(
                "ClearanceHeight", job.SetupSheet.ClearanceHeightExpression
            )
        else:
            values["ClearanceHeight"] = jobMax + 5.0

    if "NoStepDown" not in flags:
        if hasattr(obj, "OpToolDiameter"):
            obj.setExpression("StepDown", "OpToolDiameter")
            values["OpToolDiameter"] = 5.0
        elif job.SetupSheet.StepDownExpression:
            obj.setExpression("StepDown", job.SetupSheet.StepDownExpression)
            values["OpToolDiameter"] = 5.0
        else:
            values["StepDown"] = 1.0


def ExtensionsDefaultValues(job, obj, flags=[]):
    defaults = {"ExtensionCorners": True}
    if hasattr(obj, "OpTooldiameter"):
        obj.setExpression("ExtensionLengthDefault", "OpToolDiameter / 2.0")
    else:
        # obj.setExpression("ExtensionLengthDefault", "5.0")
        defaults["ExtensionLengthDefault"] = 5.0
    return defaults


def RotationDefaultValues(job, obj, flags=[]):
    defaults = {
        # "UseRotation": False,
        "RotationsValues": FreeCAD.Vector(0.0, 0.0, 0.0),
        "RotationsOrder": "",
        "CenterOfRotation": FreeCAD.Vector(0.0, 0.0, 0.0),
        "InvertRotation": False,
    }

    return defaults


# Property Enumeration Functions
def OpBaseEnumerations(flags=[]):
    return {}


def ToolControllerEnumerations(flags=[]):
    return {}


def CoolantEnumerations(flags=[]):
    return {
        "CoolantMode": (
            (translate("Path_Operation", "None"), "None"),
            (translate("Path_Operation", "Flood"), "Flood"),
            (translate("Path_Operation", "Mist"), "Mist"),
        ),
    }


def StartPointEnumerations(flags=[]):
    return {}


def BaseGeometryEnumerations(flags=[]):
    """BaseGeometryEnumerations(flags=[])
    Flags:
        Faces
        Edges
        Vertexes
    """
    return {}


def HoleGeometryEnumerations(flags=[]):
    return {}


def LocationsEnumerations(flags=[]):
    """LocationsEnumerations()... Return dictionary of enumerations for locations-related properties"""
    return {}


def HeightsDepthsEnumerations(flags=[]):
    """HeightsDepthsEnumerations()... Return dictionary of enumerations for heights and depths-related properties"""
    return {}


def ExtensionsEnumerations(flags=[]):
    """ExtensionsEnumerations()... Return dictionary of enumerations for extensions-related properties"""
    return {}


def RotationEnumerations(flags=[]):
    """RotationEnumerations()... Return dictionary of enumerations for rotation-related properties"""
    return {}


PathUtils.getToolControllers = getToolControllers
