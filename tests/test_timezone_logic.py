from datetime import datetime
from app.utils.datetime_utils import local_to_utc, utc_to_local, format_datetime_id


def test_timezone_conversion():
    # Naive local time: 2026-06-16 12:00:00
    local_dt = datetime(2026, 6, 16, 12, 0, 0)
    
    # Jakarta: UTC+7. So local 12:00 -> UTC 05:00
    utc_dt_jakarta = local_to_utc(local_dt, "Asia/Jakarta")
    assert utc_dt_jakarta == datetime(2026, 6, 16, 5, 0, 0)
    
    # Makassar: UTC+8. So local 12:00 -> UTC 04:00
    utc_dt_makassar = local_to_utc(local_dt, "Asia/Makassar")
    assert utc_dt_makassar == datetime(2026, 6, 16, 4, 0, 0)
    
    # Jayapura: UTC+9. So local 12:00 -> UTC 03:00
    utc_dt_jayapura = local_to_utc(local_dt, "Asia/Jayapura")
    assert utc_dt_jayapura == datetime(2026, 6, 16, 3, 0, 0)
    
    # Reverse conversion: UTC 05:00 -> Jakarta local 12:00
    assert utc_to_local(utc_dt_jakarta, "Asia/Jakarta") == local_dt
    assert utc_to_local(utc_dt_makassar, "Asia/Makassar") == local_dt
    assert utc_to_local(utc_dt_jayapura, "Asia/Jayapura") == local_dt


def test_format_datetime_id():
    dt = datetime(2026, 6, 16, 13, 45, 0) # Selasa (Tuesday)
    formatted = format_datetime_id(dt)
    assert "Selasa" in formatted
    assert "16" in formatted
    assert "Juni" in formatted
    assert "2026" in formatted
    assert "13:45" in formatted


def test_format_datetime_id_none():
    assert format_datetime_id(None) == "belum diset"
