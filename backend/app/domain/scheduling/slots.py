from __future__ import annotations

from datetime import datetime, timezone


def parse_hhmm(s: str) -> tuple[int, int]:
    hh, mm = s.split(":")
    return int(hh), int(mm)


def parse_local_datetime(s: str) -> tuple[int, int, int, int, int]:
    d_part, t_part = s.split("T")
    y, mo, d = d_part.split("-")
    hh, mm = t_part.split(":")
    return int(y), int(mo), int(d), int(hh), int(mm)


def iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slot_round_key(local_dt: datetime, slot_minutes: int) -> str:
    m = (local_dt.minute // slot_minutes) * slot_minutes
    return f"{local_dt.date().isoformat()}T{local_dt.hour:02d}:{m:02d}"


def tzinfo_or_utc(tz_key: str | None) -> tuple[object, str]:
    from zoneinfo import ZoneInfo
    tz = (tz_key or "UTC").strip() or "UTC"
    if tz.upper() in ("UTC", "ETC/UTC", "ETC/GMT", "GMT"):
        return timezone.utc, "UTC"
    try:
        return ZoneInfo(tz), tz
    except Exception:
        return timezone.utc, "UTC"
