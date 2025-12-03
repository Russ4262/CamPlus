"""FreeCAD initgui script of CamPlus module"""

# ***************************************************************************
# *   Copyright (c) 2025 Russell Johnson <russ4262> russ4262@gmail.com      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENSE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/

__author__ = "Russell Johnson <russ4262>"
__doc__ = (
    "InitGui.py file, based on template at https://wiki.freecad.org/Workbench_creation"
)
import FreeCAD as App
import FreeCADGui as Gui


class CamPlusWorkbench(Gui.Workbench):

    MenuText = "CamPlus"
    ToolTip = "An addon workbench intended to extend FreeCAD's internal CAM workbench features, and provide for related experimentation."
    # Icon = """paste here the contents of a 16x16 xpm icon"""
    # Icon = App.getHomePath() + "Mod\\CamPlus\\icons\\CamPlus_icon.svg"
    Icon = (
        App.getUserAppDataDir()
        + "Mod\\CamPlus\\freecad\\camplus\\icons\\CamPlus_icon.svg"
    )
    CommandList = [
        "_AmendCode",
    ]

    def Initialize(self):
        """This function is executed when the workbench is first activated.
        It is executed once in a FreeCAD session followed by the Activated function.
        """
        # import MyModuleA, MyModuleB # import here all the needed files that create your FreeCAD commands
        import freecad.camplus.gui_commands as gui_commands

        # self.list = ["MyCommand1", "MyCommand2"] # a list of command names created in the line above
        # self.appendToolbar("My Commands", self.list) # creates a new toolbar with your commands
        # self.appendMenu("CamPlus", self.list) # creates a new menu
        # self.appendMenu(["An existing Menu", "My submenu"], self.list) # appends a submenu to an existing menu

        # creates a new toolbar with your commands
        # self.appendToolbar("CamPlus Commands", [])
        # self.appendMenu("CamPlus", [])  # creates a new menu

        Gui.addLanguagePath(":/translations")
        # Gui.addIconPath(":/icons")
        Gui.addCommand("_AmendCode", gui_commands._AmendCode())
        """
        Gui.addCommand("_LinkedOperation", gui_commands._LinkedOperation())
        Gui.addCommand(
            "_DressupCompoundProfile", gui_commands._DressupCompoundProfile()
        )
        Gui.addCommand("_DressupMultitags", gui_commands._DressupMultitags())
        Gui.addCommand(
            "_DressupOffsetInsideOut", gui_commands._DressupOffsetInsideOut()
        )
        Gui.addCommand("_DressupBoundary", gui_commands._DressupBoundary())
        Gui.addCommand("_WorkingShape", gui_commands._WorkingShape())
        Gui.addCommand("_InlayOperation", gui_commands._InlayOperation())
        Gui.addCommand("_ClearingOp", gui_commands._ClearingOp())
        Gui.addCommand("_RestShape", gui_commands._RestShape())
        """

        # Gui.addCommand("_StartOperation", gui_commands._StartOperation())

        self.appendToolbar("CamPlus Toolbar", self.CommandList)
        self.appendMenu("CamPlus", self.CommandList)

    def Activated(self):
        """This function is executed whenever the workbench is activated"""
        return

    def Deactivated(self):
        """This function is executed whenever the workbench is deactivated"""
        return

    def ContextMenu(self, recipient):
        """This function is executed whenever the user right-clicks on screen"""
        # "recipient" will be either "view" or "tree"
        self.appendContextMenu(
            "CamPlus commands", self.list
        )  # add commands to the context menu

    def GetClassName(self):
        # This function is mandatory if this is a full Python workbench
        # This is not a template, the returned string should be exactly "Gui::PythonWorkbench"
        return "Gui::PythonWorkbench"


Gui.addWorkbench(CamPlusWorkbench())
