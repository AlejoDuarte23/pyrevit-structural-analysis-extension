try:
    from Autodesk.Revit.DB import Options, Curve, Transform, XYZ
    from Autodesk.Revit.DB.Structure import AnalyticalElement
except Exception:  # allow outside Revit
    Options = Curve = Transform = XYZ = AnalyticalElement = object

from .models import LocalAxes
from .utils import log_msg, eid_to_int


def get_member_endpoints(member, log_file):
    """Return (start,end) XYZ. Try single curve then longest."""
    try:
        if isinstance(member, AnalyticalElement) and hasattr(member, 'IsSingleCurve') and member.IsSingleCurve():
            c = member.GetCurve()
            if isinstance(c, Curve):
                return c.GetEndPoint(0), c.GetEndPoint(1)
    except Exception as ex:
        try:
            mid = eid_to_int(member.Id)
        except Exception:
            mid = None
        log_msg("GetCurve failed on member {}: {}".format(mid, ex), log_file)

    # Fallback: choose longest curve in geometry
    try:
        opts = Options()
        geo = member.get_Geometry(opts)
        longest = None
        maxlen = -1.0
        if geo:
            for g in geo:
                try:
                    if isinstance(g, Curve):
                        length = g.Length
                        if length > maxlen:
                            longest = g
                            maxlen = length
                except Exception:
                    continue
        if longest is not None:
            return longest.GetEndPoint(0), longest.GetEndPoint(1)
    except Exception as ex:
        try:
            mid = eid_to_int(member.Id)
        except Exception:
            mid = None
        log_msg("Geometry fallback failed on member {}: {}".format(mid, ex), log_file)
    return None, None


def get_local_axes(member):
    """Local axes from transform."""
    try:
        t = member.GetTransform()
        if isinstance(t, Transform):
            return LocalAxes(
                x=[t.BasisX.X, t.BasisX.Y, t.BasisX.Z],
                y=[t.BasisY.X, t.BasisY.Y, t.BasisY.Z],
                z=[t.BasisZ.X, t.BasisZ.Y, t.BasisZ.Z],
            )
    except Exception:
        return None
    return None

__all__ = ["get_member_endpoints", "get_local_axes"]
