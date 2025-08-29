import math
try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, BuiltInCategory, Curve, XYZ, Element
    )
except Exception:  # allow outside Revit
    FilteredElementCollector = BuiltInCategory = Curve = XYZ = Element = object

from .utils import meters_to_internal, HOST_MATCH_TOL_METERS, log_msg


def angle_between(v1, v2):
    """Angle between XYZ dirs (rad)."""
    try:
        dot = v1.Normalize().DotProduct(v2.Normalize())
        dot = max(min(dot, 1.0), -1.0)
        return math.acos(dot)
    except Exception:
        return math.pi


def find_physical_host_for_member(doc, pi, pj, log_file=None):
    """Heuristic host match (angle<=10deg, mid<=3x tol, score<=6x tol)."""
    if pi is None or pj is None:
        return None
    tol_ft = meters_to_internal(HOST_MATCH_TOL_METERS)
    line_vec = pj - pi
    mid = XYZ((pi.X + pj.X) * 0.5, (pi.Y + pj.Y) * 0.5, (pi.Z + pj.Z) * 0.5)
    candidates = []
    try:
        frames = (
            FilteredElementCollector(doc)
            .OfCategory(BuiltInCategory.OST_StructuralFraming)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        cols = (
            FilteredElementCollector(doc)
            .OfCategory(BuiltInCategory.OST_StructuralColumns)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        candidates = list(frames) + list(cols)
    except Exception:
        candidates = []
    best = None
    best_score = None
    for inst in candidates:
        try:
            loc = getattr(inst, "Location", None)
            if loc is None or not hasattr(loc, "Curve"):
                continue
            crv = loc.Curve
            if not isinstance(crv, Curve):
                continue
            a = crv.GetEndPoint(0)
            b = crv.GetEndPoint(1)
            ph_vec = b - a
            ang = angle_between(line_vec, ph_vec)
            if ang > math.radians(10.0):
                continue
            ph_mid = XYZ((a.X + b.X) * 0.5, (a.Y + b.Y) * 0.5, (a.Z + b.Z) * 0.5)
            mid_dist = mid.DistanceTo(ph_mid)
            if mid_dist > tol_ft * 3.0:
                continue
            score = min(
                pi.DistanceTo(a) + pj.DistanceTo(b),
                pi.DistanceTo(b) + pj.DistanceTo(a),
            )
            if best is None or score < (best_score if best_score is not None else float("inf")):
                best = inst
                best_score = score
        except Exception:
            continue
    if best is not None and best_score is not None and best_score <= tol_ft * 6.0:
        return best
    if log_file:
        log_msg("No physical host matched within tolerance", log_file)
    return None

__all__ = ["find_physical_host_for_member"]
