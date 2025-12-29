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
import Path
import PathScripts.PathUtils as PathUtils
import freecad.camplus.features.Features as Features
import freecad.camplus.utilities.ObjectTools as ObjectTools
import freecad.camplus.utilities.AlignToFeature as AlignToFeature

# import freecad.camplus.features.FeatureExtensions as FeatureExtensions
# import time

__title__ = "Model Features"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Using selected features, builds a shape purposed for a target shape."
__usage__ = "Import this module.  Run the 'Create(features)' function, passing it the desired features parameter,\
    as a list of tuples (base, features_list)."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate

FEATURES_DICT = {
    # "ToolController": ["NoTaskPanel"],
    # "Coolant": ["NoTaskPanel"],
    # "HeightsDepths": [
    #    "NoClearanceHeight",
    #    "NoSafeHeight",
    #    "NoFinishDepth",
    #    "NoStepDown",
    # ],
    "BaseGeometry": ["AllowEdges", "AllowFaces"],
    # "Extensions": [],
    "Locations": [],
    "HoleGeometry": ["AllowVertexes"],
    # "Rotation": [],
}


# Support functions
def _updateModelShapeProperties(job, obj, rotations):
    # Remove any existing 'Mdl_' properties
    for p in obj.PropertiesList:
        if p.startswith("Mdl_"):
            obj.removeProperty(p)

    # print(f"_updateModelShapeProperties() rotations: {rotations}")

    if len(rotations) == 0:
        obj.Stock = job.Stock.Shape
        return

    # models = job.Model.Group
    models = [m for (m, __) in obj.Base]
    for m in models:
        propName = f"Mdl_{m.Name}"
        # FreeCAD.Console.PrintWarning(f"{obj.Name}.{propName} has shape.\n")
        obj.addProperty(
            "Part::PropertyPartShape",
            propName,
            "ModelShapes",
            translate(
                "App::Property",
                f"Model shape container for" + f" {m.Name}",
            ),
        )
        setattr(
            obj,
            propName,
            AlignToFeature.rotateShapeWithList(m.Shape, rotations),
        )
        # print(f"Adding 'Mdl_{m.Name}' property")

    obj.Stock = AlignToFeature.rotateShapeWithList(job.Stock.Shape, rotations)


def getRotatedFeatureShapes(job, obj):
    points = []
    edges = []
    fcs = []
    models = []
    modelNames = []
    # parent = FreeCAD.ActiveDocument.getObject(obj.ParentName)

    for base, subNames in obj.Base:
        mdlProp = f"Mdl_{base.Name}"
        # Get rotated base shape
        if hasattr(obj, mdlProp):
            rotatedBase = getattr(obj, mdlProp)
            # print(
            #    f"ModelFeatures.getRotatedFeatureShapes() Using rotated base: {mdlProp}"
            # )
        else:
            rotatedBase = base.Shape
            # print(
            #    f"ModelFeatures.getRotatedFeatureShapes() Using standard base: {base.Name}"
            # )

        modelNames.append(base.Name)

        for n in subNames:
            if n.startswith("Face"):
                fcs.append(rotatedBase.getElement(n).copy())
            elif n.startswith("Edge"):
                edges.append(rotatedBase.getElement(n).copy())
            elif n.startswith("Vert"):
                points.append(rotatedBase.getElement(n).copy())
            elif n == "":
                models.append(rotatedBase)
            else:
                FreeCAD.Console.PrintError(f"{base.Name}:{n} is unusable.\n")
            # Eif
        # Efor
    # Efor

    if points or edges or fcs or models:
        # print(
        #    f"ModelFeatures.getRotatedFeatureShapes() Calculating zMin, zMax from features."
        # )
        zMin = min(
            [p.z for p in points] + [shp.BoundBox.ZMin for shp in edges + fcs + models]
        )
        zMax = max(
            [p.z for p in points] + [shp.BoundBox.ZMax for shp in edges + fcs + models]
        )
    else:
        # print(
        #    f"ModelFeatures.getRotatedFeatureShapes() Calculating zMin, zMax from job model(s) and stock."
        # )
        zMin = Part.makeCompound([m.Shape for m in job.Model.Group]).BoundBox.ZMax
        zMax = job.Stock.Shape.BoundBox.ZMax

    faces = fcs

    return points, edges, faces, models, (zMin, zMax), modelNames


class ModelFeatures(object):

    @classmethod
    def propertyDefinitions(cls):
        Path.Log.track()
        # Standard properties
        definitions = [
            (
                "App::PropertyString",
                "Comment",
                "Base",
                translate("PathOp", "An optional comment for this Operation"),
            ),
            (
                "App::PropertyString",
                "UserLabel",
                "Base",
                translate("PathOp", "User Assigned Label"),
            ),
            (
                "App::PropertyLink",
                "RotationObj",
                "Dependencies",
                translate("PathOp", "Linked object: Rotation"),
            ),
            (
                "App::PropertyString",
                "ParentName",
                "ModelFeatures",
                translate(
                    "App::Property",
                    "Stores name of parent Working Shape object.",
                ),
            ),
            (
                "App::PropertyFloat",
                "ZMin",
                "ModelFeatures",
                translate("Path", "Z minimum value of Base Features."),
            ),
            (
                "App::PropertyFloat",
                "ZMax",
                "ModelFeatures",
                translate("Path", "Z maximum value of Base Features."),
            ),
            (
                "App::PropertyStringList",
                "ModelNames",
                "ModelFeatures",
                translate("PathOp", "List of names of models referenced."),
            ),
            (
                "App::PropertyVectorList",
                "Vertexes",
                "Geometry",
                translate(
                    "App::Property",
                    "List of vertexes as points.",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "Edges",
                "Geometry",
                translate(
                    "App::Property",
                    "Part.Compound() container for selected edges.",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "Faces",
                "Geometry",
                translate(
                    "App::Property",
                    "Part.Compound() container for selected faces.",
                ),
            ),
            (
                "Part::PropertyPartShape",
                "Models",
                "Geometry",
                translate(
                    "App::Property",
                    "Part.Compound() container for selected models.",
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

        enums = {}

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

        defaults = {}

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getValues = getattr(Features, f + "DefaultValues")
            vals = getValues(job, obj, flags)
            if vals:
                for k, v in vals.items():
                    defaults[k] = v

        return defaults

    def __init__(self, obj, parent, rotation, baseGeometry=[]):
        # Path.Log.info("ModelFeatures.__init__()")
        self.obj = obj
        # self.job = PathUtils.addToJob(obj)
        self.job = PathUtils.findParentJob(parent)
        self.readyToExecute = True  # Flag used in canceling edit via task panel

        definitions = ModelFeatures.propertyDefinitions()
        enumerations = ModelFeatures.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(obj, definitions, enumerations)
        self._setEditorModes(obj)

        # Set default values
        propDefaults = ModelFeatures.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)

        for bs, feats in baseGeometry:
            for f in feats:
                self.addBase(obj, bs, f)

        obj.ParentName = parent.Name
        obj.RotationObj = rotation

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setEditorModes(self, obj):
        # obj.setEditorMode("OpStartDepth", 1)  # read-only
        # obj.setEditorMode("OpFinalDepth", 1)  # read-only
        pass

    def _setReadyToExecute(self, value):
        # print(f"ModelFeatures.readyToExecute = {value}")
        self.readyToExecute = value

    ##################################################
    ##################################################
    def onDocumentRestored(self, obj):
        self.obj = obj
        self.job = ObjectTools.findParentJob(obj)  # PathUtils.findParentJob(obj)
        # print(f"ModelFeatures.onDocumentRestored() self.job: {self.job}")
        self._setEditorModes(obj)
        self.readyToExecute = True  # Flag used in canceling edit via task panel

    def onDelete(self, obj, args):
        return True

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

        # print(f"ModelFeatures.onChange prop: {prop}")
        # there's a bit of cycle going on here, if sanitizeBase causes the transaction to
        # be cancelled we end right here again with the unsainitized Base - if that is the
        # case, stop the cycle and return immediately
        if prop == "Base" and sanitizeBase(obj):
            return

        if "Restore" in obj.State:
            pass
        elif prop in [
            "Base",
        ]:
            # _updateDepths(self.job, obj, True)
            pass
        # elif prop in ["RotationIndex",]:
        #    pass

        # print(f"onChange({prop}) finished")

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
                    (
                        translate(
                            "Path",
                            f"Base object {base.Label}.{sub} already in the list",
                        )
                        + "\n"
                    )
                )
                return

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

    ##################################################

    ##################################################

    def _allModels_orig(self):
        models = [
            getattr(self.obj, f"Mdl_{p}")
            for p in self.obj.PropertiesList
            if p.startswith("Mdl_")
        ]
        if models:
            return Part.makeCompound(models)
        return Part.Shape()

    def _allModels(self):
        models = [
            getattr(self.obj, p)
            for p in self.obj.PropertiesList
            if p.startswith("Mdl_")
        ]
        if models:
            return Part.makeCompound(models)
        return Part.Shape()

    def _usedModels(self):
        return [
            getattr(self.obj, p)
            for p in self.obj.PropertiesList
            if p.startswith("Mdl_") and p[4:] in self.obj.ModelNames
        ]

    def execute(self, obj):
        Path.Log.track()

        if not self.readyToExecute:
            FreeCAD.Console.PrintWarning("ModelFeatures.execute() ** CANCELLED **\n")
            self.readyToExecute = True
            return

        if hasattr(obj, "Active") and not obj.Active:
            return

        rotations = []
        if obj.RotationObj:
            rotations = AlignToFeature.getRotationsList(obj.RotationObj)
        # else:
        #    print("ModelFeatures.execute() no obj.RotationObj")

        # Create rotated models saved as Part.Shape property
        _updateModelShapeProperties(self.job, obj, rotations)

        # Get rotated feature shapes from rotated model shapes
        points, edges, faces, models, (zMin, zMax), modelNames = (
            getRotatedFeatureShapes(self.job, obj)
        )
        # Save rotated features by type, grouped as Part.Compound objects
        obj.Vertexes = points
        obj.Edges = Part.makeCompound(edges) if edges else Part.Shape()
        obj.Faces = Part.makeCompound(faces) if faces else Part.Shape()
        obj.Models = Part.makeCompound(models) if models else Part.Shape()
        obj.ModelNames = modelNames
        obj.ZMin = zMin
        obj.ZMax = zMax

        p, e, f, m, __ = ObjectTools.getAllBaseShapes(obj)
        obj.Shape = Part.makeCompound(p + e + f + m)

        # print(f"ModelFeatures ZMin: {zMin};  ZMax: {zMax}")
        # print(
        #    f"{obj.Label}.execute() Completed.\nrotations: {rotations} zMin: {zMin};  zMax: {zMax}"
        # )


# Eclass


def Create(parent, rotation, baseGeometry=[], name="ModelFeatures"):
    """Create(parent, rotation, baseGeometry=[], name="ModelFeatures")
    Creates a Model Features object."""

    if not isinstance(baseGeometry, list):
        Path.Log.error(
            translate(
                "ModelFeatures",
                "The baseGeometry parameter is not a list.",
            )
            + "\n"
        )
        return None

    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
    obj.Proxy = ModelFeatures(obj, parent, rotation, baseGeometry)
    return obj


Path.Log.notice("Loaded ModelFeatures...\n")
