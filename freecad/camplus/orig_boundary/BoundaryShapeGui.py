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
import Path
import freecad.camplus as camplus
import freecad.camplus.boundary.BoundaryShape as BoundaryShape
import FreeCADGui
import freecad.camplus.utilities.ViewObjectTools as ViewObjectTools


__title__ = "Boundary Shape Gui"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "."
__usage__ = "."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""
__contributors__ = ""


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate


def setColors(vObj, Diffuse=None, Line=None):
    if Diffuse is not None:
        vObj.ShapeAppearance = FreeCAD.Material(
            DiffuseColor=(Diffuse[0] / 255.0, Diffuse[1] / 255.0, Diffuse[2] / 255.0)
        )


class BoundaryShapeViewProvider(object):
    def __init__(self, vobj):
        self.transactionOpen = False
        self.deleteOnReject = True
        self.attach(vobj)
        self._applyColorScheme()
        # pixmap = "Path_Slot"
        # self.OpIcon = f":/icons/{pixmap}.svg"
        self.OpIcon = camplus.ICONSPATH + "\\Edge-join-miter-not.svg"
        self.vobj.ShapeColor = (255, 170, 0)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, vobj):
        self.vobj = vobj
        self.obj = vobj.Object
        self.panel = None

    def claimChildren(self):
        children = []
        if not hasattr(self, "transactionOpen"):
            self.transactionOpen = False
        if hasattr(self.obj, "BoundarySketch"):
            children.append(self.obj.BoundarySketch)

        return children

    def onDelete_old(self, vobj, args=None):
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, args)
        return True

    def onDelete_new(self, vobj=None, args=None):
        """Code to be executed upon deletion of the object."""

        # Add BoundaryShape operation back to Job and make it visible
        if vobj.Object and vobj.Object.BoundaryShape:
            fsName = vobj.Object.BoundaryShape.Name
            fs.Proxy.onDelete()
            fs = FreeCAD.ActiveDocument.removeObject(fsName)
            vobj.Object.BoundaryShape = None
        return True

    def onDelete(self, vobj=None, args=None):
        """Code to be executed upon deletion of the object."""
        # print(f"TargetShapeGui.onDelete()")
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, args)
        return True

    def setEdit(self, vobj, mode=0):
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Boundary Shape")
        """page = FeatureShapePage.TaskPanelFeatureShapePage(vobj.Object, 0)
        page.setIcon(page.OpIcon)
        selection = Selection.select("Profile")
        TaskPanelBase.FEATURES_DICT = FeatureShape.FEATURES_DICT
        TaskPanelBase._setReadyToExecute(vobj.Object, False)
        panel = TaskPanelBase.TaskPanel(
            vobj.Object,
            False,  # self.deleteObjectsOnReject(),
            page,
            selection,
            parent=self,
        )

        self.setupTaskPanel(panel)"""
        return True

    def unsetEdit(self, vobj, mode=0):
        if self.panel:
            self.panel.abort()
        self.transactionOpen = False

    def setupTaskPanel(self, panel):
        # print("setupTaskPanel()")
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()

    def clearTaskPanel(self):
        self.panel = None

    def _applyColorScheme(self):
        # self.vobj.ShapeColor = (170, 0sdf, 0)  # Set color dark red
        # self.vobj.ShapeColor = (170, 0, 255)  # Set color purple
        # self.vobj.ShapeColor = (255, 170, 0)  # (0, 85, 255)  # Set color blue
        ViewObjectTools.setDiffuseColor(self.vobj, (255, 170, 0))
        self.vobj.LineColor = (255, 170, 0)  # (0, 85, 255)  # Set color blue
        self.vobj.Transparency = 80


# Eclass


def Create(dressup, useGui=True):
    FreeCAD.ActiveDocument.openTransaction("Create Boundary Shape object.")
    # if not dressup.Name.startswith("Dressup"):
    #    return None

    obj = BoundaryShape.Create(dressup)
    if obj:
        obj.ViewObject.Proxy = BoundaryShapeViewProvider(obj.ViewObject)
        obj.ViewObject.Visibility = False
        obj.ViewObject.Proxy.transactionOpen = True
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
            FreeCAD.ActiveDocument.commitTransaction()

    return obj


FreeCAD.Console.PrintMessage("Imported BoundaryShapeGui module.\n")
