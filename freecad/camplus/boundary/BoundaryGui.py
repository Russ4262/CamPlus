# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2017, 2019 sliptonic <shopinthewoods@gmail.com>         *
# *   Copyright (c) 2025 Russell Johnson <russ4262> russ4262@gmail.com      *
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
import freecad.camplus.boundary.Boundary as Boundary
import Path.Dressup.Utils as PathDressup

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
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Apply | QtGui.QDialogButtonBox.Cancel
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
        self.obj.Stock.ViewObject.update()
        self.obj.Stock.ViewObject.Visibility = False
        self.cleanup(True)

    def cleanup(self, gui):
        self.viewProvider.clearTaskPanel()
        if gui:
            FreeCADGui.ActiveDocument.resetEdit()
            FreeCADGui.Control.closeDialog()
            FreeCAD.ActiveDocument.recompute()
        else:
            if hasattr(self.obj, "Stock") and self.obj.Stock:
                self.obj.Stock.ViewObject.Visibility = self.visibilityBoundary

    def updateDressup(self):
        if self.obj.Inside != self.form.stockInside.isChecked():
            self.obj.Inside = self.form.stockInside.isChecked()
        self.stockEdit.getFields(self.obj)
        self.setClean()


    def updateStockEditor(self, index, force=False):
        # print("BoundaryGui.updateStockEditor() ... looking for candidates")
        def setupFromExisting():
            Path.Log.track(index, force)
            if force or not self.stockFromExisting:
                self.stockFromExisting = StockFromExistingEdit(
                    self.obj, self.form, force
                )
            if self.stockFromExisting.candidates(self.obj):
                self.stockEdit = self.stockFromExisting
                return True
            return False

        setupFromExisting()

        # self.stockEdit.activate(self.obj, index == -1)
        self.stockEdit.activate(self.obj, True)
    
    def setupUi(self):
        self.updateStockEditor(-1, False)
        self.form.stock.removeItem(2)
        self.form.stock.removeItem(1)
        self.form.stock.removeItem(0)
        self.form.stock.hide()
        self.form.stockInside.setChecked(self.obj.Inside)

        # self.form.stock.currentIndexChanged.connect(self.updateStockEditor)
        if hasattr(self.form.stockInside, "checkStateChanged"):  # Qt version >= 6.7.0
            self.form.stockInside.checkStateChanged.connect(self.setDirty)
        else:  # Qt version < 6.7.0
            self.form.stockInside.stateChanged.connect(self.setDirty)
        

class DressupPathBoundaryViewProvider(object):
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

    def getIcon(self):
        if getattr(PathDressup.baseOp(self.obj), "Active", True):
            return ":/icons/CAM_Dressup.svg"
        else:
            return ":/icons/CAM_OpActive.svg"


import Path.Base.Util as PathUtil
import Path.Main.Job as PathJob
import Path.Main.Stock as PathStock
import PathScripts.PathUtils as PathUtils
import Path.Main.Gui.Job as CAMJobGui

class StockFromExistingEdit(CAMJobGui.StockEdit):
    Index = 3
    StockType = PathStock.StockType.Unknown
    StockLabelPrefix = "Stock"

    def editorFrame(self):
        return self.form.stockFromExisting

    def getFields(self, obj):
        stock = self.form.stockExisting.itemData(self.form.stockExisting.currentIndex())
        if not (
            hasattr(obj.Stock, "Objects")
            and len(obj.Stock.Objects) == 1
            and obj.Stock.Objects[0] == stock
        ):
            if stock:
                obj.Stock = stock


    def candidates(self, obj):
        solids = [o for o in obj.Document.Objects if PathUtil.isSolid(o) and o.TypeId == "PartDesign::Body" and hasattr(o, "IsBoundary")]
        if hasattr(obj, "Model"):
            job = obj
        else:
            job = PathUtils.findParentJob(obj)
        for base in job.Model.Group:
            if base in solids and PathJob.isResourceClone(job, base, "Model"):
                solids.remove(base)
        if job.Stock in solids:
            # regardless, what stock is/was, it's not a valid choice
            solids.remove(job.Stock)
        excludeIndexes = []
        for index, model in enumerate(solids):
            if [ob.Name for ob in model.InListRecursive if "Tools" in ob.Name]:
                excludeIndexes.append(index)
            elif hasattr(model, "PathResource"):
                excludeIndexes.append(index)
            elif model.InList and hasattr(model.InList[0], "ToolBitID"):
                excludeIndexes.append(index)
            elif hasattr(model, "ToolBitID"):
                excludeIndexes.append(index)
            elif model.TypeId == "App::DocumentObjectGroup":
                excludeIndexes.append(index)
            elif hasattr(model, "StockType"):
                excludeIndexes.append(index)
            elif not model.ViewObject.ShowInTree:
                excludeIndexes.append(index)

        for i in sorted(excludeIndexes, reverse=True):
            del solids[i]

        return sorted(solids, key=lambda c: c.Label)

    def setFields(self, obj):
        # Block signal propagation during stock dropdown population. This prevents
        # the `currentIndexChanged` signal from being emitted while populating the
        # dropdown list. This is important because the `currentIndexChanged` signal
        # will in the end result in the stock object being recreated in `getFields`
        # method, discarding any changes made (like position in respect to origin).
        try:
            self.form.stockExisting.blockSignals(True)
            self.form.stockExisting.clear()
            stockName = obj.Stock.Label if obj.Stock else None
            index = -1
            for i, solid in enumerate(self.candidates(obj)):
                self.form.stockExisting.addItem(solid.Label, solid)
                label = "{}-{}".format(self.StockLabelPrefix, solid.Label)
                if label == stockName:
                    index = i

            self.form.stockExisting.setCurrentIndex(index if index != -1 else 0)
        finally:
            self.form.stockExisting.blockSignals(False)

        if not self.IsStock(obj):
            self.getFields(obj)

    def setupUi(self, obj):
        self.setFields(obj)
        self.form.stockExisting.currentIndexChanged.connect(lambda: self.getFields(obj))


def Create(base, name="DressupPathBoundary"):
    FreeCAD.ActiveDocument.openTransaction("Create a Boundary dressup")
    obj = Boundary.Create(base, name)
    obj.ViewObject.Proxy = DressupPathBoundaryViewProvider(obj.ViewObject)
    obj.Base.ViewObject.Visibility = False
    obj.Stock.ViewObject.Visibility = False
    FreeCAD.ActiveDocument.commitTransaction()
    obj.ViewObject.Document.setEdit(obj.ViewObject, 0)
    obj.Stock.ViewObject.update()
    return obj


Path.Log.notice("Loading PathDressupPathBoundaryGui... done\n")
