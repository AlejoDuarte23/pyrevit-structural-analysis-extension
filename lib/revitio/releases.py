from .models import ReleaseCondition, Releases


def read_releases(member):
    try:
        lst = list(member.GetReleaseConditions()) if hasattr(member, "GetReleaseConditions") else []
        start_rc = None
        end_rc = None
        for rc in lst:
            try:
                is_start = bool(getattr(rc, "Start"))
            except Exception:
                is_start = bool(getattr(rc, "Position", True))
            data = ReleaseCondition(
                fx=bool(getattr(rc, "Fx", False)),
                fy=bool(getattr(rc, "Fy", False)),
                fz=bool(getattr(rc, "Fz", False)),
                mx=bool(getattr(rc, "Mx", False)),
                my=bool(getattr(rc, "My", False)),
                mz=bool(getattr(rc, "Mz", False)),
            )
            if is_start:
                start_rc = data
            else:
                end_rc = data
        if start_rc is None and end_rc is None:
            return None
        return Releases(start=start_rc, end=end_rc)
    except Exception:
        return None

__all__ = ["read_releases"]
