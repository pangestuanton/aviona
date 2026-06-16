import os
import sys
import asyncio

# Fix sys.path to allow absolute imports when running app/main.py directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import get_settings
from app.database.session import init_db
from app.bot.handlers import (
    start_handler,
    help_handler,
    mode_handler,
    memory_handler,
    forget_handler,
    reset_handler,
    message_handler,
    callback_query_handler,
)


async def reminder_worker(application) -> None:
    from app.database.session import SessionLocal
    from app.database.repository import get_due_timed_reminders
    from app.utils.datetime_utils import utc_now
    
    print("Background reminder worker started...")
    while True:
        try:
            await asyncio.sleep(30)
            now_utc = utc_now()
            
            with SessionLocal() as db:
                due_reminders = get_due_timed_reminders(db, now_utc)
                if not due_reminders:
                    continue
                
                for reminder in due_reminders:
                    try:
                        # Send telegram message
                        await application.bot.send_message(
                            chat_id=reminder.user_id,
                            text=reminder.message,
                            parse_mode="HTML",
                        )
                        
                        # Update reminder state
                        reminder.sent_count += 1
                        reminder.last_sent_at = utc_now()
                        db.commit()
                        print(f"Sent reminder to {reminder.user_id} (count {reminder.sent_count}/3): {reminder.message}")
                    except Exception as e:
                        print(f"Error sending reminder to {reminder.user_id}: {e}")
        except asyncio.CancelledError:
            print("Background reminder worker cancelled.")
            break
        except Exception as e:
            print(f"Error in reminder_worker: {e}")


async def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di file .env")

    # Initialize the database schema
    init_db()

    from telegram import BotCommand

    async def post_init(application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai asisten belajar & tampilkan menu"),
            BotCommand("mode", "Pilih mode/persona belajar AI"),
            BotCommand("memory", "Lihat memori jangka panjang tentangmu"),
            BotCommand("forget", "Hapus semua memori jangka panjang"),
            BotCommand("reset", "Bersihkan riwayat percakapan singkat"),
            BotCommand("help", "Tampilkan panduan bantuan"),
        ])

    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("mode", mode_handler))
    app.add_handler(CommandHandler("memory", memory_handler))
    app.add_handler(CommandHandler("forget", forget_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Telegram AI Study Assistant Bot berjalan...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Spawn background reminder worker
        worker_task = asyncio.create_task(reminder_worker(app))
        
        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
            worker_task.cancel()
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
