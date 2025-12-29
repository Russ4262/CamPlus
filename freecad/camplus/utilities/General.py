# -*- coding: utf-8 -*-
# ***************************************************************************
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
import Part
import math
import Path.Log as PathLog
import Path.Geom as PathGeom
import freecad.camplus.utilities.Edge as EdgeUtils
import freecad.camplus.utilities.Region as RegionUtils

if FreeCAD.GuiUp:
    import FreeCADGui
    import freecad.camplus.support.Gui_Input as Gui_Input


__title__ = "Path Generator Utilities"
__author__ = "russ4262 (Russell Johnson)"
__url__ = ""
__doc__ = "Utilities for clearing path generation."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())

translate = FreeCAD.Qt.translate
getAngle = EdgeUtils.getAngle
_wireMidpoint = EdgeUtils._wireMidpoint
_wireQuartilePoint = EdgeUtils._wireQuartilePoint
isArcClockwise = EdgeUtils.isArcClockwise
isOrientedTheSame = EdgeUtils.isOrientedTheSame

isDebug = True if PathLog.getLevel(PathLog.thisModule()) == 4 else False
showDebugShapes = False


IS_MACRO = False
MODULE_NAME = "Generator_Utilities"
OPTIMIZE = False
PATTERNS = [
    ("Line", "Line"),
    ("Adaptive", "Adaptive"),
    ("Circle", "Circle"),
    ("CircleZigZag", "CircleZigZag"),
    ("Offset", "Offset"),
    ("Profile", "Profile"),
    ("Spiral", "Spiral"),
    ("ZigZag", "ZigZag"),
]
PATTERNCENTERS = [
    ("CenterOfBoundBox", "CenterOfBoundBox"),
    ("CenterOfMass", "CenterOfMass"),
    ("XminYmin", "XminYmin"),
    ("Custom", "Custom"),
]
PATHTYPES = [
    ("2D", "2D"),
    ("3D", "3D"),
]
LINEARDEFLECTION = FreeCAD.Units.Quantity("0.0001 mm")
CUTDIRECTIONS = [
    ("Clockwise", "Clockwise"),
    ("CounterClockwise", "CounterClockwise"),
]
PROFILEUSE = [
    ("None", "None"),
    ("After", "After"),
    ("Before", "Before"),
    ("Only", "Only"),
]


# Debug methods
def _debugMsg(moduleName, msg, isError=False):
    """_debugMsg(moduleName, msg, isError=False)
    If `_isDebug` flag is True, the provided message is printed in the Report View.
    If not, then the message is assigned a debug status.
    """
    if isError:
        FreeCAD.Console.PrintError(f"{moduleName}: {msg}\n")
        return

    if isDebug:
        # PathLog.info(msg)
        FreeCAD.Console.PrintMessage(f"{moduleName}: {msg}\n")
    else:
        PathLog.debug(f"{moduleName}: {msg}\n")


def _addDebugShape(shape, name="debug"):
    if showDebugShapes:
        do = FreeCAD.ActiveDocument.addObject("Part::Feature", "debug_" + name)
        do.Shape = shape
        do.purgeTouched()


def _showGeom(wireList, label=""):
    g = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "Group")
    totalCnt = 0
    for w in wireList:
        p0 = w.Vertexes[0].Point
        # line = Part.makeLine(p0, FreeCAD.Vector(p0.x, p0.y, p0.z + 5.0))
        # Part.show(line, "StartLine")
        eCnt = len(w.Edges)
        totalCnt += eCnt
        # print(f"_showGeom() Wire edge count: {eCnt}")
        w = Part.show(w, "GeomWire")
        g.addObject(w)
    if len(label) > 0:
        g.Label = f"Group_{label}"

    print(f"_showGeom() {len(wireList)} wires have {totalCnt} total edges")


def _showGeomList(wireList):
    for wires in wireList:
        for w in wires:
            p0 = w.Vertexes[0].Point
            line = Part.makeLine(p0, FreeCAD.Vector(p0.x, p0.y, p0.z + 5.0))
            Part.show(line, "StartLine")


def _showGeomOpen(wireList):
    g = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "Group")
    totalCnt = 0
    for w in wireList:
        if not w.isClosed():
            p0 = w.Vertexes[0].Point
            # line = Part.makeLine(p0, FreeCAD.Vector(p0.x, p0.y, p0.z + 5.0))
            # Part.show(line, "StartLine")
            eCnt = len(w.Edges)
            totalCnt += eCnt
            # print(f"_showGeom() Wire edge count: {eCnt}")
            w = Part.show(w, "GeomWire")
            g.addObject(w)

    print(f"_showGeom() {len(wireList)} wires have {totalCnt} total edges")


# Support methods
def _prepareAttributes(
    face,
    toolRadius,
    cutOut,
    isCenterSet,
    useStaticCenter,
    patternCenterAt,
    patternCenterCustom,
):
    """_prepareAttributes()... Prepare instance attribute values for path generation."""
    _debugMsg(MODULE_NAME, "_prepareAttributes()")
    if isCenterSet:
        if useStaticCenter:
            PathLog.debug(
                "_prepareAttributes() Both `isCenterSet` and `useStaticCenter` are True."
            )
            return None

    divisor = 2.0
    # Compute weighted center of mass of all faces combined
    if patternCenterAt == "CenterOfMass":
        comF = face.CenterOfMass
        centerOfMass = FreeCAD.Vector(comF.x, comF.y, 0.0)
        centerOfPattern = FreeCAD.Vector(centerOfMass.x, centerOfMass.y, 0.0)

    elif patternCenterAt == "CenterOfBoundBox":
        cent = face.BoundBox.Center
        centerOfPattern = FreeCAD.Vector(cent.x, cent.y, 0.0)

    elif patternCenterAt == "Custom":
        divisor = 1.0
        centerOfPattern = FreeCAD.Vector(
            patternCenterCustom.x, patternCenterCustom.y, 0.0
        )
    elif patternCenterAt == "XminYmin":
        centerOfPattern = FreeCAD.Vector(face.BoundBox.XMin, face.BoundBox.YMin, 0.0)
    else:
        FreeCAD.Console.PrintError(
            f"_prepareAttributes() `patternAtCenter not recognized: {patternCenterAt}"
        )
        return None

    # calculate line length
    # Line length to span boundbox diag with 2x cutter diameter extra on each end
    deltaC = face.BoundBox.DiagonalLength
    lineLen = deltaC + (4.0 * toolRadius)
    if patternCenterAt == "Custom":
        distToCent = face.BoundBox.Center.sub(centerOfPattern).Length
        lineLen += distToCent

    halfDiag = math.ceil(lineLen / 2.0)

    # Calculate number of passes
    # Number of lines(passes) required to cover boundbox diagonal
    cutPasses = math.ceil(lineLen / cutOut) + 1
    halfPasses = math.ceil(cutPasses / divisor)

    return (centerOfPattern, halfDiag, cutPasses, halfPasses)


def _isCollinear(p1, p2, p3):
    deltaY = p2.y - p1.y
    deltaX = p2.x - p1.x

    if PathGeom.isRoughly(deltaX, 0.0):
        # Vertical line p1 -> p2
        if PathGeom.isRoughly(p3.x, (p2.x + p1.x) / 2.0):
            return True
    else:
        m = deltaY / deltaX
        b = p1.y - m * p1.x
        if PathGeom.isRoughly(p3.y, m * p3.x + b):
            return True
    return False


def isMoveInRegion(toolDiameter, workingRegion, p1, p2, maxWidth=0.0002):
    """Make simple circle with diameter of tool, at start and end points, then fuse with rectangle.
    Check for collision with working region.
    maxWidth=0.0002 might need adjustment."""
    # Make path travel of tool as 3D solid.
    rad = toolDiameter / 2.0 - 0.000001

    def getPerp(p1, p2, dist):
        toEnd = p2.sub(p1)
        perp = FreeCAD.Vector(-1 * toEnd.y, toEnd.x, 0.0)
        if perp.x == 0 and perp.y == 0:
            return perp
        perp.normalize()
        perp.multiply(dist)
        return perp

    # Make first cylinder
    ce1 = Part.Wire(Part.makeCircle(rad, p1).Edges)
    C1 = Part.Face(ce1)
    C1.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - C1.BoundBox.ZMin))
    startShp = C1

    if p2.sub(p1).Length > 0:
        # Make second cylinder
        ce2 = Part.Wire(Part.makeCircle(rad, p2).Edges)
        C2 = Part.Face(ce2)
        C2.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - C2.BoundBox.ZMin))
        endShp = C2

        # Make extruded rectangle to connect cylinders
        perp = getPerp(p1, p2, rad)
        v1 = p1.add(perp)
        v2 = p1.sub(perp)
        v3 = p2.sub(perp)
        v4 = p2.add(perp)
        e1 = Part.makeLine(v1, v2)
        e2 = Part.makeLine(v2, v3)
        e3 = Part.makeLine(v3, v4)
        e4 = Part.makeLine(v4, v1)
        edges = Part.__sortEdges__([e1, e2, e3, e4])
        rectFace = Part.Face(Part.Wire(edges))
        rectFace.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - rectFace.BoundBox.ZMin))
        boxShp = rectFace

        # Fuse two cylinders and box together
        part1 = startShp.fuse(boxShp)
        pathTravel = part1.fuse(endShp).removeSplitter()
    else:
        pathTravel = startShp

    # Check for collision with model
    vLen = p2.sub(p1).Length
    try:
        cmn = workingRegionUtils.common(pathTravel)
        width = abs(pathTravel.Area - cmn.Area) / vLen
        if width < maxWidth:
            return True
    except Exception:
        PathLog.debug("Failed to complete path collision check.")

    return False


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


def _setCutSpeeds(module, toolController):
    module.FEED_VERT = toolController.VertFeed.Value
    module.FEED_HORIZ = toolController.HorizFeed.Value
    module.RAPID_VERT = toolController.VertRapid.Value
    module.RAPID_HORIZ = toolController.HorizRapid.Value


def fuseShapes(shapes):
    if len(shapes) == 0:
        return None
    if len(shapes) == 1:
        return shapes[0]
    fusion = shapes[0]
    for s in shapes[1:]:
        f = fusion.fuse(s)
        fusion = f
    return fusion


######################################################


# Auxillary functions
def getFacesFromSelection(selections=[]):
    populateSelection(selections)

    faces = []
    wires = []
    edges = []
    selection = FreeCADGui.Selection.getSelectionEx()
    # process user selection
    for sel in selection:
        # print(f"Object.Name: {sel.Object.Name}")
        for feat in sel.SubElementNames:
            # print(f"Processing: {sel.Object.Name}::{feat}")
            if feat.startswith("Face"):
                # face = sel.Object.Shape.getElement(feat)
                faces.append(sel.Object.Shape.getElement(feat))
            elif feat.startswith("Edge"):
                # face = sel.Object.Shape.getElement(feat)
                edges.append(sel.Object.Shape.getElement(feat))
    if len(edges) > 0:
        wires = [Part.Wire(grp) for grp in Part.sortEdges(edges)]
    return faces, wires


def populateSelection(selections=[]):
    if len(selections) == 0:
        return
    for objName, features in selections:
        if hasattr(FreeCAD.ActiveDocument, objName):
            obj = FreeCAD.ActiveDocument.getObject(objName)
            for f in features:
                FreeCADGui.Selection.addSelection(obj, f)
        else:
            print(f"No '{objName}' object in active document.")


def combineFacesToRegion(faces, saveOldHoles=True, saveNewHoles=True):
    # combine faces into horizontal regions

    region, outerOpenWires = RegionUtils.combineRegions(
        faces, includeHoles=saveOldHoles, saveMergedHoles=saveNewHoles
    )
    # Part.show(region, "Region")

    # fuse faces together for projection of path geometry
    """faceShape = faces[0].copy()
    if len(faces) > 1:
        for f in faces[1:]:
            fused = faceShape.fuse(f.copy())
            faceShape = fused"""
    faceShape = fuseShapes(faces)
    # faceShape.tessellate(0.05)

    return region, faceShape


def combineSelectedFaces(saveOldHoles=True, saveNewHoles=True):
    selectedFaces, __ = getFacesFromSelection()
    if len(selectedFaces) == 0:
        return None

    # combine faces into horizontal regions
    region, faceShape = combineFacesToRegion(
        selectedFaces, saveOldHoles=True, saveNewHoles=True
    )

    return region, faceShape


def addCustomOpToJob(job, tc):
    if FreeCAD.GuiUp:
        import Path.Op.Gui.Custom as PathCustomGui

        op = PathCustomGui.PathCustom.Create("Custom", parentJob=job)
        op.ToolController = tc
        op.ViewObject.Proxy = PathCustomGui.PathOpGui.ViewProvider(
            op.ViewObject, PathCustomGui.Command.res
        )
        op.ViewObject.Proxy.deleteOnReject = False
    else:
        import Path.Op.Custom as PathCustom

        op = PathCustom.Create("Custom", parentJob=job)
        op.ToolController = tc
    FreeCAD.ActiveDocument.recompute()

    return op


def getJob():
    jobs = [obj for obj in FreeCAD.ActiveDocument.Objects if obj.Name.startswith("Job")]
    if len(jobs) == 1:
        return jobs[0]
    # Prompt user to select a Job object
    jobLabels = [j.Label for j in jobs]
    guiInput = Gui_Input.GuiInput()
    guiInput.setWindowTitle("Job Selection")
    guiInput.addComboBox("Job", jobLabels)
    jobLabel = guiInput.execute()
    jIdx = jobLabels.index(jobLabel[0])
    return jobs[jIdx]


def getToolControllerFromJob(job):
    import Tool_Controller

    # Set tool controller from Job object
    tc, __ = Tool_Controller.getToolController(job)
    return tc


def getJobAndToolController():
    # Get Job, Custom operation, and Tool Controller
    job = getJob()
    if job is None:
        print("No Job found")
        return None, None

    return job, getToolControllerFromJob(job)


# print("Imported Generator_Utilities")
