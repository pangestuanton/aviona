from __future__ import annotations

import re
import traceback
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.ai.parser import generate_chat_response
from app.bot.messages import START_MESSAGE, HELP_MESSAGE
from app.bot.keyboards import (
    MAIN_KEYBOARD,
    MAIN_INLINE_KEYBOARD,
    MODE_INLINE_KEYBOARD,
    RESET_CONFIRM_KEYBOARD,
)
from app.database.session import SessionLocal
from app.database.repository import (
    get_user_profile,
    clear_chat_history,
    clear_user_memories,
    list_memories,
    get_memory_by_id,
    delete_memory_by_id,
)

MODE_NAMES = {
    "standard": "Standar (Asisten Ramah)",
    "tutor": "Tutor Disiplin (Ada Kuis)",
    "socratic": "Sokrates (Tanya Balik)",
    "coder": "Programmer / Coder",
    "summarizer": "Summarizer (Peringkas)",
}


async def safe_reply_text(message, text: str, reply_markup=None) -> None:
    """Send text message with HTML parsing. Fallback to plain text if HTML parsing fails."""
    try:
        await message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as exc:
        print(f"Failed to send HTML message, falling back. Error: {exc}")
        clean_text = re.sub(r'<[^>]*>', '', text)
        try:
            await message.reply_text(clean_text, reply_markup=reply_markup)
        except Exception as exc2:
            print(f"Failed to send plain text fallback. Error: {exc2}")
            await message.reply_text(text, reply_markup=reply_markup)


async def safe_edit_text(query, text: str, reply_markup=None) -> None:
    """Edit message text with HTML parsing. Fallback to plain text if HTML parsing fails."""
    try:
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as exc:
        print(f"Failed to edit HTML message, falling back. Error: {exc}")
        clean_text = re.sub(r'<[^>]*>', '', text)
        try:
            await query.message.edit_text(clean_text, reply_markup=reply_markup)
        except Exception as exc2:
            print(f"Failed to edit plain text fallback. Error: {exc2}")
            await query.message.edit_text(text, reply_markup=reply_markup)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command."""
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "User"
    
    # Register/retrieve user profile
    with SessionLocal() as db:
        profile = get_user_profile(db, user_id)
        if not profile.name:
            profile.name = name
            db.commit()

    try:
        await update.message.reply_text(
            "Halo! Menu tombol di bawah ini sekarang aktif untuk interaksi cepat tanpa mengetik. 👇",
            reply_markup=MAIN_KEYBOARD
        )
        await safe_reply_text(update.message, START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
    except Exception as exc:
        print(f"Error in start_handler: {exc}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help command."""
    try:
        await safe_reply_text(update.message, HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
    except Exception as exc:
        print(f"Error in help_handler: {exc}")


async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /mode command or menu button."""
    user_id = update.effective_user.id
    with SessionLocal() as db:
        profile = get_user_profile(db, user_id)
        current_mode = profile.mode
    
    mode_name = MODE_NAMES.get(current_mode, "standard")
    text = f"🤖 <b>Mode Belajar Aktif Saat Ini:</b> {mode_name}\n\nSilakan pilih mode belajar baru di bawah ini untuk mengganti persona AI:"
    try:
        await safe_reply_text(update.message, text, reply_markup=MODE_INLINE_KEYBOARD)
    except Exception as exc:
        print(f"Error in mode_handler: {exc}")


async def memory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /memory command or menu button."""
    user_id = update.effective_user.id
    await _send_memory_view(update, user_id)


async def _send_memory_view(update: Update, user_id: int, edit_existing: bool = False) -> None:
    """Helper to display long-term memory list."""
    with SessionLocal() as db:
        memories = list_memories(db, user_id=user_id, limit=10)

    if not memories:
        text = "🧠 <b>Memori & Preferensi:</b>\nBelum ada memory/fakta yang tersimpan. Aku akan mengingat informasi tentang dirimu secara otomatis saat kita mengobrol!"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]])
    else:
        lines = ["🧠 <b>Fakta yang aku ingat tentangmu:</b>"]
        for idx, mem in enumerate(memories, start=1):
            lines.append(f"{idx}. {mem.content}")
        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🗑️ Hapus Memori", callback_data="list_delete_memories")],
                [InlineKeyboardButton("🔙 Menu Utama", callback_data="back_main")]
            ]
        )

    if edit_existing and update.callback_query:
        await safe_edit_text(update.callback_query, text, reply_markup=keyboard)
    else:
        chat = update.effective_chat
        await safe_reply_text(chat, text, reply_markup=keyboard)


async def forget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /forget command."""
    user_id = update.effective_user.id
    with SessionLocal() as db:
        clear_user_memories(db, user_id)
    await safe_reply_text(update.message, "🧠 <b>Memori dilupakan!</b>\nSemua ingatan jangka panjang tentang dirimu telah berhasil dihapus.")


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /reset command or menu button."""
    user_id = update.effective_user.id
    with SessionLocal() as db:
        clear_chat_history(db, user_id)
    
    text = "🧹 <b>Riwayat percakapan singkat berhasil dibersihkan!</b> Percakapan kita sekarang dimulai dari awal lagi.\n\nApakah kamu juga ingin menghapus memori jangka panjang?"
    await safe_reply_text(update.message, text, reply_markup=RESET_CONFIRM_KEYBOARD)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for inline keyboard callback actions."""
    query = update.callback_query
    if not query:
        return

    user_id = update.effective_user.id
    data = query.data

    try:
        if data == "menu_mode":
            with SessionLocal() as db:
                profile = get_user_profile(db, user_id)
                current_mode = profile.mode
            mode_name = MODE_NAMES.get(current_mode, "standard")
            text = f"🤖 <b>Mode Belajar Aktif Saat Ini:</b> {mode_name}\n\nSilakan pilih mode belajar baru di bawah ini untuk mengganti persona AI:"
            await safe_edit_text(query, text, reply_markup=MODE_INLINE_KEYBOARD)
            await query.answer()

        elif data.startswith("setmode_"):
            new_mode = data.split("_")[1]
            with SessionLocal() as db:
                profile = get_user_profile(db, user_id)
                profile.mode = new_mode
                db.commit()
            
            mode_name = MODE_NAMES.get(new_mode, "standard")
            await query.answer(f"Persona diubah ke: {mode_name}", show_alert=False)
            
            text = f"🤖 <b>Mode Belajar Aktif Saat Ini:</b> {mode_name}\n\nSilakan pilih mode belajar baru di bawah ini untuk mengganti persona AI:"
            await safe_edit_text(query, text, reply_markup=MODE_INLINE_KEYBOARD)

        elif data == "menu_memory":
            await _send_memory_view(update, user_id, edit_existing=True)
            await query.answer()

        elif data == "confirm_reset":
            text = "🧹 <b>Apakah kamu ingin membersihkan riwayat percakapan atau memori?</b>"
            await safe_edit_text(query, text, reply_markup=RESET_CONFIRM_KEYBOARD)
            await query.answer()

        elif data == "reset_history_act":
            with SessionLocal() as db:
                clear_chat_history(db, user_id)
            await query.answer("🧹 Riwayat chat singkat berhasil dibersihkan!", show_alert=True)
            await safe_edit_text(query, START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)

        elif data == "reset_memory_act":
            with SessionLocal() as db:
                clear_user_memories(db, user_id)
            await query.answer("🧠 Semua memori jangka panjang berhasil dilupakan!", show_alert=True)
            await _send_memory_view(update, user_id, edit_existing=True)

        elif data == "list_delete_memories":
            with SessionLocal() as db:
                memories = list_memories(db, user_id=user_id, limit=10)

            if not memories:
                await query.answer("Tidak ada memori untuk dihapus.", show_alert=True)
                await _send_memory_view(update, user_id, edit_existing=True)
                return

            buttons = []
            for m in memories:
                preview = m.content[:25] + "..." if len(m.content) > 25 else m.content
                buttons.append([InlineKeyboardButton(f"🗑️ {preview}", callback_data=f"delmemact_{m.id}")])
            buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_memory")])

            await safe_edit_text(query, "👇 <b>Klik memori yang ingin kamu hapus:</b>", reply_markup=InlineKeyboardMarkup(buttons))
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
            
            await _send_memory_view(update, user_id, edit_existing=True)

        elif data == "help_info":
            await safe_edit_text(query, HELP_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
            await query.answer()

        elif data == "back_main":
            await safe_edit_text(query, START_MESSAGE, reply_markup=MAIN_INLINE_KEYBOARD)
            await query.answer()

    except Exception as exc:
        print(f"Error in callback_query_handler: {exc}")
        traceback.print_exc()
        try:
            await query.answer("Terjadi kesalahan sistem saat memproses tombol.", show_alert=True)
        except Exception:
            pass


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for user text messages and bottom persistent menu buttons."""
    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        return

    # Check bottom persistent menu buttons
    if text == "🤖 Mode Belajar":
        await mode_handler(update, context)
        return
    elif text == "🧠 Memori Saya":
        await memory_handler(update, context)
        return
    elif text == "🧹 Mulai Baru":
        await reset_handler(update, context)
        return
    elif text == "ℹ️ Bantuan":
        await help_handler(update, context)
        return

    # Normal chat processing
    try:
        await update.message.chat.send_action(action="typing")
        
        # Call the conversational AI wrapper
        response_text = generate_chat_response(user_id=user_id, message_text=text)
        
        await safe_reply_text(update.message, response_text)
    except Exception as exc:
        print(f"Error in message_handler: {exc}")
        traceback.print_exc()
        try:
            await update.message.reply_text("Duh maaf ya, ada kesalahan teknis saat memproses jawaban. Silakan coba sesaat lagi!")
        except Exception:
            pass
