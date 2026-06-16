from datetime import datetime
from app.ai.parser import parse_with_fallback


def test_parse_task():
    now = datetime(2026, 6, 16, 10, 0, 0) # Selasa
    result = parse_with_fallback("ingetin tugas ASD besok jam 8 malam", now)
    assert result["intent"] == "create_task"
    assert "2026-06-17 20:00:00" in result["deadline"]

def test_parse_today():
    result = parse_with_fallback("tampilkan tugas hari ini", datetime.now())
    assert result["intent"] == "list_today"

def test_parse_delete():
    result = parse_with_fallback("hapus tugas ASD", datetime.now())
    assert result["intent"] == "delete_task"
    assert "ASD" in result["target"]

def test_parse_done():
    result = parse_with_fallback("tugas matematika diskrit sudah selesai", datetime.now())
    assert result["intent"] == "mark_done"
    assert "matematika diskrit" in result["target"]

def test_parse_update():
    result = parse_with_fallback("ubah deadline laporan SO jadi Jumat jam 9 malam", datetime.now())
    assert result["intent"] == "update_task"
    assert "laporan SO" in result["target"]

def test_parse_schedule():
    result = parse_with_fallback("jadwal kuliah sistem operasi setiap Selasa jam 10 sampai 11.40", datetime.now())
    assert result["intent"] == "create_schedule"
    assert result["day_of_week"] == "selasa"

def test_parse_preference():
    result = parse_with_fallback("aku lebih suka diingatkan H-1 dan 2 jam sebelum deadline", datetime.now())
    assert result["intent"] == "set_preference"
