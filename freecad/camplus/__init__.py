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

import FreeCAD as App
import os

__title__ = "CamPlus workbench __init__ module"
__author__ = "Russell Johnson <russ4262>"
__url__ = "https://github.com/Russ4262/CamPlus"
__doc__ = "__init__.py module for CamPlus workbench."
__version__ = "1.5"

directory = os.path.dirname(__file__)
ICONSPATH = os.path.join(directory, "icons")
TASKPANELSPATH = os.path.join(directory, "taskpanels")
GUIPANELSPATH = os.path.join(directory, "guipanels")
IMAGESPATH = os.path.join(directory, "images")


# Project references:
# https://wiki.freecad.org/Create_a_FeaturePython_object_part_I/ru
# https://wiki.freecad.org/Create_a_FeaturePython_object_part_II/ru

# Load the Parameter Group for this module
ParGrp = App.ParamGet("System parameter:Modules").GetGroup("CamPlus")

# Set the Parameter Group details
# ParGrp.SetString("HelpIndex", "CamPlus/Help/index.html")
ParGrp.SetString("WorkBenchName", "CamPlus")
# ParGrp.SetString("WorkBenchModule", "CamPlusWorkbench.py")

# App.__unit_test__ += ["TestCamPlusApp"]

App.Console.PrintMessage("Initializing CamPlus workbench...\n")
