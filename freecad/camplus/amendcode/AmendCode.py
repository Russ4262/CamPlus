# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2023 Russell Johnson <russ4262> russ4262@gmail.com      *
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
from PySide.QtCore import QT_TRANSLATE_NOOP
import PathScripts.PathUtils as PathUtils

__title__ = "Amend Code Dressup"
__author__ = "Russell Johnson <russ4262>"
__doc__ = "Creates an Amend Code dressup on a base operation."
__usage__ = "Import this module.  Run the 'Create(base)' function, passing it the desired base operation."
__url__ = "https://github.com/Russ4262/CamPlus"
__Wiki__ = ""
__date__ = "2023.9.30"

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate


class DressupAmendCode(object):
    def __init__(self, obj, base, job):
        self.obj = obj
        self.job = job
        job.Proxy.addOperation(obj, base, True)

        self.safeHeight = None
        self.clearanceHeight = None
        self.readyToExecute = True  # Flag used in canceling edit via task panel

        obj.addProperty(
            "App::PropertyBool",
            "Active",
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property", "Make False, to prevent dressup from generating code"
            ),
        )
        obj.addProperty(
            "App::PropertyLink",
            "Base",
            "Dressup",
            QT_TRANSLATE_NOOP("App::Property", "The base path to modify"),
        )

        obj.addProperty(
            "App::PropertyEnumeration",
            "CodeLocation",
            "Dressup",
            QT_TRANSLATE_NOOP(
                "App::Property", "Location to insert g-code: Beginning or End."
            ),
        )
        obj.addProperty(
            "App::PropertyStringList",
            "Gcode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "The G-code to be inserted"),
        )
        obj.addProperty(
            "App::PropertyString",
            "Marker",
            "Dressup",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Enter 'Line' for line number count or a specific g-code command.",
            ),
        )
        obj.addProperty(
            "App::PropertyEnumeration",
            "MarkerReference",
            "Dressup",
            QT_TRANSLATE_NOOP(
                "App::Property", "Location to insert g-code: Before or After."
            ),
        )
        obj.addProperty(
            "App::PropertyInteger",
            "MarkerInstance",
            "Dressup",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Number of markers used to locate insertion of g-code.",
            ),
        )

        # Set default values
        obj.Active = True
        obj.Base = base
        obj.CodeLocation = ["Beginning", "End"]
        obj.CodeLocation = "Beginning"
        obj.Gcode = []
        obj.Marker = "Line"
        obj.MarkerInstance = 1
        obj.MarkerReference = ["Before", "After"]
        obj.MarkerReference = "Before"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def _setReadyToExecute(self, value):
        self.readyToExecute = value

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.readyToExecute = True  # Flag used in canceling edit via task panel

    def onDelete(self, obj, args):
        if obj.Base:
            job = PathUtils.findParentJob(obj)
            if job:
                job.Proxy.addOperation(obj.Base, obj)
            if obj.Base.ViewObject:
                obj.Base.ViewObject.Visibility = True
                if hasattr(obj.Base, "Active"):
                    obj.Base.Active = True
            obj.Base = None
        return True

    def execute(self, obj):
        # print("AmendCode.execute()")
        if not self.readyToExecute:
            return

        if not obj.Gcode:
            obj.Path = obj.Base.Path
        if obj.CodeLocation == "Beginning":
            obj.Path = Path.Path(_insertCode(obj, obj.Base.Path.Commands))
        elif obj.CodeLocation == "End":
            cmds = [c for c in obj.Base.Path.Commands]
            cmds.reverse()
            obj.Path = Path.Path(_insertCode(obj, cmds, reverse=True))
        else:
            obj.Path = obj.Base.Path


# Eclass


# Support functions
def _getAmendCode(obj, reverse):
    commands = []

    commands.append(Path.Command("(Begin Amend Code)"))
    if obj.Gcode:
        for l in obj.Gcode:
            newcommand = Path.Command(str(l))
            commands.append(newcommand)

    commands.append(Path.Command("(End Amend Code)"))
    if reverse:
        commands.reverse()
    return commands


def _insertCode(obj, pathCmds, reverse=False):
    commands = []
    able = False

    # Identify command index of marker
    if obj.Marker == "Line":
        # Identify index of instance'th line
        idx = obj.MarkerInstance - 1
        if len(pathCmds) >= obj.MarkerInstance:
            able = True
    else:
        cnt = 0
        idx = 0
        # Identify index of instance'th marker
        for c in pathCmds:
            if obj.Marker == c.Name:
                cnt += 1
            if cnt == obj.MarkerInstance:
                able = True
                break
            idx += 1

    if able:
        commands.extend([c for c in pathCmds[:idx]])
        cmd = pathCmds[idx]
        if reverse:
            if obj.MarkerReference == "After":
                commands.extend(_getAmendCode(obj, reverse))
                commands.append(cmd)
            elif obj.MarkerReference == "Before":
                commands.append(cmd)
                commands.extend(_getAmendCode(obj, reverse))
        else:
            if obj.MarkerReference == "Before":
                commands.extend(_getAmendCode(obj, reverse))
                commands.append(cmd)
            elif obj.MarkerReference == "After":
                commands.append(cmd)
                commands.extend(_getAmendCode(obj, reverse))
        commands.extend([c for c in pathCmds[idx + 1 :]])

    if reverse:
        commands.reverse()

    return commands


# Public function
def Create(base, name="DressupAmendCode"):
    """Create(base, name='DressupAmendCode') ... creates a dressup amending code at specified location."""

    if not base.isDerivedFrom("Path::Feature"):
        Path.Log.error(
            translate(
                "Path_DressupAmendCode",
                "The selected object is not a Path operation.",
            )
            + "\n"
        )
        return None

    obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
    job = PathUtils.findParentJob(base)
    obj.Proxy = DressupAmendCode(obj, base, job)
    return obj
