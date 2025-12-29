# -*- coding: utf-8 -*-
# ***************************************************************************
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

import FreeCAD


__title__ = "ViewObject Tools"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Support functions to modify the ViewObject of FreeCAD objects."
__url__ = "https://github.com/Russ4262/PathRed"
__Wiki__ = ""
__date__ = ""


translate = FreeCAD.Qt.translate


def setTransparency(vObj, transparency):
    m = vObj.ShapeAppearance[0]
    if transparency >= 0.0 and transparency <= 100.0:
        t = transparency
    else:
        t = m.Transparency

    vObj.ShapeAppearance = FreeCAD.Material(
        DiffuseColor=m.DiffuseColor,
        AmbientColor=m.AmbientColor,
        SpecularColor=m.SpecularColor,
        EmissiveColor=m.EmissiveColor,
        Shininess=m.Shininess,
        Transparency=t,
    )

    if transparency >= 0.0 and transparency <= 100.0:
        vObj.Transparency = transparency


def setDiffuseColor(vObj, diffuse, transparency=None):
    """setDiffuseColor(vObj, diffuse, transparency=None)
    Sets DiffuseColor and optional Transparency of vObj"""

    if (isinstance(diffuse, tuple) or isinstance(diffuse, list)) and len(diffuse) == 3:
        m = vObj.ShapeAppearance[0]  # get current material attributes
        if transparency is not None and transparency >= 0.0 and transparency <= 100.0:
            t = float(transparency)
        else:
            t = m.Transparency
        vObj.ShapeAppearance = FreeCAD.Material(
            DiffuseColor=(diffuse[0] / 255.0, diffuse[1] / 255.0, diffuse[2] / 255.0),
            AmbientColor=m.AmbientColor,
            SpecularColor=m.SpecularColor,
            EmissiveColor=m.EmissiveColor,
            Shininess=m.Shininess,
            Transparency=t,
        )
    if transparency is not None and transparency >= 0.0 and transparency <= 100.0:
        vObj.Transparency = int(transparency)


def applyColorScheme(vObj, rbgTuple, transparency=None, application="Full"):
    if transparency is not None and transparency >= 0.0 and transparency <= 100.0:
        t = int(transparency)
    else:
        t = None

    if application == "Full":
        vObj.LineColor = rbgTuple
        setDiffuseColor(vObj, rbgTuple, t)
    elif application == "Line":
        vObj.LineColor = rbgTuple
    elif application == "Shape":
        setDiffuseColor(vObj, rbgTuple, t)
    else:
        FreeCAD.Console.PrintError(f"'{application}' application not recognized.")


# print("Imported ViewObject Tools")
