from __future__ import annotations

from datetime import timedelta
import traceback

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.ext import ContextTypes

from app.ai.parser import parse_message
from app.ai.memory import save_memory, set_user_preference, list_memories
from app.bot.messages import START_MESSAGE, HELP_MESSAGE
from app.bot.keyboards import MAIN_INLINE_KEYBOARD, ADD_INLINE_KEYBOARD, CHECK_INLINE_KEYBOARD
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
    delete_schedule_by_id,
    delete_memory_by_id,
    get_schedule_by_id,
    get_memory_by_id,
)
from app.utils.datetime_utils import (
    now_local,
    start_end_of_day,
    start_end_of_week,
    format_remaining_time,
    local_to_utc,
    utc_to_local,
    utc_now,
    format_datetime_id,
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
    except Exception as exc:
        print(f"Error in start_handler: {exc}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
    except Exception as exc:
        print(f"Error in help_handler: {exc}")


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
    query = update.callback_query

    with SessionLocal() as db:
        memories = list_memories(db, user_id=user_id, limit=10)

    if not memories:
        text = "🧠 Memori & Preferensi:\nBelum ada memory/preferensi yang tersimpan."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]])
        if query:
            await query.message.edit_text(text, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(text, reply_markup=keyboard)
        return

    lines = ["🧠 Memory yang tersimpan:"]
    for idx, memory in enumerate(memories, start=1):
        lines.append(f"{idx}. [{memory.category}] {memory.content}")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑️ Hapus Memori", callback_data="list_delete_memories")],
            [InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]
        ]
    )
    
    text = "\n".join(lines)
    if query:
        await query.message.edit_text(text, reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    try:
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
            await query.message.edit_text(HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
        elif data == "menu_add":
            await query.message.edit_text("Pilih data yang ingin kamu tambahkan di bawah ini: 👇", reply_markup=ADD_INLINE_KEYBOARD)
        elif data == "menu_check":
            await query.message.edit_text("Pilih data yang ingin kamu cek di bawah ini: 👇", reply_markup=CHECK_INLINE_KEYBOARD)
        elif data == "add_task_prompt":
            await query.message.reply_text(
                "Ketik tugas baru kamu di bawah ini (contoh: tugas ASD dikumpul jumat jam 8 malam):",
                reply_markup=ForceReply(selective=True)
            )
            await query.answer()
        elif data == "add_schedule_prompt":
            await query.message.reply_text(
                "Ketik jadwal kuliah baru kamu di bawah ini (contoh: jadwal kuliah Sistem Operasi setiap senin jam 8 di GKU 101):",
                reply_markup=ForceReply(selective=True)
            )
            await query.answer()
        elif data == "add_memory_prompt":
            await query.message.reply_text(
                "Ketik catatan atau memori baru kamu di bawah ini (contoh: preferensi diingatkan H-1 sebelum deadline):",
                reply_markup=ForceReply(selective=True)
            )
            await query.answer()
        elif data == "view_schedule":
            await _send_schedule(update)
        elif data == "list_delete_schedules":
            user_id = update.effective_user.id
            with SessionLocal() as db:
                schedules = get_user_schedules(db, user_id)

            if not schedules:
                await query.answer("Tidak ada jadwal kuliah untuk dihapus.", show_alert=True)
                return

            buttons = []
            for s in schedules:
                day_str = f" ({s.day_of_week})" if s.day_of_week else ""
                buttons.append([InlineKeyboardButton(f"🗑️ {s.course}{day_str}", callback_data=f"delschedact_{s.id}")])
            buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="view_schedule")])

            await query.message.edit_text(
                "👇 Klik jadwal kuliah yang ingin dihapus:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer()
        elif data.startswith("delschedact_"):
            schedule_id = int(data.split("_")[1])
            with SessionLocal() as db:
                sched = get_schedule_by_id(db, schedule_id)
                if sched:
                    course_title = sched.course
                    delete_schedule_by_id(db, schedule_id)
                    await query.answer(f"🗑️ Jadwal {course_title} berhasil dihapus.", show_alert=False)
                else:
                    await query.answer("Jadwal tidak ditemukan.", show_alert=True)
            await _send_schedule(update)
        elif data == "list_delete_memories":
            user_id = update.effective_user.id
            with SessionLocal() as db:
                memories = list_memories(db, user_id=user_id, limit=10)

            if not memories:
                await query.answer("Tidak ada memori untuk dihapus.", show_alert=True)
                return

            buttons = []
            for m in memories:
                preview = m.content[:25] + "..." if len(m.content) > 25 else m.content
                buttons.append([InlineKeyboardButton(f"🗑️ {preview}", callback_data=f"delmemact_{m.id}")])
            buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="tasks_memory")])

            await query.message.edit_text(
                "👇 Klik memori yang ingin dihapus:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer()
        elif data.startswith("delmemact_"):
            memory_id = int(data.split("_")[1])
            with SessionLocal() as db:
                mem = get_memory_by_id(db, memory_id)
                if mem:
                    delete_memory_by_id(db, memory_id)
                    await query.answer("🗑️ Memori berhasil dihapus.", show_alert=False)
                else:
                    await query.answer("Memori tidak ditemukan.", show_alert=True)
            await _send_memory(update)
        elif data == "back_main":
            await query.message.edit_text(START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
            await query.answer()
        elif data.startswith("refresh_"):
            period = data.split("_")[1]
            await _send_tasks_for_period(update, period)
            await query.answer("List diperbarui!", show_alert=False)
        elif data.startswith("listdone_"):
            period = data.split("_")[1]
            user_id = update.effective_user.id
            with SessionLocal() as db:
                profile = get_user_profile(db, user_id)
                tz_name = profile.timezone
                now = now_local(tz_name)

                if period == "today":
                    start, end = start_end_of_day(now)
                elif period == "tomorrow":
                    tomorrow = now + timedelta(days=1)
                    start, end = start_end_of_day(tomorrow)
                else:
                    start, end = start_end_of_week(now)

                start_utc = local_to_utc(start, tz_name)
                end_utc = local_to_utc(end, tz_name)
                tasks = get_tasks_between(db, user_id, start_utc, end_utc)

            pending_tasks = [t for t in tasks if t.status == "pending"]

            if not pending_tasks:
                await query.answer("Tidak ada tugas pending untuk diselesaikan! 🎉", show_alert=True)
                return

            buttons = []
            for t in pending_tasks:
                buttons.append([InlineKeyboardButton(f"✅ {t.title}", callback_data=f"doneact_{t.id}_{period}")])
            buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"refresh_{period}")])

            await query.message.edit_text(
                "👇 Klik tugas yang ingin diselesaikan:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer()
        elif data.startswith("listdel_"):
            period = data.split("_")[1]
            user_id = update.effective_user.id
            with SessionLocal() as db:
                profile = get_user_profile(db, user_id)
                tz_name = profile.timezone
                now = now_local(tz_name)

                if period == "today":
                    start, end = start_end_of_day(now)
                elif period == "tomorrow":
                    tomorrow = now + timedelta(days=1)
                    start, end = start_end_of_day(tomorrow)
                else:
                    start, end = start_end_of_week(now)

                start_utc = local_to_utc(start, tz_name)
                end_utc = local_to_utc(end, tz_name)
                tasks = get_tasks_between(db, user_id, start_utc, end_utc)

            active_tasks = [t for t in tasks if t.status != "deleted"]

            if not active_tasks:
                await query.answer("Tidak ada tugas untuk dihapus.", show_alert=True)
                return

            buttons = []
            for t in active_tasks:
                buttons.append([InlineKeyboardButton(f"🗑️ {t.title}", callback_data=f"delact_{t.id}_{period}")])
            buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"refresh_{period}")])

            await query.message.edit_text(
                "👇 Klik tugas yang ingin dihapus:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer()
        elif data.startswith("doneact_"):
            _, task_id_str, period = data.split("_")
            task_id = int(task_id_str)

            with SessionLocal() as db:
                task = get_task_by_id(db, task_id)
                if task:
                    task.status = "done"
                    task.completed_at = utc_now()
                    for r in task.reminders:
                        r.is_active = False
                    db.commit()
                    task_title = task.title
                    await query.answer(f"🎉 Keren! Tugas {task_title} selesai!", show_alert=False)
                else:
                    await query.answer("Tugas tidak ditemukan.", show_alert=True)

            await _send_tasks_for_period(update, period)
        elif data.startswith("delact_"):
            _, task_id_str, period = data.split("_")
            task_id = int(task_id_str)

            with SessionLocal() as db:
                task = get_task_by_id(db, task_id)
                if task:
                    task.status = "deleted"
                    task.deleted_at = utc_now()
                    for r in task.reminders:
                        r.is_active = False
                    db.commit()
                    task_title = task.title
                    await query.answer(f"🗑️ Tugas {task_title} dihapus.", show_alert=False)
                else:
                    await query.answer("Tugas tidak ditemukan.", show_alert=True)

            await _send_tasks_for_period(update, period)

    except Exception as exc:
        print(f"Error in callback_query_handler: {exc}")
        traceback.print_exc()
        try:
            await query.answer("Terjadi kesalahan sistem.", show_alert=True)
        except Exception:
            pass


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text

    try:
        with SessionLocal() as db:
            profile = get_user_profile(db, user_id)
            tz_name = profile.timezone

        now = now_local(tz_name)

        # Check if this message is a reply to one of our ForceReply prompts
        reply_to = update.message.reply_to_message
        forced_intent = None
        if reply_to and reply_to.text:
            reply_text = reply_to.text.lower()
            if "tugas baru kamu" in reply_text:
                forced_intent = "create_task"
            elif "jadwal kuliah baru kamu" in reply_text:
                forced_intent = "create_schedule"
            elif "catatan atau memori baru kamu" in reply_text:
                forced_intent = "save_memory"

        await update.message.chat.send_action(action="typing")

        parsed_items = parse_message(text=text, user_id=user_id, now=now)
        if forced_intent:
            for parsed in parsed_items:
                parsed["intent"] = forced_intent

        # 1. Single Action Flow (concise and highly tailored response)
        if len(parsed_items) == 1:
            parsed = parsed_items[0]
            intent = parsed.get("intent", "general_chat")

            with SessionLocal() as db:
                profile = get_user_profile(db, user_id)
                tz_name = profile.timezone

                if intent in ["create_task", "create_reminder"]:
                    task = create_task_from_parsed(db, user_id, parsed, raw_text=text, timezone_name=tz_name)
                    local_deadline = utc_to_local(task.deadline, tz_name) if task.deadline else None
                    deadline_str = format_datetime_id(local_deadline)
                    if local_deadline and local_deadline < now_local(tz_name):
                        deadline_str += " (⚠️ Sudah Terlewat!)"
                    
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
                    task = update_task_from_parsed(db, user_id, parsed, raw_text=text, timezone_name=tz_name)
                    if task:
                        local_deadline = utc_to_local(task.deadline, tz_name) if task.deadline else None
                        deadline_str = format_datetime_id(local_deadline)
                        if local_deadline and local_deadline < now_local(tz_name):
                            deadline_str += " (⚠️ Sudah Terlewat!)"
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

                if intent == "set_timezone":
                    new_tz = parsed.get("new_value") or text
                    tz_map = {
                        "wib": "Asia/Jakarta",
                        "wita": "Asia/Makassar",
                        "wit": "Asia/Jayapura",
                        "jakarta": "Asia/Jakarta",
                        "makassar": "Asia/Makassar",
                        "jayapura": "Asia/Jayapura",
                    }
                    clean_tz = new_tz.lower().strip()
                    mapped_tz = None
                    for key, val in tz_map.items():
                        if key in clean_tz:
                            mapped_tz = val
                            break

                    if not mapped_tz:
                        import pytz
                        try:
                            pytz.timezone(new_tz)
                            mapped_tz = new_tz
                        except Exception:
                            pass

                    if mapped_tz:
                        profile.timezone = mapped_tz
                        db.commit()
                        await update.message.reply_text(f"⚙️ Zona waktu kamu berhasil diubah ke {mapped_tz}!")
                    else:
                        await update.message.reply_text("Maaf, Aviona tidak mengenali zona waktu tersebut. Gunakan WIB, WITA, WIT, atau nama zona waktu Olson seperti Asia/Jakarta.")
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
            return

        # 2. Batch Processing Flow (aggregated summary response)
        tasks_created = []
        schedules_created = []
        memories_saved = []
        preferences_set = []
        tasks_completed = []
        tasks_deleted = []
        timezones_set = []
        errors = 0

        with SessionLocal() as db:
            profile = get_user_profile(db, user_id)
            tz_name = profile.timezone

            for parsed in parsed_items:
                intent = parsed.get("intent", "general_chat")
                try:
                    if intent in ["create_task", "create_reminder"]:
                        t = create_task_from_parsed(db, user_id, parsed, raw_text=parsed.get("title") or "Tugas", timezone_name=tz_name)
                        tasks_created.append(t.title)
                    elif intent == "create_schedule":
                        s = create_schedule_from_parsed(db, user_id, parsed, raw_text=parsed.get("course") or "Jadwal")
                        schedules_created.append(s.course)
                    elif intent == "mark_done":
                        t = mark_task_done_by_text(db, user_id, parsed.get("target") or "")
                        if t:
                            tasks_completed.append(t.title)
                    elif intent == "delete_task":
                        c = delete_task_by_text(db, user_id, parsed.get("target") or "")
                        if c:
                            tasks_deleted.append(parsed.get("target") or "tugas")
                    elif intent == "save_memory":
                        save_memory(db, user_id, content=parsed.get("memory_content") or "catatan", category="general", importance=2)
                        memories_saved.append(parsed.get("memory_content") or "catatan")
                    elif intent == "set_preference":
                        set_user_preference(db, user_id, preference=parsed.get("memory_content") or "preferensi")
                        preferences_set.append(parsed.get("memory_content") or "preferensi")
                    elif intent == "set_timezone":
                        new_tz = parsed.get("new_value")
                        if new_tz:
                            tz_map = {
                                "wib": "Asia/Jakarta", "wita": "Asia/Makassar", "wit": "Asia/Jayapura",
                                "jakarta": "Asia/Jakarta", "makassar": "Asia/Makassar", "jayapura": "Asia/Jayapura",
                            }
                            clean_tz = new_tz.lower().strip()
                            mapped_tz = None
                            for key, val in tz_map.items():
                                if key in clean_tz:
                                    mapped_tz = val
                                    break
                            if not mapped_tz:
                                import pytz
                                try:
                                    pytz.timezone(new_tz)
                                    mapped_tz = new_tz
                                except Exception:
                                    pass
                            if mapped_tz:
                                profile.timezone = mapped_tz
                                db.commit()
                                timezones_set.append(mapped_tz)
                except Exception as e:
                    print(f"Error processing batch item {parsed}: {e}")
                    errors += 1

        summary = ["✨ Rangkuman Aksi Aviona Learn ✨\n"]
        if tasks_created:
            summary.append(f"📝 Berhasil mencatat {len(tasks_created)} tugas baru:")
            for tc in tasks_created[:5]:
                summary.append(f"   • {tc}")
            if len(tasks_created) > 5:
                summary.append(f"   • ... dan {len(tasks_created) - 5} tugas lainnya.")
        if schedules_created:
            summary.append(f"📅 Berhasil mencatat {len(schedules_created)} jadwal kuliah baru:")
            for sc in schedules_created[:5]:
                summary.append(f"   • {sc}")
            if len(schedules_created) > 5:
                summary.append(f"   • ... dan {len(schedules_created) - 5} jadwal lainnya.")
        if tasks_completed:
            summary.append(f"🎉 Berhasil menyelesaikan {len(tasks_completed)} tugas: {', '.join(tasks_completed)}")
        if tasks_deleted:
            summary.append(f"🗑️ Berhasil menghapus {len(tasks_deleted)} tugas: {', '.join(tasks_deleted)}")
        if memories_saved:
            summary.append(f"🧠 Menyimpan {len(memories_saved)} memori baru.")
        if preferences_set:
            summary.append(f"⚙️ Memperbarui {len(preferences_set)} preferensi belajar.")
        if timezones_set:
            summary.append(f"🌎 Mengubah zona waktu kamu ke: {', '.join(timezones_set)}")
        if errors:
            summary.append(f"⚠️ Gagal memproses {errors} aksi.")

        if len(summary) == 1:
            await update.message.reply_text("Aviona tidak menemukan aksi terstruktur dari pesan kamu. Ada yang bisa dibantu?")
        else:
            await update.message.reply_text("\n".join(summary))

    except Exception as exc:
        print(f"Error in message_handler: {exc}")
        traceback.print_exc()
        try:
            await update.message.reply_text("Maaf, terjadi kesalahan sistem saat memproses pesanmu.")
        except Exception:
            pass


async def _send_tasks_for_period(update: Update, period: str) -> None:
    user_id = update.effective_user.id
    query = update.callback_query

    try:
        with SessionLocal() as db:
            profile = get_user_profile(db, user_id)
            tz_name = profile.timezone
            now = now_local(tz_name)

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

            start_utc = local_to_utc(start, tz_name)
            end_utc = local_to_utc(end, tz_name)
            tasks = get_tasks_between(db, user_id, start_utc, end_utc)

        if not tasks:
            text = f"📋 {title}:\nBelum ada tugas. 🎉"
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{period}"),
                        InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main"),
                    ]
                ]
            )
            if query:
                await query.message.edit_text(text, reply_markup=keyboard)
            else:
                await update.effective_chat.send_message(text, reply_markup=keyboard)
            return

        lines = [f"📋 {title}:"]
        for idx, task in enumerate(tasks, start=1):
            local_deadline = utc_to_local(task.deadline, tz_name) if task.deadline else None
            deadline_str = format_datetime_id(local_deadline)
            status_icon = "✅" if task.status == "done" else "🕒"
            time_rem = format_remaining_time(task.deadline, utc_now()) if (task.status != "done" and task.deadline) else ""
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

        text = "\n\n".join(lines)
        if query:
            await query.message.edit_text(text, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(text, reply_markup=keyboard)

    except Exception as exc:
        print(f"Error in _send_tasks_for_period ({period}): {exc}")
        traceback.print_exc()


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_schedule(update)


async def _send_schedule(update: Update) -> None:
    user_id = update.effective_user.id
    query = update.callback_query

    try:
        with SessionLocal() as db:
            schedules = get_user_schedules(db, user_id)

        if not schedules:
            text = "📅 Jadwal Kuliah:\nKamu belum mencatat jadwal kuliah apa pun. Yuk catat dengan mengetik:\n\"Jadwal kuliah ASD setiap Senin jam 8 di GKU 101\""
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]])
            if query:
                await query.message.edit_text(text, reply_markup=keyboard)
            else:
                await update.effective_chat.send_message(text, reply_markup=keyboard)
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

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🗑️ Hapus Jadwal", callback_data="list_delete_schedules")],
                [InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]
            ]
        )

        text = "\n".join(lines)
        if query:
            await query.message.edit_text(text, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(text, reply_markup=keyboard)

    except Exception as exc:
        print(f"Error in _send_schedule: {exc}")
        traceback.print_exc()


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    current_message_id = update.message.message_id

    try:
        status_message = await update.message.reply_text("🧹 Sedang membersihkan chat...")
        status_message_id = status_message.message_id

        import asyncio
        tasks = []
        for msg_id in range(current_message_id, max(1, current_message_id - 80), -1):
            if msg_id == status_message_id:
                continue
            tasks.append(context.bot.delete_message(chat_id=chat_id, message_id=msg_id))

        await asyncio.gather(*tasks, return_exceptions=True)

        try:
            await status_message.delete()
        except Exception:
            pass

    except Exception as exc:
        print(f"Error in clear_handler: {exc}")

    await context.bot.send_message(
        chat_id=chat_id,
        text="🧹 Chat berhasil dibersihkan! Silakan pilih menu di bawah ini untuk mulai kembali: 👇",
        reply_markup=MAIN_INLINE_KEYBOARD
    )
