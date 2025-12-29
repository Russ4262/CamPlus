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
import FreeCADGui
import Path
import freecad.camplus.workingshape.RotationFeatures as RotationFeatures
import freecad.camplus as camplus

# import freecad.camplus.taskpanels.TaskPanelBase as TaskPanelBase
# import freecad.camplus.taskpanels.PageRotation as RotationFeaturesPage
# import freecad.camplus.support.Selection as PathSelection

# import freecad.camplus.utilities.ViewObjectTools as ViewObjectTools


__title__ = "Rotation Features Gui"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Gui interface to create a Rotation Features."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate


def getSelectedFeatures():
    baseGeometry = []
    # if not FreeCAD.GuiUp:
    #    return baseGeometry

    # Get GUI face selection
    # base = FreeCADGui.Selection.getSelection()[0]
    # baseName = base.Name
    sel = FreeCADGui.Selection.getSelectionEx()
    if len(sel) < 1:
        Path.Log.error(
            translate("Path", "Please select one feature on a model.") + "\n"
        )
        return baseGeometry
    if len(sel[0].SubElementNames) == 0:
        Path.Log.error(
            translate("Path", "Please select one feature on a selected model.") + "\n"
        )
        return baseGeometry

    for s in sel:
        base = s.Object
        subs = sel[0].SubElementNames
        baseGeometry.append((base, [n for n in subs]))
    return baseGeometry


class RotationFeaturesViewProvider(object):
    def __init__(self, vobj):
        self.transactionOpen = False
        self.attach(vobj)
        # pixmap = "Path_Job"
        # self.OpIcon = f":/icons/{pixmap}.svg"
        self.OpIcon = camplus.ICONSPATH + "\\Path_Job.svg"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, vobj):
        self.vobj = vobj
        self.obj = vobj.Object
        self.panel = None

    def claimChildren(self):
        """claimChildren() returns list of children objects for object tree gui"""
        if not hasattr(self, "transactionOpen"):
            self.transactionOpen = False
        return []

    def onDelete(self, vobj=None, val=None):
        """Code to be executed upon deletion of the object."""

        """# Add TargetShape operation back to Job and make it visible
        if vobj.Object and vobj.Object.TargetShape:
            FreeCADGui.ActiveDocument.getObject(
                vobj.Object.TargetShape.Name
            ).Visibility = True
            job = RotationFeatures.PathUtils.findParentJob(vobj.Object)
            if job:
                job.Proxy.addOperation(vobj.Object.TargetShape, vobj.Object)
            vobj.Object.TargetShape = None
            # Then deletion occurs of vobj.Object"""
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, val)
        return True

    """
    def setEdit_orig(self, vobj, mode=0):
        # print("ViewProvider.setEdit() begin")
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Rotation Features")
        page = RotationFeaturesPage.TaskPanelRotationPage(vobj.Object, 0)
        page.setTitle("Rotation Features")
        page.setIcon(page.OpIcon)

        # print("RotationFeaturesGui.setEdit()")

        selection = PathSelection.select("Profile")
        TaskPanelBase.FEATURES_DICT = RotationFeatures.FEATURES_DICT
        panel = TaskPanelBase.TaskPanel(
            vobj.Object,
            False,  # self.deleteObjectsOnReject(),
            page,
            selection,
            parent=self,
        )

        self.setupTaskPanel(panel)
        # print("ViewProvider.setEdit() end")
        return True
    """

    def setEdit(self, vobj, mode=0):
        # print("ViewProvider.setEdit() begin")
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Rotation Features")
        return True

    def unsetEdit(self, vobj, mode=0):
        # print(f"ViewProvider.unsetEdit(mode={mode})")
        if self.panel:
            self.panel.abort()
        self.transactionOpen = False

    def setupTaskPanel(self, panel):
        # print("ViewProvider.setupTaskPanel()")
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()

    def clearTaskPanel(self):
        self.panel = None


# Eclass


def Create(parent, baseGeometry=[], useGui=True):
    FreeCAD.ActiveDocument.openTransaction("Create a Rotation Features object.")
    obj = RotationFeatures.Create(parent, baseGeometry)
    if obj:
        obj.ViewObject.Proxy = RotationFeaturesViewProvider(obj.ViewObject)
        obj.ViewObject.Visibility = False
        obj.ViewObject.Proxy.transactionOpen = True
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
            FreeCAD.ActiveDocument.commitTransaction()
        # ViewObjectTools.applyColorScheme(obj.ViewObject, (255, 170, 255), 60)

    return obj


Path.Log.notice("Loaded RotationFeaturesGui...\n")
