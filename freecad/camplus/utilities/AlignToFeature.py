# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2022 Russell Johnson (russ4262) <russ4262@gmail.com>    *
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
import Part
import math
import Path.Geom as PathGeom
import freecad.camplus.utilities.Edge as Edge

translate = FreeCAD.Qt.translate

IS_MACRO = False  # Set to True to use as macro
IS_DEBUG = False
CENTER_OF_ROTATION = FreeCAD.Vector(0.0, 0.0, 0.0)
AVAILABLE_AXES = {"X": True, "Y": True, "Z": False}
AXIS_MAP = {"x": "A", "y": "B", "z": "C"}
AXES_OF_ROTATION = {
    "X": FreeCAD.Vector(1.0, 0.0, 0.0),
    "Y": FreeCAD.Vector(0.0, 1.0, 0.0),
    "Z": FreeCAD.Vector(0.0, 0.0, 1.0),
    "A": FreeCAD.Vector(1.0, 0.0, 0.0),
    "B": FreeCAD.Vector(0.0, 1.0, 0.0),
    "C": FreeCAD.Vector(0.0, 0.0, 1.0),
}
FEED_AXIS = {"A": 5.0, "B": 6.0, "C": 7.0}
RAPID_AXIS = {"A": 10.0, "B": 12.0, "C": 14.0}


# Support functions
def _makeSquareFace(z=1.0):
    # Make simple, rectagular face
    p1 = FreeCAD.Vector(-0.5, -0.5, z)
    p2 = FreeCAD.Vector(0.5, -0.5, z)
    p3 = FreeCAD.Vector(0.5, 0.5, z)
    p4 = FreeCAD.Vector(-0.5, 0.5, z)
    l1 = Part.makeLine(p1, p2)
    l2 = Part.makeLine(p2, p3)
    l3 = Part.makeLine(p3, p4)
    l4 = Part.makeLine(p4, p1)
    return Part.Face(Part.Wire([l1, l2, l3, l4]))


def _getFirstAxisAvailable():
    for a in AVAILABLE_AXES.keys():
        if AVAILABLE_AXES[a] is True:
            return a


def _invertRotationsVector(rotVect):
    def invert(d):
        if d > 0.0:
            return d - 180.0, True
        elif d < 0.0:
            return d + 180.0, True
        else:
            return 0.0, False

    x, xd = invert(rotVect.x)
    y, yd = invert(rotVect.y)
    # Check if normalAt for Z=1 needs inverted
    if not xd and not yd:
        x = 180.0
    return FreeCAD.Vector(x, y, 0.0)


def _normalizeDegrees(degree):
    if degree > 180.0:
        return degree - 360.0
    elif degree < -180.0:
        return degree + 360.0
    else:
        return degree


def getRotationsForObject_orig(obj):
    # print("getRotationsForObject()")
    if obj.Face == "None" and obj.Edge == "None":
        FreeCAD.Console.PrintWarning("getRotationsForObject() Feature name is None.\n")
        return (
            FreeCAD.Vector(0.0, 0.0, 0.0),
            False,
        )

    if obj.Edge != "None":
        rotations, isPlanar = getRotationToLineByName(
            obj.Model, obj.Edge, obj.InvertDirection
        )
    else:
        rotations, isPlanar = getRotationToFace(
            FreeCAD.ActiveDocument.getObject(obj.Model.Name).Shape, obj.Face
        )
    # print(f"getRotations() final rotations: {rotations}")
    return rotations, isPlanar


def getRotationsForObject(obj):
    # print("getRotationsForObject()")
    if obj.Face == "None" and obj.Edge == "None":
        FreeCAD.Console.PrintWarning("getRotationsForObject() Feature name is None.\n")
        return (
            FreeCAD.Vector(0.0, 0.0, 0.0),
            False,
        )

    if obj.Edge != "None":
        rotations = getRotationToLineByName(obj.Model, obj.Edge, obj.InvertDirection)
    else:
        rotations = getRotationToFace(
            FreeCAD.ActiveDocument.getObject(obj.Model.Name).Shape, obj.Face
        )
    # print(f"getRotations() final rotations: {rotations}")
    return rotations


def getRotationsByName_orig(modelName, featureName, invert):
    print("getRotationsByName()")
    if featureName == "None":
        FreeCAD.Console.PrintWarning("Feature name is None.\n")
        return [], False
    if featureName.startswith("Edge"):
        rotations, isPlanar = getRotationToLineByName(modelName, featureName, invert)
    else:
        rotations, isPlanar = getRotationToFace(
            FreeCAD.ActiveDocument.getObject(modelName).Shape, featureName
        )
    # print(f"rotations to apply full: {rotations}")
    return rotations, isPlanar


def getRotationsByName(modelName, featureName, invert):
    print("getRotationsByName()")
    if featureName == "None":
        FreeCAD.Console.PrintWarning("Feature name is None.\n")
        return [], False
    if featureName.startswith("Edge"):
        rotations = getRotationToLineByName(modelName, featureName, invert)
    else:
        rotations = getRotationToFace(
            FreeCAD.ActiveDocument.getObject(modelName).Shape, featureName
        )
    # print(f"rotations to apply full: {rotations}")
    return rotations


def rotateShapeWithVector(shape, rotVect):
    rotated = shape.copy()
    if not PathGeom.isRoughly(rotVect.x, 0.0):
        rotated.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), rotVect.x)
    if not PathGeom.isRoughly(rotVect.y, 0.0):
        rotated.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 1.0, 0.0), rotVect.y)
    if not PathGeom.isRoughly(rotVect.z, 0.0):
        rotated.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 0.0, 1.0), rotVect.z)
    return rotated


def getRotationToLineByName_orig(modelName, edgeName, isInverted=False):
    """getRotationToLineByName(modelName, faceName)
    Return necessary degree rotations to align given line with Z=1, in vector form x, y, and z.
    Note: The rotation values may need to be inverted in order to orient model correctly.
    """
    rotations = []
    # rotVect = FreeCAD.Vector(0.0, 0.0, 0.0)
    cycles = 4
    malAligned = True

    model = FreeCAD.ActiveDocument.getObject(modelName)
    edge = model.Shape.getElement(edgeName)  # 1, 6, 4
    if edge.Curve.TypeId not in ["Part::GeomLine", "Part::GeomLineSegment"]:
        FreeCAD.Console.PrintWarning("Edge must be line.\n")
        return FreeCAD.Vector(0.0, 0.0, 0.0), False

    e = edge.copy()
    if isInverted:
        com = e.valueAt(e.LastParameter)
    else:
        com = e.valueAt(e.FirstParameter)
    trans = com.add(FreeCAD.Vector(0.0, 0.0, 0.0)).multiply(-1.0)
    e.translate(trans)

    while malAligned:
        cycles -= 1
        if isInverted:
            norm = (
                e.valueAt(e.FirstParameter).sub(e.valueAt(e.LastParameter)).normalize()
            )
        else:
            norm = (
                e.valueAt(e.LastParameter).sub(e.valueAt(e.FirstParameter)).normalize()
            )
        # print(f"--NORM: {norm}")
        x0 = PathGeom.isRoughly(norm.x, 0.0)
        y0 = PathGeom.isRoughly(norm.y, 0.0)
        z1 = PathGeom.isRoughly(norm.z, 1.0)
        z_1 = PathGeom.isRoughly(norm.z, -1.0)
        if not (z1 or z_1):
            if not x0:
                ang = math.degrees(math.atan2(norm.x, norm.z))
                if ang < 0.0:
                    ang = 0.0 - ang
                elif ang > 0.0:
                    ang = 180.0 - ang
                e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 1.0, 0.0), ang)
                rotations.append(("Y", _normalizeDegrees(ang)))
                # rotVect.y = _normalizeDegrees(ang)
                # print(f"  ang: {ang}")
                continue
            elif not y0:
                ang = math.degrees(math.atan2(norm.z, norm.y))
                ang = 90.0 - ang
                e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), ang)
                rotations.append(("X", _normalizeDegrees(ang)))
                # rotVect.x = _normalizeDegrees(ang)
                # print(f"  ang: {ang}")
                continue
        elif x0 and y0 and z_1:
            e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), 180.0)
            continue

        malAligned = False
        if cycles < 1:
            print("Break for cycles")
            break

    # norm = e.valueAt(e.LastParameter).sub(e.valueAt(e.FirstParameter)).normalize()
    # print(f"  {edgeName} norm: {norm}\n  rotations: {rotations}")
    # Part.show(e, edgeName)

    return (rotations, True)


def getRotationToLineByName(modelName, edgeName, isInverted=False):
    """getRotationToLineByName(modelName, faceName)
    Return necessary degree rotations to align given line with Z=1, in vector form x, y, and z.
    Note: The rotation values may need to be inverted in order to orient model correctly.
    """
    rotations = []
    # rotVect = FreeCAD.Vector(0.0, 0.0, 0.0)
    cycles = 4
    malAligned = True

    model = FreeCAD.ActiveDocument.getObject(modelName)
    edge = model.Shape.getElement(edgeName)  # 1, 6, 4
    if edge.Curve.TypeId not in ["Part::GeomLine", "Part::GeomLineSegment"]:
        FreeCAD.Console.PrintWarning("Edge must be line.\n")
        return FreeCAD.Vector(0.0, 0.0, 0.0)

    e = edge.copy()
    if isInverted:
        com = e.valueAt(e.LastParameter)
    else:
        com = e.valueAt(e.FirstParameter)
    trans = com.add(FreeCAD.Vector(0.0, 0.0, 0.0)).multiply(-1.0)
    e.translate(trans)

    while malAligned:
        cycles -= 1
        if isInverted:
            norm = (
                e.valueAt(e.FirstParameter).sub(e.valueAt(e.LastParameter)).normalize()
            )
        else:
            norm = (
                e.valueAt(e.LastParameter).sub(e.valueAt(e.FirstParameter)).normalize()
            )
        # print(f"--NORM: {norm}")
        x0 = PathGeom.isRoughly(norm.x, 0.0)
        y0 = PathGeom.isRoughly(norm.y, 0.0)
        z1 = PathGeom.isRoughly(norm.z, 1.0)
        z_1 = PathGeom.isRoughly(norm.z, -1.0)
        if not (z1 or z_1):
            if not x0:
                ang = math.degrees(math.atan2(norm.x, norm.z))
                if ang < 0.0:
                    ang = 0.0 - ang
                elif ang > 0.0:
                    ang = 180.0 - ang
                e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 1.0, 0.0), ang)
                rotations.append(("Y", _normalizeDegrees(ang)))
                # rotVect.y = _normalizeDegrees(ang)
                # print(f"  ang: {ang}")
                continue
            elif not y0:
                ang = math.degrees(math.atan2(norm.z, norm.y))
                ang = 90.0 - ang
                e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), ang)
                rotations.append(("X", _normalizeDegrees(ang)))
                # rotVect.x = _normalizeDegrees(ang)
                # print(f"  ang: {ang}")
                continue
        elif x0 and y0 and z_1:
            e.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), 180.0)
            continue

        malAligned = False
        if cycles < 1:
            print("Break for cycles")
            break

    # norm = e.valueAt(e.LastParameter).sub(e.valueAt(e.FirstParameter)).normalize()
    # print(f"  {edgeName} norm: {norm}\n  rotations: {rotations}")
    # Part.show(e, edgeName)

    return rotations


def getRotationToFaceByShape(modelShape, face):
    modelHash = modelShape.hashCode()
    modelName = ""
    base = None
    for o in FreeCAD.ActiveDocument.Objects:
        if hasattr(o, "Shape") and hasattr(o.Shape, "hashCode"):
            if o.Shape.hashCode() == modelHash:
                modelName = o.Name
                base = o
                break
    if not modelName:
        FreeCAD.Console.PrintError("No model name found.\n")
        return None

    faceHash = face.hashCode()
    faceName = ""
    for i in range(len(modelShape.Faces)):
        f = modelShape.Faces[i]
        if f.hashCode() == faceHash:
            rf = f
            faceName = f"Face{i+1}"
            break
    if not faceName:
        FreeCAD.Console.PrintError("No face name found.\n")
        return None

    return getRotationToFace_COPY(base, faceName)


def getRotationToFace_COPY(base, faceName):
    """getRotationToFace_COPY(base, faceName)
    Return necessary degree rotations to align given face with Z=1, in vector form x, y, and z.
    """
    global GROUP

    face = base.Shape.getElement(faceName)

    u, v = face.ParameterRange[:2]
    norm = face.normalAt(u, v)
    globPlace = base.getGlobalPlacement()
    globRotation = globPlace.Rotation
    normalVector = globRotation.multVec(norm)
    # print(f"global normalVector: {normalVector}")

    rotations = _calculateRotationsToFace(face)
    rotBase2 = rotateShapeWithList(base.Shape, rotations)
    isFlat = PathGeom.isRoughly(rotBase2.getElement(faceName).BoundBox.ZLength, 0.0)
    rb2 = Part.show(rotBase2, f"RotBase2_{faceName}")
    GROUP.addObject(rb2)
    return rotations, isFlat


def _getTwoSolutions(face, norm):
    yRotAng1 = -90.0
    xRotAng1 = math.degrees(math.atan2(norm.y, norm.x))
    sltn1 = FreeCAD.Vector(xRotAng1, yRotAng1, 0.0)
    yRotAng2 = math.degrees(math.atan2(norm.x, norm.y))
    xRotAng2 = -90.0
    sltn2 = FreeCAD.Vector(xRotAng2, yRotAng2, 0.0)
    return (sltn1, sltn2)


def _refineRotations(rotations):
    def standardizeAngle(ang):
        if ang > 180.0:
            return ang - 360.0
        if ang < -180.0:
            return ang + 360.0
        return ang

    rCnt = len(rotations)
    if rCnt < 2:
        return rotations
    refined = []
    axisCnts = {"X": 0, "Y": 0, "Z": 0}
    order = []
    for a, d in rotations:
        axisCnts[a] += d
        if a not in order:
            order.append(a)
    for a in order:
        refined.append((a, standardizeAngle(axisCnts[a])))

    return refined


def _calculateRotationsToFace(face):
    """_calculateRotationsToFace(face)
    Return necessary degree rotations to align given face with Z=1, in vector form x, y, and z.
    Return value is an ordered list of tuples, each an (axis, value) pair."""
    # print("AlignToFeature._calculateRotationsToFace()")

    if face is None or len(face.Edges) < 1:
        FreeCAD.Console.PrintWarning(
            "_calculateRotationsToFace() face is 'None' or has no edges.\n"
        )
        return []

    rotations = []  # Preferred because rotation order is important
    cycles = 0
    malAligned = True
    com = face.CenterOfMass

    faa = _getFirstAxisAvailable()
    if faa not in ["X", "Y"]:
        print("--ERROR: X and Y not available for rotation where norm.z = 0.0")
        return rotations

    f = face.copy()
    trans = com.add(FreeCAD.Vector(0.0, 0.0, 0.0)).multiply(-1.0)
    f.translate(trans)

    while malAligned:
        if IS_DEBUG:
            print(f"_calculateRotationsToFace() while rotations {rotations}")
        cycles += 1
        u, v = f.ParameterRange[:2]
        norm = f.normalAt(u, v)
        if IS_DEBUG:
            print(f"_calculateRotationsToFace() cycle {cycles},   norm {norm}")
        # print(f"--NORM: {norm}")
        x0 = PathGeom.isRoughly(norm.x, 0.0)
        x1 = PathGeom.isRoughly(norm.x, 1.0)
        x_1 = PathGeom.isRoughly(norm.x, -1.0)
        y0 = PathGeom.isRoughly(norm.y, 0.0)
        y1 = PathGeom.isRoughly(norm.y, 1.0)
        y_1 = PathGeom.isRoughly(norm.y, -1.0)
        z0 = PathGeom.isRoughly(norm.z, 0.0)
        z1 = PathGeom.isRoughly(norm.z, 1.0)
        z_1 = PathGeom.isRoughly(norm.z, -1.0)
        if z0:
            # Vertical face
            if x1 or x_1:
                # Facing along X axis
                if AVAILABLE_AXES["Y"]:
                    rotAng = -90.0
                    if x_1:
                        rotAng = 90.0
                    f.rotate(CENTER_OF_ROTATION, AXES_OF_ROTATION["Y"], rotAng)
                    # print("Rotating for Z=0 around Y axis.")
                    rotations.append(("Y", rotAng))
                    # return rotations
                    break
            elif y1 or y_1:
                # Facing along Y axis
                if AVAILABLE_AXES["X"]:
                    rotAng = 90.0
                    if y_1:
                        rotAng = -90.0
                    f.rotate(CENTER_OF_ROTATION, AXES_OF_ROTATION["X"], rotAng)
                    # print("Rotating for Z=0 around X axis.")
                    rotations.append(("X", rotAng))
                    # return rotations
                    break
            else:
                aSol, bSol = _getTwoSolutions(face, norm)
                f.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 1.0, 0.0), aSol.y)
                f.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), aSol.x)
                # print(f"Dual rotation for Z=0. Using solution A. {aSol}")
                rotations.append(("Y", aSol.y))
                rotations.append(("X", aSol.x))
                # return rotations
                break
        elif z_1 and x0 and y0:
            if AVAILABLE_AXES["Y"]:
                rotAng = 180.0
                f.rotate(CENTER_OF_ROTATION, AXES_OF_ROTATION["Y"], rotAng)
                # print("Flipping object for Z=-1.0 around Y axis.")
                rotations.append(("Y", rotAng))
                # return rotations
                break
            elif AVAILABLE_AXES["X"]:
                rotAng = 180.0
                f.rotate(CENTER_OF_ROTATION, AXES_OF_ROTATION["X"], rotAng)
                # print("Flipping object for Z=-1.0 around X axis.")
                rotations.append(("X", rotAng))
                # return rotations
                break
            else:
                print("Unable to flip Z=-1.0 object around Y or X axes.")
                # return rotations
                break
        elif z1:
            if IS_DEBUG:
                print("Breaking rotation scan loop for Z=1")
            break
        else:
            if not x0:
                ang = math.degrees(math.atan2(norm.x, norm.z))
                if ang < 0.0:
                    ang = 0.0 - ang
                elif ang > 0.0:
                    ang = 180.0 - ang
                f.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(0.0, 1.0, 0.0), ang)
                rotAng = _normalizeDegrees(ang)
                rotations.append(("Y", rotAng))
                # print(f"  ang: {ang}")
                continue
            elif not y0:
                ang = math.degrees(math.atan2(norm.z, norm.y))
                ang = 90.0 - ang
                f.rotate(CENTER_OF_ROTATION, FreeCAD.Vector(1.0, 0.0, 0.0), ang)
                rotAng = _normalizeDegrees(ang)
                rotations.append(("X", rotAng))
                # print(f"  ang: {ang}")
                continue

        malAligned = False
        if cycles > 5:
            # Fail-safe against infinite loop situation.
            print("Error: 5+ cycles used and unable to identify rotations needed.")
            break

    # norm = f.normalAt(0, 0)
    # print(f"  {faceName} norm: {norm}\n  rotations: {rotations}")
    # print(f"  center of mass: {com}")
    # Part.show(f, faceName)
    if IS_DEBUG:
        print(f"_calculateRotationsToFace() raw rotations {rotations}")

    refined = _refineRotations(rotations)
    if IS_DEBUG:
        print(f"_calculateRotationsToFace() return rotations {refined}")

    return refined


def _rotationsToOrderAndValues(rotations):
    """_rotationsToOrderAndValues(rotations)...
    From an ordered list of (axis, value) tuples,
    a single tuple is returned containing axis order as a lowercase string with no spaces,
    and a vector object containing respective float values.
    """
    axisOrder = ""
    degreeValues = FreeCAD.Vector(0.0, 0.0, 0.0)
    for axis, degree in rotations:
        attr = axis.lower()
        axisOrder += attr
        setattr(degreeValues, attr, degree)
    return axisOrder, degreeValues


def _getPlacementBase(rotations, zMin):
    sqr = _makeSquareFace(1.0)
    sqr.translate(FreeCAD.Vector(0.0, 0.0, zMin - sqr.BoundBox.ZMin))
    sqrRot = rotateShapeWithList(
        sqr,
        reverseRotationsList(rotations, reverseCorrection=False),
    )
    return sqrRot.CenterOfMass


# Regular functions
def storeRotationsInObject(rotations, obj):
    """_rotationsToOrderAndValues(rotations, obj)...
    Stores the 'rotations' list of (axis, value) tuples into the 'obj' provided.
    """
    # Store for reference by other objects
    if rotations and obj:
        rOrder, rVals = _rotationsToOrderAndValues(rotations)
        obj.RotationsOrder = rOrder
        obj.RotationsValues = rVals
        return True
    return False


def clearRotationsInObject(obj):
    """clearRotationsInObject(obj)...
    Clears the rotations data stored in the 'obj' provided.
    """
    obj.RotationsOrder = ""
    obj.RotationsValues = FreeCAD.Vector(0.0, 0.0, 0.0)
    return True


def buildRotationsList(obj, mapped=False):
    """buildRotationsList(obj, mapped=False)...
    Given an obj parameter, will return an ordered list of tuples,
    each containing an (axis, value) pair.
    Details:
        obj.RotationsOrder is a lowercase string of axes, no spaces
        obj.RotationsValues is a vector object containing float values
    """
    return getRotationsList(obj, mapped)


def getRotationsList(obj, mapped=False):
    """getRotationsList(obj, mapped=False)...
    Given an obj parameter, will return an ordered list of tuples,
    each containing an (axis, value) pair.
    Details:
        obj.RotationsOrder is a lowercase string of axes, no spaces
        obj.RotationsValues is a vector object containing float values
    """
    rotations = []
    for i in range(len(obj.RotationsOrder)):
        axis = obj.RotationsOrder[i]
        useAxis = axis.upper()
        if mapped:
            useAxis = AXIS_MAP[axis]

        rotations.append(
            (
                useAxis,
                getattr(obj.RotationsValues, axis),
            )
        )
    return rotations


def reverseRotationsList(rotations, reverseCorrection=True):
    """reverseRotationsList(rotations)...
    Returns reversed version of rotations to apply to return to start point.
    DO NOT USE THIS FUNCTION if rotation angles are absolute, and not relative."""
    if len(rotations) == 0:
        return []

    r = [(axis, -1.0 * val) for axis, val in rotations]

    if len(r) == 1:
        return r

    if reverseCorrection:
        if r[0][1] == 90.0:
            return r
        if r[0][1] == -90.0:
            return r

    r.reverse()
    return r


def rotateShapeWithList(shape, rotations):
    rotated = shape.copy()
    if not rotations or len(rotations) == 0:
        return rotated

    rotVects = {
        "X": FreeCAD.Vector(1.0, 0.0, 0.0),
        "Y": FreeCAD.Vector(0.0, 1.0, 0.0),
        "Z": FreeCAD.Vector(0.0, 0.0, 1.0),
    }
    for axis, angle in rotations:
        rotated.rotate(CENTER_OF_ROTATION, rotVects[axis], angle)
    return rotated


def setObjectPlacement(obj, zShift=0.0, rotations=[]):
    """setObjectPlacement(obj, zShift=0.0, rotations=[])
    Set obj's Placement property per zShift value and rotations list."""
    # print(f"setObjectPlacement(obj, {rotations}, {zShift})")
    origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    if zShift == 0.0:
        base = FreeCAD.Vector(0.0, 0.0, 0.0)
    else:
        base = FreeCAD.Vector(0.0, 0.0, zShift)

    if len(rotations) == 0:
        # if zShift != 0.0:
        #    obj.Placement.Base = base
        obj.Placement.Base = base
    elif len(rotations) == 1:
        rotTup = rotations[0]
        axis = AXES_OF_ROTATION[rotTup[0]]
        angle = rotTup[1]
        # print(f".. base, axis, angle: {origin};  {axis};  {angle}")
        obj.Placement = FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))
    elif len(rotations) == 2:
        rotTup1 = rotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {b1};  {axis1};  {ang1}")

        rotTup2 = rotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {b2};  {axis2};  {ang2}")

        # apply multiple rotations in order
        obj.Placement = p1.multiply(p2)
        # apply zShift to Placement as FreeCAD.Vector(0.0, 0.0, zShift)
        obj.Placement.Base = base
    else:
        FreeCAD.Console.PrintError(
            translate("PathRed", "More than two rotations to apply.")
        )


def setObjectPlacementFull(obj, base, rotations=[]):
    """setObjectPlacementFull(obj, base, rotations=[])
    Set obj's Placement property per zShift value and rotations list."""
    # print(f"setObjectPlacementFull(obj, {base}, {rotations})")

    origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    if len(rotations) == 0:
        # if zShift != 0.0:
        #    obj.Placement.Base = base
        obj.Placement.Base = base
    elif len(rotations) == 1:
        rotTup = rotations[0]
        axis = AXES_OF_ROTATION[rotTup[0]]
        angle = rotTup[1]
        # print(f".. base, axis, angle: {origin};  {axis};  {angle}")
        obj.Placement = FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))
    elif len(rotations) == 2:
        rotTup1 = rotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis1, ang1))
        print(f"1 base, axis, angle: {origin};  {axis1};  {ang1}")

        rotTup2 = rotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis2, ang2))
        print(f"2 base, axis, angle: {origin};  {axis2};  {ang2}")

        # apply multiple rotations in order
        obj.Placement = p1.multiply(p2)
        print(f"placement after p1*p2: {obj.Placement}")
        # apply zShift to Placement as FreeCAD.Vector(0.0, 0.0, zShift)
        obj.Placement.Base = base
        print(f"final placement: {obj.Placement}")
    elif len(rotations) == 3:
        rotTup1 = rotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {b1};  {axis1};  {ang1}")

        rotTup2 = rotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {b2};  {axis2};  {ang2}")

        rotTup3 = rotations[1]
        axis3 = AXES_OF_ROTATION[rotTup3[0]]
        ang3 = rotTup3[1]
        p3 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis3, ang3))
        # print(f"3 base, axis, angle: {b3};  {axis3};  {ang3}")

        # apply multiple rotations in order
        obj.Placement = p1.multiply(p2).multiply(p3)
        # apply zShift to Placement as FreeCAD.Vector(0.0, 0.0, zShift)
        obj.Placement.Base = base
    else:
        FreeCAD.Console.PrintError(
            translate("PathRed", "More than two rotations to apply.")
        )


def setObjectPlacementFullAlt(obj, zMin, rotations):
    """setObjectPlacementFullAlt(obj, zMin, rotations)
    Set obj's Placement property per base value, zMin and rotations list."""
    # print(f"setObjectPlacementFullAlt(obj, {zMin}, {rotations})")

    revCor = False if len(rotations) < 2 else True

    useRotations = reverseRotationsList(
        rotations, reverseCorrection=False
    )  # default: False
    if revCor:
        useRotations.reverse()
        # print(f"useRotations REVERSED: {useRotations}")

    base = _getPlacementBase(rotations, zMin)

    if len(rotations) > 1:
        if not revCor:
            print(f"Negating original 'base': {base}")
            base.multiply(-1.0)
    # print(f"obj.Placement base: {base}")

    # origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    if len(useRotations) == 0:
        obj.Placement.Base = base
    elif len(useRotations) == 1:
        rotTup = useRotations[0]
        axis = AXES_OF_ROTATION[rotTup[0]]
        angle = rotTup[1]
        # print(f".. base, axis, angle: {origin};  {axis};  {angle}")
        obj.Placement = FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))
    elif len(useRotations) == 2:
        rotBase = FreeCAD.Vector(0.0, 0.0, 0.0 - zMin)
        rotTup1 = useRotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {rotBase};  {axis1};  {ang1}")

        rotTup2 = useRotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {rotBase};  {axis2};  {ang2}")

        # apply multiple rotations in order
        obj.Placement = p1.multiply(p2)
        # print(f"placement after p1*p2: {obj.Placement}")

        # apply base translation to Placement
        obj.Placement.Base = base
        # print(f"final placement: {obj.Placement}")
    elif len(useRotations) == 3:
        rotBase = FreeCAD.Vector(0.0, 0.0, 0.0 - zMin)
        rotTup1 = useRotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {rotBase};  {axis1};  {ang1}")

        rotTup2 = useRotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {rotBase};  {axis2};  {ang2}")

        rotTup3 = useRotations[1]
        axis3 = AXES_OF_ROTATION[rotTup3[0]]
        ang3 = rotTup3[1]
        p3 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis3, ang3))
        # print(f"3 base, axis, angle: {rotBase};  {axis3};  {ang3}")

        # apply multiple rotations in order
        obj.Placement = p1.multiply(p2).multiply(p3)

        # apply base translation to Placement
        obj.Placement.Base = base
    else:
        FreeCAD.Console.PrintError(
            translate("PathRed", "More than two rotations to apply.")
        )


def makeObjectPlacement(base, rotations=[]):
    """makeObjectPlacement(base, rotations=[])
    Return Placement object per base with rotations list."""
    # print(f"makeObjectPlacement({base}, {rotations})")
    origin = FreeCAD.Vector(0.0, 0.0, 0.0)
    if len(rotations) == 0:
        return FreeCAD.Placement(
            origin, FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 0.0)
        )
    elif len(rotations) == 1:
        rotTup = rotations[0]
        axis = AXES_OF_ROTATION[rotTup[0]]
        angle = rotTup[1]
        # print(f".. base, axis, angle: {origin};  {axis};  {angle}")
        return FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))
    elif len(rotations) == 2:
        rotTup1 = rotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {b1};  {axis1};  {ang1}")

        rotTup2 = rotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {b2};  {axis2};  {ang2}")

        # apply multiple rotations in order
        placement = p1.multiply(p2)
        # apply zShift to Placement as FreeCAD.Vector(0.0, 0.0, zShift)
        placement.Base = base
        return placement
    elif len(rotations) == 3:
        rotTup1 = rotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {b1};  {axis1};  {ang1}")

        rotTup2 = rotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {b2};  {axis2};  {ang2}")

        rotTup3 = rotations[1]
        axis3 = AXES_OF_ROTATION[rotTup3[0]]
        ang3 = rotTup3[1]
        p3 = FreeCAD.Placement(origin, FreeCAD.Rotation(axis3, ang3))
        # print(f"3 base, axis, angle: {b3};  {axis3};  {ang3}")

        # apply multiple rotations in order
        placement = p1.multiply(p2).multiply(p3)
        # apply zShift to Placement as FreeCAD.Vector(0.0, 0.0, zShift)
        placement.Base = base
        return placement
    else:
        FreeCAD.Console.PrintError(
            translate("PathRed", "More than three rotations to apply.")
        )


def makeObjectPlacementAlt(zMin, rotations):
    """makeObjectPlacementAlt(zMin, rotations)
    Set obj's Placement property per base value, zMin and rotations list."""
    # print(f"setObjectPlacementFull(obj, {base}, {zMin}, {rotations})")

    revCor = False if len(rotations) < 2 else True

    useRotations = reverseRotationsList(
        rotations, reverseCorrection=False
    )  # default: False
    if revCor:
        useRotations.reverse()
        # print(f"useRotations REVERSED: {useRotations}")

    base = _getPlacementBase(rotations, zMin)

    if len(rotations) > 1:
        if not revCor:
            # print("default base.multiply(-1.0)")
            base.multiply(-1.0)
    # print(f"obj.Placement base: {base}")

    if len(useRotations) == 0:
        placement = FreeCAD.Placement()
        placement.Base = base
        return placement
    elif len(useRotations) == 1:
        rotTup = useRotations[0]
        axis = AXES_OF_ROTATION[rotTup[0]]
        angle = rotTup[1]
        # print(f".. base, axis, angle: {origin};  {axis};  {angle}")
        return FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))
    elif len(useRotations) == 2:
        rotBase = FreeCAD.Vector(0.0, 0.0, 0.0 - zMin)
        rotTup1 = useRotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {rotBase};  {axis1};  {ang1}")

        rotTup2 = useRotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {rotBase};  {axis2};  {ang2}")

        # apply multiple rotations in order
        placement = p1.multiply(p2)
        # print(f"placement after p1*p2: {obj.Placement}")

        # apply base translation to Placement
        placement.Base = base
        # print(f"final placement: {obj.Placement}")
        return placement
    elif len(useRotations) == 3:
        rotBase = FreeCAD.Vector(0.0, 0.0, 0.0 - zMin)
        rotTup1 = useRotations[0]
        axis1 = AXES_OF_ROTATION[rotTup1[0]]
        ang1 = rotTup1[1]
        p1 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis1, ang1))
        # print(f"1 base, axis, angle: {rotBase};  {axis1};  {ang1}")

        rotTup2 = useRotations[1]
        axis2 = AXES_OF_ROTATION[rotTup2[0]]
        ang2 = rotTup2[1]
        p2 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis2, ang2))
        # print(f"2 base, axis, angle: {rotBase};  {axis2};  {ang2}")

        rotTup3 = useRotations[1]
        axis3 = AXES_OF_ROTATION[rotTup3[0]]
        ang3 = rotTup3[1]
        p3 = FreeCAD.Placement(rotBase, FreeCAD.Rotation(axis3, ang3))
        # print(f"3 base, axis, angle: {rotBase};  {axis3};  {ang3}")

        # apply multiple rotations in order
        placement = p1.multiply(p2).multiply(p3)

        # apply base translation to Placement
        placement.Base = base
        return placement
    else:
        FreeCAD.Console.PrintError(
            translate("PathRed", "More than two rotations to apply.")
        )
    return None


def clearObjectPlacement(obj, zShift=0.0):
    """setObjectPlacement(obj, rotations, zShift)
    Set obj's Placement property per rotations and zShift values"""
    # print(f"setObjectPlacement(obj, {rotations}, {zShift})")
    base = FreeCAD.Vector(0.0, 0.0, zShift)
    axis = FreeCAD.Vector(0.0, 0.0, 1.0)
    angle = 0.0
    obj.Placement = FreeCAD.Placement(base, FreeCAD.Rotation(axis, angle))


def isFaceHoriz(rotatedBaseShape, faceName):
    return PathGeom.isRoughly(
        rotatedBaseShape.getElement(faceName).BoundBox.ZLength, 0.0
    )


def getRotationToFace(baseShape, faceName):
    """getRotationToFace(baseShape, faceName)
    Return necessary degree rotations to align given face with Z=1, in vector form x, y, and z.
    """
    # print("AlignToFeature.getRotationToFace()")
    face = baseShape.getElement(faceName)
    return _calculateRotationsToFace(face)  # Needs normalVector calculated above


def getRotationToEdge(edge):
    """getRotationToEdge(edge)
    Returns rotations to edge. Edge provided must be nonlinear."""
    return _calculateRotationsToFace(Edge.getPlaneFaceFromEdge(edge))


def invertRotation(rotations):
    if len(rotations) == 0:
        return []
    elif len(rotations) == 1:
        r1 = rotations[0]
        return [(r1[0], _normalizeDegrees(r1[1] + 180.0))]
    elif len(rotations) == 2:
        r1 = rotations[0]
        r2 = rotations[1]
        return [
            (r1[0], _normalizeDegrees(r1[1] + 180.0)),
            (r2[0], _normalizeDegrees(r2[1] + 180.0)),
        ]
    print("invertRotation() ERROR: rotations length > 2")
    return []


def getRotationVector(rotations):
    """getRotationVector(rotations)
    Return the 'rotations' list argument as a single vector"""
    l = Part.makeLine(FreeCAD.Vector(0.0, 0.0, 0.0), FreeCAD.Vector(0.0, 0.0, 10.0))
    reversedRotations = reverseRotationsList(rotations)
    rotLine = rotateShapeWithList(l, reversedRotations)
    p = rotLine.Vertexes[1].Point
    return FreeCAD.Vector(p.x, p.y, p.z)


def _executeAsMacro8():
    global GROUP
    baseObj = []

    print("\n")

    selection = FreeCADGui.Selection.getSelectionEx()
    # process user selection
    for sel in selection:
        # print(f"Object.Name: {sel.Object.Name}")
        baseObj.append((sel.Object, [n for n in sel.SubElementNames]))

    for base, featList in baseObj:
        for feat in featList:
            print(f"Working... {feat}")
            rotations = getRotationToFace(base.Shape, feat)


def test01():
    rotationVectors = [
        FreeCAD.Vector(0.0, 90, 0),
        FreeCAD.Vector(45, -45, 0),
        FreeCAD.Vector(-100, 20, 0),
        FreeCAD.Vector(0, 0, 0),
    ]
    for v in rotationVectors:
        inverted = _invertRotationsVector(v)
        print(f"{v}\n{inverted}\n")


# Primary function

# print("Imported Macro_AlignToFeature")


if IS_MACRO and FreeCAD.GuiUp:
    import FreeCADGui

    GROUP = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "Group")
    _executeAsMacro8()
    # CENTER_OF_ROTATION = FreeCAD.Vector(100, 50, 0)
    # _executeAsMacro()
    # test01()
    FreeCAD.ActiveDocument.recompute()
