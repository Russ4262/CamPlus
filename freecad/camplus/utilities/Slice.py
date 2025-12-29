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
import Path.Log as PathLog
import Path.Geom as PathGeom
import PathScripts.PathUtils as PathUtils
import Part


__title__ = "Slice Solid Macro"
__author__ = "russ4262 (Russell Johnson)"
__url__ = "https://www.freecadweb.org"
__doc__ = "Path slicing macro for 3D shapes with regional efficiency included."


if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


translate = FreeCAD.Qt.translate

IS_MACRO = False


# Support functions
def removeTopFaceFromSlice(slice):
    faces = []
    zMax = slice.BoundBox.ZMax
    for f in slice.Faces:
        if not PathGeom.isRoughly(f.BoundBox.ZMin, zMax):
            faces.append(f)

    return faces


def _getBottomFaces(shape):
    faces = []
    if len(shape.Faces) == 0:
        print("_getBottomFaces() Shape has no faces.")
        return faces

    zMin = min([f.BoundBox.ZMin for f in shape.Faces])
    # print("{} faces in shape & ZMin: {}".format(len(shape.Faces), round(zMax, 6)))

    return [
        f
        for f in shape.Faces
        if PathGeom.isRoughly(f.BoundBox.ZMax, zMin)
        and PathGeom.isRoughly(f.BoundBox.ZLength, 0.0)
    ]


def _getTopFaces(shape):
    faces = []
    if len(shape.Faces) == 0:
        print("_getBottomFaces() Shape has no faces.")
        return faces

    zMax = max([f.BoundBox.ZMax for f in shape.Faces])
    # print("{} faces in shape & ZMin: {}".format(len(shape.Faces), round(zMax, 6)))

    return [
        f
        for f in shape.Faces
        if PathGeom.isRoughly(f.BoundBox.ZMin, zMax)
        and PathGeom.isRoughly(f.BoundBox.ZLength, 0.0)
    ]


def _makeSliceToolShape(shape, zmin, thickness):
    try:
        face = PathGeom.makeBoundBoxFace(shape.BoundBox, 5.0, zmin)
    except Exception as ee:
        PathLog.error(f"_makeSliceToolShape():: {ee}")
        return None
    return face.extrude(FreeCAD.Vector(0.0, 0.0, thickness))


def _sliceSolid(solid, depths, region=None):
    if not isinstance(depths, list):
        PathLog.error("sliceSolid() `depths` is not list object")
        return []

    # print(f"_sliceSolid() depths are {depths}")
    solids = []
    toolRegion = solid if region is None else region

    topDep = depths[0]
    idx = 0
    for d in depths[1:]:
        idx += 1
        thickness = topDep - d
        # PathLog.info(f"slicing at {round(d, 2)} mm with thickness of {thickness} mm")

        sliceTool = _makeSliceToolShape(toolRegion, d, thickness)
        if sliceTool is None:
            PathLog.info("Slice tool is None. Possible error.")
            break

        # common = solid.common(sliceTool).removeSplitter()
        common = solid.common(sliceTool)
        # Part.show(common, "CommonSlice")

        if len(common.Solids) > 1:
            useDepths = depths[idx:]
            # print(f"useDepths: {useDepths}")
            for rgn in common.Solids:
                solids.append(rgn)
                # print("       Processing sub-solid...")
                subSolids = _sliceSolid(solid, useDepths, rgn)
                solids.extend(subSolids)
            # print("Breaking main loop after processing multiple solids.")
            break
        else:
            # print("   Processed single solid.")
            solids.append(common)
        topDep = d

    return [s for s in solids if len(s.Edges) > 0]


def _slicesToCrossSections(slices):
    faces = []
    for s in slices:
        faces.extend([f.copy() for f in _getBottomFaces(s)])
    return faces


def _slicesToCutRegions(slices):
    faces = []
    for s in slices:
        faces.extend([f.copy() for f in _getTopFaces(s)])
    return faces


def _slicesTo3DShells(slices):
    faces = []
    for s in slices:
        nonTopFaces = [f.copy() for f in removeTopFaceFromSlice(s)]
        fusion = nonTopFaces[0]
        for ntf in nonTopFaces[1:]:
            fused = fusion.fuse(ntf)
            fusion = fused
        faces.append(fusion)
    return faces


# Macro use support functions
def getDepthParams(obj):
    """getDepthParams(obj) Copied from featureshape.FeatureShape.py"""
    clearance_height = obj.StartDepth.Value + 10.0
    safe_height = obj.StartDepth.Value + 5.0
    start_depth = obj.StartDepth.Value
    step_down = (
        obj.StepDown.Value
    )  # (obj.FinalDepth.Value - obj.StartDepth.Value) / 5.0
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
    return [obj.StartDepth.Value] + [float(d) for d in depthParams.data]


# Public function
def sliceSolid(solid, depths, output="Solids"):
    """sliceSolid(solid, depths, output="Solids")
    Return slices of a solid as set of solids, cross-sections, or 3D shells.  The shapes returned are provided
    in order of region, for efficiency's sake.
    Arguments:
        solid = Shape object containing one or more `Solids` in Shape.Solids attribute
        depths = slice depths with first depth being top of first slice, and second value being
                 the bottom of the first slice.
        output = Type of shapes list to return
    """
    if output not in ["Solids", "CrossSections", "3DShells", "CutRegions"]:
        PathLog.error(
            "output value not in list: Solids, CrossSections, 3DShells, CutRegions"
        )
        raise ValueError
    if not isinstance(depths, list):
        PathLog.error("depths is not list")
        raise ValueError
    if len(depths) < 2:
        PathLog.error("depths list is too short")
        raise ValueError

    # PathLog.info(f"solid top: {solid.BoundBox.ZMax}  and  first depth: {depths[0]}")
    slices = _sliceSolid(solid, depths)

    if output == "CrossSections":
        return _slicesToCrossSections(slices)
    elif output == "3DShells":
        return _slicesTo3DShells(slices)
    elif output == "CutRegions":
        return _slicesToCutRegions(slices)

    return slices


def executeAsMacro():
    print("\n\n\n\n")
    doc = FreeCAD.ActiveDocument
    obj = doc.FeatureShape
    depths = getDepthParams(obj)
    print(f"depths: {depths}")

    docGroupSolids = doc.addObject("App::DocumentObjectGroup", "Group")
    docGroupSolids.Label = "Solids"
    docGroupSections = doc.addObject("App::DocumentObjectGroup", "Group")
    docGroupSections.Label = "Cross-sections"

    solids = sliceSolid(obj.Shape, depths, "Solids")
    for s in solids:
        slc = Part.show(s, "Solid")
        docGroupSolids.addObject(slc)
        fcs = _getBottomFaces(s)
        for f in fcs:
            fc = Part.show(f, "Face")
            docGroupSections.addObject(fc)

    """docGroupShells = doc.addObject("App::DocumentObjectGroup", "Group")
    docGroupShells.Label = "Shells"
    shells = _slicesTo3DShells(solids)
    for s in shells:
        slc = Part.show(s, "Shell")
        docGroupShells.addObject(slc)"""

    doc.recompute()


if IS_MACRO:
    executeAsMacro()
