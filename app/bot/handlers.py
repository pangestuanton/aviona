from __future__ import annotations

from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes

from app.ai.parser import parse_message
from app.ai.memory import save_memory, set_user_preference, list_memories
from app.bot.messages import START_MESSAGE, HELP_MESSAGE
from app.bot.keyboards import MAIN_KEYBOARD, MAIN_INLINE_KEYBOARD
from app.database.session import SessionLocal
from app.database.repository import (
    create_task_from_parsed,
    update_task_from_parsed,
    create_schedule_from_parsed,
    delete_task_by_text,
    mark_task_done_by_text,
    get_tasks_between,
    get_user_profile,
)
from app.utils.datetime_utils import now_local, start_end_of_day, start_end_of_week, format_remaining_time


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_tasks_for_period(update, "today")


async def tomorrow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_tasks_for_period(update, "tomorrow")


async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_tasks_for_period(update, "week")


async def memory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_memory(update)


async def _send_memory(update: Update) -> None:
    user_id = update.effective_user.id
    with SessionLocal() as db:
        memories = list_memories(db, user_id=user_id, limit=10)

    chat = update.effective_chat
    if not chat:
        return

    if not memories:
        await chat.send_message("🧠 *Memori & Preferensi*:\nBelum ada memory/preferensi yang tersimpan.", parse_mode="Markdown")
        return

    lines = ["🧠 *Memory yang tersimpan:*"]
    for idx, memory in enumerate(memories, start=1):
        lines.append(f"{idx}. `[{memory.category}]` {memory.content}")

    await chat.send_message("\n".join(lines), parse_mode="Markdown")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data
    if data == "tasks_today":
        await _send_tasks_for_period(update, "today")
    elif data == "tasks_tomorrow":
        await _send_tasks_for_period(update, "tomorrow")
    elif data == "tasks_week":
        await _send_tasks_for_period(update, "week")
    elif data == "tasks_memory":
        await _send_memory(update)
    elif data == "help_info":
        chat = update.effective_chat
        if chat:
            await chat.send_message(HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    now = now_local()

    await update.message.chat.send_action(action="typing")

    parsed = parse_message(text=text, user_id=user_id, now=now)
    intent = parsed.get("intent", "general_chat")

    with SessionLocal() as db:
        profile = get_user_profile(db, user_id)

        if intent in ["create_task", "create_reminder"]:
            task = create_task_from_parsed(db, user_id, parsed, raw_text=text)
            deadline_str = task.deadline.strftime("%A, %d %B %Y jam %H:%M") if task.deadline else "belum diset"
            await update.message.reply_text(
                f"✨ *Catatan Aviona Learn* ✨\n\n"
                f"Siap! Tugas kamu sudah berhasil aku catat ya:\n\n"
                f"📝 *{task.title}*\n"
                f"📚 Matkul: {task.course or '-'}\n"
                f"⏰ Deadline: {deadline_str}\n"
                f"🔔 Reminder: Sudah dijadwalkan secara otomatis! Semangat! 💪",
                parse_mode="Markdown"
            )
            return

        if intent == "create_schedule":
            schedule = create_schedule_from_parsed(db, user_id, parsed, raw_text=text)
            await update.message.reply_text(
                f"📅 *Jadwal Kuliah Baru oleh Aviona*:\n\n"
                f"📖 *{schedule.course}*\n"
                f"📅 Hari: {schedule.day_of_week or '-'}\n"
                f"🕒 Jam: {schedule.start_time or '-'} - {schedule.end_time or '-'}\n"
                f"📍 Ruang: {schedule.room or '-'}\n\n"
                f"Aku bakal ingetin kamu sebelum kelas dimulai ya! 😉",
                parse_mode="Markdown"
            )
            return

        if intent == "update_task":
            task = update_task_from_parsed(db, user_id, parsed, raw_text=text)
            if task:
                deadline_str = task.deadline.strftime("%A, %d %B %Y jam %H:%M") if task.deadline else "belum diset"
                await update.message.reply_text(
                    f"🔄 *Aviona berhasil memperbarui tugasmu*:\n\n"
                    f"📝 *{task.title}*\n"
                    f"⏰ Deadline baru: {deadline_str}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("Maaf, aku tidak menemukan tugas yang dimaksud untuk diubah.")
            return

        if intent == "delete_task":
            count = delete_task_by_text(db, user_id, parsed.get("target") or text)
            if count:
                await update.message.reply_text(f"🗑️ Oke, tugas tersebut sudah Aviona hapus dari daftar ya.")
            else:
                await update.message.reply_text("Hmm, Aviona tidak menemukan tugas yang cocok untuk dihapus.")
            return

        if intent == "mark_done":
            task = mark_task_done_by_text(db, user_id, parsed.get("target") or text)
            if task:
                await update.message.reply_text(f"🎉 *Keren banget!* Tugas *{task.title}* sudah selesai. Aviona bangga sama kamu! Semangat terus ya! 🚀", parse_mode="Markdown")
            else:
                await update.message.reply_text("Aviona tidak menemukan tugas yang cocok untuk ditandai selesai.")
            return

        if intent == "save_memory":
            content = parsed.get("memory_content") or text
            save_memory(db, user_id, content=content, category="general", importance=2)
            await update.message.reply_text("🧠 Siap, fakta baru itu sudah Aviona simpan di memori-ku.")
            return

        if intent == "set_preference":
            content = parsed.get("memory_content") or text
            set_user_preference(db, user_id, preference=content)
            await update.message.reply_text("⚙️ Oke, preferensi belajarmu sudah Aviona catat dan sesuaikan.")
            return

    if intent == "list_today":
        await _send_tasks_for_period(update, "today")
        return

    if intent == "list_tomorrow":
        await _send_tasks_for_period(update, "tomorrow")
        return

    if intent == "list_week":
        await _send_tasks_for_period(update, "week")
        return

    reply = parsed.get("reply") or "Ada lagi yang bisa Aviona bantu? Aku bisa catat tugas, jadwal kuliah, atau preferensi belajar kamu."
    await update.message.reply_text(reply)


async def _send_tasks_for_period(update: Update, period: str) -> None:
    user_id = update.effective_user.id
    now = now_local()

    if period == "today":
        start, end = start_end_of_day(now)
        title = "Tugas hari ini"
    elif period == "tomorrow":
        tomorrow = now + timedelta(days=1)
        start, end = start_end_of_day(tomorrow)
        title = "Tugas besok"
    else:
        start, end = start_end_of_week(now)
        title = "Tugas minggu ini"

    with SessionLocal() as db:
        tasks = get_tasks_between(db, user_id, start, end)

    chat = update.effective_chat
    if not chat:
        return

    if not tasks:
        await chat.send_message(f"📋 *{title}*:\nBelum ada tugas. 🎉", parse_mode="Markdown")
        return

    lines = [f"📋 *{title}*:"]
    for idx, task in enumerate(tasks, start=1):
        deadline_str = task.deadline.strftime("%d %b %Y %H:%M") if task.deadline else "-"
        status_icon = "✅" if task.status == "done" else "🕒"
        time_rem = format_remaining_time(task.deadline, now) if task.status != "done" else ""
        time_rem_str = f"\n   _{time_rem}_" if time_rem else ""
        lines.append(
            f"{idx}. {status_icon} *{task.title}*\n"
            f"   📚 Matkul: {task.course or '-'}\n"
            f"   ⏰ Deadline: {deadline_str}{time_rem_str}"
        )

    await chat.send_message("\n\n".join(lines), parse_mode="Markdown")
