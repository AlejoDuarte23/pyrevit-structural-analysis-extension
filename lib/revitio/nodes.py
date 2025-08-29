try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, BuiltInCategory, XYZ
    )
except Exception:  # allow outside Revit
    FilteredElementCollector = BuiltInCategory = XYZ = object

from .utils import xyz_to_out, eid_to_int, log_msg, UNIT_OUT
from .models import Node


def get_node_position(elem):
    try:
        cs = elem.GetCoordinateSystem()
        if cs:
            return cs.Origin
    except Exception:
        pass
    try:
        loc = elem.Location
        if loc and hasattr(loc, "Point") and isinstance(loc.Point, XYZ):
            return loc.Point
    except Exception:
        pass
    try:
        bbox = elem.get_BoundingBox(None)
        if bbox:
            cx = 0.5 * (bbox.Min.X + bbox.Max.X)
            cy = 0.5 * (bbox.Min.Y + bbox.Max.Y)
            cz = 0.5 * (bbox.Min.Z + bbox.Max.Z)
            return XYZ(cx, cy, cz)
    except Exception:
        pass
    return None


def collect_nodes(doc, log_file):
    """Collect nodes. Return (map, list, total, missing)."""
    nodes = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_AnalyticalNodes)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    nodes_map = {}
    out = []
    missing = 0
    for n in nodes:
        nid = eid_to_int(n.Id)
        pos = get_node_position(n)
        if pos is None:
            missing += 1
            log_msg(
                "Node {} missing position".format(nid if nid is not None else n.UniqueId),
                log_file,
            )
            continue
        if nid is not None:
            nodes_map[nid] = pos
        out.append(
            Node(
                id=nid,
                unique_id=n.UniqueId,
                position=xyz_to_out(pos),
                units=UNIT_OUT.lower(),
            )
        )
    return nodes_map, out, len(nodes), missing


def squared_dist(a, b):
    dx = a.X - b.X
    dy = a.Y - b.Y
    dz = a.Z - b.Z
    return dx*dx + dy*dy + dz*dz


def find_closest_node_id(pt, nodes_map, tol_ft):
    """Closest node id within tol."""
    best_id = None
    best_d2 = tol_ft * tol_ft
    for nid, npt in nodes_map.items():
        d2 = squared_dist(pt, npt)
        if d2 <= best_d2:
            best_id = nid
            best_d2 = d2
    return best_id


__all__ = ["collect_nodes", "find_closest_node_id"]
