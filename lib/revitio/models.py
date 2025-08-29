"""Model classes (no dataclasses for old Python)."""


class Node(object):
    def __init__(self, id, unique_id, position, units="meters", status=None):
        self.id = id
        self.unique_id = unique_id
        self.position = list(position) if position is not None else [0.0, 0.0, 0.0]
        self.units = units
        self.status = status
        if len(self.position) != 3:
            raise ValueError("Node.position must have exactly 3 numbers")

    def to_dict(self):
        d = {
            "id": self.id,
            "unique_id": self.unique_id,
            "position": self.position,
            "units": self.units,
        }
        if self.status:
            d["status"] = self.status
        return d


class LineGeom(object):
    def __init__(self, point_i, point_j, units="meters"):
        self.point_i = list(point_i)
        self.point_j = list(point_j)
        self.units = units
        if len(self.point_i) != 3 or len(self.point_j) != 3:
            raise ValueError("LineGeom points must have length 3")

    def to_dict(self):
        return {"i": self.point_i, "j": self.point_j}


class SectionInfo(object):
    def __init__(self, type_id, type_name, family_name, shape):
        self.type_id = type_id
        self.type_name = type_name
        self.family_name = family_name
        self.shape = shape

    def to_dict(self):
        return {
            "type_id": self.type_id,
            "type_name": self.type_name,
            "family_name": self.family_name,
            "shape": self.shape,
        }


class SectionProperties(object):
    def __init__(self, values=None):
        self.values = values or {}

    def to_dict(self):
        return dict(self.values)


class MaterialRef(object):
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class MaterialInfo(object):
    def __init__(self, primary, all_list=None):
        self.primary = primary
        self.all = list(all_list) if all_list else []

    def to_dict(self):
        if self.primary is None and not self.all:
            return None
        return {
            "primary": self.primary.to_dict() if self.primary else None,
            "all": [m.to_dict() for m in self.all],
        }


class ReleaseCondition(object):
    def __init__(self, fx, fy, fz, mx, my, mz):
        self.fx = bool(fx)
        self.fy = bool(fy)
        self.fz = bool(fz)
        self.mx = bool(mx)
        self.my = bool(my)
        self.mz = bool(mz)

    def to_dict(self):
        return {"fx": self.fx, "fy": self.fy, "fz": self.fz, "mx": self.mx, "my": self.my, "mz": self.mz}


class Releases(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def to_dict(self):
        if self.start is None and self.end is None:
            return None
        return {
            "start": self.start.to_dict() if self.start else None,
            "end": self.end.to_dict() if self.end else None,
        }


class LocalAxes(object):
    def __init__(self, x, y, z):
        self.x = list(x)
        self.y = list(y)
        self.z = list(z)
        for name, vec in (("x", self.x), ("y", self.y), ("z", self.z)):
            if len(vec) != 3:
                raise ValueError("Local axis %s must have length 3" % name)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "z": self.z}


class MemberRecord(object):
    def __init__(self, id, unique_id, node_i, node_j, line, units, status, material,
                 section, section_properties, releases=None, local_axes=None,
                 structural_role=None, cross_section_rotation_rad=None,
                 host_id=None, host_unique_id=None):
        # Core analytical member identifiers
        self.id = id
        self.unique_id = unique_id
        # Analytical connectivity
        self.node_i = node_i
        self.node_j = node_j
        # Geometry & units
        self.line = line
        self.units = units
        # Metadata / classification
        self.status = status
        self.material = material
        self.section = section
        self.section_properties = section_properties
        self.releases = releases
        self.local_axes = local_axes
        self.structural_role = structural_role
        self.cross_section_rotation_rad = cross_section_rotation_rad
        # Physical host element (if analytical member is not directly tied to a type)
        self.host_id = host_id
        self.host_unique_id = host_unique_id

    def to_dict(self):
        d = {
            "id": self.id,
            "unique_id": self.unique_id,
            "nodeI": self.node_i,
            "nodeJ": self.node_j,
            "units": self.units,
            "status": self.status,
            "material": self.material.to_dict() if self.material else None,
            "section": self.section.to_dict() if self.section else None,
            "section_properties": self.section_properties.to_dict() if self.section_properties else None,
            "releases": self.releases.to_dict() if self.releases else None,
            "local_axes": self.local_axes.to_dict() if self.local_axes else None,
            "structural_role": self.structural_role,
            "cross_section_rotation_rad": self.cross_section_rotation_rad,
        }
        # Only include host identifiers if we actually resolved a host element
        if self.host_id is not None:
            d["host_id"] = self.host_id
        else:
            d["host_id"] = None
        if self.host_unique_id is not None:
            d["host_unique_id"] = self.host_unique_id
        else:
            d["host_unique_id"] = None
        if self.line:
            d["endpoints"] = self.line.to_dict()
        return d


class ExportCounts(object):
    def __init__(self, members_total, nodes_seen):
        self.members_total = members_total
        self.nodes_seen = nodes_seen

    def to_dict(self):
        return {"members_total": self.members_total, "nodes_seen": self.nodes_seen}


class ExportResult(object):
    def __init__(self, model, exported_at, units, snap_tolerance_m, counts,
                 analytical_nodes, analytical_members):
        self.model = model
        self.exported_at = exported_at
        self.units = units
        self.snap_tolerance_m = snap_tolerance_m
        self.counts = counts
        self.analytical_nodes = analytical_nodes
        self.analytical_members = analytical_members

    def to_dict(self):
        return {
            "model": self.model,
            "exported_at": self.exported_at,
            "units": self.units,
            "snap_tolerance_m": self.snap_tolerance_m,
            "counts": self.counts.to_dict(),
            "analytical_nodes": [n.to_dict() for n in self.analytical_nodes],
            "analytical_members": [m.to_dict() for m in self.analytical_members],
        }


__all__ = [
    "Node", "LineGeom", "SectionInfo", "SectionProperties", "MaterialRef", "MaterialInfo",
    "ReleaseCondition", "Releases", "LocalAxes", "MemberRecord",
    "ExportCounts", "ExportResult"
]
