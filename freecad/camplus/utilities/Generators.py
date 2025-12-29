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

import Path.Log as PathLog
import PathScripts.PathUtils as PathUtils
import freecad.camplus.utilities.DropCut as DropCut
import freecad.camplus.generators.Line as Line

# import Part

__title__ = "Generator Utilities"
__author__ = "russ4262 (Russell Johnson)"
__url__ = "https://github.com/Russ4262/PathRed"
__doc__ = "Utility functions for generating path geometry and converting that geometry to g-code."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


isDebug = True if PathLog.getLevel(PathLog.thisModule()) == 4 else False
showDebugShapes = False


IS_MACRO = False
GENERATOR = None
FEED_VERT = 0.0
FEED_HORIZ = 0.0
RAPID_VERT = 0.0
RAPID_HORIZ = 0.0


def _logText(text, force=False, isError=False):
    if isError:
        PathLog.error(text)
    elif isDebug or force:
        PathLog.info(text)
    else:
        PathLog.debug(text)


def _setFeedRates(tc):
    global FEED_VERT
    global RAPID_VERT
    global FEED_HORIZ
    global RAPID_HORIZ

    FEED_VERT = tc.VertFeed.Value
    RAPID_VERT = tc.VertRapid.Value
    FEED_HORIZ = tc.HorizFeed.Value
    RAPID_HORIZ = tc.HorizRapid.Value


def _setGeneratorFeedRates(generator):
    generator.FEED_VERT = FEED_VERT
    generator.RAPID_VERT = RAPID_VERT
    generator.FEED_HORIZ = FEED_HORIZ
    generator.RAPID_HORIZ = RAPID_HORIZ


class Heights:
    def __init__(self, clearance, safe, start, final):
        self.clearance = clearance
        self.safe = safe
        self.start = start
        self.final = final


def _importGeneratorModule(cutPattern="Line"):
    # _logText("_importGeneratorModule()")
    global GENERATOR

    if cutPattern == "Adaptive":
        import freecad.camplus.generators.Adaptive as generator
    elif cutPattern == "Circle":
        import freecad.camplus.generators.Circle as generator
    elif cutPattern == "CircleZigZag":
        import freecad.camplus.generators.CircleZigZag as generator
    elif cutPattern == "Line":
        import freecad.camplus.generators.Line as generator
    elif cutPattern == "Offset":
        import freecad.camplus.generators.Offset as generator
    elif cutPattern == "Profile":
        import freecad.camplus.generators.Profile as generator
    elif cutPattern == "CompoundProfile":
        import freecad.camplus.generators.CompoundProfile as generator
    elif cutPattern == "Spiral":
        import freecad.camplus.generators.Spiral as generator
    elif cutPattern == "ZigZag":
        import freecad.camplus.generators.ZigZag as generator
    else:
        print(
            f"_importGeneratorModule() The '{cutPattern}' generator is not available."
        )
        return False

    GENERATOR = generator
    _setGeneratorFeedRates(generator)
    generator.isDebug = isDebug
    _logText(f"_importGeneratorModule() GENERATOR: {cutPattern}")
    # generator.showDebugShapes = True
    return True


def _getPatternGeomWires(
    obj,
    regionFace,
    toolRadius=5.0,
    cutPattern="Line",
    heights=Heights(20.0, 15.0, 10.0, 0.0),
    useHelixEntry=False,
    operationType="Clearing",
    forceInsideOut=True,
    liftDistance=1.0,
    finishingProfile=False,
    helixAngle=10.0,
    helixConeAngle=0.0,
    useHelixArcs=False,
    helixDiameterLimit=2.5,
    keepToolDownRatio=2.0,
    adaptiveTolerance=0.1,
    stockObj=None,
    minTravel=False,
    keepToolDown=False,
    jobTolerance=0.01,
):
    if cutPattern == "Adaptive":
        wires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            heights,
            obj.CutPatternReversed,
            useHelixEntry,
            obj.MaterialAllowance.Value,
            operationType,
            obj.CutSide,
            forceInsideOut,
            liftDistance,
            finishingProfile,
            helixAngle,
            helixConeAngle,
            useHelixArcs,
            helixDiameterLimit,
            keepToolDownRatio,
            adaptiveTolerance,
            stockObj,
            minTravel,
            keepToolDown,
            jobTolerance,
        )
        geomWires = [w.copy() for w in wires]
    elif cutPattern == "Circle":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "CircleZigZag":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "Line":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "Offset":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "Profile":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "CompoundProfile":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutSide,
            obj.CompoundWidth.Value,
            obj.CutPatternReversed,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "Spiral":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    elif cutPattern == "ZigZag":
        geomWires = GENERATOR.generatePathGeometry(
            regionFace,
            toolRadius,
            obj.StepOverPercent,
            obj.CutDirection,
            obj.CutPatternCenterAt,
            obj.CutPatternCenter,
            obj.CutPatternAngle,
            obj.CutPatternReversed,
            obj.MinTravel,
            obj.KeepToolDown,
            jobTolerance,
        )
    else:
        print(f"_getPatternGeomWires() The '{cutPattern}' is not available.")
        geomWires = []

    return geomWires


def _generatePathGeometry(fusedFace, region, obj, job, toolRadius, pattern):
    _logText("_generatePathGeometry()")

    if not _importGeneratorModule(pattern):
        print(f"_generatePathGeometry(): Failed to import {pattern} generator.")
        return []

    # Set offset value for Profile cuts (- inside; + outside)
    offset = -1.0 * toolRadius - obj.MaterialAllowance.Value
    if obj.ProfileUse in ["Only", "Compound"] and pattern in [
        "Profile",
        "CompoundProfile",
    ]:
        if obj.CutSide == "Outside":
            offset = toolRadius + obj.MaterialAllowance.Value

    if pattern == "Adaptive":  # obj.CutPattern == "Adaptive":
        fc = region
    else:
        fc = PathUtils.getOffsetArea(
            region,
            offset,
            removeHoles=False,
            # Default: XY plane
            # plane=Part.makeCircle(10),
            # tolerance=1e-4,
        )

    if fc:
        geomWires = _getPatternGeomWires(
            obj,
            fc,
            toolRadius,
            cutPattern=pattern,
            stockObj=job.Stock,
        )
        if obj.PathType == "2D":
            return geomWires

        elif obj.PathType == "3D":
            # Part.show(Part.makeCompound(geomWires), "GeomWires")
            if isDebug:
                DropCut.isDebug = True
            toolShape = DropCut.getToolShape(obj.ToolController)
            pointsLists = DropCut.dropCutWires(
                geomWires,
                fusedFace,
                toolShape,
                obj.SampleInterval,
                obj.DropCutThreshold,
                obj.OptimizePaths,
            )

            # return list of wires
            return DropCut.pointsToLines(
                pointsLists, obj.StartDepth.Value, obj.FinalDepth.Value, obj.DepthOffset
            )

    # print(f"fc: {fc} Error with offsetting region.")
    return []


def _generate2dCommands(geomWires, obj, heights, toolRadius, cutPattern, startPoint):
    """_generate2dCommands(geomWires, obj, heights, toolRadius, cutPattern, startPoint)"""
    _logText("_generate2dCommands()")
    if cutPattern == "Adaptive":
        commands = GENERATOR._generateGCode(
            heights.clearance,
            heights.safe,
            heights.start,
            heights.final,
        )
    else:
        commands = GENERATOR.geometryToGcode(
            geomWires,
            heights.safe,
            heights.final,
            obj.KeepToolDown,
            obj.KeepToolDownThreshold.Value,
            startPoint,
            toolRadius,
            obj.MinTravel,
        )
    return commands


def _generate3dCommands(geomWires, obj, heights, toolRadius, cutPattern, startPoint):
    """_generate3dCommands(geomWires, obj, heights, toolRadius, cutPattern, startPoint)"""
    _logText("_generate3dCommands()")
    paths = Line.geometryToGcode(
        geomWires,
        heights.safe,
        None,  # None forces use of vertex Z values (hence 3D)
        obj.KeepToolDown,
        obj.KeepToolDownThreshold.Value,
        startPoint,
        toolRadius,
    )
    return paths


def _generatePathOnRegion_V1(fusedFace, region, obj, job, heights):
    _logText(f"_generatePathOnRegion_V1() ProfileUse: {obj.ProfileUse}", force=False)
    tc = obj.ToolController
    toolRadius = tc.Tool.Diameter.Value / 2.0
    startPoint = None
    if hasattr(obj, "UseStartPoint"):
        if obj.UseStartPoint:
            startPoint = obj.StartPoint
    else:
        print(
            "Generators._generatePathOnRegion_V1() obj has no property UseStartPoint."
        )

    if obj.PathType == "2D":
        generateCommands = _generate2dCommands
    elif obj.PathType == "3D":
        generateCommands = _generate3dCommands

    commands = []
    geomWires1 = []
    geomWires2 = []

    if obj.ProfileUse == "None":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )
        commands = generateCommands(
            geomWires1, obj, heights, toolRadius, obj.CutPattern, startPoint
        )
    elif obj.ProfileUse == "Only":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )
        commands = generateCommands(
            geomWires1, obj, heights, toolRadius, "Profile", startPoint
        )
    elif obj.ProfileUse == "Before":
        commands = []
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )
        paths1 = generateCommands(
            geomWires1, obj, heights, toolRadius, "Profile", startPoint
        )
        commands.extend(paths1)
        commands.append(
            GENERATOR.Path.Command("G0", {"Z": heights.clearance, "F": RAPID_VERT})
        )
        geomWires2 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )
        paths2 = generateCommands(
            geomWires2, obj, heights, toolRadius, obj.CutPattern, startPoint
        )
        commands.extend(paths2)
    elif obj.ProfileUse == "After":
        commands = []
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )
        paths1 = generateCommands(
            geomWires1, obj, heights, toolRadius, obj.CutPattern, startPoint
        )
        commands.extend(paths1)
        commands.append(
            GENERATOR.Path.Command("G0", {"Z": heights.clearance, "F": RAPID_VERT})
        )
        geomWires2 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )
        paths2 = generateCommands(
            geomWires2, obj, heights, toolRadius, "Profile", startPoint
        )
        commands.extend(paths2)
    elif obj.ProfileUse == "Compound":
        # PathLog.error("The 'Compound' feature of ProfileUse is non-functional.")
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "CompoundProfile"
        )
        commands = generateCommands(
            geomWires1, obj, heights, toolRadius, "Profile", startPoint
        )
    else:
        PathLog.error(f"ProfileUse '{obj.ProfileUse}' value not recognized.")

    _logText(f"_generatePathOnRegion_V1() {len(commands)} commands returned")
    return (geomWires1 + geomWires2, commands)


def _generatePathOnRegion_V2(fusedFace, region, obj, job, heights):
    _logText("_generatePathOnRegion_V2()")
    tc = obj.ToolController
    toolRadius = tc.Tool.Diameter.Value / 2.0
    if obj.UseStartPoint:
        startPoint = obj.StartPoint
    else:
        startPoint = None

    if obj.PathType == "2D":
        generateCommands = _generate2dCommands
    elif obj.PathType == "3D":
        generateCommands = _generate3dCommands

    commands = []
    geomWires1 = []
    geomWires2 = []

    _logText(f"ProfileUse: {obj.ProfileUse}")
    # PathLog.info(f"_generatePathOnRegion_V2() ProfileUse: {obj.ProfileUse}")
    if obj.ProfileUse == "None":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )
        commands.extend(
            generateCommands(
                geomWires1,
                obj,
                heights,
                toolRadius,
                obj.CutPattern,
                startPoint,
            )
        )
    elif obj.ProfileUse == "Only":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )
        commands.extend(
            generateCommands(
                geomWires1,
                obj,
                heights,
                toolRadius,
                "Profile",
                startPoint,
            )
        )
    elif obj.ProfileUse == "Before":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )
        geomWires2 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )

        paths1 = generateCommands(
            geomWires1, obj, heights, toolRadius, "Profile", startPoint, fusedFace
        )
        commands.extend(paths1)
        commands.append(
            GENERATOR.Path.Command("G0", {"Z": heights.clearance, "F": RAPID_VERT})
        )
        paths2 = generateCommands(
            geomWires2,
            obj,
            heights,
            toolRadius,
            obj.CutPattern,
            startPoint,
        )
        commands.extend(paths2)
    elif obj.ProfileUse == "After":
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, obj.CutPattern
        )
        geomWires2 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "Profile"
        )

        paths1 = generateCommands(
            geomWires1,
            obj,
            heights,
            toolRadius,
            obj.CutPattern,
            startPoint,
        )
        commands.extend(paths1)
        commands.append(
            GENERATOR.Path.Command("G0", {"Z": heights.clearance, "F": RAPID_VERT})
        )
        paths2 = generateCommands(
            geomWires2, obj, heights, toolRadius, "Profile", startPoint
        )
        commands.extend(paths2)
    elif obj.ProfileUse == "Compound":
        # PathLog.error("The 'Compound' feature of ProfileUse is non-functional.")
        geomWires1 = _generatePathGeometry(
            fusedFace, region, obj, job, toolRadius, "CompoundProfile"
        )
        commands.extend(
            generateCommands(
                geomWires1,
                obj,
                heights,
                toolRadius,
                "Profile",
                startPoint,
            )
        )
    else:
        PathLog.error(f"ProfileUse '{obj.ProfileUse}' value not recognized.")

    _logText(f"_generatePathOnRegion_V2() {len(commands)} commands returned")
    return (geomWires1 + geomWires2, commands)


# print("Imported Generators utilities.")
