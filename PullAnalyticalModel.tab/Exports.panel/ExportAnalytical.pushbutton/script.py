#! python3

import os
import sys

# Add lib to path
try:
    _this = os.path.dirname(__file__)
    _root = _this
    # ascend to root
    for _i in range(3):
        _root = os.path.dirname(_root)
    _lib = os.path.join(_root, 'lib')
    if os.path.isdir(_lib) and _lib not in sys.path:
        sys.path.insert(0, _lib)
except Exception:
    pass

try:
    from revitio.members_exporter import ExportAnalyticalModel
    from revitio.models import ExportResult
except Exception as _imp_err:
    print("Warning: failed to import revitio package ({}). Exporter disabled.".format(_imp_err))
    ExportAnalyticalModel = None
    ExportResult = None

try:  # optional, ignore outside Revit
    from Autodesk.Revit.DB import Document
except Exception:
    Document = None

try:  # get doc
    doc = __revit__.ActiveUIDocument.Document
except Exception:
    doc = None  # no doc

_export_dir = os.environ.get("REVIT_ANALYTICAL_OUT")  # optional override

# CLI model open
if doc is None:
    try:
        from pyrevit import HOST_APP  # only available inside pyRevit
    # __models__ injected
        if '__models__' in globals() and __models__:
            _model_path = __models__[0]
            _uidoc = HOST_APP.uiapp.OpenAndActivateDocument(_model_path)
            doc = _uidoc.Document
            print("Opened model: {0}".format(_model_path))
    except Exception as _open_ex:
    # ignore
        pass

if _export_dir:
    print("Using export directory from REVIT_ANALYTICAL_OUT: {0}".format(_export_dir))
else:
    print("Using default export dir (utils.ensure_output_dir)")

def run_export(active_doc):
    """Run export."""
    if ExportAnalyticalModel is None:
        print("Exporter unavailable; skipping analytical export.")
        return None
    exporter = ExportAnalyticalModel(active_doc, output_dir=_export_dir)
    try:
        print("Resolved export directory: {0}".format(exporter.outputDirectory))
    except Exception:
        pass
    result = exporter.export()
    print(result)
    try:
        print("Export complete: {m} members, {n} nodes".format(
            m=len(result.analytical_members), n=len(result.analytical_nodes)
        ))
    except Exception:
        print("Export complete.")
    return result

# Auto-run when loaded
if doc is not None and __name__ != "__main__":
    try:
        run_export(doc)
    except Exception as _ex:
        print("Export failed:", _ex)

if __name__ == "__main__":
    if doc is None:
        print("No Revit document (run inside pyRevit)")
    else:
        run_export(doc)
