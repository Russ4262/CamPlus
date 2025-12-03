# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2019 sliptonic <shopinthewoods@gmail.com>               *
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

import PySide
import FreeCAD
import FreeCADGui
import Path
import freecad.camplus.amendcode.AmendCode as DressupAmendCode
import freecad.camplus.utilities.GuiTools as GuiTools
from freecad.camplus import GUIPANELSPATH

__title__ = "Amend Code Dressup Gui"
__author__ = "Russell Johnson <russ4262>"
__doc__ = (
    "Gui interface to create an Amend Code dressup on a referenced base operation."
)
__usage__ = "Import this module.  Run the 'Create(base)' function, passing it the desired base operation."
__url__ = "https://github.com/Russ4262/CamPlus"
__Wiki__ = ""
__date__ = ""


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


translate = FreeCAD.Qt.translate
PathUtils = DressupAmendCode.PathUtils


class TaskPanel(object):
    def __init__(self, obj, viewProvider):
        """__init__(obj, viewProvider) Initiate TaskPanel object for Amend Code dressup."""
        self.obj = obj
        self.viewProvider = viewProvider
        self.buttonBox = None
        self.isDirty = False
        self.form = self._getForm()

    def _getForm(self):
        """_getForm() returns GUI form containing input/output fields, from '.ui' file."""
        form = FreeCADGui.PySideUic.loadUi(GUIPANELSPATH + "\\DressupAmendCodeEdit.ui")
        form.marker.setToolTip(
            translate(
                "AmendCode",
                "Enter 'Line' for line number count, or a specific g-code command.",
            )
        )
        return form

    # Callback and support methods for Qt GUI on C++ side
    def getStandardButtons(self):
        """getStandardButtons() return integer value representing standard buttons"""
        return (
            PySide.QtGui.QDialogButtonBox.Ok
            | PySide.QtGui.QDialogButtonBox.Apply
            | PySide.QtGui.QDialogButtonBox.Cancel
        )

    def modifyStandardButtons(self, buttonBox):
        """modifyStandardButtons(buttonBox) Modify buttonBox as needed and save reference to same."""
        self.buttonBox = buttonBox

    def clicked(self, button):
        """clicked(button)  Execute code based on button clicked - callback method"""
        if button == PySide.QtGui.QDialogButtonBox.Apply:
            # Action to take when Apply button clicked
            self._setObjectValues(self.obj)
            self.setClean()
            self.obj.Proxy._setReadyToExecute(True)
            self.obj.touch()
            FreeCAD.ActiveDocument.recompute()

    def abort(self):
        """abort()  callback method when close button (X) is clicked in GUI"""
        FreeCAD.ActiveDocument.abortTransaction()
        self.cleanup(True)

    def reject(self):
        """abort()  callback method when Cancel button is clicked in GUI"""
        FreeCAD.ActiveDocument.abortTransaction()
        self.cleanup(True)

    def accept(self):
        """accept()  callback method when OK button is clicked in GUI"""
        # print("AmendCodeGui.accept()")
        if self.isDirty:
            self._setObjectValues(self.obj)
            self.setClean()
        FreeCAD.ActiveDocument.commitTransaction()
        self.cleanup(True)

    # Support methods to track changes to values/conditions in task panel
    def setDirty(self):
        """setDirty() sets obj.Proxy status to dirty, requiring recompute."""
        self.isDirty = True
        self.buttonBox.button(PySide.QtGui.QDialogButtonBox.Apply).setEnabled(True)

    def setClean(self):
        """setClean() sets obj.Proxy status to clean."""
        self.isDirty = False
        self.buttonBox.button(PySide.QtGui.QDialogButtonBox.Apply).setEnabled(False)

    # Support methods to set up and close the GUI task panel
    def _setObjectValues(self, obj):
        """_setObjectValues(obj) copies values from GUI task panel to obj properties."""
        # print("AmendCodeGui._setObjectValues()")
        if obj.CodeLocation != self.form.codeLocation.currentText():
            obj.CodeLocation = self.form.codeLocation.currentText()

        if obj.Marker != self.form.marker.text():
            obj.Marker = self.form.marker.text()

        if obj.MarkerInstance != self.form.markerInstance.value():
            obj.MarkerInstance = self.form.markerInstance.value()

        if obj.MarkerReference != self.form.markerReference.currentText():
            obj.MarkerReference = self.form.markerReference.currentText()

        obj.Gcode = self.form.gCode.toPlainText().splitlines()

    def _setTaskPanelValues(self, obj):
        """_setTaskPanelValues(obj) copies values from obj properties to GUI task panel fields."""
        GuiTools.selectInComboBox(obj.CodeLocation, self.form.codeLocation)
        # Transfer value from obj properties to UI task panel inputs
        GuiTools.selectInComboBox(obj.MarkerReference, self.form.markerReference)
        self.form.marker.setText(obj.Marker)
        self.form.markerInstance.setValue(obj.MarkerInstance)
        self.form.gCode.setText("\n".join(obj.Gcode))

    def _applySignalHandlers(self, obj):
        """_applySignalHandlers(obj) Apply signal handlers to task panel fields"""
        self.form.codeLocation.currentIndexChanged.connect(self.setDirty)
        self.form.markerReference.currentIndexChanged.connect(self.setDirty)
        self.form.marker.textChanged.connect(self.setDirty)
        self.form.markerInstance.valueChanged.connect(self.setDirty)
        self.form.gCode.textChanged.connect(self.setDirty)

    def setupUi(self):
        """setupUi() Executes code to set up the GUI after form is activated."""
        self._setTaskPanelValues(self.obj)
        self._applySignalHandlers(self.obj)

    def cleanup(self, gui):
        """cleanup(gui)  method called when GUI is closed, either with OK, or Cancel/abort"""
        # print("AmendCodeGui.cleanup()")
        self.viewProvider.clearTaskPanel()
        if gui:
            try:
                self.obj.Proxy._setReadyToExecute(True)
            except Exception as __:
                # Continue if object is deleted
                pass

            FreeCADGui.ActiveDocument.resetEdit()
            FreeCADGui.Control.closeDialog()
            FreeCAD.ActiveDocument.recompute()


# Eclass


class DressupAmendCodeViewProvider(object):
    def __init__(self, viewObj):
        self.transactionOpen = False
        self.attach(viewObj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, viewObj):
        """attach(viewObj) attach dependency objects to this proxy view provider class as attributes"""
        self.viewObj = viewObj
        self.obj = viewObj.Object
        self.panel = None

    def claimChildren(self):
        """claimChildren() returns list of children objects for object tree gui"""
        # print(f"ViewProvider.claimChildren()")
        if not hasattr(self, "transactionOpen"):
            self.transactionOpen = False
        return [self.obj.Base]

    def onDelete(self, viewObj, args=None):
        """onDelete() Code to execute when object is deleted"""
        # Add obj.Base back to Job, and make it visible
        if viewObj.Object and viewObj.Object.Base:
            FreeCADGui.ActiveDocument.getObject(viewObj.Object.Base.Name).Visibility = (
                True
            )
            job = PathUtils.findParentJob(viewObj.Object)
            if job:
                job.Proxy.addOperation(viewObj.Object.Base, viewObj.Object)
            viewObj.Object.Base = None
            viewObj.Object.Proxy.onDelete(viewObj.Object, args)
        return True

    def setEdit(self, viewObj, mode=0):
        # print(f"ViewProvider.setEdit(mode={mode})")
        if not self.transactionOpen:
            FreeCAD.ActiveDocument.openTransaction("Edit Amend Code dressup")
        viewObj.Object.Proxy._setReadyToExecute(False)
        panel = TaskPanel(viewObj.Object, self)
        self.setupTaskPanel(panel)
        return True

    def unsetEdit(self, viewObj, mode=0):
        # print(f"ViewProvider.unsetEdit(mode={mode})")
        if self.panel:
            self.panel.abort()
        self.transactionOpen = False

    def setupTaskPanel(self, panel):
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()

    def clearTaskPanel(self):
        self.panel = None


# Eclass


def Create(base, name="DressupAmendCode"):
    FreeCAD.ActiveDocument.openTransaction("Create an Amend Code dressup")
    obj = DressupAmendCode.Create(base, name)
    obj.ViewObject.Proxy = DressupAmendCodeViewProvider(obj.ViewObject)
    obj.ViewObject.Proxy.transactionOpen = True
    obj.Base.ViewObject.Visibility = False
    FreeCAD.ActiveDocument.commitTransaction()
    obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
    return obj


Path.Log.notice("Loading DressupAmendCodeGui... done\n")
