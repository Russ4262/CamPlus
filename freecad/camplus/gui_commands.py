# -*- coding: utf-8 -*-
# ***************************************************************************
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


import FreeCAD
import FreeCADGui
from PySide import QtGui
from PySide import QtCore
from PySide.QtCore import QT_TRANSLATE_NOOP
import importlib
import freecad.camplus as CamPlus
import freecad.camplus.support.Gui_Input as Gui_Input


__title__ = "FreeCAD CAM Plus workbench commands"
__author__ = "russ4262 (Russell Johnson)"
__url__ = "https://github.com/Russ4262/CamPlus"
__doc__ = "Module containing GUI command classes for CAM Plus workbench."

translate = FreeCAD.Qt.translate


class _LoadCamPlusWorkbench:
    "command definition to load the CamPlus workbench"

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\PathWorkbench.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Load CamPlus"),
            # "Accel": "R, L",
            "ToolTip": QT_TRANSLATE_NOOP("CamPlus", "Load the CamPlus workbench."),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        return True

    def Activated(self):
        FreeCADGui.activateWorkbench("CamPlusWorkbench")


class _AmendCode:
    "command definition to amend gcode of operation"

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\IndentMore.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Amend Code"),
            "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Amend gcode to an existing operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            for o in FreeCAD.ActiveDocument.Objects:
                if o.Name[:3] == "Job":
                    if len(o.Operations.Group) > 0:
                        return True
        return False

    def Activated(self):
        import freecad.camplus.amendcode.AmendCodeGui as ACG

        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate(
                    "CamPlus", "Please select one path object"
                )
                + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create Amend Code dressup")
        ACG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


class _LinkedOperation:
    "command definition to create Linked Operation in current Job001, from base operation in source Job."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\PartDesign_MoveFeature.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Linked Operation"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Create a Linked Operation in a separate Job, based upon an operation in another Job object.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.linkedoperation.LinkedOperationGui as LOG

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) < 1:
            FreeCAD.Console.PrintError(
                translate("Path_LinkedOperation", "Please select one operation object")
                + "\n"
            )
            return
        elif len(selection) == 1:
            FreeCAD.ActiveDocument.openTransaction("Create Path Linked Operation")
            LOG.Create(selection[0])
        else:
            FreeCAD.ActiveDocument.openTransaction(
                "Create multiple Path Linked Operation objects"
            )
            for base in selection:
                obj = LOG.LinkedOperation.Create(base)
                obj.ViewObject.Proxy = LOG.LinkedOperationViewProvider(obj.ViewObject)
                obj.ViewObject.Proxy.deleteOnReject = False

            FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()


class _DressupCompoundProfile:
    "command definition to create a Compound Profile dressup on a referenced Profile operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Path_Compound.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Dressup Compound Profile"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Creates a Compound Profile dressup on a referenced Profile operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.compoundprofile.CompoundProfileGui as MPG

        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupCompoundProfile",
                    "Please select one path Profile object",
                )
                + "\n"
            )
            return
        if len(selection) == 1 and not selection[0].Name.startswith("Profile"):
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupCompoundProfile", "Please select a path Profile object"
                )
                + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create Path Compound Profile Dress-up")
        MPG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


class _DressupMultitags:
    "command definition to create Multi-tags dressup on base Profile operation or Compound Profile dressup."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Path_Shape.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Dressup Multi-tags"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Create Multi-tags dressup on base Profile operation or Compound Profile dressup.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.multitags.TagsGui as TG

        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate("Path_DressupMultitags", "Please select one path object")
                + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create Path Multi-tags dressup")
        TG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


class _DressupOffsetInsideOut:
    "command definition to create an Offset Inside-out dressup on a referenced Pocket operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Path_ExportTemplate.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Dressup Offset Inside-out"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Creates an Offset Inside-out dressup on a referenced Pocket operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.offsetinsideout.OffsetInsideOutGui as OIO

        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupOffsetInsideOut", "Please select one path object"
                )
                + "\n"
            )
            return
        if len(selection) == 1 and not selection[0].Name.startswith("Pocket"):
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupCompoundProfile",
                    "Please select a path Pocket or PocketShape object",
                )
                + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create Offset Inside-out Dress-up")
        OIO.Create(selection[0])

        FreeCAD.ActiveDocument.recompute()


class _InlayOperation:
    "command definition to create an Inlay Operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Edge-join-miter-not.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Inlay Operation"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Create an Inlay Operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.inlay.InlayGui as IG

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate(
                    "Path_InlayOperation", "Please select one Target Shape object"
                )
                + "\n"
            )
            return
        if not selection[0].Name.startswith("WorkingShape"):
            FreeCAD.Console.PrintError(
                translate("Path_InlayOperation", "Please select a Working Shape object")
                + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create Inlay Operation")
        IG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


class _WorkingShape:
    "command definition to build a working shape"

    def GetResources(self):
        return {
            # "Pixmap": "Path_Simulator",  # Path_SelectLoop
            "Pixmap": CamPlus.ICONSPATH + "\\TechDraw_TreeMulti.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Working Shape"),
            "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Build a working shape as a basis for a subsequent cutting operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.workingshape.WorkingShapeGui as WorkingShapeGui

        """
        import freecad.CamPlus.modelfeatures.ModelFeaturesGui as ModelFeaturesGui
        import freecad.CamPlus.rotationfeatures.RotationFeaturesGui as RotationFeaturesGui
        import freecad.CamPlus.utilities.SupportSketch as SupportSketch

        baseGeometry = WorkingShapeGui.getSelectedFeatures()

        ws = WorkingShapeGui.Create(useGui=False)
        ws.Rotation = RotationFeaturesGui.Create(ws, useGui=False)
        ws.ModelFeatures = ModelFeaturesGui.Create(
            ws,
            ws.Rotation,
            baseGeometry,
            useGui=False,
        )
        ws.ModelFeatures.ViewObject.Visibility = False
        ws.ModelFeatures.RotationObj.ViewObject.Visibility = False
        ws.ExtendFeatures = SupportSketch.addSketch(ws, name="Extend")
        ws.TrimFeatures = SupportSketch.addSketch(ws, name="Trim")
        """
        # ws = WorkingShapeGui.Create(useGui=False)
        ws = WorkingShapeGui.Create(useGui=True)
        FreeCAD.ActiveDocument.recompute()


class _ClearingOp:
    "command definition to create ClearingOp operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Path_Job.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "ClearingOp Operation"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Create an ClearingOp Operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.clearing.ClearingOpGui as COG

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate("Inlay", "Please select one Working Shape object") + "\n"
            )
            return
        if not selection[0].Name.startswith("WorkingShape"):
            FreeCAD.Console.PrintError(
                translate("Inlay", "Please select a Working Shape object") + "\n"
            )
            return

        FreeCAD.ActiveDocument.openTransaction("Create ClearingOp Operation")
        COG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


class _RestShape:
    "command definition to create a Rest Shape from a selected base operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\Path_FacePocket.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Rest Shape"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Create a Rest Shape from a selected base operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            for o in FreeCAD.ActiveDocument.Objects:
                if o.Name[:3] == "Job":
                    for op in o.Operations.Group:
                        if op.Name.startswith("ClearingOp"):
                            return True
        return False

    def Activated(self):
        import freecad.CamPlus.restshape.RestShapeGui as RMG

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) < 1:
            FreeCAD.Console.PrintError(
                translate("Path_RestShape", "Please select one operation object") + "\n"
            )
            return
        elif len(selection) == 1:
            if selection[0].Name.startswith("Clearing"):
                # FreeCAD.ActiveDocument.openTransaction("Create Rest Shape")
                RMG.Create(selection[0])
            else:
                FreeCAD.Console.PrintError(
                    f"{selection[0].Name} "
                    + translate("Path_RestShape", "is not a Clearing object.")
                    + "\n"
                )
        else:
            # FreeCAD.ActiveDocument.openTransaction("Create multiple Rest Shape objects")
            for base in selection:
                if base.Name.startswith("Clearing"):
                    obj = RMG.RestShape.Create(base)
                    obj.ViewObject.Proxy = RMG.RestShapeViewProvider(obj.ViewObject)
                    obj.ViewObject.Proxy.deleteOnReject = False
                else:
                    FreeCAD.Console.PrintError(
                        f"{base.Name} "
                        + translate("Path_RestShape", "is not a Clearing object.")
                        + "\n"
                    )

            # FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()


class _DressupBoundary:
    "command definition to create a Boundary dressup on a referenced operation."

    def GetResources(self):
        return {
            "Pixmap": CamPlus.ICONSPATH + "\\CAM_Area_Workplane.svg",
            "MenuText": QT_TRANSLATE_NOOP("CamPlus", "Dressup Boundary"),
            # "Accel": "P, S",
            "ToolTip": QT_TRANSLATE_NOOP(
                "CamPlus",
                "Creates a Boundary dressup on a referenced Profile operation.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        return True

    def Activated(self):
        import freecad.CamPlus.boundary.BoundaryGui as BG

        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupBoundary",
                    "Please select one path Profile object",
                )
                + "\n"
            )
            return
        if len(selection) == 1 and not hasattr(selection[0], "Active"):
            FreeCAD.Console.PrintError(
                translate(
                    "Path_DressupBoundary",
                    "Please select a path object with 'Active' property.",
                )
                + "\n"
            )
            return

        # FreeCAD.ActiveDocument.openTransaction("Create Path Boundary Dressup")
        BG.Create(selection[0])
        FreeCAD.ActiveDocument.recompute()


FreeCAD.Console.PrintMessage("Loading gui_commands module of CamPlus workbench...\n")
