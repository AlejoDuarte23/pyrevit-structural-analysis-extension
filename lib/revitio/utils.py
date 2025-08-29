import os
import datetime

from Autodesk.Revit.DB import UnitUtils, UnitTypeId

UNIT_OUT = "meters"  # or feet
SNAP_TOLERANCE_METERS = 0.015  # 15mm
HOST_MATCH_TOL_METERS = 0.05   # 50mm


def ensure_output_dir(custom_path=None):
    """Return export dir.

    Order: arg, env, user docs, temp.
    Creates and returns abs path.
    """
    candidates = []

    # arg
    if custom_path:
        candidates.append(custom_path)

    # env
    env_override = os.environ.get("REVIT_ANALYTICAL_OUT")
    if env_override:
        candidates.append(env_override)

    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    one_drive = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE") or os.environ.get("OneDriveConsumer")

    # user docs
    if user_profile:
        candidates.append(os.path.join(user_profile, "Documents", "revit_analytical_exports"))
    if one_drive:
        candidates.append(os.path.join(one_drive, "Documents", "revit_analytical_exports"))

    # temp
    candidates.append(os.path.join(os.environ.get("TEMP", os.path.abspath(".")), "revit_analytical_exports"))

    chosen = None
    for path in candidates:
        if not path:
            continue
        try:
            # norm path
            p = os.path.normpath(os.path.expandvars(os.path.expanduser(path)))
            # Attempt creation (ignore exists race)
            if not os.path.isdir(p):
                try:
                    os.makedirs(p)
                except OSError:
                    # Another process may have created it, re-check
                    if not os.path.isdir(p):
                        continue
            # Basic writability check
            test_file = os.path.join(p, "__writetest.tmp")
            try:
                with open(test_file, "w") as tf:
                    tf.write("ok")
                os.remove(test_file)
            except Exception:
                continue
            chosen = p
            break
        except Exception:
            continue

    if chosen is None:
        # Last resort: current working directory
        chosen = os.path.abspath("revit_analytical_exports")
        try:
            if not os.path.isdir(chosen):
                os.makedirs(chosen)
        except Exception:
            pass
    return chosen


def log_msg(msg, logfile):
    """Append timestamped line."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(logfile, "a") as f:
        f.write("[{}] {}\n".format(ts, msg))


def eid_to_int(eid):
    """ElementId -> int or None."""
    try:  # ElementId.Value
        return int(eid.Value)
    except Exception:
        pass
    try:  # ElementId.IntegerValue (older API variants)
        return int(eid.IntegerValue)
    except Exception:
        pass
    try:  # already an int / numeric
        return int(eid)
    except Exception:
        return None


def eid_positive(eid):
    """True if id > 0."""
    v = eid_to_int(eid)
    return v is not None and v > 0


def xyz_to_out(xyz):
    """XYZ to list in out units."""
    if UNIT_OUT.lower() == "meters":
        return [
            UnitUtils.ConvertFromInternalUnits(xyz.X, UnitTypeId.Meters),
            UnitUtils.ConvertFromInternalUnits(xyz.Y, UnitTypeId.Meters),
            UnitUtils.ConvertFromInternalUnits(xyz.Z, UnitTypeId.Meters),
        ]
    return [xyz.X, xyz.Y, xyz.Z]


def meters_to_internal(val_m):
    """Meters to internal units."""
    return UnitUtils.ConvertToInternalUnits(val_m, UnitTypeId.Meters)


def model_name(document):
    """Name from path or title."""
    try:
        if document.PathName:
            base = os.path.splitext(os.path.basename(document.PathName))[0]
            if base:
                return base
        title = getattr(document, "Title", None)
        if title:
            return title
        return "unsaved_model"
    except Exception:
        return "model"


__all__ = [
    "UNIT_OUT", "SNAP_TOLERANCE_METERS", "HOST_MATCH_TOL_METERS",
    "ensure_output_dir", "log_msg", "eid_to_int", "eid_positive",
    "xyz_to_out", "meters_to_internal", "model_name"
]
