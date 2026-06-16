from datetime import datetime
from app.ai.parser import parse_with_fallback


def test_parse_task():
    now = datetime(2026, 6, 16, 10, 0, 0) # Selasa (Tuesday)
    result = parse_with_fallback("ingetin tugas ASD besok jam 8 malam", now)[0]
    assert result["intent"] == "create_task"
    assert "2026-06-17 20:00:00" in result["deadline"]


def test_parse_today():
    result = parse_with_fallback("tampilkan tugas hari ini", datetime.now())[0]
    assert result["intent"] == "list_today"


def test_parse_delete():
    result = parse_with_fallback("hapus tugas ASD", datetime.now())[0]
    assert result["intent"] == "delete_task"
    assert "ASD" in result["target"]


def test_parse_done():
    result = parse_with_fallback("tugas matematika diskrit sudah selesai", datetime.now())[0]
    assert result["intent"] == "mark_done"
    assert "matematika diskrit" in result["target"]


def test_parse_update():
    result = parse_with_fallback("ubah deadline laporan SO jadi Jumat jam 9 malam", datetime.now())[0]
    assert result["intent"] == "update_task"
    assert "laporan SO" in result["target"]


def test_parse_schedule():
    result = parse_with_fallback("jadwal kuliah sistem operasi setiap Selasa jam 10 sampai 11.40", datetime.now())[0]
    assert result["intent"] == "create_schedule"
    assert result["day_of_week"] == "selasa"


def test_parse_preference():
    result = parse_with_fallback("aku lebih suka diingatkan H-1 dan 2 jam sebelum deadline", datetime.now())[0]
    assert result["intent"] == "set_preference"


def test_parse_batch_schedules():
    text = (
        "Jadwal kuliah:\n"
        "1. ASD setiap senin jam 8\n"
        "2. SO setiap selasa jam 10\n"
        "3. PBO setiap rabu jam 13"
    )
    results = parse_with_fallback(text, datetime.now())
    assert len(results) == 3
    assert results[0]["intent"] == "create_schedule"
    assert results[0]["day_of_week"] == "senin"
    assert results[1]["day_of_week"] == "selasa"
    assert results[2]["day_of_week"] == "rabu"
