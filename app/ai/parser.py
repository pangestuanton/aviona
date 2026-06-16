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


def parse_with_fallback(text: str, now: datetime) -> dict[str, Any]:
    """
    Parser sederhana tanpa API AI.
    """
    lower = text.lower()
    result = _empty_result()

    if any(x in lower for x in ["lebih suka", "biasanya", "prefer", "preferensi"]):
        result["intent"] = "set_preference"
        result["memory_content"] = text
        result["confidence"] = 0.7
        return result

    is_creation = any(x in lower for x in ["ingetin", "catat", "tambah", "buat", "kumpul", "dikumpul"])

    if not is_creation:
        if any(x in lower for x in ["hari ini", "/today", "tugas hari ini"]):
            result["intent"] = "list_today"
            result["confidence"] = 0.8
            return result

        if any(x in lower for x in ["besok", "/tomorrow"]) and any(x in lower for x in ["tampilkan", "lihat", "apa aja", "daftar", "tugas"]):
            result["intent"] = "list_tomorrow"
            result["confidence"] = 0.8
            return result

        if any(x in lower for x in ["minggu ini", "/week", "tugas minggu ini"]):
            result["intent"] = "list_week"
            result["confidence"] = 0.8
            return result

    if any(x in lower for x in ["hapus", "delete"]):
        result["intent"] = "delete_task"
        result["target"] = text
        result["confidence"] = 0.7
        return result

    if any(x in lower for x in ["selesai", "done", "sudah dikerjakan", "beres"]):
        result["intent"] = "mark_done"
        result["target"] = text
        result["confidence"] = 0.7
        return result

    if any(x in lower for x in ["ubah", "ganti", "set deadline"]):
        result["intent"] = "update_task"
        result["target"] = text
        result["confidence"] = 0.7
        return result

    if any(x in lower for x in ["ingat bahwa", "remember", "catat bahwa"]):
        result["intent"] = "save_memory"
        result["memory_content"] = text
        result["confidence"] = 0.7
        return result

    if any(x in lower for x in ["lebih suka", "biasanya", "prefer", "preferensi", "ingetin"]):
        if "tugas" in lower or "deadline" in lower or "kuis" in lower:
             # Likely creating a task if 'ingetin' is used with 'tugas'
             pass
        else:
            result["intent"] = "set_preference"
            result["memory_content"] = text
            result["confidence"] = 0.7
            return result

    if any(x in lower for x in ["jadwal kuliah", "setiap senin", "setiap selasa", "setiap rabu", "setiap kamis", "setiap jumat"]):
        result["intent"] = "create_schedule"
        result["title"] = text
        result["course"] = _guess_course(text)
        result["day_of_week"] = _guess_day(lower)
        result["confidence"] = 0.65
        return result

    if any(x in lower for x in ["tugas", "deadline", "dikumpul", "kumpul", "pr", "laporan", "kuis", "ujian", "ingetin"]):
        result["intent"] = "create_task"
        result["title"] = text
        result["course"] = _guess_course(text)
        parsed_date = _clean_and_parse_date(text, now)
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


def parse_message(text: str, user_id: int, now: datetime) -> dict[str, Any]:
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
        # Strip potential markdown code blocks
        if content.startswith("```json"):
            content = content.replace("```json", "", 1).replace("```", "", 1).strip()
        elif content.startswith("```"):
            content = content.replace("```", "", 1).replace("```", "", 1).strip()
            
        parsed = json.loads(content)

        base = _empty_result()
        base.update(parsed)
        return base

    except Exception:
        return parse_with_fallback(text, now)
