# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2023 Russell Johnson (russ4262) <russ4262@gmail.com>    *
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
import Mesh
import MeshPart
import Sketcher
import Path.Geom as PathGeom
import Path.Op.Util as PathUtil
import freecad.camplus.utilities.Edge as Edge
import freecad.camplus.inlay.Support as InlaySupport


if FreeCAD.GuiUp:
    import FreeCADGui

math = PathUtil.math


__title__ = "Mesh Tools Macro"
__author__ = "Russell Johnson (russ4262) <russ4262@gmail.com>"
__doc__ = "Macro utility to create vertical projection from faces that wrap around the X and/or Y axises."
__usage__ = "Select a 3D face that wraps around the X or Y axis, then run this macro."
__url__ = ""
__Wiki__ = ""
__date__ = "2023.06.29"
__version__ = 1.0
__files__ = "Test_Mesh_Tools-1.FCStd"


IS_MACRO = False
RES_IDX = 0
RESOLUTION = [
    (1.0, 3.14 / 180.0 * 30.0),
    (0.25, 3.14 / 180.0 * 20.0),
    (0.05, 3.14 / 180.0 * 10.0),
    (0.01, 3.14 / 180.0 * 5.0),
    (0.005, 3.14 / 180.0 * 2.5),
]


def setResolutionIndex(idx=1):
    if not isinstance(idx, int):
        print(f"Resolution index must integer 1-{len(RESOLUTION)}.")
        return None
    if idx < 0 or idx > len(RESOLUTION):
        print(f"Resolution index must be 1-{len(RESOLUTION)}.")
        return None
    RES_IDX = idx - 1
    return RESOLUTION[RES_IDX]


def fuseShapes(shapes):
    if len(shapes) == 0:
        return None
    if len(shapes) == 1:
        return shapes[0]
    return shapes[0].fuse(shapes[1:])


def simplifyFaces(faceGroup):
    """simplifyFaces(faceGroup)
    Expectation is that incoming faces are coplanar,
    and one is the exterior and the others interior 'holes' to be cut out."""
    faces = sorted(faceGroup, key=lambda f: abs(f.Area), reverse=True)
    if len(faces) == 0:
        return None
    if len(faces) == 1:
        return faces[0]
    f = faces[0]
    for fc in faces[1:]:
        cut = f.cut(fc)
        f = cut
    return f


def meshToObject(mesh, label="Mesh"):
    __doc__ = FreeCAD.ActiveDocument
    __obj__ = __doc__.addObject("Mesh::Feature", "Mesh")
    __obj__.Mesh = mesh
    __obj__.Label = label
    return


def shapeToObject(shape, label="Shape"):
    if shape is None:
        print("Error: shapeToObject(None)")
        return
    __doc__ = FreeCAD.ActiveDocument
    __obj__ = __doc__.addObject("Part::Feature", "Shape")
    __obj__.Shape = shape
    __obj__.Label = label


def sketchToObject(sketch, label="Sketch"):
    if sketch is None:
        print("Error: sketchToObject(None)")
        return
    __doc__ = FreeCAD.ActiveDocument
    __obj__ = __doc__.addObject("Sketcher::SketchObject", "Sketch")
    __obj__.Sketch = sketch
    __obj__.Label = label


def shapeToMesh(shape, linearDeflection=2.0, angularDeflection=20.0):
    return MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=linearDeflection,
        AngularDeflection=math.radians(angularDeflection),
        Relative=False,
    )


def meshToShape(mesh, sewShape=True, resolution=0.1):
    shp = Part.Shape()
    shp.makeShapeFromMesh(mesh.Topology, resolution, sewShape)
    return shp


def shapeToMeshSolid(shape, linearDeflection=2.0, angularDeflection=20.0):
    mesh = shapeToMesh(shape, linearDeflection, angularDeflection)
    faces = [facetPointsToFace(f.Points) for f in mesh.Facets]
    return Part.makeSolid(Part.makeShell(faces))


def meshToFace(mesh):
    faces = []
    for fct in mesh.Facets:
        pnts = fct.Points
        p1 = FreeCAD.Vector(pnts[0][0], pnts[0][1], pnts[0][2])
        p2 = FreeCAD.Vector(pnts[1][0], pnts[1][1], pnts[1][2])
        p3 = FreeCAD.Vector(pnts[2][0], pnts[2][1], pnts[2][2])
        faces.append(
            Part.Face(
                Part.Wire(
                    [
                        Part.makeLine(p1, p2),
                        Part.makeLine(p2, p3),
                        Part.makeLine(p3, p1),
                    ]
                )
            )
        )
    return fuseShapes(faces)


def facetToEdges(fct):
    pnts = fct.Points
    p1 = FreeCAD.Vector(pnts[0][0], pnts[0][1], pnts[0][2])
    p2 = FreeCAD.Vector(pnts[1][0], pnts[1][1], pnts[1][2])
    p3 = FreeCAD.Vector(pnts[2][0], pnts[2][1], pnts[2][2])
    return (Part.makeLine(p1, p2), Part.makeLine(p2, p3), Part.makeLine(p3, p1))


def facetToFlatEdges(fct):
    pnts = fct.Points
    p1 = FreeCAD.Vector(pnts[0][0], pnts[0][1], 0.0)
    p2 = FreeCAD.Vector(pnts[1][0], pnts[1][1], 0.0)
    p3 = FreeCAD.Vector(pnts[2][0], pnts[2][1], 0.0)
    segments = []
    if not PathGeom.isRoughly(p1.sub(p2).Length, 0.0):
        segments.append(Part.makeLine(p1, p2))
    if not PathGeom.isRoughly(p2.sub(p3).Length, 0.0):
        segments.append(Part.makeLine(p2, p3))
    if not PathGeom.isRoughly(p3.sub(p1).Length, 0.0):
        segments.append(Part.makeLine(p3, p1))
    return segments


def extrudeMesh(mesh, vector):
    faces = [facetPointsToFace(f.Points) for f in mesh.Facets]
    solids = [f.extrude(vector) for f in faces]
    return fuseShapes(solids)


def extractMeshProjection_orig(mesh, zNormLimit=0.000001):
    """extractMeshProjection(mesh)
    Return mesh portion with postitive Z normal values"""
    meshProj = Mesh.Mesh()
    meshProj.addFacets([f for f in mesh.Facets if f.Normal.z > zNormLimit])
    return meshProj


def extractMeshProjection(mesh, precision=6):
    """extractMeshProjection(mesh)
    Return mesh portion with postitive Z normal values"""
    meshProj = Mesh.Mesh()
    meshProj.addFacets([f for f in mesh.Facets if round(f.Normal.z, precision) > 0.0])
    return meshProj


def extractMeshPerimeterWires_orig(
    mesh, flatten=False, refine=True, zNormLimit=0.000001
):
    """extractMeshPerimeterWires(mesh, flatten=False, refine=True, zNormLimit=0.000001)
    Return all perimeter wires of mesh whose facets have postitive Z normal values"""
    edges = []

    if flatten:
        for fct in [f for f in mesh.Facets if f.Normal.z > zNormLimit]:
            edges.extend(facetToFlatEdges(fct))
    else:
        for fct in [f for f in mesh.Facets if f.Normal.z > zNormLimit]:
            edges.extend(facetToEdges(fct))

    wires = []
    for g in Part.sortEdges(Edge.uniqueEdges(edges, precision=4)):
        if refine:
            oeb = Edge._orientEdgesBasic(g)
            grp = [oeb[0]]
            lstDir = oeb[0].Vertexes[1].Point.sub(oeb[0].Vertexes[0].Point).normalize()
            for o in oeb[1:]:
                curDir = o.Vertexes[1].Point.sub(o.Vertexes[0].Point).normalize()
                if PathGeom.isRoughly(curDir.sub(lstDir).Length, 0.0):
                    # direction of last edge and current edge are within tolerance,
                    # so extend previous line to end of current
                    grp.append(
                        Part.makeLine(grp.pop().Vertexes[0].Point, o.Vertexes[1].Point)
                    )
                else:
                    grp.append(o)
                    lstDir = curDir
            # Efor
            wires.append(Part.Wire(grp))
        else:
            wires.append(Part.Wire(g))
    return wires


def extractMeshPerimeterWires_orig(
    mesh, flatten=False, refine=True, zNormLimit=0.000001
):
    """extractMeshPerimeterWires(mesh, flatten=False, refine=True, zNormLimit=0.000001)
    Return all perimeter wires of mesh whose facets have postitive Z normal values"""
    edges = []

    if flatten:
        for fct in [f for f in mesh.Facets if f.Normal.z > zNormLimit]:
            edges.extend(facetToFlatEdges(fct))
    else:
        for fct in [f for f in mesh.Facets if f.Normal.z > zNormLimit]:
            edges.extend(facetToEdges(fct))

    wires = []
    for g in Part.sortEdges(Edge.uniqueEdges(edges, precision=4)):
        if refine:
            wires.append(Part.Wire(Edge.refineWireEdges(g)))
        else:
            wires.append(Part.Wire(g))
    return wires


def extractMeshPerimeterWires(mesh, flatten=False, refine=True, precision=6):
    """extractMeshPerimeterWires(mesh, flatten=False, refine=True, zNormLimit=0.000001)
    Return all perimeter wires of mesh whose facets have postitive Z normal values"""
    edges = []

    if flatten:
        for fct in [f for f in mesh.Facets if round(f.Normal.z, precision) > 0.0]:
            edges.extend(facetToFlatEdges(fct))
    else:
        for fct in [f for f in mesh.Facets if round(f.Normal.z, precision) > 0.0]:
            edges.extend(facetToEdges(fct))

    wires = []
    for g in Part.sortEdges(Edge.uniqueEdges(edges, 4)):
        if refine:
            wires.append(Part.Wire(Edge.refineWireEdges(g)))
        else:
            wires.append(Part.Wire(g))
    return wires


def meshToFlatProjection(mesh):
    """meshToFlatProjection(mesh)
    Return flat projection of mesh at Z=0.0
    """
    faces = [
        facetPointsToFlatFace(f.Points)
        for f in [f for f in mesh.Facets if f.Normal.z > 0.0000001]
    ]
    mf = faces[0].fuse(faces[1:])
    return PathGeom.makeBoundBoxFace(mf.BoundBox, 5.0).cut(
        PathGeom.makeBoundBoxFace(mf.BoundBox, 10.0).cut(mf)
    )


def extractOverheadRegion(shape, ld=2.0, ad=20.0):
    """extractMeshProjectionDown(mesh)
    Return mesh portion with postitive Z normal values"""

    def fMax(points):
        return max([p[2] for p in points])

    trimShpMesh = shapeToMesh(shape, ld, ad)
    meshProj = Mesh.Mesh()
    meshProj.addFacets(
        [
            f
            for f in trimShpMesh.Facets
            if f.Normal.z < 0.0001
            and not PathGeom.isRoughly(fMax(f.Points), shape.BoundBox.ZMin)
        ]
    )
    fcs = []
    for fct in meshProj.Facets:
        try:
            fcs.append(facetPointsToFlatFace(fct.Points))
        except:
            pass
    r = simplifyRegion(fuseShapes(fcs))
    return r


def identifyOverheadRegion(mesh, shape):
    """extractMeshProjectionDown(mesh)
    Return mesh portion with postitive Z normal values"""

    def fMax(points):
        return max([p[2] for p in points])

    meshProj = Mesh.Mesh()
    meshProj.addFacets([f for f in mesh.Facets if fMax(f.Points) > shape.BoundBox.ZMin])
    fcs = []
    for fct in meshProj.Facets:
        try:
            fcs.append(facetPointsToFlatFace(fct.Points))
        except:
            pass
    r = simplifyRegion(fuseShapes(fcs))
    return r


def isFacePlanar(face, linearDeflection=2.0, angularDeflection=20.0):
    """isFacePlanar(face, linearDeflection=2.0, angularDeflection=0.26)
    Return True if face is coplanar."""
    mesh = shapeToMesh(face, linearDeflection, angularDeflection)
    # norm = mesh.Facets[0].Normal.z
    # for f in mesh.Facets[1:]:
    #    if not PathGeom.isRoughly(f.Normal.z, norm):
    #        return False
    norm = mesh.Facets[0].Normal
    for f in mesh.Facets:
        if not PathGeom.isRoughly(norm.sub(f.Normal).Length, 0.0):
            return False

    return True


def faceHasUndercut(face, linearDeflection=2.0, angularDeflection=20.0, roundTo=6):
    """isFacePlanar(face, linearDeflection=2.0, angularDeflection=0.26)
    Return True if face is coplanar."""
    mesh = shapeToMesh(face, linearDeflection, angularDeflection)
    allNegative = True
    rtn = False
    for f in mesh.Facets:
        n = round(f.Normal.z, roundTo)
        if n < 0.0:
            # print(f"faceHasUndercut() Normal.z: {f.Normal.z}")
            rtn = True
        elif n == 0.0 and allNegative:
            pass
        elif n == -0.0 and allNegative:
            pass
        else:
            # print(f"faceHasUndercut() Normal.z: {round(f.Normal.z, roundTo)}")
            allNegative = False
    print(f"allNegative: {allNegative}")

    if allNegative:
        return False, mesh

    return rtn, mesh


def areFacesEquiPlanar(faces, linearDeflection=2.0, angularDeflection=20.0):
    """areFacesEquiPlanar(faces, linearDeflection=2.0, angularDeflection=0.26)
    Return True if all faces are coplanar."""

    """
    # Method 1 - z value only
    meshes = [shapeToMesh(f, linearDeflection, angularDeflection) for f in faces]
    norm = meshes[0].Facets[0].Normal.z
    for m in meshes:
        for f in m.Facets:
            if not PathGeom.isRoughly(f.Normal.z, norm):
                return False

    # Method 2 - z value only
    norm = None
    for fc in faces:
        m = shapeToMesh(fc, linearDeflection, angularDeflection)
        if norm is None:
            norm = m.Facets[0].Normal.z
        for f in m.Facets:
            if not PathGeom.isRoughly(f.Normal.z, norm):
                return False
    """

    # Method 3 - Use full Normal vector for comparison
    norm = None
    for fc in faces:
        m = shapeToMesh(fc, linearDeflection, angularDeflection)
        if norm is None:
            norm = m.Facets[0].Normal
        for f in m.Facets:
            if not PathGeom.isRoughly(norm.sub(f.Normal).Length, 0.0):
                return False

    return True


#############################################
#############################################


def simplifyRegion(region):
    """simplifyRegion(region)
    Expected that region is a single, cohesive face shape, comprised of multiple sub-faces.
    Removes internal dividing wires.
    This is an alternate to 'removeSplitter()' method.
    """
    if not region:
        return None

    edges = []
    for f in region.Faces:
        edges.extend([e.copy() for e in f.Edges])
    unique = Edge.uniqueEdges(edges)
    groups = Part.sortEdges(unique)
    faces = []
    i = 0
    for grp in groups:
        w = Part.Wire(grp)
        # Part.show(w, "Wire")
        if w.isClosed():
            try:
                f = Part.Face(w)
            except Exception as ee:
                Part.show(w, f"ErrorWire_{i}_")
                print("Closed wire likely not coplanar.")
            else:
                # print(f"Face.Area: {f.Area};  Wire.Length: {w.Length}")
                if f.Area > 0.05:
                    if w.Length > 1.0:
                        faces.append(f)
                        print("Adding face from unique edges closed wire.")
        else:
            # print("group of edges is OPEN")
            print("Adding face from unique edges open wire, with closing edge.")
            # shapeToObject(w, "OpenWire")
            # Close the open wire with a line segment.
            p1 = w.Vertexes[-1].Point
            p2 = w.Vertexes[0].Point
            print(f"Closing edge length: {round(p2.sub(p1).Length, 6)}")
            f = Part.Face(
                Part.Wire([e.copy() for e in w.Edges] + [Part.makeLine(p1, p2)])
            )
            faces.append(f)
        i += 1
    # Efor

    # shapeToObject(Part.makeCompound(faces), "SR_Faces")

    return simplifyFaces(faces)


def getUniqueEdges(edges):
    data = [(f"H{e.hashCode()}", e) for e in edges]
    data.sort(key=lambda t: t[0])
    keep = []
    last = data[0]
    trash = False

    for now in data[1:]:
        if now[0] == last[0]:
            # repeat of last
            trash = True  # ignore
        else:
            if trash:
                last.pop()
                trash = False
            keep.append(last)
            last = now
    if trash:
        last.pop()
        trash = False
    else:
        keep.append(last)
    return [e for __, e in keep]


def simplifyRegion_exp(region):
    """simplifyRegion(region)
    Expected that region is a single, cohesive face shape, comprised of multiple sub-faces.
    Removes internal dividing wires.
    This is an alternate to 'removeSplitter()' method.
    """
    # unique = Edge.uniqueEdges(edges)
    unique = getUniqueEdges(region.Edges)
    groups = Part.sortEdges(unique)
    faces = []
    i = 0
    for grp in groups:
        w = Part.Wire(grp)
        if w.isClosed():
            try:
                f = Part.Face(w)
            except Exception as ee:
                Part.show(w, f"ErrorWire_{i}_")
                print("Closed wire likely not coplanar.")
            else:
                # print(f"Face.Area: {f.Area};  Wire.Length: {w.Length}")
                if f.Area > 0.05:
                    if w.Length > 1.0:
                        faces.append(f)
        i += 1
    # Efor

    # shapeToObject(Part.makeCompound(faces), "SR_Faces")

    return simplifyFaces(faces)


def getMeshWires(faces):
    """getMeshWires(faces)
    Expected that faces belong to a single, cohesive meshed face."""
    edges = []
    for f in faces:
        edges.extend([e.copy() for e in f.Edges])
    unique = Edge.uniqueEdges(edges)
    groups = Part.sortEdges(unique)
    faces = []
    wires = []
    for grp in groups:
        # w = Part.Wire(Part.__sortEdges__(grp))
        # w = Part.Wire(Edge._orientEdgesBasic(grp))
        w = Part.Wire(grp)
        if w.isClosed():
            wires.append(w)
    return wires


def cleanAndFlattenWire(wire):
    edges = []
    for e in wire.Edges:
        if e.Length < 0.01:
            print(f"e.Length: {e.Length}")
        v1 = e.Vertexes[0]
        v2 = e.Vertexes[1]
        p1 = FreeCAD.Vector(round(v1.X, 7), round(v1.Y, 7), 0.0)
        p2 = FreeCAD.Vector(round(v2.X, 7), round(v2.Y, 7), 0.0)
        if p1.sub(p2).Length > 0.0001:
            line = Part.makeLine(p1, p2)
            edges.append(line)
            # edges.append(Part.LineSegment(p1, p2))
        else:
            print(f"Line.Length: {p1.sub(p2).Length} - IGNORING")
    return Part.Wire(Edge._orientEdges(edges))


def cleanFace(face):
    bbFace1 = PathGeom.makeBoundBoxFace(face.BoundBox, 2.0)
    bbFace2 = PathGeom.makeBoundBoxFace(face.BoundBox, 4.0)
    neg = bbFace2.cut(face)
    clean = bbFace1.cut(neg)
    return clean.copy()


def wireToSketch(wire):
    __doc__ = FreeCAD.ActiveDocument
    sketch = __doc__.addObject("Sketcher::SketchObject", "Sketch")
    # sketch = Sketcher.Sketch()
    pi = 0
    for e in wire.Edges:
        v1 = e.Vertexes[0]
        v2 = e.Vertexes[1]
        x1 = round(v1.X, 7)
        y1 = round(v1.Y, 7)
        x2 = round(v2.X, 7)
        y2 = round(v2.Y, 7)
        p1 = FreeCAD.Vector(x1, y1, 0.0)
        p2 = FreeCAD.Vector(x2, y2, 0.0)
        sketch.addGeometry(Part.LineSegment(p1, p2))
        # sketch.addConstraint(Sketcher.Constraint("DistanceX", pi, 1, -1, 1, -x1))
        # sketch.addConstraint(Sketcher.Constraint("DistanceY", pi, 1, -1, 1, -y1))
        if pi > 0:
            sketch.addConstraint(Sketcher.Constraint("Coincident", pi - 1, 2, pi, 1))
        pi += 1
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 2, pi - 1, 1))

    return sketch


def flattenAndCombineWiresIntoFace(wires):
    faces = []
    for wr in wires:
        cw = cleanAndFlattenWire(wr)
        w = PathUtil.orientWire(cw)
        # s = wireToSketch(w)
        f = Part.Face(w)
        faces.append(f)

    return simplifyFaces(faces)


def flattenAndCombineWiresIntoRegion(wires):
    faces = []
    for wr in wires:
        proj = InlaySupport.makeProjection(wr)
        w = Part.Wire(proj.Edges)
        # w = PathUtil.orientWire(pw)
        # s = wireToSketch(w)
        f = Part.Face(w)
        if f.Area < 0.0:
            proj2 = InlaySupport.makeProjection(wr)
            pw2 = Part.Wire(proj2.Edges)
            w = PathUtil.orientWire(pw2)
            f = Part.Face(w)
        a = f.Area
        if abs(a) > 0.05:
            if w.Length > 1.0:
                faces.append(f)
        else:
            print(f"Face.Area: {f.Area};  Wire.Length: {w.Length}")
    # shapeToObject(Part.makeCompound(faces), "FlatFaces")

    return simplifyFaces(faces)


def applyHoles(region, holeFaces):
    if not holeFaces:
        return region
    face = region.copy()
    for h in holeFaces:
        cut = face.cut(h)
        face = cut
    return face


def facetPointsToFlatFace(pnt):
    p1 = FreeCAD.Vector(pnt[0][0], pnt[0][1], 0.0)
    p2 = FreeCAD.Vector(pnt[1][0], pnt[1][1], 0.0)
    p3 = FreeCAD.Vector(pnt[2][0], pnt[2][1], 0.0)
    return Part.Face(
        Part.Wire([Part.makeLine(p1, p2), Part.makeLine(p2, p3), Part.makeLine(p3, p1)])
    )


def meshToFlatEdges(mesh):
    """meshToFlatEdges(mesh)
    Will likely throw errors due to line through same points, since all points are at Z=0.0
    """
    iR = PathGeom.isRoughly
    edges = []
    for f in mesh.Facets:
        pnts = f.Points
        p1 = FreeCAD.Vector(pnts[0][0], pnts[0][1], 0.0)
        p2 = FreeCAD.Vector(pnts[1][0], pnts[1][1], 0.0)
        p3 = FreeCAD.Vector(pnts[2][0], pnts[2][1], 0.0)
        if not iR(p1.sub(p2).Length, 0.0):
            edges.append(Part.makeLine(p1, p2))
        if not iR(p2.sub(p3).Length, 0.0):
            edges.append(Part.makeLine(p2, p3))
        if not iR(p3.sub(p1).Length, 0.0):
            edges.append(Part.makeLine(p3, p1))
    return edges


def meshToEdges(mesh):
    edges = []
    for f in mesh.Facets:
        pnts = f.Points
        p1 = FreeCAD.Vector(pnts[0][0], pnts[0][1], pnts[0][2])
        p2 = FreeCAD.Vector(pnts[1][0], pnts[1][1], pnts[1][2])
        p3 = FreeCAD.Vector(pnts[2][0], pnts[2][1], pnts[2][2])
        edges.extend(
            [Part.makeLine(p1, p2), Part.makeLine(p2, p3), Part.makeLine(p3, p1)]
        )
    return edges


def facetPointsToFace(pnt):
    p1 = FreeCAD.Vector(pnt[0][0], pnt[0][1], pnt[0][2])
    p2 = FreeCAD.Vector(pnt[1][0], pnt[1][1], pnt[1][2])
    p3 = FreeCAD.Vector(pnt[2][0], pnt[2][1], pnt[2][2])
    return Part.Face(
        Part.Wire([Part.makeLine(p1, p2), Part.makeLine(p2, p3), Part.makeLine(p3, p1)])
    )


def isVerticalExtrusion(f):
    if f.ShapeType == "Face":
        if type(f.Surface) == Part.Plane and PathGeom.isVertical(f):
            return True
        if (
            type(f.Surface) == Part.Cylinder or type(f.Surface) == Part.Cone
        ) and PathGeom.isVertical(f):
            return True
    return False


def isFlatPlane(f):
    if f.ShapeType == "Face":
        if type(f.Surface) == Part.Plane and PathGeom.isHorizontal(f):
            return True
    return False


def flattenVerticalFace(f):
    """Face is expected to be vertical extrusion with or without holes.
    Any interior holes are vain for vertical projection."""
    fc = None
    w = Part.Wire(InlaySupport.makeProjection(f.Wires[0]).Edges)
    if w.isClosed():
        fc = Part.Face(w)
    return fc, w


def edgesToFlatWires(edges):
    flat = []
    for e in edges:
        flat.extend(InlaySupport.makeProjection(e).Edges)
    groups = Part.sortEdges(flat)
    return [Part.Wire(g) for g in groups]


def wiresToRegions(wires):
    faces = []
    openWires = []
    edges = []
    for w in wires:
        for e in w.Edges:
            edges.append(e)
    groups = Part.sortEdges(edges)
    for g in groups:
        w = Part.Wire(g)
        if w.isClosed():
            faces.append(Part.Face(w))
        else:
            openWires.append(w)
    return faces, openWires


def getAbove_BndBx_CutMethod(baseShape, f):
    bbf = PathGeom.makeBoundBoxFace(f.BoundBox, zHeight=baseShape.BoundBox.ZMin - 1.0)
    bbbs = PathGeom.makeBoundBoxFace(
        baseShape.BoundBox, 1.0, zHeight=baseShape.BoundBox.ZMin - 1.0
    )
    fc = bbbs.copy().cut(bbf)
    extFC = fc.extrude(FreeCAD.Vector(0.0, 0.0, baseShape.BoundBox.ZLength + 2.0))
    # shapeToObject(extFC, "extFC")
    return baseShape.cut(extFC)


def getAbove_BndBx_CommonMethod(baseShape, f):
    fc = PathGeom.makeBoundBoxFace(f.BoundBox, zHeight=baseShape.BoundBox.ZMin - 1.0)
    extFC = fc.extrude(FreeCAD.Vector(0.0, 0.0, baseShape.BoundBox.ZLength + 2.0))
    # shapeToObject(extFC, "extFC")
    return baseShape.common(extFC)


def facesToRegions(baseShape, faces, faceWrap, avoidOverhangs):
    regions = []
    wires = []
    above = []
    ld, ad = RESOLUTION[RES_IDX]

    for f in faces:
        # shapeToObject(f, "SourceFace")
        if isFlatPlane(f):
            print("facesToRegions() Face is simple flat.")
            fc = f.copy()
            fc.translate(FreeCAD.Vector(0.0, 0.0, 0.0 - f.BoundBox.ZMin))
            regions.append(fc)
            if avoidOverhangs:
                focus = getAbove_BndBx_CommonMethod(baseShape, f)
                # shapeToObject(focus, "AboveFocus")
                abv = identify_1(f, focus)
                # shapeToObject(abv, "AboveSolid")
                if above:
                    above.append(abv)
        elif isVerticalExtrusion(f):
            print("facesToRegions() Face is vertical extrusion.")
            r, w = flattenVerticalFace(f)
            if r:
                regions.append(r)
                if avoidOverhangs:
                    focus = getAbove_BndBx_CommonMethod(baseShape, f)
                    # shapeToObject(focus, "AboveFocus")
                    abv = identify_1(f, focus)
                    # shapeToObject(abv, "AboveSolid")
                    if above:
                        above.append(abv)

            else:
                wires.append(w)
        else:
            print("facesToRegions() Face is complex - meshing it.")
            m = shapeToMesh(f, ld, ad)
            if faceWrap:
                mp = extractMeshProjection(m)
            else:
                mp = m

            try:
                fcs = [facetPointsToFlatFace(fct.Points) for fct in mp.Facets]
            except Exception as ee:
                print(f"Error with Face: {ee}")
                shapeToObject(f, "ErrorFace")
                # meshToObject(mp, "ErrorMesh")
                continue
            else:
                r = simplifyRegion(fuseShapes(fcs))
                # shapeToObject(r, "FlatFace_new")
                if r:
                    regions.append(r)

            if r and avoidOverhangs:
                if faceWrap:
                    # print("Above feature for faceWrap is non-functional.")
                    print("Above feature for faceWrap.")
                    fc = Part.Face(r.Wires[0].copy())
                    fc.translate(
                        FreeCAD.Vector(0.0, 0.0, f.BoundBox.ZMin - fc.BoundBox.ZMin)
                    )
                    focus = getAbove_BndBx_CommonMethod(baseShape, fc)
                    if len(focus.Faces) > 0:
                        # shapeToObject(focus, "AboveFocus2")
                        abv = identify_1(f, focus)
                        # abv2 = identify_2(f, focus2)
                        # shapeToObject(abv, "AboveSolid")
                        if above:
                            above.append(abv)
                    else:
                        print("focus shape error. 1a")
                        focus = getAbove_BndBx_CutMethod(baseShape, fc.copy())
                        if len(focus.Faces) > 0:
                            # shapeToObject(focus, "AboveFocus2")
                            abv = identify_1(f, focus.copy())
                            # abv2 = identify_2(f, focus2)
                            # shapeToObject(abv, "AboveSolid")
                            if above:
                                above.append(abv)
                        else:
                            print("focus shape error. 1b")

                else:
                    fc = Part.Face(r.Wires[0].copy())
                    fc.translate(
                        FreeCAD.Vector(0.0, 0.0, f.BoundBox.ZMin - fc.BoundBox.ZMin)
                    )
                    focus = getAbove_BndBx_CommonMethod(baseShape, fc)
                    if len(focus.Faces) > 0:
                        # shapeToObject(focus, "AboveFocus2")
                        abv = identify_1(f, focus)
                        # abv2 = identify_2(f, focus2)
                        # shapeToObject(abv, "AboveSolid")
                        if above:
                            above.append(abv)
                    else:
                        print("focus shape error. 2")
            # Eif
    # Efor

    return regions, wires, fuseShapes(above)


def manageOverlapingRegions(outTups, inTups):
    idxs = []
    for ifi, fi in inTups:
        inArea = fi.Area
        # next = False
        for ofi, fo in outTups:
            outArea = fo.Area
            if outArea < inArea:
                if fi.common(fo).Area > outArea * 0.95:
                    idxs.append(ifi)
                    # next = True
                    # break
            # if next:
            #    break
    return idxs


def deconstructRegions(regions, complex=False):
    outer = []
    inner = []
    fi = 0
    for r in regions:
        for f in r.Faces:
            # shapeToObject(f, f"RawFace_{fi}_")
            isPlural = False
            for w in f.Wires:
                if isPlural:
                    inner.append((fi, Part.Face(w)))
                else:
                    outer.append((fi, Part.Face(w)))
                isPlural = True
            fi += 1
    outer.sort(key=lambda t: t[1].Area, reverse=True)
    inner.sort(key=lambda t: t[1].Area, reverse=True)

    if complex:
        # If any smaller outer faces are common with larger inner faces, replace that outer face with original version
        rawIdxs = manageOverlapingRegions(outer, inner)
        # reduce rawIdxs to unique values
        idxs = []
        for i in rawIdxs:
            if i not in idxs:
                idxs.append(i)
        # print(f"idxs: {idxs}")

        # delete overlapping outer face and corresponding inner holes
        oDel = [i for i in range(len(outer)) if outer[i][0] in idxs]
        iDel = [i for i in range(len(inner)) if inner[i][0] in idxs]
        oDel.sort(reverse=True)
        iDel.sort(reverse=True)
        # print(f"oDel: {oDel}")
        # print(f"iDel: {iDel}")
        for i in oDel:
            outer.pop(i)
        for i in iDel:
            inner.pop(i)

        # replace deleted outer face with entire original face
        fi = 0
        for r in regions:
            for f in r.Faces:
                if fi in idxs:
                    outer.append((fi, f.copy()))
                fi += 1

    outside = fuseShapes([t[1] for t in outer])
    inside = [t[1] for t in inner]
    return outside, inside


def cleanOuterRegions(outsideFeat):
    bbf1 = PathGeom.makeBoundBoxFace(outsideFeat.BoundBox, 4.0)
    cut = bbf1.cut(outsideFeat)
    # shapeToObject(cut, "NegOutFeat")
    cutFace = fuseShapes(
        [f for f in cut.Faces if f.Area > 0.05 and f.Wires[0].Length > 1.0]
    )
    bbf2 = PathGeom.makeBoundBoxFace(outsideFeat.BoundBox, 2.0)
    clean = bbf2.cut(cutFace)
    # shapeToObject(clean, "CleanOutFeat")
    return clean


def separateMergedHoles(combined):
    outer = []
    holes = []
    for f in combined.Faces:
        isPlural = False
        for w in f.Wires:
            if isPlural:
                holes.append(Part.Face(w))
            else:
                outer.append(Part.Face(w))
        isPlural = True
    return fuseShapes(outer), holes


def getFocusArea(baseShape, region, zMin):
    areas = []
    rgn = region.copy()
    rgn.translate(FreeCAD.Vector(0.0, 0.0, zMin))
    extLen = baseShape.BoundBox.ZMax + 1.0 - zMin
    for f in rgn.Faces:
        r = Part.Face(f.Wires[0])
        extrusion = r.extrude(FreeCAD.Vector(0.0, 0.0, extLen))
        focus = baseShape.common(extrusion)
        if hasattr(focus, "Volumne") and not PathGeom.isRoughly(focus.Volumne, 0.0):
            areas.append(focus)
    if len(areas) > 0:
        return fuseShapes(areas)
    return None


def solidToRegion_orig(shape, linearDeflection=2.0, angularDeflection=20.0):
    m = shapeToMesh(shape, linearDeflection, angularDeflection)
    mp = extractMeshProjection(m)
    fcs = [facetPointsToFlatFace(fct.Points) for fct in mp.Facets]
    r = simplifyRegion(fuseShapes(fcs))
    return r


def solidToRegion(shape, linearDeflection=2.0, angularDeflection=20.0):
    return meshToFlatProjection(shapeToMesh(shape, linearDeflection, angularDeflection))


def faceToRegion(face, linearDeflection=2.0, angularDeflection=20.0):
    meshProj = extractMeshProjection(
        shapeToMesh(face, linearDeflection, angularDeflection)
    )
    fcs = [facetPointsToFlatFace(fct.Points) for fct in meshProj.Facets]
    # if len(fcs) > 0:
    #    for f in fcs:
    #        Part.show(f, "Face")
    # r = simplifyRegion(fuseShapes(fcs))
    # Part.show(r, "MeshRegion")
    return simplifyRegion(fuseShapes(fcs)), meshProj.BoundBox.ZMin


def processAllFeatures(
    b, feats, faceWrap, saveFeatureHoles, saveMergedHoles, avoidOverhangs
):
    # print(f"processAllFeatures({b.Name}:{feats})")
    aboveRegion = None
    zMin = b.Shape.BoundBox.ZMin
    faces = [b.Shape.getElement(f) for f in feats if f.startswith("Face")]
    edges = [b.Shape.getElement(f) for f in feats if f.startswith("Edge")]

    # Adjust zMin as needed
    if faces:
        faceComp = Part.makeCompound(faces)
        zMin = max(zMin, faceComp.BoundBox.ZMin)
    if edges:
        edgeComp = Part.makeCompound(edges)
        zMin = max(zMin, edgeComp.BoundBox.ZMin)

    # Process available edges
    wires = edgesToFlatWires(edges)

    # Process available faces
    regions, faceWires, above = facesToRegions(b.Shape, faces, faceWrap, avoidOverhangs)
    if above is not None:
        # shapeToObject(above, "AboveSolid")
        aboveRegion = solidToRegion(above)
        # shapeToObject(aboveRegion, "AboveRegion")

    """
    if True:
        print("Ending prematurely")
        return
    """

    if faceWires:
        # shapeToObject(Part.makeCompound(faceWires), "FaceWires")
        wires.extend(faceWires)
    wRegions, openWires = wiresToRegions(wires)
    regions.extend(wRegions)

    outsideFeat, insideFeatHoles = deconstructRegions(regions, True)

    # shapeToObject(outsideFeat, "OutsideFeat")
    # for ifh in insideFeatHoles:
    #    shapeToObject(ifh, "FeatHole")

    if not outsideFeat:
        print("Error:  No outside feature.")
        return None

    # combined = simplifyRegion(outsideFeat) # Less effective
    combined = cleanOuterRegions(outsideFeat)
    # shapeToObject(combined, "Combined")

    # outside, insideMergeHoles = separateMergedHoles(combined)
    if len(combined.Faces) > 1:
        outside, insideMergeHoles = deconstructRegions([combined], True)
    else:
        outside = Part.Face(combined.Faces[0].Wires[0])
        insideMergeHoles = [Part.Face(w) for w in combined.Faces[0].Wires[1:]]

    # for imh in insideMergeHoles:
    #    shapeToObject(imh, "MergedHole")

    preregion = outside
    if saveFeatureHoles:
        preregion = applyHoles(outside, insideFeatHoles)

    if saveMergedHoles:
        preregion = applyHoles(preregion, insideMergeHoles)

    focusArea = getFocusArea(b.Shape, preregion, zMin)
    if focusArea:
        shapeToObject(focusArea, "FocusArea")
        __ = setResolutionIndex(3)
        focusMeshes = [shapeToMesh(s) for s in focusArea.Solids]
        # for fm in focusMeshes:
        #    meshToObject(fm, "FocusMesh")
    else:
        print("No focusArea produced.")

    if avoidOverhangs:
        if aboveRegion:
            return preregion.cut(aboveRegion)

    return preregion


def procesEntireBase(b, saveFeatureHoles):
    crossSection = solidToRegion(b.Shape)
    outside, insideFeatHoles = deconstructRegions([crossSection])
    if saveFeatureHoles:
        return applyHoles(outside, insideFeatHoles)

    return outside


def combineRegions(
    objBase,
    faceWrap,
    processFeatures,
    saveFeatureHoles,
    saveMergedHoles,
    processBase,
    avoidOverhangs,
):
    print(
        f"MeshTools.execute()\n:-:-: faceWrap: {faceWrap};  prcsBase: {processBase};  \
prcsFeats: {processFeatures};  saveFeatHoles: {saveFeatureHoles};  saveMergHoles: {saveMergedHoles}"
    )

    for b, feats in objBase:
        if processFeatures:
            __ = setResolutionIndex()
            region = processAllFeatures(
                b, feats, faceWrap, saveFeatureHoles, saveMergedHoles, avoidOverhangs
            )
            shapeToObject(region, "Region")
        if processBase:
            __ = setResolutionIndex()
            region = procesEntireBase(b, saveFeatureHoles)
            shapeToObject(region)


#########################################################
#########################################################
def getMidpointText(e, eLen):
    return f"L{round(eLen,4)}_" + Edge._pointToText(Edge.valueAtEdgeLength(e, eLen))


def makeEdgeMidpointIds(faces):
    ids = []
    fi = 0
    for f in faces:
        edges = f.Edges
        for ei in range(0, len(edges)):
            e = edges[ei]
            eLen = e.Length / 2.0
            ids.append(getMidpointText(e, eLen))
        fi += 1
    # Sort tups by xyz_length text, so same edges find each other
    ids.sort()
    return ids


def makeEdgeMidpointTups_2(f):
    tups = []
    fi = 0
    edges = f.Edges
    for ei in range(0, len(edges)):
        e = edges[ei]
        tups.append((getMidpointText(e, e.Length / 2.0), round(e.Length, 3)))
    fi += 1
    # Sort tups by xyz_length text, so same edges find each other
    tups.sort(key=lambda t: t[0])
    return tups


def makeEdgeMidpointTups(faces):
    tups = []
    fi = 0
    for f in faces:
        edges = f.Edges
        for ei in range(0, len(edges)):
            e = edges[ei]
            eLen = e.Length / 2.0
            tups.append((getMidpointText(e, eLen), fi))
        fi += 1
    # Sort tups by xyz_length text, so same edges find each other
    tups.sort(key=lambda t: t[0])
    return tups


def facesShareEdge(f1_tups, f2):
    # f1_tups = makeEdgeMidpointTups_2(f1)
    f2_tups = makeEdgeMidpointTups_2(f2)
    for txt, eLen in f1_tups:
        for t, l in f2_tups:
            if txt == t and eLen == l:
                return True
    return False


def identify_1(sf, af):
    zMin = sf.BoundBox.ZMin
    zMax = sf.BoundBox.ZMax
    area = sf.Area
    com = sf.CenterOfMass
    f1_tups = makeEdgeMidpointTups_2(sf)
    above = []
    other = []
    fi = 0
    debugMsg = False

    def dbgMsg(msg):
        if debugMsg:
            print(msg)

    def isSameFace(f):
        if f.CenterOfMass.sub(com).Length < 0.02 and abs((f.Area - area) / area) < 0.01:
            return True
        return False

    dbgMsg(f"len(af.Faces): {len(af.Faces)}")
    dbgMsg(f"sf.ZMin: {zMin}")
    dbgMsg(f"sf.ZMax: {zMax}")
    for f in af.Faces:
        # shapeToObject(f, f"AF_{fi}_")
        fMin = f.BoundBox.ZMin
        fMax = f.BoundBox.ZMax
        dbgMsg(f"Face idx {fi} ZMin: {fMin}")
        dbgMsg(f"Face idx {fi} ZMax: {fMax}")
        if PathGeom.isRoughly(fMin, zMin):
            dbgMsg(f"  starts at")
            if PathGeom.isRoughly(fMax, zMin):
                dbgMsg(f"  idx {fi} A")
                other.append(f.copy())
            elif fMax < zMax or PathGeom.isRoughly(fMax, zMax) or isSameFace(f):
                dbgMsg(f"  idx {fi} B")
                other.append(f.copy())
            elif fMax > zMax:
                dbgMsg(f"  idx {fi} C:")
                if isSameFace(f):
                    dbgMsg(f"  C1")
                    other.append(f.copy())
                elif facesShareEdge(f1_tups, f):
                    dbgMsg(f"  C2")
                    other.append(f.copy())
                else:
                    dbgMsg(f"  C3")
                    above.append(f.copy())
            else:
                dbgMsg(f"  idx {fi} D")
                above.append(f.copy())
        elif fMin < zMin:
            dbgMsg(f"  starts below")
            if fMax < zMin or PathGeom.isRoughly(fMax, zMin):
                other.append(f.copy())
            elif fMax < zMax or PathGeom.isRoughly(fMax, zMax):
                other.append(f.copy())
            elif isSameFace(f):
                other.append(f.copy())
            else:
                above.append(f.copy())
        elif fMin > zMin:
            dbgMsg(f"  starts above")
            if fMax < zMax or PathGeom.isRoughly(fMax, zMax):
                other.append(f.copy())
            else:
                above.append(f.copy())
        else:
            dbgMsg(f"Face idx {fi} starts elsewhere")
            other.append(f.copy())

        fi += 1

    # Part.show(Part.makeCompound(above), "RawAboveFaces")
    # if other:
    #    Part.show(Part.makeCompound(other), "Other")

    try:
        shell = Part.Shell(above)
        solid = Part.Solid(shell)
        return solid
    except Exception as ee:
        print(f"identify_1() Error: {ee}")

    return None


def identify_2(sf, af):
    sf_ids = makeEdgeMidpointIds(sf.Faces)
    af_tups = makeEdgeMidpointTups(af.Faces)
    # print(f"sf_ids: {sf_ids}")
    # print(f"af_tups: {af_tups}")

    # Identify faces with shared edges
    keep = []
    delete = []
    for mpTxt, fi in af_tups:
        if fi in delete:
            pass
        elif mpTxt in sf_ids:
            delete.append(fi)
        else:
            keep.append(fi)

    print(f"keep: {keep}")
    print(f"delete: {delete}")

    # purge keep of any delete values
    u = []
    for k in keep:
        if k not in delete and k not in u:
            u.append(k)

    print(f"keep unique: {u}")

    faces = []
    other = []
    fi = 0
    for f in af.Faces:
        if fi in u:
            faces.append(f.copy())
        else:
            other.append(f.copy())
        fi += 1

    # Part.show(Part.makeCompound(faces), "Faces")
    # Part.show(Part.makeCompound(other), "Other")
    try:
        shell = Part.Shell(other)
        solid = Part.Solid(shell)
        # Part.show(solid, "Solid")
        cut = af.cut(solid)
        # Part.show(cut, "Above")
        return cut
    except Exception as ee:
        print(f"identify_2() Error: {ee}")
    return None


#########################################################
#########################################################


def preparedSelection(idx, key):
    selections = [
        {
            "base": "Body001",
            "A": ("Face10",),
            "B": ("Face12", "Face69", "Face83", "Face10"),
            "C": ("Face12", "Face69", "Face83", "Face23", "Face10"),
            "D": ("Face12", "Face69", "Face83", "Face23", "Face10", "Face90", "Face92"),
            "E": ("Face12", "Face69", "Face83", "Face10", "Face90", "Face92"),
            "F": (
                "Face21",
                "Face80",
                "Face67",
                "Face65",
                "Face16",
                "Face6",
                "Face15",
                "Face10",
            ),
            "G": (
                "Face21",
                "Face80",
                "Face67",
                "Face65",
                "Face16",
                "Face6",
                "Face15",
                "Face10",
                "Face90",
                "Face92",
            ),
            "H": (
                "Face21",
                "Face80",
                "Face67",
                "Face65",
                "Face16",
                "Face6",
                "Face15",
                "Face10",
                "Face90",
                "Face92",
                "Face12",
            ),
            "I": ("Face3", "Face2", "Face4", "Face1"),
        },
        {
            "base": "Box",
            "A": ("Face3", "Face2", "Face4", "Face1"),
        },
        {
            "base": "Fusion002",
            "A": ("Face8",),
        },
        {
            "base": "Cut002",
            "A": ("Face24",),
            "B": ("Face12",),
            "C": ("Face5",),
        },
    ]

    sel = selections[idx]
    base = [
        (
            FreeCAD.ActiveDocument.getObject(sel["base"]),
            sel[key],
        )
    ]

    print(f"Prepared selection: ({base[0][0].Name}, {base[0][1]})")
    return base


def getBaseFromSelection(features=["Face", "Edge", "Vertex"], selIdx=0, sel="A"):
    if not FreeCAD.GuiUp:
        print("No Gui selection available.")
        return []

    selection = FreeCADGui.Selection.getSelectionEx()
    if IS_MACRO:
        if not selection:
            return preparedSelection(selIdx, sel)
    else:
        return []

    base = []
    accept = [f[:4] for f in features]
    # process user selection
    for sel in selection:
        # print(f"Object.Name: {sel.Object.Name}")
        if len(sel.SubElementNames) > 0:
            # print(f"sub element count: {len(sel.SubElementNames)}")
            feats = []
            for feat in sel.SubElementNames:
                # print(f"Processing: {sel.Object.Name}.feat}")
                if feat[:4] in accept:
                    feats.append(feat)
            if feats:
                base.append((sel.Object, tuple(feats)))
                print(f"({sel.Object.Name}, {feats})")
        else:
            # print(f"no sub element names for {sel.Object.Name}")
            pass
    return base


def testSelections():
    faceWrap = True
    processFeatures = True
    saveFeatureHoles = True
    saveMergedHoles = True
    processBase = False
    avoidOverhangs = True

    # for s in ["A", "B", "C", "D"]:
    # for s in ["C"]:
    # for s in ["A", "B", "C", "D", "E", "F", "G", "H"]:
    # for s in ["A", "B", "C"]:
    for s in ["C"]:
        objBase = getBaseFromSelection(features=["Face", "Edge"], selIdx=3, sel=s)
        cr = combineRegions(
            objBase,
            faceWrap,
            processFeatures,
            saveFeatureHoles,
            saveMergedHoles,
            processBase,
            avoidOverhangs,
        )
        print("\n")


def execute():
    faceWrap = False
    processFeatures = True
    saveFeatureHoles = True
    saveMergedHoles = True
    processBase = False
    avoidOverhangs = True

    objBase = getBaseFromSelection(features=["Face", "Edge"], sel="A")
    if objBase:
        cr = combineRegions(
            objBase,
            faceWrap,
            processFeatures,
            saveFeatureHoles,
            saveMergedHoles,
            processBase,
            avoidOverhangs,
        )


if IS_MACRO:
    testSelections()
    # execute()
