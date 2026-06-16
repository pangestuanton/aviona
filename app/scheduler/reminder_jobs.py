from __future__ import annotations

import pytz
from datetime import datetime, timedelta
from telegram import Bot

from app.database.session import SessionLocal
from app.database.repository import get_due_reminders, get_user_profile
from app.database.models import CourseSchedule
from app.utils.datetime_utils import utc_now, utc_to_local, format_datetime_id


# Session cache for sent class reminders to prevent duplicate notifications
SENT_CLASS_REMINDERS = set()

DAY_MAP = {
    "monday": "senin",
    "tuesday": "selasa",
    "wednesday": "rabu",
    "thursday": "kamis",
    "friday": "jumat",
    "saturday": "sabtu",
    "sunday": "minggu"
}


async def check_due_reminders(bot: Bot) -> None:
    now_u = utc_now()

    with SessionLocal() as db:
        reminders = get_due_reminders(db, now_u)

        for reminder in reminders:
            try:
                task = reminder.task
                
                # Skip if reminder is not active or task is deleted/done
                if not reminder.is_active or (task and task.status in ["deleted", "done"]):
                    reminder.sent = True
                    reminder.is_active = False
                    db.commit()
                    continue

                message = reminder.message or "Halo! Ini pengingat untuk tugasmu."

                if task:
                    profile = get_user_profile(db, reminder.user_id)
                    tz_name = profile.timezone
                    local_deadline = utc_to_local(task.deadline, tz_name) if task.deadline else None
                    deadline_str = format_datetime_id(local_deadline)
                    
                    message = (
                        f"🔔 PENGINGAT AVIONA LEARN 🔔\n\n"
                        f"Hai! Aviona mau ingetin tugas penting kamu nih:\n\n"
                        f"📝 {task.title}\n"
                        f"📚 Matkul: {task.course or '-'}\n"
                        f"⏰ Deadline: {deadline_str}\n"
                        f"⚠️ Prioritas: {task.priority.capitalize()}\n\n"
                        f"Yuk dicicil sekarang biar tenang! Kamu pasti bisa! 💪🚀"
                    )

                await bot.send_message(chat_id=reminder.user_id, text=message)
                reminder.sent = True
                db.commit()
            except Exception as exc:
                print(f"Gagal kirim reminder {reminder.id}: {exc}")


async def check_class_reminders(bot: Bot) -> None:
    with SessionLocal() as db:
        try:
            schedules = db.query(CourseSchedule).all()
        except Exception as exc:
            print(f"Gagal mengambil data jadwal dari database: {exc}")
            return

        for s in schedules:
            try:
                profile = get_user_profile(db, s.user_id)
                tz_name = profile.timezone
                tz = pytz.timezone(tz_name)
                
                # Get current local time in user's timezone
                user_now = datetime.now(tz)
                
                # Check day of week
                current_day_eng = user_now.strftime("%A").lower()
                current_day_id = DAY_MAP.get(current_day_eng)
                if not current_day_id or s.day_of_week != current_day_id:
                    continue
                
                # Check start_time
                if not s.start_time:
                    continue
                
                # Parse start_time (format: "HH:MM")
                try:
                    hour, minute = map(int, s.start_time.split(":"))
                except ValueError:
                    continue
                
                # Create class time today in user's local timezone
                class_time = user_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Calculate difference
                diff = class_time - user_now
                
                # Notify if class starts in 30 minutes (up to 30 minutes in the future)
                if timedelta(minutes=0) < diff <= timedelta(minutes=30):
                    cache_key = (s.id, user_now.date().isoformat())
                    if cache_key not in SENT_CLASS_REMINDERS:
                        msg = (
                            f"🔔 PENGINGAT KELAS AVIONA LEARN 🔔\n\n"
                            f"Hai! Aviona mau ingetin kalau kelas kamu sebentar lagi dimulai nih:\n\n"
                            f"📖 {s.course}\n"
                            f"🕒 Jam: {s.start_time} - {s.end_time or '-'}\n"
                            f"📍 Ruangan: {s.room or '-'}\n"
                            f"👤 Dosen: {s.lecturer or '-'}\n\n"
                            f"Jangan telat ya! Siapkan catatannya! Semangat kuliahnya! 🎓✨"
                        )
                        await bot.send_message(chat_id=s.user_id, text=msg)
                        SENT_CLASS_REMINDERS.add(cache_key)
            except Exception as exc:
                print(f"Gagal memproses pengingat kelas untuk schedule {s.id}: {exc}")
