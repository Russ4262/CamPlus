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

# import PathScripts.PathUtils as PathUtils
# import freecad.camplus.features.Features as Features
# import freecad.camplus.utilities.Generators as Generators
# import freecad.camplus.utilities.Slice as SliceUtils
# import freecad.camplus.utilities.AlignToFeature as AlignToFeature


__title__ = "Object Tools"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Support functions for Path objects."
__usage__ = ""
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

isDebug = False
translate = FreeCAD.Qt.translate


def findParentJob(obj):
    if obj.Name.startswith("Job"):
        return obj
    elif obj.Name.startswith("Operations"):
        for o in obj.InList:
            if o.Name.startswith("Job"):
                return o
    for o in obj.InList:
        out = findParentJob(o)
        if out.Name.startswith("Job"):
            return out
    return None


def initProperties(obj, definitions, enumerations, warn=False):
    """_initProperties(obj) ... create operation specific properties"""
    Path.Log.track()
    addedProperties = []

    for prtyp, nm, grp, tt in definitions:
        if not hasattr(obj, nm):
            obj.addProperty(prtyp, nm, grp, tt)
            addedProperties.append(nm)

    # Set enumeration lists for enumeration properties
    if len(addedProperties) > 0:
        for k, tupList in enumerations.items():
            if k in addedProperties:
                setattr(obj, k, [t[1] for t in tupList])

        if warn:
            newPropMsg = translate("Path", "New property added to")
            newPropMsg += ' "{}": {}'.format(obj.Label, addedProperties) + ". "
            newPropMsg += translate("Path", "Check default value(s).")
            FreeCAD.Console.PrintWarning(newPropMsg + "\n")

    return addedProperties


def applyPropertyDefaults(obj, propList, propDefaults):
    # PathLog.debug("applyPropertyDefaults(obj, propList, propDefaults)")
    # Set standard property defaults
    for n in propDefaults:
        if n in propList:
            prop = getattr(obj, n)
            val = propDefaults[n]
            setVal = False
            if hasattr(prop, "Value"):
                if isinstance(val, int) or isinstance(val, float):
                    setVal = True
            if setVal:
                # propVal = getattr(prop, 'Value')
                # Need to check if `val` below should be `propVal` commented out above
                setattr(prop, "Value", val)
            else:
                setattr(obj, n, val)


def getAllBaseShapes(obj):
    points = []
    edges = []
    faces = []
    models = []
    modelNames = []

    if not hasattr(obj, "Base"):
        return (points, edges, faces, models, modelNames)

    for base, subNames in obj.Base:
        modelNames.append(base.Name)
        for n in subNames:
            if n.startswith("Face"):
                faces.append(base.Shape.getElement(n).copy())
            elif n.startswith("Edge"):
                edges.append(base.Shape.getElement(n).copy())
            elif n.startswith("Vert"):
                points.append(base.Shape.getElement(n).copy())
            elif n == "":
                models.append(base.Shape)
            else:
                FreeCAD.Console.PrintError(f"{base.Name}:{n} is unusable.\n")
            # Eif
        # Efor
    # Efor

    return (points, edges, faces, models, modelNames)


def updateExpression(obj, propertyName):
    if hasattr(obj, "ExpressionEngine"):
        for prop, exp in obj.ExpressionEngine:
            if prop == propertyName:
                setattr(obj, prop, obj.evalExpression(exp))
                return True
    return False
