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
import freecad.camplus.utilities.Region as Region

DEBUG = False
DEBUG_SHP = False


def _debugText(txt, force=False):
    if DEBUG or force:
        print(txt)


def _debugShape(shape, name, force=False):
    obj = None
    if shape is not None and (DEBUG_SHP or force):
        if FreeCAD.ActiveDocument.getObject(name):
            FreeCAD.ActiveDocument.removeObject(name)
        obj = Part.show(shape, name)
    return obj


def vertexToPoint(v):
    return FreeCAD.Vector(v.X, v.Y, v.Z)


def _vector_to_degrees(vector):
    ang = round(math.degrees(math.atan2(vector.y, vector.x)), 6)
    if ang < 0.0:
        ang += 360.0
    return ang


def _duplicateArc(edge):
    if edge.Curve.TypeId == "Part::GeomCircle":
        ang_1 = _vector_to_degrees(
            vertexToPoint(edge.SubShapes[0]).sub(edge.Curve.Center)
        )
        ang_2 = _vector_to_degrees(
            vertexToPoint(edge.SubShapes[1]).sub(edge.Curve.Center)
        )
        return Part.makeCircle(
            edge.Curve.Radius, edge.Curve.Center, edge.Curve.Axis, ang_1, ang_2
        )
    elif edge.Curve.TypeId == "Part::GeomLine":
        return Part.makeLine(
            vertexToPoint(edge.Vertexes[0]), vertexToPoint(edge.Vertexes[1])
        )
    else:
        FreeCAD.Console.PrintError(
            f"duplicateArc() edge.Curve.TypeId not processed: {edge.Curve.TypeId}"
        )
        return None  # Part.Shape()


# Face-filtering functions
def _edgeMidpointText(e):
    eLen = e.Length / 2.0
    return f"L{round(eLen, 6)}_" + Edge._pointToText(Edge.valueAtEdgeLength(e, eLen))


def _identifyMultiples(ary):
    identified = []
    multiples = []

    for a in ary:
        if a in identified:
            if a not in multiples:
                multiples.append(a)
        else:
            identified.append(a)

    return multiples


def _makeEdgeFilterRefTups(faces):
    """_makeEdgeFilterRefTups(faces) return list of edge midpoint tups that each contain:
    - text edge midpoint values
    - face index
    - edge index
    - edge count
    """
    # print("Filters._makeEdgeFilterRefTups()")

    tups = []
    for fi in range(len(faces)):
        f = faces[fi]
        eCnt = len(f.Edges)
        for ei in range(eCnt):
            e = f.Edges[ei]
            txt = Edge._pointToText(Edge.valueAtMidpoint(e))
            tups.append((txt, fi, ei, eCnt))

    # Sort tups by xyz text, so same vertexes find each other
    tups.sort(key=lambda t: t[0])

    return tups


def _makeFaceFilterRefTups(faces, depth=None):
    """_makeFaceFilterRefTups() return list of vertex tups that each contain:
    - text vertex values
    - face index
    - vertex index
    """
    tups = []
    if depth is None:
        # Use all vertexes
        for fi in range(0, len(faces)):
            f = faces[fi]
            vCnt = len(f.Vertexes)
            for vi in range(0, vCnt):
                v = f.Vertexes[vi]
                txt = Edge._pointToText(v.Point)
                tups.append((txt, fi, vi, vCnt))
    else:
        # Restrict vertexes to those at depth
        for fi in range(0, len(faces)):
            f = faces[fi]
            vCnt = len(f.Vertexes)
            for vi in range(0, vCnt):
                v = f.Vertexes[vi]
                if PathGeom.isRoughly(v.Z, depth):
                    txt = Edge._pointToText(v.Point)
                    tups.append((txt, fi, vi, vCnt))
    # Sort tups by xyz text, so same vertexes find each other
    tups.sort(key=lambda t: t[0])
    return tups


def _TriangleFaceHasHorizLowEdge(f, zTop):
    for e in f.Edges:
        if PathGeom.isRoughly(
            e.BoundBox.ZMin, e.BoundBox.ZMax
        ) and not PathGeom.isRoughly(e.BoundBox.ZMax, zTop):
            return _edgeMidpointText(e)
    return None


def _filterOutSpecialTriangularFaces(faces):
    _debugText("_filterOutSpecialTriangularFaces()")
    comp = Part.makeCompound(faces)
    zMax = comp.BoundBox.ZMax
    keepIdxs = []
    tups = []

    for fi in range(0, len(faces)):
        f = faces[fi]
        # _debugShape(f, f"STF_{fi}_")
        if len(f.Edges) == 3:
            mpTxt = _TriangleFaceHasHorizLowEdge(f, zMax)
            if mpTxt is None:
                keepIdxs.append(fi)
                continue
            # print(f"face[{fi}] is flagged.")
            tups.append((mpTxt, fi))
        else:
            keepIdxs.append(fi)

    tupsLen = len(tups)
    # print(f"tupsLen: {tupsLen}")
    if tupsLen == 0:
        pass
    elif tupsLen == 1:
        keepIdxs.append(tups[1])
    else:
        tups.sort(key=lambda t: t[0])
        unique = [tups[0]]
        cnt = 1
        for t in tups[1:]:
            if cnt > 0 and t[0] == unique[-1][0]:
                unique.pop()
                cnt -= 1
            else:
                unique.append(t)
                cnt += 1
        for txt, fi in unique:
            keepIdxs.append(fi)

    return [faces[fi] for fi in keepIdxs]


def _filterInlay_1(inlay):
    _debugText(f"_filterInlay_1() ")
    # Filter out all faces not touching top of inlay

    keep = []
    iMax = inlay.BoundBox.ZMax
    skip = 0
    for f in inlay.Faces:
        if PathGeom.isRoughly(f.BoundBox.ZMax, iMax):
            keep.append(f.copy())
        else:
            skip += 1

    if skip == 0:
        return inlay

    return Edge.fuseShapes(keep)


def _filterInlay_2(inlay, isClosed, filterTriangular):
    _debugText("_filterInlay_2() ")
    # Filter out faces having lone vertex not touching any others

    tups = _makeFaceFilterRefTups(inlay.Faces)
    save = [tups[0]]
    remove = []
    count = 1
    for tup in tups[1:]:  # txt, fi, vi
        if save[-1][0] == tup[0]:
            save.append(tup)
            count += 1
        elif count == 1:
            remove.append(save.pop()[1])
            count = 1
            save.append(tup)
        else:
            save.append(tup)
            count = 1
    if count == 1:
        remove.append(save.pop()[1])

    remove.sort()
    # _debugText(f"remove list: {remove}")

    if isClosed:
        faces = [inlay.Faces[t[1]].copy() for t in save if t[1] not in remove]
    else:
        # Only filter out triangles with lone vertex
        faces = [
            inlay.Faces[t[1]].copy()
            for t in save
            if (t[1] not in remove) or (t[1] in remove and t[3] != 3)
        ]

    if filterTriangular:
        cleanFaces = _filterOutSpecialTriangularFaces(faces)
        return Edge.fuseShapes(cleanFaces)

    return Edge.fuseShapes(faces)


def _filterInlay_3(inlay):
    _debugText(f"_filterInlay_3() ")
    # Filter out all faces with edge touching top of inlay, but no other edges
    tups = []
    if inlay is None:
        return None

    iMax = inlay.BoundBox.ZMax
    iFaces = inlay.Faces
    fCnt = len(iFaces)
    for fi in range(0, fCnt):
        f = iFaces[fi]
        for ei in range(0, len(f.Edges)):
            e = f.Edges[ei]
            ebb = e.BoundBox
            if PathGeom.isRoughly(ebb.ZMax, iMax):
                if not PathGeom.isRoughly(ebb.ZMin, iMax):
                    txt = Edge._pointToText(Edge.valueAtEdgeLength(e, e.Length / 2.0))
                    tups.append((txt, fi))
    # if len(tups) == 0:
    #    return inlay

    tups.sort(key=lambda t: t[0])
    idxs = [tups[0][1]]
    txt = tups[0][0]
    multi = False
    for t in tups[1:]:
        if t[0] == txt:
            multi = True
        else:
            if multi:
                idxs.pop()
            idxs.append(t[1])
            txt = t[0]
            multi = False
    if multi:
        idxs.pop()
    idxs.sort(reverse=True)

    fIdxs = [True for i in range(fCnt)]
    for i in idxs:
        fIdxs[i] = False
    keep = [iFaces[i] for i in range(fCnt) if fIdxs[i]]

    return Edge.fuseShapes(keep)


def _filterInlay_4(inlay):
    _debugText(f"_filterInlay_4() ")
    # Filter out all faces that have an edge shared by three faces

    keep = []
    remove = []

    tups = _makeEdgeFilterRefTups(inlay.Faces)  # (txt, fi, ei, eCnt)
    zMax = inlay.BoundBox.ZMax * 0.999
    last = tups[0][0]
    current = [tups[0][1]]
    # print(f"tup point text: {tups[0]}")
    cnt = 1
    singles = []

    for ti in range(1, len(tups)):
        txt = tups[ti][0]
        # print(f"tup point text: {tups[ti]}")
        if txt == last:
            # if txt matches, increment, and remove if cnt > 2
            cnt += 1
            current.append(tups[ti][1])
            if cnt > 2:
                remove.extend(current)
        else:
            # reset cnt and last with new text value
            if cnt == 1:
                singles.append(tups[ti - 1][1])
            cnt = 1
            last = txt
            current = [tups[ti][1]]

    singles.sort()
    # print(f"singles: {singles}")
    plural = _identifyMultiples(singles)
    # print(f"plural: {plural}")

    # recombine faces, ignoring faces flagged as remove
    i = 0
    for f in inlay.Faces:
        if i not in remove:
            keep.append(f)
        elif i not in plural:
            keep.append(f)
        i += 1

    return Edge.fuseShapes(keep)


def filterInlay(rawInlay, isOutside, isClosed, extra=False):
    """filterInlay(rawInlay, isOutside, isClosed, extra=False)"""
    _debugText(
        f"filterInlay(rawInlay, isOutside: {isOutside}, isClosed: {isClosed}, extra: {extra})"
    )
    _debugShape(rawInlay, "PreInlayFace")

    filter_1 = _filterInlay_1(rawInlay)  # Remove faces not touching rim
    _debugShape(filter_1, "Filter_1")

    if isOutside:
        _debugText("Filter isOutside")
        f3 = _filterInlay_2(filter_1, isClosed, False)
        _debugShape(f3, "Filter_2")
        if isClosed:
            final = _filterInlay_3(f3)
            _debugShape(final, "Filter_3")
        else:
            final = f3
    else:
        _debugText("Filter inside")
        f2 = _filterInlay_2(filter_1, isClosed, True)
        _debugShape(f2, "Filter_2a")
        f4 = _filterInlay_4(f2)
        _debugShape(f4, "Filter_4a")
        if extra:
            final = _filterInlay_2(f4, isClosed, False)
            _debugShape(final, "Filter_2b")
        else:
            final = f4

    return final


# Wire-filtering functions
# Path generation functions
def uniqueEdges(edges):
    # Filter out duplicate edges
    # _debugText("uniqueEdges()")

    tups = Region.makeEdgeMidpointTups(edges)
    if len(tups) == 0:
        return tups

    # Remove duplicates
    unique = [tups[0]]
    deleted = []
    for t in tups[1:]:
        if t[0] == unique[-1][0]:
            deleted.append(t)
        else:
            unique.append(t)

    return [u[2] for u in unique]


# EDIT makeEdgeRefTups() relocated to Region.py module


def _touchesObtusePoint(e, obtusePoints):
    for v in e.Vertexes:
        vp = v.Point
        p1 = FreeCAD.Vector(vp.x, vp.y, 0.0)
        for op in obtusePoints:
            p2 = FreeCAD.Vector(op.x, op.y, 0.0)
            if p1.sub(p2).Length < 0.00001:
                return True
    return False


def faceAnalysis(f, fi, eCnt, zMin, zMax, obtusePoints):
    """faceAnalysis(f, fi, eCnt, zMin, zMax, obtusePoints)
    Return tuple of (rim, support, other, bottom, cats).
        rim, support, other, and bottom are tuples of (edge, face_index, edge_index).
        'cats' is list of edge types, represented by lowercase first letter of edge type.
        Uppercase edge type letter means entire edge is at rim height.
    """
    rim = []
    support = []
    other = []
    bottom = []
    trash = []
    cats = ""
    # flag = ""

    # _debugText(f"FaceIdx{fi}_")

    for ei in range(0, eCnt):
        e = f.Edges[ei]
        eType = e.Curve.TypeId[10]
        # _debugText(f"eType {ei}: {eType}")
        # _debugText(f"e.TypeId {ei}: {e.Curve.TypeId}")
        # _debugText(f"e.Length {ei}: {e.Length}")

        # Entire edge at rim height
        if e.Length < 0.0000001:
            trash.append((e, fi, ei))
            # _debugText("   if(0)")
        elif PathGeom.isRoughly(e.BoundBox.ZMin, zMax):
            rim.append((e, fi, ei))
            cats += eType
            # _debugText("   if(1)")
        # Entire edge at bottom height
        elif PathGeom.isRoughly(e.BoundBox.ZMax, zMin):
            bottom.append((e, fi, ei))
            cats += eType.lower()
            # _debugText("   if(2)")
        # Edge touches rim
        elif PathGeom.isRoughly(e.BoundBox.ZMax, zMax):
            if _touchesObtusePoint(e, obtusePoints):
                trash.append((e, fi, ei))
                # _debugText("   if(3a)")
            else:
                support.append((e, fi, ei))
                cats += eType.lower()
                # _debugText("   if(3b)")
        # All other edges
        else:
            other.append((e, fi, ei))
            cats += eType.lower()
            # _debugText("   if(4)")

    # if eCnt == 3:
    #    if len(bottom) == 1 and len(support) == 2:
    #        print("Found bottom-botRim-botRim face.")
    #        flag = "T"

    return rim, support, other, bottom, cats  # , flag


def commonEndPointAtRim(rim, e1, e2):
    e1p1 = e1.Vertexes[0].Point
    e1p2 = e1.Vertexes[1].Point
    e2p1 = e2.Vertexes[0].Point
    e2p2 = e2.Vertexes[1].Point
    if PathGeom.isRoughly(e1p1.z, rim):
        if PathGeom.isRoughly(e1p1.sub(e2p1).Length, 0.0):
            return True
        if PathGeom.isRoughly(e1p1.sub(e2p2).Length, 0.0):
            return True
    if PathGeom.isRoughly(e1p2.z, rim):
        if PathGeom.isRoughly(e1p2.sub(e2p1).Length, 0.0):
            return True
        if PathGeom.isRoughly(e1p2.sub(e2p2).Length, 0.0):
            return True
    return False


def removeEdges(full, ignore):
    """Remove edges in ignore list from full list"""
    eTups = Region.makeEdgeMidpointTups(full)
    rTups = Region.makeEdgeMidpointTups(ignore)
    rTxts = [t[0] for t in rTups]
    edges = []
    for t in eTups:
        if t[0] not in rTxts:
            edges.append(t[2])
    return edges


def inlayEdgesToWires_orig(inlay, edges):
    if len(edges) == 0:
        # Place 10.0 mm vertical line at lowest point of inlay.
        p = inlay.Edges[0].Vertexes[0].Point
        pMin = p.z
        for e in inlay.Edges:
            for v in e.Vertexes:
                if v.Z < pMin:
                    pMin = v.Z
                    p = v.Point
        l = Part.makeLine(p, FreeCAD.Vector(p.x, p.y, p.z + 10.0))
        return Part.Wire(l)
    else:
        try:
            wire = Part.Wire(Part.__sortEdges__(edges))
            _debugText(f"len(wire.Edges): {len(wire.Edges)}")
            _debugText(f"len(edges): {len(edges)}")
            _debugText(f"wire.isClosed(): {wire.isClosed()}")
            if len(wire.Edges) == len(edges) and wire.isClosed():
                _debugText("inlayEdgesToWires() Part.Wire() returned.")
                return wire
        except:
            _debugText("inlayEdgesToWires() Part.Wire() failed.")
            wires = []
            for g in Part.sortEdges(edges):
                _debugText("inlayEdgesToWires() Found edge group")
                wires.append(Part.Wire(g))

            return Part.makeCompound(wires)


def inlayEdgesToWires(inlay, edges):
    if len(edges) == 0:
        # Place 10.0 mm vertical line at lowest point of inlay.
        p = inlay.Edges[0].Vertexes[0].Point
        pMin = p.z
        for e in inlay.Edges:
            for v in e.Vertexes:
                if v.Z < pMin:
                    pMin = v.Z
                    p = v.Point
        l = Part.makeLine(p, FreeCAD.Vector(p.x, p.y, p.z + 10.0))
        return Part.Wire(l)
    else:
        _debugText("inlayEdgesToWires() Part.Wire() failed.")
        wires = []
        for g in Part.sortEdges(edges):
            _debugText("inlayEdgesToWires() Found edge group")
            wires.append(Part.Wire(g))

        return Part.makeCompound(wires)


def inlayBottomEdgesToWires(inlay, edges):
    if len(edges) == 0:
        # Place 10.0 mm vertical line at lowest point of inlay.
        p = inlay.Edges[0].Vertexes[0].Point
        pMin = p.z
        for e in inlay.Edges:
            for v in e.Vertexes:
                if v.Z < pMin:
                    pMin = v.Z
                    p = v.Point
        l = Part.makeLine(p, FreeCAD.Vector(p.x, p.y, p.z + 10.0))
        return Part.Wire(l)
    else:
        cleanEdges = [_duplicateArc(e) for e in edges]
        return inlayEdgesToWires(inlay, cleanEdges)


def identifyInsideInlayPathWires(inlay, wireType, obtusePoints):
    """identifyInsideInlayPathWires(inlay, wireType, obtusePoints)  Working version, but incomplete"""
    _debugText("identifyInsideInlayPathWires()")

    zMax = inlay.BoundBox.ZMax
    zMin = inlay.BoundBox.ZMin

    rim = []
    support = []
    other = []
    bottom = []
    remove = []
    keep = []
    avoid = []

    # sort edges into appropriate groups
    for fi in range(0, len(inlay.Faces)):
        f = inlay.Faces[fi]
        # _debugShape(f, f"FaceIdx{fi}_")
        eCnt = len(f.Edges)
        _debugText(f"FaceIdx{fi} eCnt: {eCnt}")
        r, s, o, b, cats = faceAnalysis(f, fi, eCnt, zMin, zMax, obtusePoints)
        # rim, support, other, and bottom & cats string
        _debugText(
            f"FaceIdx{fi} faceAnalysis(r, s, o, b, cats): {len(r)}, {len(s)}, {len(o)}, {len(b)}, {cats}"
        )
        rim.extend(r)
        bottom.extend(b)
        # show(f, f"Face_{fi}_", True)
        # _debugText(f"cats {fi}: {cats}")

        if eCnt == 3:
            # _debugText("___ 3 edges")
            if "L" in cats:
                # _debugText("  _ L rim")
                # line edge at rim, use supports
                keep.extend(s)
            elif "c" in cats:
                # _debugText("  _ c bottom")
                remove.extend(s)
            else:
                # _debugText("  _ else")
                support.extend(s)
            other.extend(o)
        else:
            _debugText("___ Multi edges")
            if "C" in cats and "c" in cats:
                _debugText(" __ C and c:  attempt arcs at rim and bottom")
                # Arcs (circle edges) at rim and bottom
                ri = cats.index("C")  # rim index
                bi = cats.index("c")  # bottom index
                re = f.Edges[ri]  # rim edge length
                if re.Length > 0.00001:
                    _debugText(f"  _ rim circle has length, {re.Length} mm")
                    be = f.Edges[bi]
                    if (
                        hasattr(be.Curve, "Radius")
                        and re.Curve.Radius > be.Curve.Radius
                    ):
                        for sTup in s:
                            _debugText(
                                f"   sTup[0].Curve.TypeId: {sTup[0].Curve.TypeId}"
                            )
                            if sTup[0].Curve.TypeId[10] == "P":
                                avoid.append(sTup)
                                _debugText(f"   avoid")
                            else:
                                remove.append(sTup)
                                _debugText(f"   remove")
                    else:
                        # _debugText("  _ support edges")
                        support.extend(s)  # keep.extend(s)
                elif len(s) > 0 and commonEndPointAtRim(zMax, s[0][0], s[1][0]):
                    # _debugText("  _ remove - common point")
                    remove.extend(s)
                else:
                    # _debugText("  _ support - NOT common point")
                    support.extend(s)
            elif len(s) == 2:
                # _debugText(" __ 2 supports")
                if commonEndPointAtRim(zMax, s[0][0], s[1][0]):
                    # _debugText("  _ remove - common point")
                    remove.extend(s)
                else:
                    # _debugText("  _ support - NOT common point")
                    support.extend(s)
            else:
                # _debugText(" __ else")
                if "C" in cats:
                    # line edge at rim, use supports
                    support.extend(s)
                else:
                    support.extend(s)
            other.extend(o)

    r = uniqueEdges([t[0] for t in rim])
    b = uniqueEdges([t[0] for t in bottom])
    o = uniqueEdges([t[0] for t in other])
    d = uniqueEdges([t[0] for t in remove])
    k = uniqueEdges([t[0] for t in keep])
    sRaw = uniqueEdges([t[0] for t in support])
    s = removeEdges(sRaw, d)

    _debugText(
        f"identifyInsideInlayPathWires() r: {len(r)}, b: {len(b)}, o: {len(o)}, d: {len(d)}, k: {len(k)}, s: {len(s)}"
    )

    _debugText(f"identifyInsideInlayPathWires() wireTye: {wireType}")
    if wireType == "Inlay":
        # show(Part.makeCompound(d), "RemoveEdges", True)
        chains = Part.sortEdges(o + b + k + s)
        return Part.makeCompound([Part.Wire(g) for g in chains])
    elif wireType == "Midline":
        return inlayEdgesToWires(inlay, b + o)
    elif wireType == "Bottom":
        _debugShape(Part.makeCompound(b), "BottomEdges")
        # for ed in b:
        #    Part.show(ed, "BottomEdge")
        return inlayBottomEdgesToWires(inlay, b)
    elif wireType == "Top":
        return inlayEdgesToWires(inlay, r)

    return None


def identifyOutsideInlayPathWires(inlay, wireType, obtusePoints):
    """identifyOutsideInlayPathWires(inlay, wireType="Inlay")  Working version, but incomplete"""
    _debugText("identifyOutsideInlayPathWires()")

    zMax = inlay.BoundBox.ZMax
    zMin = inlay.BoundBox.ZMin

    rim = []
    support = []
    other = []
    bottom = []
    remove = []
    keep = []
    avoid = []

    # sort edges into appropriate groups: rim, support, other, bottom
    for fi in range(0, len(inlay.Faces)):
        f = inlay.Faces[fi]
        eCnt = len(f.Edges)
        r, s, o, b, cats = faceAnalysis(f, fi, eCnt, zMin, zMax, obtusePoints)
        rim.extend(r)
        bottom.extend(b)
        # show(f, f"Face_{fi}_", True)
        # _debugText(f"cats {fi}: {cats}")

        if eCnt == 3:
            # _debugText("___ 3 edges")
            if "L" in cats:
                # _debugText("  _ L rim")
                # line edge at rim, use supports
                keep.extend(s)
            elif "c" in cats:
                # _debugText("  _ c bottom")
                remove.extend(s)
            else:
                # _debugText("  _ else")
                support.extend(s)
            other.extend(o)
        else:
            # _debugText("___ Multi edges")
            if "C" in cats and "c" in cats:
                # _debugText(" __ C and c")
                # circle edge at rim and bottom
                ri = cats.index("C")  # rim index
                bi = cats.index("c")  # bottom index
                re = f.Edges[ri]  # rim edge length
                if re.Length > 0.00001:
                    # _debugText(f"  _ rim circle has length, {re.Length} mm")
                    be = f.Edges[bi]
                    if re.Curve.Radius > be.Curve.Radius:
                        for sTup in s:
                            if sTup[0].Curve.TypeId[10] == "P":
                                avoid.append(sTup)
                            else:
                                remove.append(sTup)
                    else:
                        # _debugText("  _ support edges")
                        support.extend(s)  # keep.extend(s)
                elif commonEndPointAtRim(zMax, s[0][0], s[1][0]):
                    # _debugText("  _ remove - common point")
                    remove.extend(s)
                else:
                    # _debugText("  _ support - NOT common point")
                    support.extend(s)
            elif len(s) == 2:
                # _debugText(" __ 2 supports")
                if commonEndPointAtRim(zMax, s[0][0], s[1][0]):
                    # _debugText("  _ remove - common point")
                    remove.extend(s)
                else:
                    # _debugText("  _ support - NOT common point")
                    support.extend(s)
            else:
                # _debugText(" __ else")
                if "C" in cats:
                    # line edge at rim, use supports
                    support.extend(s)
                else:
                    support.extend(s)
            other.extend(o)

    r = uniqueEdges([t[0] for t in rim])
    b = uniqueEdges([t[0] for t in bottom])
    o = uniqueEdges([t[0] for t in other])
    d = uniqueEdges([t[0] for t in remove])
    k = uniqueEdges([t[0] for t in keep])
    sRaw = uniqueEdges([t[0] for t in support])
    s = removeEdges(sRaw, d)

    # remove line segments from supports
    rmvIdxs = [i for i in range(len(s)) if s[i].Curve.TypeId == "Part::GeomLine"]
    rmvIdxs.sort(reverse=True)
    for ri in rmvIdxs:
        s.pop(ri)

    if wireType == "Inlay":
        # show(Part.makeCompound(d), "RemoveEdges", True)
        chains = Part.sortEdges(o + b + k + s)
        return Part.makeCompound([Part.Wire(g) for g in chains])
    elif wireType == "Midline":
        return inlayEdgesToWires(inlay, b + o)
    elif wireType == "Bottom":
        return inlayEdgesToWires(inlay, b)
    elif wireType == "Top":
        return inlayEdgesToWires(inlay, r)

    return None
