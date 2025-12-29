# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2019 sliptonic <shopinthewoods@gmail.com>               *
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
import freecad.camplus.workingshape.ModelFeatures as ModelFeatures
import freecad.camplus.utilities.ViewObjectTools as ViewObjectTools

# import freecad.camplus.workingshape.PageModelFeatures as ModelFeaturesPage
# import freecad.camplus.taskpanels.TaskPanelBase as TaskPanelBase
# import freecad.camplus.support.Selection as Selection


__title__ = "Model Features Gui"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = (
    "View provider class for GUI task panel interface for Model Features creation."
)
__usage__ = ""
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""


translate = FreeCAD.Qt.translate

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


class ModelFeaturesViewProvider(object):
    def __init__(self, vobj):
        self.attach(vobj)
        pixmap = "Path_Slot"
        self.OpIcon = f":/icons/{pixmap}.svg"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, vobj):
        self.vobj = vobj
        self.obj = vobj.Object
        self.panel = None

    def claimChildren(self):
        return []

    def onDelete(self, vobj, args=None):
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, args)
        return True

    """
    def setEdit_orig(self, vobj, mode=0):
        page = ModelFeaturesPage.TaskPanelModelFeaturesPage(vobj.Object, 0)
        page.setIcon(page.OpIcon)
        selection = Selection.select("Profile")
        TaskPanelBase.FEATURES_DICT = ModelFeatures.FEATURES_DICT
        panel = TaskPanelBase.TaskPanel(
            vobj.Object,
            False,  # self.deleteObjectsOnReject(),
            page,
            selection,
            parent=self,
        )

        self.setupTaskPanel(panel)
        return True
    """

    def setEdit(self, vobj, mode=0):
        return True

    def unsetEdit(self, vobj, mode=0):
        if self.panel:
            self.panel.abort()

    def setupTaskPanel(self, panel):
        # print("setupTaskPanel()")
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()

    def clearTaskPanel(self):
        self.panel = None


# Eclass


def getSelectedFeatures():
    baseGeometry = []
    sel = FreeCADGui.Selection.getSelectionEx()
    if len(sel) < 1:
        Path.Log.error(
            translate("ModelFeatures", "Please select one feature on a model.") + "\n"
        )
        return baseGeometry
    if len(sel[0].SubElementNames) == 0:
        Path.Log.error(
            translate("ModelFeatures", "Please select one feature on a selected model.")
            + "\n"
        )
        return baseGeometry

    for s in sel:
        base = s.Object
        subs = sel[0].SubElementNames
        baseGeometry.append((base, [n for n in subs]))

    return baseGeometry


def Create(parent, rotation, baseGeometry=[], useGui=True):
    FreeCAD.ActiveDocument.openTransaction("Create a feature shape.")
    obj = ModelFeatures.Create(parent, rotation, baseGeometry)
    if obj:
        obj.ViewObject.Proxy = ModelFeaturesViewProvider(obj.ViewObject)
        obj.ViewObject.Visibility = False
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
            FreeCAD.ActiveDocument.commitTransaction()
        ViewObjectTools.applyColorScheme(obj.ViewObject, (0, 85, 255), 60)
    return obj


Path.Log.notice("Loaded ModelFeaturesGui...\n")
