from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

import dateparser
from openai import OpenAI

from app.config import get_settings
from app.ai.prompts import AI_PARSER_SYSTEM_PROMPT


def _empty_result(intent: str = "general_chat") -> dict[str, Any]:
    return {
        "intent": intent,
        "confidence": 0.4,
        "title": None,
        "course": None,
        "description": None,
        "deadline": None,
        "event_time": None,
        "start_time": None,
        "end_time": None,
        "day_of_week": None,
        "room": None,
        "lecturer": None,
        "reminders": [],
        "priority": "normal",
        "memory_content": None,
        "target": None,
        "new_value": None,
        "reply": None,
    }


def _clean_and_parse_date(text: str, now: datetime) -> datetime | None:
    lower = text.lower()
    
    triggers = ["besok", "hari ini", "lusa", "senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu", "tanggal"]
    
    start_idx = -1
    for trigger in triggers:
        idx = lower.find(trigger)
        if idx != -1:
            if start_idx == -1 or idx < start_idx:
                start_idx = idx
                
    if start_idx == -1:
        from dateparser.search import search_dates
        try:
            cleaned_text = re.sub(r'\b(\d{1,2})\.(\d{2})\b', r'\1:\2', text)
            cleaned_text = cleaned_text.replace("jam ", " ").replace("pukul ", " ")
            cleaned_text = cleaned_text.replace("malam", "PM").replace("sore", "PM").replace("siang", "PM").replace("pagi", "AM")
            found = search_dates(cleaned_text, languages=["id", "en"], settings={"RELATIVE_BASE": now, "PREFER_DATES_FROM": "future"})
            if found:
                return found[0][1]
        except Exception:
            pass
        return None
        
    date_part = text[start_idx:]
    date_part = re.sub(r'\b(\d{1,2})\.(\d{2})\b', r'\1:\2', date_part)
    date_part = re.sub(r'\b(jam|pukul)\b', ' ', date_part, flags=re.IGNORECASE)
    date_part = re.sub(r'\b(malam|sore|siang)\b', 'PM', date_part, flags=re.IGNORECASE)
    date_part = re.sub(r'\b(pagi)\b', 'AM', date_part, flags=re.IGNORECASE)
    date_part = re.sub(r'\s+', ' ', date_part).strip()
    
    parsed = dateparser.parse(
        date_part,
        languages=["id", "en"],
        settings={
            "RELATIVE_BASE": now,
            "TIMEZONE": "Asia/Jakarta",
            "RETURN_AS_TIMEZONE_AWARE": False,
            "PREFER_DATES_FROM": "future",
        },
    )
    return parsed


def _parse_single_line_fallback(text: str, now: datetime) -> dict[str, Any]:
    lower = text.lower().strip()
    # Strip basic list markers like "1. ", "- ", "* " from line start
    lower_clean = re.sub(r'^(\d+[\.\)]|[\-\*\u2022])\s+', '', lower)
    text_clean = text[len(lower) - len(lower_clean):]

    result = _empty_result()

    if any(x in lower_clean for x in ["timezone", "zona waktu", "ubah wib", "ubah wita", "ubah wit"]):
        result["intent"] = "set_timezone"
        result["confidence"] = 0.8
        tz_word = None
        for word in ["wib", "wita", "wit", "jakarta", "makassar", "jayapura"]:
            if word in lower_clean:
                tz_word = word
                break
        result["new_value"] = tz_word or text_clean
        return result

    # Standardize bottom keyboard button & commands matches
    if any(x == lower_clean for x in ["jadwal kuliah", "lihat jadwal", "tampilkan jadwal", "cek jadwal", "daftar jadwal", "/schedule"]):
        result["intent"] = "list_schedules"
        result["confidence"] = 0.8
        return result

    if any(x in lower_clean for x in ["bersihkan chat", "clear chat", "hapus semua pesan", "/clear"]):
        result["intent"] = "clear_chat"
        result["confidence"] = 0.8
        return result

    if any(x in lower_clean for x in ["bantuan", "/help", "help"]):
        result["intent"] = "general_chat"
        from app.bot.messages import HELP_MESSAGE
        result["reply"] = HELP_MESSAGE
        result["confidence"] = 0.8
        return result

    if any(x in lower_clean for x in ["lebih suka", "biasanya", "prefer", "preferensi"]):
        result["intent"] = "set_preference"
        result["memory_content"] = text_clean
        result["confidence"] = 0.7
        return result

    is_creation = any(x in lower_clean for x in ["ingetin", "catat", "tambah", "buat", "kumpul", "dikumpul"])

    if not is_creation:
        if any(x in lower_clean for x in ["hari ini", "/today", "tugas hari ini"]):
            result["intent"] = "list_today"
            result["confidence"] = 0.8
            return result

        if any(x in lower_clean for x in ["besok", "/tomorrow"]) and any(x in lower_clean for x in ["tampilkan", "lihat", "apa aja", "daftar", "tugas"]):
            result["intent"] = "list_tomorrow"
            result["confidence"] = 0.8
            return result

        if any(x in lower_clean for x in ["minggu ini", "/week", "tugas minggu ini"]):
            result["intent"] = "list_week"
            result["confidence"] = 0.8
            return result

    if any(x in lower_clean for x in ["hapus", "delete"]):
        result["intent"] = "delete_task"
        result["target"] = text_clean
        result["confidence"] = 0.7
        return result

    if any(x in lower_clean for x in ["selesai", "done", "sudah dikerjakan", "beres"]):
        result["intent"] = "mark_done"
        result["target"] = text_clean
        result["confidence"] = 0.7
        return result

    if any(x in lower_clean for x in ["ubah", "ganti", "set deadline"]):
        result["intent"] = "update_task"
        result["target"] = text_clean
        result["confidence"] = 0.7
        return result

    if any(x in lower_clean for x in ["ingat bahwa", "remember", "catat bahwa"]):
        result["intent"] = "save_memory"
        result["memory_content"] = text_clean
        result["confidence"] = 0.7
        return result

    if any(x in lower_clean for x in ["lebih suka", "biasanya", "prefer", "preferensi", "ingetin"]):
        if "tugas" in lower_clean or "deadline" in lower_clean or "kuis" in lower_clean:
             pass
        else:
            result["intent"] = "set_preference"
            result["memory_content"] = text_clean
            result["confidence"] = 0.7
            return result

    if any(x in lower_clean for x in ["jadwal kuliah", "setiap senin", "setiap selasa", "setiap rabu", "setiap kamis", "setiap jumat"]):
        result["intent"] = "create_schedule"
        result["title"] = text_clean
        result["course"] = _guess_course(text_clean)
        result["day_of_week"] = _guess_day(lower_clean)
        result["confidence"] = 0.65
        return result

    if any(x in lower_clean for x in ["tugas", "deadline", "dikumpul", "kumpul", "pr", "laporan", "kuis", "ujian", "ingetin"]):
        result["intent"] = "create_task"
        result["title"] = text_clean
        result["course"] = _guess_course(text_clean)
        parsed_date = _clean_and_parse_date(text_clean, now)
        if parsed_date:
            result["deadline"] = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            result["reminders"] = [
                (parsed_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                (parsed_date - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            ]
        result["confidence"] = 0.7
        return result

    result["reply"] = "Aku bisa bantu catat tugas, jadwal kuliah, reminder, dan preferensi belajarmu."
    return result


def parse_with_fallback(text: str, now: datetime) -> list[dict[str, Any]]:
    """
    Parser sederhana tanpa API AI. Mendukung multi-baris.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) <= 1:
        return [_parse_single_line_fallback(text, now)]

    results = []
    for line in lines:
        lower_line = line.lower()
        # Skip header info
        if any(lower_line.startswith(x) for x in ["jadwal kuliah", "tugas semester", "daftar", "berikut", "ini jadwal"]):
            if len(lines) > 1:
                continue
        parsed_line = _parse_single_line_fallback(line, now)
        # Skip general chat if we successfully parsed other schedules or tasks
        if parsed_line["intent"] == "general_chat" and any(r["intent"] != "general_chat" for r in results):
            continue
        results.append(parsed_line)

    if not results:
        results.append(_empty_result())
    return results


def _guess_course(text: str) -> str | None:
    courses = {
        "asd": "Algoritma dan Struktur Data",
        "algoritma": "Algoritma dan Struktur Data",
        "math diskrit": "Matematika Diskrit",
        "matematika diskrit": "Matematika Diskrit",
        "sistem operasi": "Sistem Operasi",
        "so": "Sistem Operasi",
        "agama": "Agama Islam",
        "matriks": "Matriks dan Ruang Vektor",
        "komputasi": "Pengenalan Komputasi",
    }
    lower = text.lower()
    for key, value in courses.items():
        if key in lower:
            return value
    return None


def _guess_day(lower: str) -> str | None:
    days = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]
    for day in days:
        if day in lower:
            return day
    return None


def parse_message(text: str, user_id: int, now: datetime) -> list[dict[str, Any]]:
    """
    Parser utama:
    - Jika API AI tersedia, pakai AI.
    - Jika gagal/tidak ada API key, pakai fallback sederhana.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        return parse_with_fallback(text, now)

    try:
        from app.database.session import SessionLocal
        from app.ai.memory import list_memories
        
        memories_text = ""
        with SessionLocal() as db:
            memories = list_memories(db, user_id, limit=5)
            if memories:
                memories_text = "\nUser Memories/Preferences:\n" + "\n".join([f"- {m.content}" for m in memories])

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.ai_base_url,
        )

        response = client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": AI_PARSER_SYSTEM_PROMPT + memories_text},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_id": user_id,
                            "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "timezone": settings.timezone,
                            "message": text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content or "{}"
        
        # Clean json content to extract only the valid JSON dictionary/array
        content = content.strip()
        start_idx_obj = content.find('{')
        end_idx_obj = content.rfind('}')
        start_idx_arr = content.find('[')
        end_idx_arr = content.rfind(']')

        # Prioritize whichever wrapper is present and outer
        start_idx = -1
        end_idx = -1
        if start_idx_obj != -1 and (start_idx_arr == -1 or start_idx_obj < start_idx_arr):
            start_idx = start_idx_obj
            end_idx = end_idx_obj
        elif start_idx_arr != -1:
            start_idx = start_idx_arr
            end_idx = end_idx_arr

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
            
        parsed = json.loads(content)

        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict) and "actions" in parsed:
            items = parsed["actions"]
        elif isinstance(parsed, dict):
            items = [parsed]
        else:
            items = [_empty_result()]

        normalized = []
        for item in items:
            base = _empty_result()
            base.update(item)
            normalized.append(base)
        return normalized

    except Exception:
        return parse_with_fallback(text, now)
