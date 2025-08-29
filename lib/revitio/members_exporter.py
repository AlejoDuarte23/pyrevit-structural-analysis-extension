import json
import datetime

from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.DB.Structure import AnalyticalMember

from .utils import (
    ensure_output_dir as ensureOutputDirectory,
    log_msg as logMessage,
    meters_to_internal as metersToInternal,
    UNIT_OUT,
    SNAP_TOLERANCE_METERS,
    model_name as modelName,
    eid_to_int as elementIdToInt,
    xyz_to_out as xyzToOut,
)
from .nodes import (
    collect_nodes as collectNodes,
    find_closest_node_id as findClosestNodeId,
)
from .sections_materials import (
    section_info_for_member as sectionInfoForMember,
    material_info as materialInfo,
)
from .member_geometry import (
    get_member_endpoints as getMemberEndpoints,
    get_local_axes as getLocalAxes,
)
from .host_match import find_physical_host_for_member as findPhysicalHostForMember
from .releases import read_releases as readReleases
from .models import (
    LineGeom, SectionProperties, MemberRecord, ExportCounts, ExportResult
)



class ExportAnalyticalModel(object):

    def __init__(self, doc, output_dir=None):
        self.doc = doc
        # Delegate output directory resolution/creation to utils helper
        self.outputDirectory = ensureOutputDirectory(output_dir)
        self.logFile = self.outputDirectory + "/export_members.log"
        logMessage("Initialized ExportAnalyticalModel", self.logFile)

    def collectNodes(self):
        """Collect nodes (map,list,total)."""
        node_map, node_objects, total_node_count, missing = collectNodes(self.doc, self.logFile)
        logMessage(
            "Members pass sees {} nodes ({} missing positions)".format(total_node_count, missing),
            self.logFile,
        )
        return node_map, node_objects, total_node_count

    def iterateAnalyticalMembers(self):
        members = (
            FilteredElementCollector(self.doc)
            .OfClass(AnalyticalMember)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        logMessage("Found {} AnalyticalMember elements".format(len(members)), self.logFile)
        return members

    def buildMemberRecord(self, memberElement, nodeMap, snapToleranceFeet):
        memberIdInt = elementIdToInt(memberElement.Id)
        startPoint, endPoint = getMemberEndpoints(memberElement, self.logFile)

        # If geometry is missing, return minimal record
        if startPoint is None or endPoint is None:
            return MemberRecord(
                id=memberIdInt,
                unique_id=memberElement.UniqueId,
                node_i=None,
                node_j=None,
                line=None,
                units=UNIT_OUT.lower(),
                status="no_curve",
                material=None,
                section=None,
                section_properties=None,
                releases=None,
                local_axes=None,
                structural_role=None,
                cross_section_rotation_rad=None,
                host_id=None,
                host_unique_id=None,
            )

        # Node association
        nodeIdStart = findClosestNodeId(startPoint, nodeMap, snapToleranceFeet)
        nodeIdEnd = findClosestNodeId(endPoint, nodeMap, snapToleranceFeet)

        # Section / type info
        sectionInfo, sectionProps, _ = sectionInfoForMember(self.doc, memberElement, startPoint, endPoint, self.logFile)

        # 1. Try direct API association (preferred & reliable if available)
        hostElement = None
        _direct_host = False
        try:
            if hasattr(memberElement, 'GetElementId'):
                pid = memberElement.GetElementId()
                if pid and getattr(pid, 'IntegerValue', 0) > 0:
                    he = self.doc.GetElement(pid)
                    if he is not None:
                        hostElement = he
                        _direct_host = True
        except Exception:
            hostElement = None

        # 2. Fallback: heuristic spatial match if direct association not found
        if hostElement is None:
            hostElement = findPhysicalHostForMember(self.doc, startPoint, endPoint, self.logFile)
            _heuristic_host = hostElement is not None
        else:
            _heuristic_host = False

        materialData = materialInfo(self.doc, memberElement, hostElement)
        releaseData = readReleases(memberElement)
        localAxes = getLocalAxes(memberElement)
        lineGeometry = LineGeom(point_i=xyzToOut(startPoint), point_j=xyzToOut(endPoint), units=UNIT_OUT.lower())
        status = (
            "ok" if (nodeIdStart is not None and nodeIdEnd is not None)
            else ("no_node_i" if nodeIdStart is None else "no_node_j")
        )
        host_id = elementIdToInt(hostElement.Id) if hostElement else None
        host_unique_id = hostElement.UniqueId if hostElement else None

        try:
            print("[AnalyticalExport] member_id={0} unique_id={1} direct_host={2} heuristic_host={3} host_id={4} host_unique_id={5}".format(
                memberIdInt, memberElement.UniqueId, _direct_host, _heuristic_host, host_id, host_unique_id
            ))
        except Exception:
            pass

        return MemberRecord(
            id=memberIdInt,
            unique_id=memberElement.UniqueId,
            node_i=nodeIdStart,
            node_j=nodeIdEnd,
            line=lineGeometry,
            units=UNIT_OUT.lower(),
            status=status,
            material=materialData,
            section=sectionInfo,
            section_properties=SectionProperties(values=sectionProps) if sectionProps else None,
            releases=releaseData,
            local_axes=localAxes,
            structural_role=str(getattr(memberElement, "StructuralRole", None)) if hasattr(memberElement, "StructuralRole") else None,
            cross_section_rotation_rad=float(getattr(memberElement, "CrossSectionRotation", 0.0)) if hasattr(memberElement, "CrossSectionRotation") else None,
            host_id=host_id,
            host_unique_id=host_unique_id,
        )

    def writeOutput(self, result):
        fileName = "members_{model}_{ts}.json".format(
            model=modelName(self.doc),
            ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        )
        filePath = self.outputDirectory + "/" + fileName
        with open(filePath, "w") as fp:
            json.dump(result.to_dict(), fp, indent=2)
        logMessage(
            "Members metadata export complete, JSON saved to: {}".format(filePath),
            self.logFile,
        )
        return filePath

    def export(self):
        logMessage("Starting analytical members metadata export", self.logFile)
        nodeMap, nodeObjects, totalNodeCount = self.collectNodes()
        snapToleranceFeet = metersToInternal(SNAP_TOLERANCE_METERS)
        memberRecords = []
        for memberElement in self.iterateAnalyticalMembers():
            memberRecords.append(self.buildMemberRecord(memberElement, nodeMap, snapToleranceFeet))
        result = ExportResult(
            model=modelName(self.doc),
            exported_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            units=UNIT_OUT.lower(),
            snap_tolerance_m=SNAP_TOLERANCE_METERS,
            counts=ExportCounts(members_total=len(memberRecords), nodes_seen=totalNodeCount),
            analytical_nodes=nodeObjects,
            analytical_members=memberRecords,
        )
        self.writeOutput(result)
        return result


def export_members_with_metadata(doc, output_dir=None):
    """Legacy helper returns ExportResult."""
    return ExportAnalyticalModel(doc, output_dir=output_dir).export()


__all__ = ["ExportAnalyticalModel", "export_members_with_metadata"]
