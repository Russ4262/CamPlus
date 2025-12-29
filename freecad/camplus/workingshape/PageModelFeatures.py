# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2017 sliptonic <shopinthewoods@gmail.com>               *
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
import Path.Log as PathLog
import freecad.camplus.taskpanels.TaskPanelPage as PageTaskPanel
from freecad.camplus import GUIPANELSPATH


__title__ = "Path UI Task Panel Pages base classes"
__author__ = "sliptonic (Brad Collette)"
__url__ = "https://www.freecadweb.org"
__doc__ = "Base classes for UI features within Path operations"


translate = FreeCAD.Qt.translate


if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


class TaskPanelModelFeaturesPage(PageTaskPanel.TaskPanelPage):
    """Page controller for diameters."""

    def __init__(self, obj, features):
        super(TaskPanelModelFeaturesPage, self).__init__(obj, features)
        pixmap = "Path_Slot"
        self.OpIcon = f":/icons/{pixmap}.svg"

    def getForm(self):
        formFile = GUIPANELSPATH + "\\PageModelFeatures.ui"
        return FreeCADGui.PySideUic.loadUi(formFile)

    def initPage(self, obj):
        enumTups = obj.Proxy.propertyEnumerations(dataType="raw")
        # self.populateCombobox(self.form, enumTups, [("shapeType", "ShapeType")])
        self.isdirty = True

    def getTitle(self, obj):
        return translate("Path", "Model Features")

    def getFields(self, obj):
        """getFields(obj) Transfer values from task panel field to obj properties."""

        """
        if self.form.includeHoles.isChecked() != obj.IncludeHoles:
            obj.IncludeHoles = self.form.includeHoles.isChecked()

        if self.form.respectMergedHoles.isChecked() != obj.RespectMergedHoles:
            obj.RespectMergedHoles = self.form.respectMergedHoles.isChecked()

        if obj.ShapeType != self.form.shapeType.currentData():
            obj.ShapeType = self.form.shapeType.currentData()

        if self.form.includeProfile.isChecked() != obj.IncludeProfile:
            obj.IncludeProfile = self.form.includeProfile.isChecked()

        if obj.TrimWithStock != self.form.trimWithStock.isChecked():
            obj.TrimWithStock = self.form.trimWithStock.isChecked()

        if obj.TrimExtrusion != self.form.trimExtrusion.isChecked():
            obj.TrimExtrusion = self.form.trimExtrusion.isChecked()

        if obj.TrimOverhang != self.form.trimOverhang.isChecked():
            obj.TrimOverhang = self.form.trimOverhang.isChecked()
        """

        # if self.form.enable3D.isChecked() != obj.Enable3D:
        #    obj.Enable3D = self.form.enable3D.isChecked()

        # self.parent is TaskPanel and self.parent.parent is ViewProvider
        pass

    def setFields(self, obj):
        """setFields(obj) Transfer values from obj properties to task panel fields."""

        """
        # self.form.enable3D.setChecked(obj.Enable3D)
        self.selectInComboBox(obj.ShapeType, self.form.shapeType)
        self.form.includeHoles.setChecked(obj.IncludeHoles)
        self.form.respectMergedHoles.setChecked(obj.RespectMergedHoles)
        self.form.includeProfile.setChecked(obj.IncludeProfile)
        self.form.trimWithStock.setChecked(obj.TrimWithStock)
        self.form.trimExtrusion.setChecked(obj.TrimExtrusion)
        self.form.trimOverhang.setChecked(obj.TrimOverhang)
        """
        pass

    def getSignalsForUpdate(self, obj):
        signals = []
        """
        # signals.append(self.form.enable3D.stateChanged)
        signals.append(self.form.includeHoles.stateChanged)
        signals.append(self.form.respectMergedHoles.stateChanged)
        signals.append(self.form.shapeType.currentIndexChanged)
        signals.append(self.form.includeProfile.stateChanged)
        signals.append(self.form.trimWithStock.stateChanged)
        signals.append(self.form.trimExtrusion.stateChanged)
        signals.append(self.form.trimOverhang.stateChanged)
        """
        return signals

    def registerSignalHandlers(self, obj):
        self.form.hideShape.stateChanged.connect(self._toggleVisibility)

    def pageUpdateData(self, obj, prop):
        """Any property change belonging to 'obj' will trigger this method.
        The list should only contain property names affected by this Task Panel Page."""
        # if prop in ["ShapeType", "CutPattern"]:
        #    self.setFields(obj)
        pass

    def _toggleVisibility(self):
        if self.form.hideShape.isChecked():
            self.obj.ViewObject.Visibility = False
        else:
            self.obj.ViewObject.Visibility = True


FreeCAD.Console.PrintLog("Loading PageModelFeatures... done\n")
