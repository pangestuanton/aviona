from __future__ import annotations

from datetime import datetime, timedelta
import pytz

from app.config import get_settings


def now_local() -> datetime:
    settings = get_settings()
    tz = pytz.timezone(settings.timezone)
    return datetime.now(tz).replace(tzinfo=None)


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

