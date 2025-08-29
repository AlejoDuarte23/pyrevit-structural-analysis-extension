try:
    from Autodesk.Revit.DB import (
        BuiltInParameter, UnitUtils, UnitTypeId, Element
    )
except Exception:  # allow outside Revit
    BuiltInParameter = UnitUtils = UnitTypeId = Element = object

from .utils import eid_to_int, eid_positive
from .models import SectionInfo, SectionProperties, MaterialInfo, MaterialRef


def safe_param_double(elem, bip, unit_id=None):
    try:
        p = elem.get_Parameter(bip)
        if p and p.HasValue:
            val = p.AsDouble()
            if unit_id is not None:
                try:
                    return UnitUtils.ConvertFromInternalUnits(val, unit_id)
                except Exception:
                    return val
            return val
    except Exception:
        return None
    return None


def safe_param_str(elem, bip):
    try:
        p = elem.get_Parameter(bip)
        if p and p.HasValue:
            return p.AsString()
    except Exception:
        return None
    return None


_SECTION_NUMERIC_PARAMS = [
    (BuiltInParameter.STRUCTURAL_SECTION_AREA, UnitTypeId.SquareMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_WIDTH, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_HEIGHT, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_DIAMETER, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_PERIMETER, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_PLASTIC_MODULUS_STRONG_AXIS, UnitTypeId.CubicMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_PLASTIC_MODULUS_WEAK_AXIS, UnitTypeId.CubicMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_SHEAR_AREA_STRONG_AXIS, UnitTypeId.SquareMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_SHEAR_AREA_WEAK_AXIS, UnitTypeId.SquareMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_TORSIONAL_MODULUS, UnitTypeId.CubicMeters),
    (BuiltInParameter.STRUCTURAL_SECTION_ISHAPE_WEBHEIGHT, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_ISHAPE_WEBTHICKNESS, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_FLANGE_THICKNESS, UnitTypeId.Meters) if hasattr(BuiltInParameter, "STRUCTURAL_SECTION_FLANGE_THICKNESS") else None,
    (BuiltInParameter.STRUCTURAL_SECTION_IWELDED_TOPFLANGEWIDTH, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_IWELDED_TOPFLANGETHICKNESS, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_IWELDED_BOTTOMFLANGEWIDTH, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_IWELDED_BOTTOMFLANGETHICKNESS, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_HSS_OUTERFILLET, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_HSS_INNERFILLET, UnitTypeId.Meters),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_MOMENT_OF_INERTIA_STRONG_AXIS, UnitTypeId.MetersToTheFourthPower),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_MOMENT_OF_INERTIA_WEAK_AXIS, UnitTypeId.MetersToTheFourthPower),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_TORSIONAL_MOMENT_OF_INERTIA, UnitTypeId.MetersToTheFourthPower),
    (BuiltInParameter.STRUCTURAL_SECTION_COMMON_WARPING_CONSTANT, UnitTypeId.MetersToTheSixthPower),
]
_SECTION_NUMERIC_PARAMS = [t for t in _SECTION_NUMERIC_PARAMS if t is not None]


def section_info_from_symbol(symbol, shape_str):
    if symbol is None:
        return None, None
    from Autodesk.Revit.DB import BuiltInParameter  # local import to avoid polluting namespace
    tname = (safe_param_str(symbol, BuiltInParameter.SYMBOL_NAME_PARAM)
             or getattr(symbol, "Name", None)
             or safe_param_str(symbol, BuiltInParameter.ALL_MODEL_TYPE_NAME))
    fam_name = safe_param_str(symbol, BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    type_info = SectionInfo(type_id=eid_to_int(symbol.Id), type_name=tname, family_name=fam_name, shape=shape_str)
    props = {}
    for bip, unit_id in _SECTION_NUMERIC_PARAMS:
        try:
            val = safe_param_double(symbol, bip, unit_id)
            if val is not None:
                props[str(bip)] = val
        except Exception:
            continue
    return type_info, (SectionProperties(values=props) if props else None)


def section_info_for_member(doc, member, pi, pj, log_file=None):
    te = None
    try:
        tid = member.SectionTypeId if hasattr(member, "SectionTypeId") else None
        if eid_positive(tid):
            te = doc.GetElement(tid)
    except Exception:
        te = None
    shape = None
    try:
        shape = str(getattr(member, "StructuralSectionShape"))
    except Exception:
        shape = None
    if te is not None:
        ti, props = section_info_from_symbol(te, shape)
        return ti, (props.values if props else None), None
    return SectionInfo(type_id=None, type_name=None, family_name=None, shape=shape), None, None


def material_info(doc, analytical_member, host_elem=None):
    # try analytical first
    try:
        if hasattr(analytical_member, "MaterialId"):
            mid = getattr(analytical_member, "MaterialId")
            if eid_positive(mid):
                me = doc.GetElement(mid)
                if me:
                    ref = MaterialRef(id=eid_to_int(me.Id), name=getattr(me, "Name", None))
                    return MaterialInfo(primary=ref, all=[ref])
    except Exception:
        pass

    try:
        mat_id = None
        if host_elem is not None:
            p = host_elem.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM)
            if p and p.HasValue:
                mat_id = p.AsElementId()
            if (mat_id is None) or (not eid_positive(mat_id)):
                sym = doc.GetElement(host_elem.GetTypeId())
                if sym:
                    pt = sym.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM)
                    if pt and pt.HasValue:
                        mat_id = pt.AsElementId()
        if eid_positive(mat_id):
            me = doc.GetElement(mat_id)
            if me:
                ref = MaterialRef(id=eid_to_int(me.Id), name=getattr(me, "Name", None))
                return MaterialInfo(primary=ref, all=[ref])
        if host_elem is not None:
            ids = host_elem.GetMaterialIds(False) or host_elem.GetMaterialIds(True)
            if ids:
                mats = [doc.GetElement(i) for i in ids]
                mats = [m for m in mats if m]
                refs = [MaterialRef(id=eid_to_int(m.Id), name=getattr(m, "Name", None)) for m in mats]
                if refs:
                    return MaterialInfo(primary=refs[0], all=refs)
    except Exception:
        pass
    return None


__all__ = [
    "safe_param_double", "safe_param_str", "section_info_from_symbol", "section_info_for_member", "material_info"
]
