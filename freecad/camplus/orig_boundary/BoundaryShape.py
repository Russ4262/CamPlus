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

import PathScripts.PathUtils as PathUtils
import freecad.camplus.features.Features as Features
import freecad.camplus.utilities.ObjectTools as ObjectTools
import freecad.camplus.utilities.SupportSketch as SupportSketch

__title__ = "Boundary Shape"
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

FEATURES_DICT = {}


class BoundaryShape(object):
    @classmethod
    def propertyDefinitions(cls):
        Path.Log.track()
        # Standard properties
        definitions = [
            (
                "App::PropertyString",
                "Comment",
                "Base",
                translate("Path", "An optional comment for this Operation"),
            ),
            (
                "App::PropertyString",
                "UserLabel",
                "Base",
                translate("Path", "User Assigned Label"),
            ),
            (
                "App::PropertyString",
                "DressupName",
                "Shape",
                translate("Path", "Name of the parent dressup."),
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

    def __init__(self, obj, dressup):
        # Path.Log.info("BoundaryShape.__init__()")
        self.obj = obj
        if hasattr(dressup.Proxy, "job"):
            self.job = dressup.Proxy.job  # PathUtils.addToJob(obj)
        else:
            self.job = PathUtils.findParentJob(dressup.Base)
        print(f"self.job.Name: {self.job.Name}")
        self.readyToExecute = True  # Flag used in canceling edit via task panel
        # self.job.Proxy.addOperation(obj, featShapeObj, True)

        definitions = BoundaryShape.propertyDefinitions()
        enumerations = BoundaryShape.propertyEnumerations(dataType="raw")
        addNewProps = ObjectTools.initProperties(obj, definitions, enumerations)
        self._setEditorModes(obj)

        # Set default values
        propDefaults = BoundaryShape.propertyDefaults(obj, self.job)
        ObjectTools.applyPropertyDefaults(obj, addNewProps, propDefaults)
        obj.DressupName = dressup.Name

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setEditorModes(self, obj):
        # obj.setEditorMode("OpStartDepth", 1)  # read-only
        # obj.setEditorMode("OpFinalDepth", 1)  # read-only
        pass

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.job = ObjectTools.findParentJob(obj)  # PathUtils.findParentJob(obj)
        self._setEditorModes(obj)
        self.readyToExecute = True  # Flag used in canceling edit via task panel

    def onDelete_old(self, obj, args):
        # print(f"BoundaryShape.onDelete()")
        for n in ["FeatureExtend", "FeatureTrim"]:
            prop = f"{n}"
            if hasattr(obj, prop):
                sn = getattr(obj, prop).Name
                setattr(obj, prop, None)
                FreeCAD.ActiveDocument.removeObject(sn)
        return True

    def onDelete(self, obj, args):
        sn = obj.BoundarySketch.Name
        setattr(obj, "BoundarySketch", None)
        FreeCAD.ActiveDocument.removeObject(sn)
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

        # there's a bit of cycle going on here, if sanitizeBase causes the transaction to
        # be cancelled we end right here again with the unsainitized Base - if that is the
        # case, stop the cycle and return immediately
        if prop == "Base" and sanitizeBase(obj):
            return

        if "Restore" in obj.State:
            pass
        """elif prop in [
            "Base",
            "StartDepth",
            "FinalDepth",
            "UseRotation",
            "RotationBase",
            "InvertRotation",
        ]:
            _updateDepths(self.job, obj, rotations, True)"""
        # print("onChange() finished")

    ##################################################

    def execute(self, obj):
        # print("BoundaryShape.execute()")
        recompute = False
        boundary = None
        # print(f"BS.execute() {obj.Name} rotations: {rotations}")

        sketchName = SupportSketch._addBoundarySketch(obj)
        boundary = SupportSketch._getSketchRegion(sketchName)
        if boundary is not None:
            obj.Shape = boundary
            sbb = self.job.Stock.Shape.BoundBox
            boundary.translate(FreeCAD.Vector(0.0, 0.0, sbb.ZMin))
            obj.Shape = boundary.extrude(FreeCAD.Vector(0.0, 0.0, sbb.ZLength))
        else:
            obj.Shape = Part.Shape()

        ####################################################################

        if obj.ViewObject and obj.ViewObject.Proxy:
            obj.ViewObject.Proxy.claimChildren()

        if recompute:
            FreeCAD.ActiveDocument.recompute()


# Eclass


def Create(dressup, obj=None):
    """Create(obj=None) ... create Boundary Shape object."""
    if obj is None:
        obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "BoundaryShape")
    obj.Proxy = BoundaryShape(obj, dressup)
    return obj


FreeCAD.Console.PrintMessage("Imported BoundaryShape module.\n")
