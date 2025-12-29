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
import FreeCADGui
import Path
import freecad.camplus.workingshape.WorkingShape as WorkingShape
import freecad.camplus.utilities.ViewObjectTools as ViewObjectTools
import freecad.camplus as camplus

# import freecad.camplus.taskpanels.TaskPanelBase as TaskPanelBase
# import freecad.camplus.taskpanels.PageWorkingShape as WorkingShapePage
# import freecad.camplus.support.Selection as PathSelection


__title__ = "Working Shape Gui"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Gui interface to create a Working Shape."
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
        subs = s.SubElementNames
        baseGeometry.append((base, [n for n in subs]))
    return baseGeometry


class WorkingShapeViewProvider(object):
    def __init__(self, vobj):
        self.transactionOpen = False
        # pixmap = "Path_Job"
        # self.OpIcon = f":/icons/{pixmap}.svg"
        self.OpIcon = self.getIcon() #camplus.ICONSPATH + "\\TechDraw_TreeMulti.svg"
        self.attach(vobj)

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
        return [
            self.obj.Rotation,
            self.obj.ModelFeatures,
            self.obj.ExtendFeatures,
            self.obj.TrimFeatures,
            # self.obj.RotationIndex,
        ]

    def getIcon(self):
        return camplus.ICONSPATH + "\\TechDraw_TreeMulti.svg" # ":/icons/CAM_Job.svg"

    def onDelete(self, vobj=None, val=None):
        """Code to be executed upon deletion of the object."""
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, val)
        return True

    """
    def setEdit_ORIG(self, vobj, mode=0):
        # print("ViewProvider.setEdit() begin")
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Working Shape")
        page = WorkingShapePage.TaskPanelWorkingShapePage(vobj.Object, 0)
        page.setTitle("Working Shape")
        page.setIcon(page.OpIcon)

        selection = PathSelection.select("Profile")
        TaskPanelBase.FEATURES_DICT = WorkingShape.FEATURES_DICT
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
            FreeCAD.ActiveDocument.openTransaction("Edit WorkingShape")

        # self.setupTaskPanel(panel)
        # print("ViewProvider.setEdit() end")
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


def addDependencies(parentObj, use_Gui):
    import freecad.camplus.workingshape.ModelFeaturesGui as ModelFeaturesGui
    import freecad.camplus.workingshape.RotationFeaturesGui as RotationFeaturesGui
    import freecad.camplus.utilities.SupportSketch as SupportSketch

    r = RotationFeaturesGui.Create(parentObj, useGui=use_Gui)
    mf = ModelFeaturesGui.Create(
        parentObj,
        r,  # parentObj.Rotation,
        getSelectedFeatures(),
        useGui=use_Gui,
    )
    e = SupportSketch.addSketch(parentObj, name="Extend")
    t = SupportSketch.addSketch(parentObj, name="Trim")
    return (r, mf, e, t)


def Create(parentJob=None, useGui=True):
    base = [
        (s.Object, [n for n in s.SubElementNames])
        for s in FreeCADGui.Selection.getSelectionEx()
    ]

    FreeCAD.ActiveDocument.openTransaction("Create a WorkingShape operation.")
    obj = WorkingShape.Create(parentJob, base)
    r, mf, ef, tf = addDependencies(obj, False)
    if obj:
        obj.ViewObject.Proxy = WorkingShapeViewProvider(obj.ViewObject)
        # obj.ViewObject.Visibility = True
        obj.ViewObject.Proxy.transactionOpen = True
        obj.Rotation = r
        obj.ModelFeatures = mf
        obj.ExtendFeatures = ef
        obj.TrimFeatures = tf
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
            FreeCAD.ActiveDocument.commitTransaction()
        ViewObjectTools.applyColorScheme(obj.ViewObject, (255, 170, 255), 60)

    return obj


Path.Log.notice("Loaded WorkingShapeGui...\n")
