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
import freecad.camplus.features.Features as Features
import freecad.camplus.utilities.ObjectTools as ObjectTools
import freecad.camplus.utilities.SupportSketch as SupportSketch
import freecad.camplus.utilities.Region as RegionUtils
import freecad.camplus.utilities.AlignToFeature as AlignToFeature

# from PySide.QtCore import translate


__title__ = "Working Shape"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Creates a Working Shape object."
__usage__ = "Import this module.  Run the 'Create()' function, passing it the desired base operation."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate

FEATURES_DICT = {
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
    # "ToolController": ["NoTaskPanel"],
    # "Coolant": ["NoTaskPanel"],
}

AXES_OF_ROTATION = {
    "X": FreeCAD.Vector(1.0, 0.0, 0.0),
    "Y": FreeCAD.Vector(0.0, 1.0, 0.0),
    "Z": FreeCAD.Vector(0.0, 0.0, 1.0),
    "A": FreeCAD.Vector(1.0, 0.0, 0.0),
    "B": FreeCAD.Vector(0.0, 1.0, 0.0),
    "C": FreeCAD.Vector(0.0, 0.0, 1.0),
}


# Support functions
def _resetSketches(obj):

    if obj.ModelFeatures:
        zDefault = obj.ModelFeatures.ZMax
    else:
        FreeCAD.Console.PrintWarning("_resetSketches() missing obj.ModelFeatures.\n")
        return

    if obj.ExtendFeatures:
        SupportSketch.clearSketchSupport(obj.ExtendFeatures, zDefault)
        # print("reseting ExtendedFeatures sketch")

    if obj.TrimFeatures:
        SupportSketch.clearSketchSupport(obj.TrimFeatures, zDefault)
        # print("reseting TrimFeatures sketch")


def _updateSketchesAlt(obj, rotations):
    """_updateSketchesAlt(obj, rotations)
    Update the MapMode and corresponding details of Extend and Trim sketches for the Working Shape parent.
    """
    # Assign attachment object
    attachObj = obj.ModelFeatures
    # calculate placement for sketch
    if obj.ModelFeatures:
        zDefault = obj.ModelFeatures.ZMax
    else:
        FreeCAD.Console.PrintWarning(
            "_updateSketchesAlt() missing obj.ModelFeatures.\n"
        )
        return
    placement = AlignToFeature.makeObjectPlacementAlt(zDefault, rotations)

    if obj.ExtendFeatures:
        if obj.ExtendFeatures.MapMode == "Deactivated" and placement:
            SupportSketch.addSketchSupportNew(obj.ExtendFeatures, attachObj, placement)
        elif obj.ExtendFeatures.MapMode == "ObjectXY":
            if placement is None:
                SupportSketch.clearSketchSupport(obj.ExtendFeatures, zDefault)
            else:
                SupportSketch.addSketchSupportNew(
                    obj.ExtendFeatures, attachObj, placement
                )
        else:
            SupportSketch.clearSketchSupport(obj.ExtendFeatures, zDefault)

    if obj.TrimFeatures:
        if obj.TrimFeatures.MapMode == "Deactivated" and placement:
            SupportSketch.addSketchSupportNew(obj.TrimFeatures, attachObj, placement)
        elif obj.TrimFeatures.MapMode == "ObjectXY":
            if placement is None:
                SupportSketch.clearSketchSupport(obj.TrimFeatures, zDefault)
            else:
                SupportSketch.addSketchSupportNew(
                    obj.TrimFeatures, attachObj, placement
                )
        else:
            SupportSketch.clearSketchSupport(obj.TrimFeatures, zDefault)


def _updateDepths(job, obj, showErrors=False):
    """_updateDepths(job, obj, showErrors=False) ... Calculate start and final depths."""
    # print("WorkingShape._updateDepths()")

    if obj.ModelFeatures:
        # print("WorkingShape._updateDepths() using obj.ModelFeatures")
        stockBB = obj.ModelFeatures.Stock.BoundBox
    else:
        stockBB = job.Stock.Shape.BoundBox

    zmin = stockBB.ZMin
    zmax = stockBB.ZMax

    obj.OpStockZMin = zmin
    obj.OpStockZMax = zmax
    # print(f"_updateDepths() zmin: {round(zmin, 4)};  zmax: {round(zmax, 4)}")

    if hasattr(obj, "ModelFeatures") and obj.ModelFeatures:
        # print(f"_updateDepths() obj.ModelFeatures")
        if obj.ShapeType == "3DSolid":
            zmin = obj.ModelFeatures.ZMin  # max(zmin, obj.ModelFeatures.ZMin)
        else:
            zmin = obj.ModelFeatures.ZMax
        zmax = max(zmax, obj.ModelFeatures.ZMax)
    else:
        # print(f"_updateDepths() using stock boundaries")
        # clearing with stock boundaries
        if obj.ModelFeatures:
            zmin = obj.ModelFeatures.Proxy._allModels().BoundBox.ZMin
        else:
            zmin = job.Proxy.modelBoundBox(job).ZMin

    # print(f"     WS._updateDepths()a min: {zmin};  max: {zmax}")

    if not Path.Geom.isRoughly(obj.OpFinalDepth.Value, zmin):
        obj.OpFinalDepth = zmin
    zmin = obj.OpFinalDepth.Value

    # print(f"     WS._updateDepths()b min: {zmin};  max: {zmax}")
    # ensure zmax is higher than zmin
    if (zmax - job.GeometryTolerance.Value) <= zmin:
        if showErrors:
            print(f"_updateDepths() Setting zmax = zmin + 1.0")
        zmax = zmin + 1.0

    # update start depth if requested and required
    if not Path.Geom.isRoughly(obj.OpStartDepth.Value, zmax):
        obj.OpStartDepth = zmax


def _printDepths(obj):
    print(
        f"OpStartDepth: {round(obj.OpStartDepth, 4)};  OpStartDepth.Value: {round(obj.OpStartDepth.Value, 4)}"
    )
    print(
        f"OpFinalDepth: {round(obj.OpFinalDepth, 4)};  OpFinalDepth.Value: {round(obj.OpFinalDepth.Value, 4)}"
    )
    print(
        f"StartDepth: {round(obj.StartDepth, 4)};  StartDepth.Value: {round(obj.StartDepth.Value, 4)}"
    )
    print(
        f"FinalDepth: {round(obj.FinalDepth, 4)};  FinalDepth.Value: {round(obj.FinalDepth.Value, 4)}"
    )
    print(f"obj.ExpressionEngine: {obj.ExpressionEngine}")


def _getFeatureShapes(job, obj):
    """_getFeatureShapes(job, obj)
    Returns tuple of (points, edges, faces, models), all with obj.Rotation applied."""
    # print("WorkingShape._getFeatureShapes()")
    mf = obj.ModelFeatures
    if not obj.ModelFeatures:
        # print("WorkingShape._getFeatureShapes() no obj.ModelFeatures")
        return [], [], [], []

    points = mf.Vertexes
    edges = mf.Edges.Edges
    faces = mf.Faces.Faces
    # This 'models' composite needs more work to recognize and include compounds of only wires or edges or faces, not just solids
    models = mf.Models.Solids if len(mf.Models.Edges) > 0 else []
    # models = [getattr(mf, f"Mdl_{n}") for n in mf.ModelNames]
    # Part.show(Part.makeCompound(fcs), "Fcs")

    # print(
    #    f"WorkingShape._getFeatureShapes()\nlen(points): {len(points)}\nlen(edges): {len(edges)}\nlen(faces): {len(faces)}"
    # )
    return points, edges, faces, models


def _getRequestedShape(job, obj, shape, rotations, haveNonplanar):
    if shape is None or len(shape.Edges) < 1:
        # print("_getRequestedShape() No edges in shape.")
        return Part.Shape()

    if obj.ShapeType == "3DSolid":
        extDist = obj.StartDepth.Value - obj.FinalDepth.Value
        # extDist = obj.StartDepth.Value - obj.ModelFeatures.ZMin
        if Path.Geom.isRoughly(extDist, 0.0):
            FreeCAD.Console.PrintWarning(
                "Extrude distance of 0.0 increased to 1.0 mm.\n"
            )
            extDist = 1.0
        ext = shape.extrude(FreeCAD.Vector(0.0, 0.0, extDist))
        ext.translate(
            FreeCAD.Vector(0.0, 0.0, obj.FinalDepth.Value - ext.BoundBox.ZMin)
        )
        mdls = [
            getattr(obj.ModelFeatures, p)
            for p in obj.ModelFeatures.PropertiesList
            if p.startswith("Mdl_")
        ]
        if len(mdls) == 0:
            mdls = [
                FreeCAD.ActiveDocument.getObject(n).Shape
                for n in obj.ModelFeatures.ModelNames
            ]
        if haveNonplanar:
            models = [
                RegionUtils.MeshTools.shapeToMeshSolid(
                    mdl, obj.LinearDeflection, obj.AngularDeflection
                )
                for mdl in mdls
            ]
        else:
            models = mdls

        shape = ext
        for m in models:
            cut = ext.cut(m)
            shape = cut

        shape.translate(
            FreeCAD.Vector(0.0, 0.0, obj.FinalDepth.Value - shape.BoundBox.ZMin)
        )

        # print(f"shape.Solids: {len(shape.Solids)}")

        return shape
    elif obj.ShapeType == "ExtrudedRegion":
        extDist = obj.StartDepth.Value - obj.FinalDepth.Value
        if Path.Geom.isRoughly(extDist, 0.0):
            FreeCAD.Console.PrintWarning(
                "Extrude distance of 0.0 increased to 1.0 mm.\n"
            )
            extDist = 1.0
        ext = shape.extrude(
            # FreeCAD.Vector(0.0, 0.0, obj.StartDepth.Value - obj.FinalDepth.Value)
            FreeCAD.Vector(0.0, 0.0, extDist)
        )
        ext.translate(
            FreeCAD.Vector(0.0, 0.0, obj.FinalDepth.Value - ext.BoundBox.ZMin)
        )
        return ext
    elif obj.ShapeType == "Region":
        if len(shape.Faces) > 0:
            shp = shape.copy()
            shp.translate(
                FreeCAD.Vector(0.0, 0.0, obj.FinalDepth.Value - shp.BoundBox.ZMin)
            )
            return shp
        Path.Log.warning("Check 'ShapeType': No faces available in shape. ")
        return Part.Shape()
    elif obj.ShapeType == "Wire":
        wire = RegionUtils.fuseShapes([w for w in shape.Wires])
        wire.translate(
            FreeCAD.Vector(0.0, 0.0, obj.FinalDepth.Value - wire.BoundBox.ZMin)
        )
        return wire

    print(f"_getRequestedShape() ShapeType unknown: {obj.ShapeType}")
    return Part.Shape()


def _highestSolid(shape):
    if len(shape.Edges) == 0:
        # print(f"_highestSolid() shape has no Edges. Returning Part.Shape()")
        return Part.Shape()

    solid = None
    zMax = shape.BoundBox.ZMin
    # print(f"len(shape.Solids): {len(shape.Solids)}")
    if len(shape.Solids) > 0:
        for s in shape.Solids:
            if s.BoundBox.ZMax > zMax:
                zMax = s.BoundBox.ZMax
                solid = s.copy()
    else:
        solid = shape

    return solid


class ObjectWorkingShape(object):
    @classmethod
    def propertyDefinitions(cls):
        Path.Log.track()
        # Standard properties
        definitions = [
            (
                "App::PropertyBool",
                "Active",
                "Base",
                translate(
                    "App::Property",
                    "Make False, to prevent dressup from generating code",
                ),
            ),
            (
                "App::PropertyLink",
                "Rotation",
                "Dependencies",
                translate("App::Property", "Linked object containing rotation data."),
            ),
            (
                "App::PropertyLink",
                "ModelFeatures",
                "Dependencies",
                translate("App::Property", "Linked object containing model features."),
            ),
            (
                "App::PropertyLink",
                "ExtendFeatures",
                "Dependencies",
                translate(
                    "App::Property",
                    "Linked sketch object containing feature extension regions.",
                ),
            ),
            (
                "App::PropertyLink",
                "TrimFeatures",
                "Dependencies",
                translate(
                    "App::Property",
                    "Linked sketch object containing feature trim regions.",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "ExtraShape",
                "Shape",
                translate(
                    "App::Property",
                    "Extra Part.Shape() container.",
                ),
            ),
            (
                "App::PropertyBool",
                "IncludeHoles",
                "Shape",
                translate("Path", "Set True to respect feature holes."),
            ),
            (
                "App::PropertyBool",
                "RespectMergedHoles",
                "Shape",
                translate(
                    "Path",
                    "Set True to respect holes formed by merger of faces or regions.",
                ),
            ),
            (
                "App::PropertyEnumeration",
                "ShapeType",
                "Shape",
                translate(
                    "Path",
                    "Select the intended shape type.",
                ),
            ),
            (
                "App::PropertyBool",
                "IncludeProfile",
                "Shape",
                translate("Path", "Set True to include profile in shape."),
            ),
            (
                "App::PropertyBool",
                "TrimToStock",
                "Shape",
                translate("Path", "Set True to trim shape to stock."),
            ),
            (
                "App::PropertyDistance",
                "DiscretizeValue",
                "Mesh",
                translate(
                    "App::Property",
                    "Discretize value to use when discretizing curves.",
                ),
            ),
            (
                "App::PropertyAngle",
                "AngularDeflection",
                "Mesh",
                translate(
                    "App::Property",
                    "Smaller values yield a finer, more accurate mesh. Smaller values increase processing time a lot.",
                ),
            ),
            (
                "App::PropertyDistance",
                "LinearDeflection",
                "Mesh",
                translate(
                    "App::Property",
                    "Smaller values yield a finer, more accurate mesh. Smaller values do not increase processing time much.",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "Stock",
                "ModelShapes",
                translate(
                    "App::Property",
                    "Part.Shape() container for rotated Job.Stock object.",
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
            "ShapeType": (
                (translate("Path", "Wire"), "Wire"),
                (translate("Path", "Region"), "Region"),
                (translate("Path", "Extruded Region"), "ExtrudedRegion"),
                (translate("Path", "3D Solid"), "3DSolid"),
            ),
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
            "ShapeType": "Region",  # Wire, Region, Extrusion, 3D
            "IncludeProfile": True,
            "IncludeHoles": True,
            "RespectMergedHoles": True,
            "DiscretizeValue": 2.0,
            "AngularDeflection": 30.0,
            "LinearDeflection": 2.0,
            "PlacementCorrection": False,
        }

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getValues = getattr(Features, f + "DefaultValues")
            vals = getValues(job, obj, flags)
            if vals:
                for k, v in vals.items():
                    defaults[k] = v

        return defaults

    def __init__(self, obj, parentJob=None):
        # Path.Log.info("ObjectWorkingShape.__init__()")
        self.readyToExecute = True  # Flag used in canceling edit via task panel
        self.obj = obj
        self.rotations = None
        if parentJob is None:
            # self.job = PathUtils.findParentJob(obj)
            self.job = PathUtils.addToJob(obj)
        else:
            self.job = parentJob
            self.job.Proxy.addOperation(obj)

        definitions = ObjectWorkingShape.propertyDefinitions()
        enumerations = ObjectWorkingShape.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(obj, definitions, enumerations)
        self._setEditorModes(obj)

        # Set default values
        propDefaults = ObjectWorkingShape.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setEditorModes(self, obj):
        # obj.setEditorMode("OpStartDepth", 1)  # read-only
        # obj.setEditorMode("OpFinalDepth", 1)  # read-only
        pass

    def _setReadyToExecute(self, value):
        # print(f"WorkingShape.readyToExecute = {value}")
        self.readyToExecute = value

    def onDelete(self, obj, args):
        if obj.TrimFeatures:
            name = obj.TrimFeatures.Name
            obj.TrimFeatures = None
            FreeCAD.ActiveDocument.removeObject(name)
        if obj.ExtendFeatures:
            name = obj.ExtendFeatures.Name
            obj.ExtendFeatures = None
            FreeCAD.ActiveDocument.removeObject(name)
        if obj.ModelFeatures:
            name = obj.ModelFeatures.Name
            obj.ModelFeatures = None
            FreeCAD.ActiveDocument.removeObject(name)
        if obj.Rotation:
            name = obj.Rotation.Name
            obj.Rotation = None
            FreeCAD.ActiveDocument.removeObject(name)
        return True

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.job = PathUtils.findParentJob(obj)
        definitions = ObjectWorkingShape.propertyDefinitions()
        enumerations = ObjectWorkingShape.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(
            obj, definitions, enumerations, warn=True
        )
        propDefaults = ObjectWorkingShape.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)
        self._setEditorModes(obj)
        self.readyToExecute = True  # Flag used in canceling edit via task panel

    def onChanged(self, obj, prop):
        """onChanged(obj, prop) ... method called when objECT is changed,
        with source propERTY of the change."""

        if "Restore" in obj.State:
            pass
        elif prop in [
            "Rotation",
            "ModelFeatures",
            "StartDepth",
            "FinalDepth",
        ]:
            # print(f"WorkingShape.onChange({prop}) calling _updateDepths()")
            _updateDepths(self.job, obj)

    def _getRegion(self, obj):
        regAreas = []
        outerOpenWires = []
        haveNonplanar = False
        points, edges, faces, models = _getFeatureShapes(self.job, obj)
        # print(
        #    f"_getRegion() points: {len(points)},  edges: {len(edges)},  faces: {len(faces)},  models: {len(models)}"
        # )

        # rawCompound = Part.makeCompound(edges + faces + models)
        # Part.show(rawCompound, "Features")
        # return rawCompound, haveNonplanar

        edgeFaces, openWires = RegionUtils.edgesToFaces2(edges)
        openFaces = RegionUtils.openWiresToFaces(obj, openWires)
        modelFaces = RegionUtils.modelsToRegions(
            models, True, obj.LinearDeflection, obj.AngularDeflection
        )

        allFaces = faces + edgeFaces + openFaces + modelFaces
        if len(points) > 0:
            Path.Log.info("Points available!")

        if len(openWires) > 0:
            Path.Log.info("Open wires available!")

        # if len(allFaces) > 0:
        #    Path.Log.info("Faces available!")

        if len(allFaces) == 0:
            Path.Log.warning("No faces available. 'allFaces' is empty.")
            return None, outerOpenWires, haveNonplanar

        # Part.show(Part.makeCompound(allFaces), f"{obj.Label}_AllFaces")

        planar, nonplanar = RegionUtils._separateNonplanarFaces(allFaces)
        # print(f"_getRegion() len(planar): {len(planar)}")
        # print(f"_getRegion() len(nonplanar): {len(nonplanar)}")
        # Part.show(Part.makeCompound(planar), "Planar1")

        if nonplanar:
            FreeCAD.Console.PrintWarning("Processing nonplanar faces.\n")
            for f in nonplanar:
                rslt, regMin = RegionUtils.MeshTools.faceToRegion(
                    f, obj.LinearDeflection, obj.AngularDeflection
                )
                if rslt is not None:
                    planar.append(rslt)
                    haveNonplanar = True
        else:
            # print("_getRegion() no 'nonplanar' shapes")
            pass

        plnr = []
        for p in planar:
            cp = p.copy()
            cp.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - cp.BoundBox.ZMin))
            plnr.append(cp)

        # if plnr:
        #    Part.show(Part.makeCompound(plnr), "Planar_Faces")
        # if nonplanar:
        #    Part.show(Part.makeCompound(nonplanar), "NonplanarRaw")

        # print(f"len(regAreas) A: {len(regAreas)}")
        # print(f"len(planar) A: {len(planar)}")

        # Process planar regions collectively
        r, oow = RegionUtils.combineRegions(
            plnr,  # planar,
            0.0,
            obj.IncludeProfile,
            obj.IncludeHoles,
            obj.RespectMergedHoles,
        )
        outerOpenWires.extend(oow)
        if r and r.Area > 0.000001:
            regAreas.append(r)

        # print(f"len(regAreas) B: {len(regAreas)}")

        # Process planar regions independently
        # for p in planar:
        for p in plnr:
            # Part.show(p, "Planar")
            flat = RegionUtils._flattenSingleFace(p)
            if len(flat.Faces) == 0:
                outerOpenWires.extend(flat.Wires)
            else:
                # print("processing closed planar face")
                r2, oow2 = RegionUtils.combineRegions(
                    flat.Faces,
                    0.0,
                    obj.IncludeProfile,
                    obj.IncludeHoles,
                    obj.RespectMergedHoles,
                )
                outerOpenWires.extend(oow2)
                if r2:
                    if r2.Area > 0.00001:
                        regAreas.append(r2)
                    else:
                        # print("r2.Area < 0.00001 - not included")
                        # Part.show(p, "Planar_No_r2_area")
                        pass
                else:
                    # Path.Log.info("No 'r2' shape.")
                    pass
        # Efor

        # print(f"_getRegion() len(planar) 2: {len(planar)}")
        # print(f"len(regAreas) C: {len(regAreas)}")

        # if len(planar) == 0:
        if len(regAreas) == 0:
            FreeCAD.Console.PrintWarning("_getRegion() No region to return.\n")
            return None, outerOpenWires, haveNonplanar

        region = RegionUtils.fuseShapes(regAreas)
        # Part.show(region, "WorkingShape685_Raw_Region")
        if not region:
            Path.Log.info("_getRegion() 'region' is 'None'")
            region = None  # Part.Shape()

        if len(outerOpenWires) > 0:
            Path.Log.info("Open outer wires available!")

        if region:
            region.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - region.BoundBox.ZMin))
            # print("WorkingShape._getRegion()  region exists, translated and returned")
            # Part.show(region, "WS_Raw_Region")
            return (region, outerOpenWires, haveNonplanar)

        print("_getRegion() No region to return.")
        return None, outerOpenWires, haveNonplanar

    def _getRegion_alt(self, obj):
        regAreas = []
        outerOpenWires = []
        haveNonplanar = False
        points, edges, faces, models = _getFeatureShapes(self.job, obj)
        # print(
        #    f"_getRegion() points: {len(points)},  edges: {len(edges)},  faces: {len(faces)},  models: {len(models)}"
        # )

        # rawCompound = Part.makeCompound(edges + faces + models)
        # Part.show(rawCompound, "Features")
        # return rawCompound, haveNonplanar

        edgeFaces, openWires = RegionUtils.edgesToFaces2(edges)
        openFaces = RegionUtils.openWiresToFaces(obj, openWires)
        modelFaces = RegionUtils.modelsToRegions(
            models, True, obj.LinearDeflection, obj.AngularDeflection
        )

        allFaces = faces + edgeFaces + openFaces + modelFaces
        if len(points) > 0:
            # Path.Log.info("_getRegion() Points available!")
            pass

        if len(openWires) > 0:
            # Path.Log.info("_getRegion() Open wires available!")
            pass

        if len(allFaces) > 0:
            # Path.Log.info("_getRegion() Faces available!")
            pass

        if len(allFaces) == 0:
            Path.Log.warning("_getRegion() No faces available. 'allFaces' is empty.")
            return None, outerOpenWires, haveNonplanar

        # Part.show(Part.makeCompound(allFaces), f"{obj.Label}_AllFaces")

        planar, nonplanar = RegionUtils._separateNonplanarFaces(allFaces)
        if nonplanar:
            FreeCAD.Console.PrintWarning("Processing nonplanar faces.\n")
            for f in nonplanar:
                rslt, regMin = RegionUtils.MeshTools.faceToRegion(
                    f, obj.LinearDeflection, obj.AngularDeflection
                )
                if rslt is not None:
                    planar.append(rslt)
                    haveNonplanar = True
        else:
            # print("_getRegion() no 'nonplanar' shapes")
            pass

        plnr = []
        for p in planar:
            cp = p.copy()
            cp.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - cp.BoundBox.ZMin))
            plnr.append(cp)

        # if plnr:
        #     Part.show(Part.makeCompound(plnr), "Planar_Faces")
        # if nonplanar:
        #    Part.show(Part.makeCompound(nonplanar), "NonplanarRaw")

        # print(f"len(regAreas) A: {len(regAreas)}")
        # print(f"len(planar) A: {len(planar)}")

        # Process planar regions collectively
        cr, oow = RegionUtils.combineRegions(
            plnr,
            0.0,
            obj.IncludeProfile,
            obj.IncludeHoles,
            obj.RespectMergedHoles,
        )
        if oow:
            outerOpenWires.extend(oow)
        if cr:
            # print("r exists after regionUtils.combineRegions()")
            for fc in cr.Faces:
                if fc.Area > 0.000001:
                    regAreas.append(fc.copy())
                    # print("fc.Area above threshold, adding to regAreas")
                else:
                    # print("r2.Area < 0.00001 - not included")
                    pass

        # print(f"len(regAreas) B: {len(regAreas)}")

        # Process planar regions independently
        """
        # for p in planar:
        for p in plnr:
            # Part.show(p, "Planar")
            flat = RegionUtils._flattenSingleFace(p)
            if len(flat.Faces) == 0:
                outerOpenWires.extend(flat.Wires)
            else:
                print("processing closed planar face")
                r2, oow2 = RegionUtils.combineRegions(
                    flat.Faces,
                    0.0,
                    obj.IncludeProfile,
                    obj.IncludeHoles,
                    obj.RespectMergedHoles,
                )
                outerOpenWires.extend(oow2)
                if r2:
                    if r2.Area > 0.00001:
                        regAreas.append(r2)
                    else:
                        print("r2.Area < 0.00001 - not included")
                        Part.show(p, "Planar_No_r2_area")
                else:
                    Path.Log.info("No 'r2' shape.")
        # Efor
        """

        # print(f"_getRegion() len(planar) 2: {len(planar)}")
        # print(f"len(regAreas) C: {len(regAreas)}")

        if len(regAreas) == 0:
            FreeCAD.Console.PrintWarning("_getRegion() No region to return.\n")
            return None, outerOpenWires, haveNonplanar

        region = RegionUtils.fuseShapes(regAreas)
        # Part.show(region, "WorkingShape685_Raw_Region")
        if not region:
            Path.Log.info("_getRegion() 'region' is 'None'")
            region = None  # Part.Shape()

        if len(outerOpenWires) > 0:
            Path.Log.info("Open outer wires available!")

        if region:
            region.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - region.BoundBox.ZMin))
            # print("WorkingShape._getRegion()  region exists, translated and returned")
            # Part.show(region, "WS_Raw_Region")
            return (region, outerOpenWires, haveNonplanar)

        print("_getRegion() No region to return.")
        return None, outerOpenWires, haveNonplanar

    def _combineRegions_orig(self, rgn, extend, trim):
        # print(
        #    f"_combineRegions() rgn: {True if rgn else False},  extend: {True if extend else False},  trim: {True if trim else False}"
        # )
        if rgn:
            # print("_combineRegions() has region")
            if extend:
                # print("   ... has extend")
                fused = rgn.fuse(extend)
                if trim:
                    # print("   ... has trim")
                    shape = fused.cut(trim)
                else:
                    shape = fused
            elif trim:
                # print("   ... has trim")
                shape = rgn.cut(trim)
            else:
                shape = rgn
        else:
            FreeCAD.Console.PrintWarning("_combineRegions() NO region received.\n")
            if extend:
                if trim:
                    shape = extend.cut(trim)
                else:
                    shape = extend
            # elif trim:
            #    shape = trim
            else:
                shape = None
        # Eif

        # return RegionUtils._refinePlanarFaces(shape.Faces)
        # return shape
        if shape is None or len(shape.Edges) == 0 or shape.Area < 0.0001:
            FreeCAD.Console.PrintWarning(f"_combineRegions() returning None.\n")
            return None

        # Part.show(shape, "Shape_preconsolidate")
        # print("_combineRegions() now consolidating flat face...")
        return RegionUtils._consolidateFlatFace(shape)

    def _combineRegions(self, rgn, extend, trim):
        # print(
        #    f"_combineRegions() rgn: {True if rgn else False},  extend: {True if extend else False},  trim: {True if trim else False}"
        # )
        if rgn:
            # print("_combineRegions() has region")
            if extend:
                # print("   ... has extend")
                fused = rgn.fuse(extend)
                if trim:
                    # print("   ... has trim")
                    shape = fused.cut(trim)
                else:
                    shape = fused
            elif trim:
                # print("   ... has trim")
                shape = rgn.cut(trim)
            else:
                shape = rgn
        else:
            FreeCAD.Console.PrintWarning("_combineRegions() NO region received.\n")
            if extend:
                if trim:
                    shape = extend.cut(trim)
                else:
                    shape = extend
            # elif trim:
            #    shape = trim
            else:
                shape = None
        # Eif

        # return RegionUtils._refinePlanarFaces(shape.Faces)
        # return shape
        if shape is None or len(shape.Edges) == 0 or shape.Area < 0.0001:
            FreeCAD.Console.PrintWarning(f"_combineRegions() returning None.\n")
            return None

        # Part.show(shape, "Shape_preconsolidate")
        # print("_combineRegions() now consolidating flat face...")
        return shape

    def _getExtendShape(self, obj, rotations):
        extend = None
        e = SupportSketch._getSketchRegion(obj.ExtendFeatures.Name)
        if e:
            if rotations:
                extend = AlignToFeature.rotateShapeWithList(e, rotations)
            else:
                extend = e
            extend.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - extend.BoundBox.ZMin))
        return extend

    def _getTrimShape(self, obj, rotations):
        trim = None
        t = SupportSketch._getSketchRegion(obj.TrimFeatures.Name)
        if t:
            if rotations:
                trim = AlignToFeature.rotateShapeWithList(t, rotations)
            else:
                trim = t
            trim.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - trim.BoundBox.ZMin))
        return trim

    def _applyPlacement(self, obj, rotations):
        zMin = 0.0 if obj.TrimToStock else obj.FinalDepth.Value
        AlignToFeature.clearObjectPlacement(obj)
        if rotations:
            if obj.ShapeType == "3DSolid":
                zMin = 0.0
                AlignToFeature.setObjectPlacementFullAlt(obj, zMin, rotations)
            elif obj.ShapeType == "ExtrudedRegion":
                AlignToFeature.setObjectPlacementFullAlt(obj, zMin, rotations)

            elif obj.ShapeType == "Region":
                AlignToFeature.setObjectPlacementFullAlt(obj, zMin, rotations)

            elif obj.ShapeType == "Wire":
                AlignToFeature.setObjectPlacementFullAlt(obj, zMin, rotations)

            else:
                FreeCAD.Console.PrintError(
                    f"{obj.Name}.ShapeType needs placement calculation for {obj.ShapeType}"
                )
        else:
            AlignToFeature.clearObjectPlacement(obj)
            if obj.ShapeType == "3DSolid":
                zMin = 0.0 if not obj.TrimToStock else zMin
            elif obj.ShapeType == "ExtrudedRegion":
                pass
            elif obj.ShapeType == "Region":
                pass
            elif obj.ShapeType == "Wire":
                pass
            else:
                FreeCAD.Console.PrintError(
                    f"{obj.Name}.ShapeType needs placement resetting calculation for {obj.ShapeType}"
                )
            AlignToFeature.setObjectPlacementFull(
                obj, FreeCAD.Vector(0.0, 0.0, zMin), []
            )

    #########################
    #########################

    def showShape(self, obj):
        Part.show(obj.Shape, "WS_Shape")

    def execute(self, obj):
        Path.Log.track()

        if not self.readyToExecute:
            FreeCAD.Console.PrintWarning("WorkingShape.execute() ** CANCELLED **\n")
            self.readyToExecute = True
            return

        if not obj.Active:
            return

        # Update object depths
        _updateDepths(self.job, obj)
        ObjectTools.updateExpression(obj, "StartDepth")
        ObjectTools.updateExpression(obj, "FinalDepth")
        # _printDepths(obj)

        region = None
        haveNonplanar = False
        openWires = None
        stockShape = self.job.Stock.Shape

        # if obj.ModelFeatures:
        #    obj.ModelFeatures.Proxy.execute(obj.ModelFeatures)
        #    # obj.ModelFeatures.purgeTouched()
        #    obj.ModelFeatures.recompute()

        rotations = []
        if obj.Rotation:
            rotations = AlignToFeature.getRotationsList(obj.Rotation)
            # print(f"rotations: {rotations}")

        # Update sketches
        if rotations:
            _updateSketchesAlt(obj, rotations)
        elif obj.ModelFeatures:
            _resetSketches(obj)

        if obj.ModelFeatures:
            stockShape = obj.ModelFeatures.Stock
            region, oWires, haveNonplanar = self._getRegion(obj)

            """
            if region:
                Part.show(region, "Model_Region")
                print(f"region_zmin: {region.BoundBox.ZMin}")
            else:
                print(f"obj.ModelFeatures -> no region returned")
            """

            if oWires:
                openWires = Part.makeCompound(oWires)
                # Part.show(openWires, "OpenWires")

        extend = None
        if obj.ExtendFeatures:
            extend = self._getExtendShape(obj, rotations)
            if extend:
                extend.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - extend.BoundBox.ZMin))
                # Part.show(extend, "Model_Extend")
                # print(f"extend_zmin: {extend.BoundBox.ZMin}")

        trim = None
        if obj.TrimFeatures:
            trim = self._getTrimShape(obj, rotations)
            if trim:
                trim.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - trim.BoundBox.ZMin))
                # Part.show(trim, "Model_Trim")

        # if region:
        # print(f"region: {region}")
        # Part.show(region, "WS_Region_A")

        shape = self._combineRegions(region, extend, trim)
        PathGeom = RegionUtils.PathGeom
        # neg = PathGeom.makeBoundBoxFace(shape.BoundBox, 10.0).cut(shape)
        # clean = PathGeom.makeBoundBoxFace(shape.BoundBox, 5.0).cut(neg)
        # ready = RegionUtils._refinePlanarFaces(clean.Faces)

        if shape:
            # Part.show(shape, "Shape_Combined")
            # Clean planar 'shape', removing internal splitting edges
            big = PathGeom.makeBoundBoxFace(shape.BoundBox, 10.0)
            for fc in shape.Faces:
                cut = big.cut(fc)
                big = cut
            small = PathGeom.makeBoundBoxFace(shape.BoundBox, 5.0)
            cln = small.cut(big)
            # Part.show(cln, "Shape_Clean2")
            shape = cln
        # if clean:
        #    Part.show(clean, "Shape_Clean")
        #    shape = clean
        # if ready:
        #    Part.show(ready, "Shape_Ready")
        #    shape = ready

        if shape:
            # Part.show(shape, "WS_CombineRegions")
            # FreeCAD.Console.PrintWarning("CombineRegions shape returned.\n")
            pass
        elif openWires:
            shape = openWires
            FreeCAD.Console.PrintWarning(
                "No CombineRegions shape returned. Using OpenWires.\n"
            )
        else:
            # FreeCAD.Console.PrintWarning(
            #    "No CombineRegions shape returned, and no open wires available.\n"
            # )
            if region:
                # Part.show(region, "Raw_Region_2")
                pass

        if shape:
            # Part.show(shape, "Shapee")
            if obj.ShapeType == "3DSolid" and False:
                # _highestSolid() needs improvement to retain multiple solids
                rawShp = _highestSolid(
                    _getRequestedShape(self.job, obj, shape, rotations, haveNonplanar)
                )
            else:
                rawShp = _getRequestedShape(
                    self.job, obj, shape, rotations, haveNonplanar
                )

            # Part.show(rawShp, "RawShp")

            if obj.TrimToStock:
                obj.Shape = rawShp.common(stockShape)
            else:
                obj.Shape = rawShp

            # Apply necessary placement adjustments for alignment to model
            self._applyPlacement(obj, rotations)
        else:
            # print(f"{obj.Label}.execute() has NO SHAPE.")
            obj.Shape = Part.Shape()

        print(f"{obj.Label}.execute() completed and rotations={rotations}")


# Eclass


# Public function
def Create(parentJob=None, baseGeometry=[], addDependencies=False, name="WorkingShape"):
    """Create(base, name='WorkingShape') ... creates a Working Shape object with support objects."""
    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
    obj.Proxy = ObjectWorkingShape(obj, parentJob)
    if addDependencies:
        # _addDependencies_orig(obj)
        import freecad.camplus.workingshape.ModelFeatures as ModelFeatures
        import freecad.camplus.workingshape.RotationFeatures as RotationFeatures
        import freecad.camplus.utilities.SupportSketch as SupportSketch

        r = RotationFeatures.Create(obj)
        obj.Rotation = r
        obj.ModelFeatures = ModelFeatures.Create(
            obj,
            r,
            baseGeometry,
        )
        obj.ExtendFeatures = SupportSketch.addSketch(obj, name="Extend")
        obj.TrimFeatures = SupportSketch.addSketch(obj, name="Trim")

    FreeCAD.ActiveDocument.recompute()
    return obj


Path.Log.notice("Loaded WorkingShape...\n")
