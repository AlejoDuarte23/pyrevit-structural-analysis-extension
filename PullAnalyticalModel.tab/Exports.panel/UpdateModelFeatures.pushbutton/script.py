#! python3
import os
import sys
import json
import datetime
print('[UpdateSections] script module loading... (__name__={})'.format(__name__))

# Try Revit API import
try:
    from Autodesk.Revit.DB import (
    Transaction, ElementId, FilteredElementCollector, BuiltInCategory, Document,
    SynchronizeWithCentralOptions, TransactWithCentralOptions, RelinquishOptions, SaveAsOptions
    )
except Exception as _revit_imp_err:
    Transaction = ElementId = FilteredElementCollector = BuiltInCategory = Document = None
    print("[UpdateSections] Warning: Revit API not available ({}).".format(_revit_imp_err))

_DEFAULT_INPUT_PATH = r"C:\Users\aleja\Documents\revit_analytical_exports\Input\updated_sections.json"
# Can override with REVIT_ANALYTICAL_UPDATE_JSON
INPUT_PATH = os.environ.get("REVIT_ANALYTICAL_UPDATE_JSON", _DEFAULT_INPUT_PATH)
print('[UpdateSections] Using INPUT_PATH={0}'.format(INPUT_PATH))
print('[UpdateSections] Env REVIT_ANALYTICAL_AUTO_SAVE={0}'.format(os.environ.get('REVIT_ANALYTICAL_AUTO_SAVE')))
print('[UpdateSections] Env REVIT_ANALYTICAL_AUTO_SYNC={0}'.format(os.environ.get('REVIT_ANALYTICAL_AUTO_SYNC')))
print('[UpdateSections] Env REVIT_ANALYTICAL_SAVE_PROMPT={0}'.format(os.environ.get('REVIT_ANALYTICAL_SAVE_PROMPT')))
print('[UpdateSections] Env REVIT_ANALYTICAL_CLI_SAVE={0}'.format(os.environ.get('REVIT_ANALYTICAL_CLI_SAVE')))
print('[UpdateSections] Env REVIT_ANALYTICAL_SAVEAS_PATH={0}'.format(os.environ.get('REVIT_ANALYTICAL_SAVEAS_PATH')))

# Add lib to path
try:
    _this = os.path.dirname(__file__)
    _root = _this
    for _i in range(3):
        _root = os.path.dirname(_root)
    _lib = os.path.join(_root, 'lib')
    if os.path.isdir(_lib) and _lib not in sys.path:
        sys.path.insert(0, _lib)
except Exception:
    pass

try:
    from revitio.utils import log_msg as logMessage, ensure_output_dir as ensureOutputDirectory
except Exception:
    def logMessage(msg, log_file=None):
        print(msg)
    def ensureOutputDirectory(p=None):
        return p or os.getcwd()

try:
    if '__revit__' in globals():
        _rv = globals()['__revit__']
        doc = _rv.ActiveUIDocument.Document
    else:
        doc = None
except Exception:
    doc = None

if doc is None:
    # Try open model in CLI
    try:
        from pyrevit import HOST_APP
        if '__models__' in globals() and globals().get('__models__'):
            _model_path = globals()['__models__'][0]
            _uidoc = HOST_APP.uiapp.OpenAndActivateDocument(_model_path)
            doc = _uidoc.Document
            print('[UpdateSections] Opened model: {0}'.format(_model_path))
    except Exception:
        pass

if doc is None:
    # Second fallback
    try:
        from pyrevit import revit
        if getattr(revit, 'doc', None):
            doc = revit.doc
            print('[UpdateSections] Fallback acquired revit.doc')
    except Exception:
        pass

print('[UpdateSections] doc acquired? {0}'.format('YES' if doc else 'NO'))

LOG_FILE = None

def _index_symbols_by_names(revit_doc):
    """Map (family_name, type_name) to symbol."""
    idx = {}
    try:
        fam_syms = (FilteredElementCollector(revit_doc)
                    .OfCategory(BuiltInCategory.OST_StructuralFraming)
                    .WhereElementIsElementType()  # type symbols
                    .ToElements())
        for s in fam_syms:
            try:
                fam_name = getattr(getattr(s, 'Family', None), 'Name', None)
                tname = getattr(s, 'Name', None)
                if fam_name and tname:
                    idx[(fam_name, tname)] = s
            except Exception:
                continue
    except Exception:
        pass
    return idx

def _load_json(path):
    with open(path, 'r') as fp:
        return json.load(fp)

def _iter_modified_members(data):
    for rec in data.get('analytical_members', []):
        section = rec.get('section') or {}
        host_id = rec.get('host_id')
        host_uid = rec.get('host_unique_id')
        if host_id is None and host_uid is None:
            continue
        yield rec.get('id'), host_id, host_uid, section.get('family_name'), section.get('type_name'), section.get('type_id')


def _resolve_host(doc, host_id, host_uid):
    e = None
    if host_uid:
        try:
            e = doc.GetElement(host_uid)
        except Exception:
            e = None
    if e is None and host_id is not None:
        try:
            e = doc.GetElement(ElementId(int(host_id)))
        except Exception:
            e = None
    return e


def _change_type_if_needed(doc, inst, new_symbol):
    try:
        if inst is None or new_symbol is None:
            return False
        cur_tid = inst.GetTypeId()
        if cur_tid == new_symbol.Id:
            return False
        # Prefer ChangeTypeId; fall back to setting Symbol
        try:
            inst.ChangeTypeId(new_symbol.Id)
        except Exception:
            try:
                inst.Symbol = new_symbol  # direct assignment
            except Exception:
                return False
        return True
    except Exception:
        return False


def run_update():
    print('[UpdateSections] Starting update routine.')
    if doc is None:
        print('[UpdateSections] No active Revit document. Aborting.')
        return
    if Transaction is None:
        print('[UpdateSections] Revit API unavailable; cannot proceed.')
        return
    if not os.path.isfile(INPUT_PATH):
        print('[UpdateSections] Input JSON not found: {0}'.format(INPUT_PATH))
        return
    print('[UpdateSections] Loading JSON: {0}'.format(INPUT_PATH))
    data = _load_json(INPUT_PATH)
    members = data.get('analytical_members', [])
    print('[UpdateSections] Loaded {0} analytical member records'.format(len(members)))
    sym_index = _index_symbols_by_names(doc)
    print('[UpdateSections] Indexed {0} framing symbols'.format(len(sym_index)))
    changes = 0
    total_checked = 0
    skipped_missing_symbol = 0
    skipped_no_host = 0
    unchanged = 0
    t = Transaction(doc, 'Update Host Section Types')
    t.Start()
    try:
        for mid, host_id, host_uid, fam_name, type_name, type_id in _iter_modified_members(data):
            total_checked += 1
            if not fam_name or not type_name:
                print('[UpdateSections] member {0}: missing target family/type, skipping'.format(mid))
                continue
            sym = sym_index.get((fam_name, type_name))
            if sym is None:
                skipped_missing_symbol += 1
                print('[UpdateSections] member {0}: target symbol not found ({1} :: {2})'.format(mid, fam_name, type_name))
                continue  # unknown symbol name combination
            host_elem = _resolve_host(doc, host_id, host_uid)
            if host_elem is None:
                skipped_no_host += 1
                print('[UpdateSections] member {0}: host element not resolved (host_id={1} host_uid={2})'.format(mid, host_id, host_uid))
                continue
            # Determine current type names
            try:
                cur_type_elem = doc.GetElement(host_elem.GetTypeId())
                cur_tname = getattr(cur_type_elem, 'Name', None)
                cur_fname = getattr(getattr(cur_type_elem, 'Family', None), 'Name', None)
            except Exception:
                cur_tname = cur_fname = None
            print('[UpdateSections] member {0}: host resolved id={1} current=({2} :: {3}) target=({4} :: {5})'.format(
                mid, host_elem.Id.IntegerValue if hasattr(host_elem.Id, 'IntegerValue') else host_elem.Id, cur_fname, cur_tname, fam_name, type_name))
            if _change_type_if_needed(doc, host_elem, sym):
                changes += 1
                print('[UpdateSections] member {0}: type CHANGED'.format(mid))
            else:
                unchanged += 1
                print('[UpdateSections] member {0}: type unchanged'.format(mid))
        t.Commit()
    except Exception as _tx_ex:
        try:
            t.RollBack()
        except Exception:
            pass
        print('[UpdateSections] ERROR inside transaction:', _tx_ex)
        raise
    print('[UpdateSections] Summary: processed={0} changed={1} unchanged={2} missing_symbol={3} no_host={4}'.format(
        total_checked, changes, unchanged, skipped_missing_symbol, skipped_no_host))
    # Save changes and timestamp copy
    _saved = False
    _synced = False
    _saveas_path = None
    _cli_mode = '__revit__' not in globals()
    _do_sync = os.environ.get('REVIT_ANALYTICAL_AUTO_SYNC', '1').lower() not in ('0', 'false', 'no')
    _force_saveas = True  # always produce a timestamped copy when changes > 0
    _base_save_folder = os.environ.get('REVIT_ANALYTICAL_SAVEAS_PATH', r'C:\Users\aleja\Documents\revit_analytical_exports')

    def _safe_make_dir(p):
        try:
            if not os.path.isdir(p):
                os.makedirs(p)
        except Exception as _mk_ex:
            print('[UpdateSections] Could not ensure directory {0}: {1}'.format(p, _mk_ex))

    try:
        if changes > 0:
            # If workshared do sync first
            if getattr(doc, 'IsWorkshared', False) and _do_sync:
                try:
                    print('[UpdateSections] Attempting SynchronizeWithCentral (pre-SaveAs).')
                    swc_opts = SynchronizeWithCentralOptions()
                    try:
                        rel_opts = RelinquishOptions(True)
                        swc_opts.SetRelinquishOptions(rel_opts)
                    except Exception:
                        pass
                    twc_opts = TransactWithCentralOptions()
                    doc.SynchronizeWithCentral(twc_opts, swc_opts)
                    _synced = True
                    print('[UpdateSections] SynchronizeWithCentral complete.')
                except Exception as _sync_ex:
                    print('[UpdateSections] Sync failed, will still attempt SaveAs:', _sync_ex)

            # Timestamped SaveAs
            if _force_saveas and SaveAsOptions:
                try:
                    import datetime as _dt
                    try:
                        import System
                    except Exception:
                        System = None
                    if System and getattr(doc, 'PathName', None):
                        try:
                            base_name = System.IO.Path.GetFileNameWithoutExtension(doc.PathName)
                        except Exception:
                            base_name = None
                    else:
                        base_name = None
                    if not base_name:
                        base_name = getattr(doc, 'Title', 'RevitModel')
                    ts = _dt.datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_filename = '{}_{}.rvt'.format(base_name, ts)
                    _safe_make_dir(_base_save_folder)
                    candidate = os.path.join(_base_save_folder, new_filename)
                    print('[UpdateSections] Saving timestamped copy: {0}'.format(candidate))
                    sao = SaveAsOptions()
                    try:
                        sao.OverwriteExistingFile = True
                    except Exception:
                        pass
                    doc.SaveAs(candidate, sao)
                    _saveas_path = candidate
                    _saved = True
                    print('[UpdateSections] Timestamped SaveAs complete.')
                except Exception as _saveas_ex:
                    print('[UpdateSections] Timestamped SaveAs failed:', _saveas_ex)
                    # Try plain Save
                    if not _saved:
                        try:
                            print('[UpdateSections] Attempting fallback Save().')
                            doc.Save()
                            _saved = True
                            print('[UpdateSections] Fallback Save() succeeded.')
                        except Exception as _sv2_ex:
                            print('[UpdateSections] Fallback Save() failed:', _sv2_ex)
            elif not _force_saveas:
                # Direct save
                try:
                    print('[UpdateSections] Direct Save (no SaveAs).')
                    doc.Save()
                    _saved = True
                except Exception as _ds_ex:
                    print('[UpdateSections] Direct Save failed:', _ds_ex)
        else:
            print('[UpdateSections] No changes -> no save attempt.')
    except Exception as _persist_ex:
        print('[UpdateSections] Persistence step error:', _persist_ex)

    # Write status JSON
    try:
        status_path = INPUT_PATH + '.update_status.json'
        status_payload = {
            'input_path': INPUT_PATH,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model_title': getattr(doc, 'Title', None),
            'counts': {
                'processed': total_checked,
                'changed': changes,
                'unchanged': unchanged,
                'missing_symbol': skipped_missing_symbol,
                'no_host': skipped_no_host
            },
            'auto_save': True,  # always-save mode
            'auto_sync': _synced,
            'cli_mode': _cli_mode,
            'saved': _saved,
            'synced': _synced,
            'saveas_path': _saveas_path,
            'success': True
        }
        with open(status_path, 'w') as sf:
            json.dump(status_payload, sf, indent=2)
        print('[UpdateSections] Wrote status JSON: {0}'.format(status_path))
    except Exception as _status_ex:
        print('[UpdateSections] Failed to write status JSON:', _status_ex)

_UPDATE_RAN = False

def _maybe_autorun():
    global _UPDATE_RAN
    if _UPDATE_RAN:
        return
    if doc is None:
        print('[UpdateSections] Skipping autorun; doc is None.')
        return
    print('[UpdateSections] Autorun trigger (__name__={}).'.format(__name__))
    try:
        run_update()
        _UPDATE_RAN = True
    except Exception as _ex:
        print('[UpdateSections] ERROR during autorun:', _ex)

# Run when imported
if ('__revit__' in globals()) or (__name__ != '__main__'):
    _maybe_autorun()

# Run when main
if __name__ == '__main__':
    _maybe_autorun()