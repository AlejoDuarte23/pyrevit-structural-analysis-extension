# PullAnalyticalModel Extension

Minimal pyRevit extension with two buttons: Export Analytical and Update Model Features.

## 1. Export Analytical
Button: `ExportAnalytical.pushbutton`

What it does:
- Finds all AnalyticalMember elements.
- Builds node list (XYZ -> meters) and member records.
- Captures: endpoints, local axes, section (family, type, id, shape, numeric props), material (id+name), releases (start/end), structural role, cross section rotation, host element (id + unique id) via direct ref or heuristic, status flags.
- Writes `members_{model}_{timestamp}.json`.
- Output folder auto chosen (Documents/revit_analytical_exports or TEMP) unless `REVIT_ANALYTICAL_OUT` is set.

## 2. Update Model Features
Button: `UpdateModelFeatures.pushbutton`

What it does:
- Reads an input JSON (usually edited export) listing analytical_members with new section family/type.
- For each entry resolves host element (id or unique id) and swaps type if different.
- If any changes: optional workshared sync, then timestamped SaveAs copy in save folder.
- Writes a status JSON summarizing counts + save path.

### Input JSON
Edit only members needing new section (keep host refs + section):
```
{
  "analytical_members": [
    {
      "id": 123,
      "host_id": 456789,
      "host_unique_id": "...",
      "section": {
        "family_name": "W Shapes",
        "type_name": "W18x35",
        "type_id": 112233
      }
    }
  ]
}
```
Default path:
`C:\Users\<user>\Documents\revit_analytical_exports\Input\updated_sections.json`

Override via `REVIT_ANALYTICAL_UPDATE_JSON` (full path).

### Status JSON
After update a `updated_sections.json.update_status.json` file is written with counts (processed, changed, missing_symbol, no_host) and save path.

## 3. Running: Revit UI vs CLI
Revit UI (panel):
- Click button; active document used; folders auto resolved.

CLI (pyRevit):
- Provide model path; script opens first model from `__models__` list.
- Set env vars before launching to control output and update behavior.

Key difference: CLI can run headless with explicit model path; UI uses the open doc.

## 4. Environment Variables
Set (UI or CLI) before run. Grouped by use:

Export only:
- `REVIT_ANALYTICAL_OUT`  Folder for export JSON. If unset a folder under Documents or TEMP is picked.

Update only:
- `REVIT_ANALYTICAL_UPDATE_JSON`  Full path to input JSON with edited sections. If unset defaults to `C:\Users\<user>\Documents\revit_analytical_exports\Input\updated_sections.json`.
- `REVIT_ANALYTICAL_AUTO_SYNC`  If workshared and not 0/false, attempt SynchronizeWithCentral before saving.
- `REVIT_ANALYTICAL_SAVEAS_PATH`  Base folder for timestamped SaveAs copies (fallback: `C:\Users\<user>\Documents\revit_analytical_exports`).

Shared (affects update save outcome visibility):
- (None extra; export does not save the model, only writes JSON. Update may sync + SaveAs.)

Additional (CLI only):
- `__models__` injected by pyRevit CLI: first element is model path to open.

Save behavior (Update):
- If at least one member type changed a timestamped copy `BaseName_YYYYMMDD_HHMMSS.rvt` is written under `REVIT_ANALYTICAL_SAVEAS_PATH` (or fallback).
- A status file `<input>.update_status.json` records counts, save path, sync flag, and success.

## 5. Quick Flow
1. Export (button) -> JSON created in export folder (or `REVIT_ANALYTICAL_OUT`).
2. Edit only needed member `section` blocks in that JSON (or copy/subset) keeping host ids.
3. Provide to Update: either save as default path OR set env var `REVIT_ANALYTICAL_UPDATE_JSON` to edited file path.
4. Run Update (button) -> types changed (if needed), optional sync, timestamped SaveAs, status JSON beside input.

## 6. Notes
- Skips members if symbol or host not found.
- Host search: direct link then geometric heuristic.
- Coordinates in meters unless you change `UNIT_OUT`.
- Status JSON adds counts and save path.

## 7. Python Version / Style
No type hints or modern syntax: kept compatible with Python 3.4 (IronPython). Simplicity over style.

## 8. Files
- `ExportAnalytical.pushbutton/script.py` export logic wrapper.
- `UpdateModelFeatures.pushbutton/script.py` update routine.
- `lib/revitio/*.py` helper modules (geometry, nodes, sections, materials, host matching, model structures).

Done.
