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
import freecad.camplus.utilities.AlignToFeature as AlignToFeature


__title__ = "Rotation Features"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Creates a Rotation Features object."
__usage__ = "Import this module.  Run the 'Create(base)' function, passing it the desired base operation."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


"""
Part::GeomCircle
Part::GeomBSplineCurve
Part::GeomLine
Part::GeomEllipse
Part::GeomHyperbola
"""

translate = FreeCAD.Qt.translate


def _verifyFeatureSet(tup):
    baseObj, features = tup
    if len(features) == 1:
        if features[0].startswith("Face"):
            return True
        elif features[0].startswith("Edge"):
            e = baseObj.Shape.getElement(features[0])
            if e.Curve.TypeId == "Part::GeomLine":
                return False
            elif e.Curve.TypeId == "Part::GeomCircle":
                return True
            else:
                return False


FEATURES_DICT = {
    # "HeightsDepths": [
    #    "NoClearanceHeight",
    #    "NoSafeHeight",
    #    "NoFinishDepth",
    #    "NoStepDown",
    # ],
    "BaseGeometry": ["AllowFaces", "AllowEdges"],
    # "Extensions": [],
    # "Locations": [],
    # "HoleGeometry": ["AllowVertexes"],
    # "Rotation": [],
    # "ToolController": ["NoTaskPanel"],
    # "Coolant": ["NoTaskPanel"],
}


class ObjectRotationFeatures(object):
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
                "App::PropertyString",
                "ParentName",
                "Rotation",
                translate(
                    "App::Property",
                    "Stores name of parent Working Shape object.",
                ),
            ),
            (
                "App::PropertyBool",
                "EnableRotation",
                "Rotation",
                translate(
                    "App::Property",
                    "Set TRUE, to disable rotation calculation and usage.",
                ),
            ),
        ]

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getProps = getattr(Features, f + "PropertyDefinitions")
            definitions.extend(getProps(flags))

        # Get Rotation definitions
        definitions.extend(Features.RotationPropertyDefinitions())

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

        # Get Rotation enumerations
        vals = Features.RotationEnumerations(flags)
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
            "EnableRotation": True,
        }

        # Add operation feature property definitions
        for f, flags in FEATURES_DICT.items():
            getValues = getattr(Features, f + "DefaultValues")
            vals = getValues(job, obj, flags)
            if vals:
                for k, v in vals.items():
                    defaults[k] = v

        # Get Rotation property default values
        vals = Features.RotationDefaultValues(job, obj, flags)
        if vals:
            for k, v in vals.items():
                defaults[k] = v

        return defaults

    def __init__(self, obj, parent, baseGeometry=[]):
        # Path.Log.info("ObjectRotationFeatures.__init__()")
        self.readyToExecute = True  # Flag used in canceling edit via task panel
        self.obj = obj
        self.rotations = None
        self.job = PathUtils.findParentJob(parent)
        # self.job = PathUtils.addToJob(obj)
        # self.job.Proxy.addOperation(obj)

        definitions = ObjectRotationFeatures.propertyDefinitions()
        enumerations = ObjectRotationFeatures.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(obj, definitions, enumerations)
        self._setEditorModes(obj)

        # Set default values
        propDefaults = ObjectRotationFeatures.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)

        for bs, feats in baseGeometry:
            for f in feats:
                self.addBase(obj, bs, f)

        obj.ParentName = parent.Name

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setEditorModes(self, obj):
        obj.setEditorMode("ParentName", 1)  # read-only

    def _setReadyToExecute(self, value):
        # print(f"RotationFeatures.readyToExecute = {value}")
        self.readyToExecute = value

    def onDelete(self, obj, args):
        # if obj.RotationIndex:
        #    name = obj.RotationIndex.Name
        #    obj.RotationIndex = None
        #    FreeCAD.ActiveDocument.removeObject(name)
        return True

    def _updateExpressionEngine(self, obj):
        print("_updateExpressionEngine(obj)")
        return

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.job = PathUtils.findParentJob(
            FreeCAD.ActiveDocument.getObject(obj.ParentName)
        )
        definitions = ObjectRotationFeatures.propertyDefinitions()
        enumerations = ObjectRotationFeatures.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(
            obj, definitions, enumerations, warn=True
        )
        propDefaults = ObjectRotationFeatures.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)
        self._setEditorModes(obj)
        self.readyToExecute = True  # Flag used in canceling edit via task panel

    def onChanged(self, obj, prop):
        """onChanged(obj, prop) ... method called when objECT is changed,
        with source propERTY of the change."""

        if "Restore" in obj.State:
            pass
        elif prop in ["Base", "EnableRotation"]:
            # ws = FreeCAD.ActiveDocument.getObject(obj.ParentName)
            # ws.Proxy.onChanged(ws, "Rotation")
            pass

    def _verifyRotationBase(self, base):
        # Expected 'base' format is [(baseObj, (featName,))]
        if not base:
            return False
        if len(base) != 1:
            FreeCAD.Console.PrintError(
                f"{self.obj.Name}.Base has multiple bases included.\n"
            )
            return False
        if len(base[0][1]) != 1:  # tuple of features
            FreeCAD.Console.PrintError(
                f"{self.obj.Name}.Base has multiple features included.\n"
            )
            return False
        if not isinstance(base[0][1][0], str):
            FreeCAD.Console.PrintError(
                f"{self.obj.Name}.Base has feature that is not a string.\n"
            )
            return False
        try:
            # base object is accessible
            b = FreeCAD.ActiveDocument.getObject(base[0][0].Name)
        except:
            return False
        try:
            # feature on base object is accessible
            f = b.Shape.getElement(base[0][1][0])
        except:
            return False
        return True

    def _calculateRotations(self, obj):
        if self._verifyRotationBase(obj.Base):
            tup = obj.Base[0]
            base = tup[0]
            subs = tup[1]
            # print(
            #    f"_calculateRotations() calculating rotation... {base.Name}.{subs[0]}"
            # )
            # calculate rotations and store in obj properties
            if len(subs) == 1:
                ft = subs[0]
                if ft.startswith("Face"):
                    rotations = AlignToFeature.getRotationToFace(base.Shape, ft)
                elif ft.startswith("Edge"):
                    # Part.show(
                    #    AlignToFeature._getNonlinearEdgePlaneFace(
                    #        base.Shape.getElement(ft)
                    #    ),
                    #    "NLEdgeFace",
                    # )
                    rotations = AlignToFeature.getRotationToEdge(
                        base.Shape.getElement(ft)
                    )
                else:
                    FreeCAD.Console.PrintError(
                        f"{ft} is not supported for rotation base.\n"
                    )
                    rotations = []
                if obj.InvertRotation:
                    return AlignToFeature.invertRotation(rotations)
                else:
                    return rotations
            else:
                FreeCAD.Console.PrintError("_calculateRotations() error\n")
        return []

    def _storeRotationsList(self, rotations):
        if rotations:
            AlignToFeature.storeRotationsInObject(rotations, self.obj)
        else:
            AlignToFeature.clearRotationsInObject(self.obj)

    # Regular functions
    def addBase(self, obj, base, sub, prop="Base"):
        Path.Log.track(obj, base, sub)
        base = Path.Base.Util.getPublicObject(base)

        for model in self.job.Model.Group:
            if base == self.job.Proxy.baseObject(self.job, model):
                base = model
                break

        # For faces, require flat, planar faces as rotational reference
        if sub.startswith("Face"):
            f = base.Shape.getElement(sub)
            if f.Surface.TypeId != "Part::GeomPlane":
                Path.Log.warning(
                    (translate("Path", "Base object %s.%s is not planar.") + "\n")
                    % (base.Label, sub)
                )
                return

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

    def getRotations(self):
        return AlignToFeature.getRotationsList(self.obj)

    def showShape(self):
        Part.show(self.obj.Shape, "RF_Shape")

    def execute(self, obj):
        Path.Log.track()

        if not self.readyToExecute:
            FreeCAD.Console.PrintWarning("RotationFeatures.execute() ** CANCELLED **\n")
            self.readyToExecute = True
            return

        if not obj.Active:
            return

        if obj.EnableRotation:
            rotations = self._calculateRotations(obj)
            self._storeRotationsList(rotations)
        else:
            self._storeRotationsList([])

        p, e, f, m, __ = ObjectTools.getAllBaseShapes(obj)
        shapes = p + e + f + m
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 0 else Part.Shape()

        # mf = FreeCAD.ActiveDocument.getObject(obj.ParentName).ModelFeatures
        # if mf:
        #    mf.Proxy.execute(mf)
        #    mf.purgeTouched()

        print(f"RotationFeatures.execute() Completed.  len(shapes) = {len(shapes)}")


# Eclass


# Public function
def Create(parent, baseGeometry=[], name="RotationFeatures"):
    """Create(base, name='RotationFeatures') ... creates a Rotation Features object with support objects."""

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
    obj.Proxy = ObjectRotationFeatures(obj, parent, baseGeometry)
    FreeCAD.ActiveDocument.recompute()
    return obj


Path.Log.notice("Loaded RotationFeatures...\n")
