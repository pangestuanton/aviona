from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytz

from app.config import get_settings


INDONESIAN_DAYS = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}

INDONESIAN_MONTHS = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}


def utc_now() -> datetime:
    """Return naive current UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now_local(tz_name: str | None = None) -> datetime:
    """Return naive current local datetime for the given timezone."""
    settings = get_settings()
    if not tz_name:
        tz_name = settings.timezone
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone(settings.timezone)
    return datetime.now(tz).replace(tzinfo=None)


def local_to_utc(dt: datetime | None, tz_name: str) -> datetime | None:
    """Convert naive local datetime to naive UTC datetime."""
    if dt is None:
        return None
    try:
        tz = pytz.timezone(tz_name)
        local_dt = tz.localize(dt)
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
    except Exception:
        return dt


def utc_to_local(dt: datetime | None, tz_name: str) -> datetime | None:
    """Convert naive UTC datetime to naive local datetime."""
    if dt is None:
        return None
    try:
        tz = pytz.timezone(tz_name)
        utc_dt = dt.replace(tzinfo=pytz.utc)
        return utc_dt.astimezone(tz).replace(tzinfo=None)
    except Exception:
        return dt


def format_datetime_id(dt: datetime | None) -> str:
    """Format naive local datetime in Indonesian language format."""
    if not dt:
        return "belum diset"
    try:
        day_name = INDONESIAN_DAYS[dt.weekday()]
        month_name = INDONESIAN_MONTHS[dt.month]
        return f"{day_name}, {dt.day} {month_name} {dt.year} jam {dt.strftime('%H:%M')}"
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "belum diset"


def start_end_of_day(dt: datetime) -> tuple[datetime, datetime]:
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def start_end_of_week(dt: datetime) -> tuple[datetime, datetime]:
    start = dt - timedelta(days=dt.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def format_remaining_time(deadline: datetime | None, now: datetime) -> str:
    if not deadline:
        return ""
    
    if deadline > now:
        diff = deadline - now
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} hari")
        if hours > 0:
            parts.append(f"{hours} jam")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes} menit")
            
        return "⏳ Sisa " + " ".join(parts) if parts else "⏳ Sisa beberapa detik"
    else:
        diff = now - deadline
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} hari")
        if hours > 0:
            parts.append(f"{hours} jam")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes} menit")
            
        return "⚠️ Terlewat " + " ".join(parts) if parts else "⚠️ Baru saja terlewat"
