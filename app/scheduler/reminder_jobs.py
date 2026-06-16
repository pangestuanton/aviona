from __future__ import annotations

from telegram import Bot

from app.database.session import SessionLocal
from app.database.repository import get_due_reminders
from app.utils.datetime_utils import now_local


async def check_due_reminders(bot: Bot) -> None:
    now = now_local()

    with SessionLocal() as db:
        reminders = get_due_reminders(db, now)

        for reminder in reminders:
            task = reminder.task
            
            # Skip if reminder is not active or task is deleted/done
            if not reminder.is_active or (task and task.status in ["deleted", "done"]):
                reminder.sent = True
                reminder.is_active = False
                db.commit()
                continue

            message = reminder.message or "Halo! Ini pengingat untuk tugasmu."

            if task:
                deadline_str = task.deadline.strftime("%A, %d %B %Y jam %H:%M") if task.deadline else "-"
                message = (
                    f"🔔 *PENGINGAT AVIONA LEARN* 🔔\n\n"
                    f"Hai! Aviona mau ingetin tugas penting kamu nih:\n\n"
                    f"📝 *{task.title}*\n"
                    f"📚 Matkul: {task.course or '-'}\n"
                    f"⏰ Deadline: {deadline_str}\n"
                    f"⚠️ Prioritas: {task.priority.capitalize()}\n\n"
                    f"Yuk dicicil sekarang biar tenang! Kamu pasti bisa! 💪🚀"
                )

            try:
                await bot.send_message(chat_id=reminder.user_id, text=message, parse_mode="Markdown")
                reminder.sent = True
                db.commit()
            except Exception as exc:
                print(f"Gagal kirim reminder {reminder.id}: {exc}")
