from __future__ import annotations

from datetime import timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
    get_user_schedules,
    get_task_by_id,
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
        await chat.send_message("🧠 Memori & Preferensi:\nBelum ada memory/preferensi yang tersimpan.")
        return

    lines = ["🧠 Memory yang tersimpan:"]
    for idx, memory in enumerate(memories, start=1):
        lines.append(f"{idx}. [{memory.category}] {memory.content}")

    await chat.send_message("\n".join(lines))


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
    elif data == "view_schedule":
        await _send_schedule(update)
    elif data == "back_main":
        chat = update.effective_chat
        if chat:
            await chat.send_message(START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
    elif data.startswith("refresh_"):
        period = data.split("_")[1]
        await _send_tasks_for_period(update, period)
    elif data.startswith("listdone_"):
        period = data.split("_")[1]
        user_id = update.effective_user.id
        now = now_local()

        if period == "today":
            start, end = start_end_of_day(now)
        elif period == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start, end = start_end_of_day(tomorrow)
        else:
            start, end = start_end_of_week(now)

        with SessionLocal() as db:
            tasks = get_tasks_between(db, user_id, start, end)

        pending_tasks = [t for t in tasks if t.status == "pending"]

        if not pending_tasks:
            await update.effective_chat.send_message("Tidak ada tugas pending untuk diselesaikan! 🎉")
            return

        buttons = []
        for t in pending_tasks:
            buttons.append([InlineKeyboardButton(f"✅ {t.title}", callback_data=f"doneact_{t.id}_{period}")])
        buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"refresh_{period}")])

        await update.effective_chat.send_message(
            "👇 Klik tugas yang ingin diselesaikan:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif data.startswith("listdel_"):
        period = data.split("_")[1]
        user_id = update.effective_user.id
        now = now_local()

        if period == "today":
            start, end = start_end_of_day(now)
        elif period == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start, end = start_end_of_day(tomorrow)
        else:
            start, end = start_end_of_week(now)

        with SessionLocal() as db:
            tasks = get_tasks_between(db, user_id, start, end)

        active_tasks = [t for t in tasks if t.status != "deleted"]

        if not active_tasks:
            await update.effective_chat.send_message("Tidak ada tugas untuk dihapus.")
            return

        buttons = []
        for t in active_tasks:
            buttons.append([InlineKeyboardButton(f"🗑️ {t.title}", callback_data=f"delact_{t.id}_{period}")])
        buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"refresh_{period}")])

        await update.effective_chat.send_message(
            "👇 Klik tugas yang ingin dihapus:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif data.startswith("doneact_"):
        _, task_id_str, period = data.split("_")
        task_id = int(task_id_str)

        with SessionLocal() as db:
            task = get_task_by_id(db, task_id)
            if task:
                task.status = "done"
                import datetime as dt_mod
                task.completed_at = dt_mod.datetime.utcnow()
                for r in task.reminders:
                    r.is_active = False
                db.commit()
                task_title = task.title
            else:
                task_title = "tugas"

        await update.effective_chat.send_message(
            f"🎉 Keren! Tugas {task_title} berhasil diselesaikan! Aviona bangga! 🚀"
        )
        await _send_tasks_for_period(update, period)
    elif data.startswith("delact_"):
        _, task_id_str, period = data.split("_")
        task_id = int(task_id_str)

        with SessionLocal() as db:
            task = get_task_by_id(db, task_id)
            if task:
                task.status = "deleted"
                import datetime as dt_mod
                task.deleted_at = dt_mod.datetime.utcnow()
                for r in task.reminders:
                    r.is_active = False
                db.commit()
                task_title = task.title
            else:
                task_title = "tugas"

        await update.effective_chat.send_message(
            f"🗑️ Tugas {task_title} berhasil dihapus dari daftar."
        )
        await _send_tasks_for_period(update, period)


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
                f"✨ Catatan Aviona Learn ✨\n\n"
                f"Siap! Tugas kamu sudah berhasil aku catat ya:\n\n"
                f"📝 {task.title}\n"
                f"📚 Matkul: {task.course or '-'}\n"
                f"⏰ Deadline: {deadline_str}\n"
                f"🔔 Reminder: Sudah dijadwalkan secara otomatis! Semangat! 💪"
            )
            return

        if intent == "create_schedule":
            schedule = create_schedule_from_parsed(db, user_id, parsed, raw_text=text)
            await update.message.reply_text(
                f"📅 Jadwal Kuliah Baru oleh Aviona:\n\n"
                f"📖 {schedule.course}\n"
                f"📅 Hari: {schedule.day_of_week or '-'}\n"
                f"🕒 Jam: {schedule.start_time or '-'} - {schedule.end_time or '-'}\n"
                f"📍 Ruang: {schedule.room or '-'}\n\n"
                f"Aku bakal ingetin kamu sebelum kelas dimulai ya! 😉"
            )
            return

        if intent == "update_task":
            task = update_task_from_parsed(db, user_id, parsed, raw_text=text)
            if task:
                deadline_str = task.deadline.strftime("%A, %d %B %Y jam %H:%M") if task.deadline else "belum diset"
                await update.message.reply_text(
                    f"🔄 Aviona berhasil memperbarui tugasmu:\n\n"
                    f"📝 {task.title}\n"
                    f"⏰ Deadline baru: {deadline_str}"
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
                await update.message.reply_text(f"🎉 Keren banget! Tugas {task.title} sudah selesai. Aviona bangga sama kamu! Semangat terus ya! 🚀")
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
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{period}"),
                    InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main"),
                ]
            ]
        )
        await chat.send_message(f"📋 {title}:\nBelum ada tugas. 🎉", reply_markup=keyboard)
        return

    lines = [f"📋 {title}:"]
    for idx, task in enumerate(tasks, start=1):
        deadline_str = task.deadline.strftime("%d %b %Y %H:%M") if task.deadline else "-"
        status_icon = "✅" if task.status == "done" else "🕒"
        time_rem = format_remaining_time(task.deadline, now) if task.status != "done" else ""
        time_rem_str = f"\n   {time_rem}" if time_rem else ""
        lines.append(
            f"{idx}. {status_icon} {task.title}\n"
            f"   📚 Matkul: {task.course or '-'}\n"
            f"   ⏰ Deadline: {deadline_str}{time_rem_str}"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Selesaikan Tugas", callback_data=f"listdone_{period}"),
                InlineKeyboardButton("🗑️ Hapus Tugas", callback_data=f"listdel_{period}"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{period}"),
                InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main"),
            ]
        ]
    )

    await chat.send_message("\n\n".join(lines), reply_markup=keyboard)


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_schedule(update)


async def _send_schedule(update: Update) -> None:
    user_id = update.effective_user.id
    chat = update.effective_chat
    if not chat:
        return

    with SessionLocal() as db:
        schedules = get_user_schedules(db, user_id)

    if not schedules:
        await chat.send_message(
            "📅 Jadwal Kuliah:\nKamu belum mencatat jadwal kuliah apa pun. Yuk catat dengan mengetik:\n\"Jadwal kuliah ASD setiap Senin jam 8 di GKU 101\""
        )
        return

    lines = ["📅 Jadwal Kuliah Kamu:"]
    current_day = None
    for s in schedules:
        day_title = (s.day_of_week or "Lainnya").capitalize()
        if day_title != current_day:
            current_day = day_title
            lines.append(f"\n📌 {current_day}")

        time_str = f"{s.start_time or ''} - {s.end_time or ''}" if s.start_time else "Waktu belum diset"
        room_str = f" @ {s.room}" if s.room else ""
        lines.append(f"  • {s.course} ({time_str}){room_str}")

    await chat.send_message("\n".join(lines))
