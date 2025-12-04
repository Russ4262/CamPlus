# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2019 sliptonic <shopinthewoods@gmail.com>               *
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

from PySide import QtGui
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD
import FreeCADGui
import Path

# import Path.Dressup.Boundary as DressupBoundary
import freecad.camplus.boundary.Boundary as DressupBoundary

# import PathGui
import freecad.camplus as camplus

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate


class TaskPanel(object):
    def __init__(self, obj, viewProvider):
        self.obj = obj
        self.viewProvider = viewProvider
        self.form = FreeCADGui.PySideUic.loadUi(":/panels/DressupPathBoundary.ui")
        if obj.Stock:
            self.visibilityBoundary = obj.Stock.ViewObject.Visibility
            obj.Stock.ViewObject.Visibility = True
        else:
            self.visibilityBoundary = False

        self.buttonBox = None
        self.isDirty = False

        self.stockFromBase = None
        self.stockFromExisting = None
        self.stockCreateBox = None
        self.stockCreateCylinder = None
        self.stockEdit = None

    def getStandardButtons(self):
        return (
            QtGui.QDialogButtonBox.Ok
            | QtGui.QDialogButtonBox.Apply
            | QtGui.QDialogButtonBox.Cancel
        )

    def modifyStandardButtons(self, buttonBox):
        self.buttonBox = buttonBox

    def setDirty(self):
        self.isDirty = True
        self.buttonBox.button(QtGui.QDialogButtonBox.Apply).setEnabled(True)

    def setClean(self):
        self.isDirty = False
        self.buttonBox.button(QtGui.QDialogButtonBox.Apply).setEnabled(False)

    def clicked(self, button):
        # callback for standard buttons
        if button == QtGui.QDialogButtonBox.Apply:
            self.updateDressup()
            FreeCAD.ActiveDocument.recompute()

    def abort(self):
        FreeCAD.ActiveDocument.abortTransaction()
        self.cleanup(False)

    def reject(self):
        FreeCAD.ActiveDocument.abortTransaction()
        self.cleanup(True)

    def accept(self):
        if self.isDirty:
            self.updateDressup()
        FreeCAD.ActiveDocument.commitTransaction()
        self.cleanup(True)

    def cleanup(self, gui):
        self.viewProvider.clearTaskPanel()
        if gui:
            FreeCADGui.ActiveDocument.resetEdit()
            FreeCADGui.Control.closeDialog()
            FreeCAD.ActiveDocument.recompute()
            try:
                if self.obj.Stock:
                    self.obj.Stock.ViewObject.Visibility = self.visibilityBoundary
            except:
                pass

    def updateDressup(self):
        if self.obj.Inside != self.form.stockInside.isChecked():
            self.obj.Inside = self.form.stockInside.isChecked()
        # self.stockEdit.getFields(self.obj)
        self.setClean()

    def setupUi(self):
        self.form.stockInside.setChecked(self.obj.Inside)

        self.form.stockInside.stateChanged.connect(self.setDirty)
        self.form.stockExtXneg.textChanged.connect(self.setDirty)
        self.form.stockExtXpos.textChanged.connect(self.setDirty)
        self.form.stockExtYneg.textChanged.connect(self.setDirty)
        self.form.stockExtYpos.textChanged.connect(self.setDirty)
        self.form.stockExtZneg.textChanged.connect(self.setDirty)
        self.form.stockExtZpos.textChanged.connect(self.setDirty)
        self.form.stockBoxLength.textChanged.connect(self.setDirty)
        self.form.stockBoxWidth.textChanged.connect(self.setDirty)
        self.form.stockBoxHeight.textChanged.connect(self.setDirty)
        self.form.stockCylinderRadius.textChanged.connect(self.setDirty)
        self.form.stockCylinderHeight.textChanged.connect(self.setDirty)


class DressupBoundaryViewProvider(object):
    def __init__(self, vobj):
        self.attach(vobj)

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def attach(self, vobj):
        self.vobj = vobj
        self.obj = vobj.Object
        self.panel = None

    def claimChildren(self):
        return [self.obj.Base, self.obj.Stock]

    def onDelete(self, vobj, args=None):
        if vobj.Object and vobj.Object.Proxy:
            vobj.Object.Proxy.onDelete(vobj.Object, args)
        return True

    def setEdit(self, vobj, mode=0):
        panel = TaskPanel(vobj.Object, self)
        self.setupTaskPanel(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        if self.panel:
            self.panel.abort()

    def setupTaskPanel(self, panel):
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()

    def clearTaskPanel(self):
        self.panel = None


def Create(base, name="DressupPathBoundary", useGui=True):
    FreeCAD.ActiveDocument.openTransaction("Create a Boundary dressup")
    obj = DressupBoundary.Create(base, name)
    if obj:
        obj.ViewObject.Proxy = DressupBoundaryViewProvider(obj.ViewObject)
        # obj.ViewObject.Visibility = True
        obj.ViewObject.Proxy.transactionOpen = True
        if useGui:
            obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
            obj.Base.ViewObject.Visibility = False
            if obj.Stock:
                obj.Stock.ViewObject.Visibility = False
                obj.Stock.ViewObject.Transparency = 80
        else:
            obj.ViewObject.Proxy.deleteOnReject = False
            FreeCAD.ActiveDocument.commitTransaction()

    return obj


FreeCAD.Console.PrintMessage("Imported BoundaryGui module\n")
