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
# **********************************T****************************************

import FreeCAD
import FreeCADGui
import Path
import freecad.camplus as camplus
import freecad.camplus.inlay.Inlay as Inlay
#import freecad.camplus.taskpanels.TaskPanelBase as TaskPanelBase
#import freecad.camplus.taskpanels.PageInlay as InlayPage
#import freecad.camplus.support.Selection as PathSelection


__title__ = "Inlay Gui"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Gui interface to create an Inlay operation."
__usage__ = ""
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""


translate = FreeCAD.Qt.translate

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


class InlayViewProvider(object):
    def __init__(self, vobj):
        self.transactionOpen = False
        self.attach(vobj)
        # pixmap = "Path_Slot"
        # self.OpIcon = f":/icons/{pixmap}.svg"
        self.OpIcon = self.getIcon()

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, vobj):
        self.vobj = vobj
        self.obj = vobj.Object
        self.panel = None

    def claimChildren(self):
        if not hasattr(self, "transactionOpen"):
            self.transactionOpen = False
        return [self.obj.BaseShape]

    def getIcon(self):
        return camplus.ICONSPATH + "\\Edge-join-miter-not.svg"

    def onDelete_OLD(self, vobj, args=None):
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, args)
        return True

    def onDelete(self, vobj=None, val=None):
        """Code to be executed upon deletion of the object."""

        # Add base operation back to Job and make it visible
        if vobj.Object and vobj.Object.BaseShape:
            FreeCADGui.ActiveDocument.getObject(
                vobj.Object.BaseShape.Name
            ).Visibility = True
            job = Inlay.PathUtils.findParentJob(vobj.Object)
            if job:
                job.Proxy.addOperation(vobj.Object.BaseShape, vobj.Object)
            vobj.Object.BaseShape = None
        return True

    '''
    def setEdit_orig(self, vobj, mode=0):
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Inlay")
        page = InlayPage.TaskPanelInlayPage(vobj.Object, 0)
        page.setIcon(page.OpIcon)

        selection = PathSelection.select("Profile")
        TaskPanelBase.FEATURES_DICT = Inlay.FEATURES_DICT
        panel = TaskPanelBase.TaskPanel(
            vobj.Object,
            False,  # self.deleteObjectsOnReject(),
            page,
            selection,
            parent=self,
        )

        self.setupTaskPanel(panel)
        return True
    '''

    def setEdit(self, vobj, mode=0):
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Inlay")
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


# Eclass


def Create(baseObj, name="Inlay", parentJob=None, useGui=True):
    FreeCAD.ActiveDocument.openTransaction("Create an Inlay operation.")
    obj = Inlay.Create(baseObj, name=name, parentJob=parentJob)
    if obj:
        obj.ViewObject.Proxy = InlayViewProvider(obj.ViewObject)
        # obj.ViewObject.Visibility = True
        obj.ViewObject.Proxy.transactionOpen = True
        FreeCAD.ActiveDocument.commitTransaction()
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
        obj.BaseShape.ViewObject.Visibility = False
    return obj


Path.Log.notice("Loading InlayGui... done\n")
