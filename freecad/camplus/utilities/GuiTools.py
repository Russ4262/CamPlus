# -*- coding: utf-8 -*-
# ***************************************************************************
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

import PySide6
import Path.Base.Gui.Util as Util

__title__ = "GUI Tools"
__author__ = "Russell Johnson <russ4262>"
__url__ = "https://github.com/Russ4262/CamPlus"
__doc__ = "Utility functions for GUI task panel classes."

populateComboboxes = Util.populateCombobox


def selectInComboBox(name, combo):
    """selectInComboBox(name, combo) ...
    helper function to select a specific value in a combo box."""

    """
    This function copied from FreeCAD source, src/Mod/CAM/Path/Tool/Gui/Controller.py.
    Copy of ToolControllerEditor.selectInComboBox()
    """

    try:
        combo.blockSignals(True)
        index = combo.currentIndex()  # Save initial index

        # Search using currentData and return if found
        newindex = combo.findData(name)
        if newindex >= 0:
            combo.setCurrentIndex(newindex)
            return

        # if not found, search using current text
        newindex = combo.findText(name, PySide6.QtCore.Qt.MatchFixedString)
        if newindex >= 0:
            combo.setCurrentIndex(newindex)
            return

        # not found, return unchanged
        combo.setCurrentIndex(index)
    finally:
        combo.blockSignals(False)


#######################################################
# print("Imported GUI Tools.")
