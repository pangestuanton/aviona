import os
import sys
import asyncio

# Fix sys.path to allow absolute imports when running app/main.py directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import get_settings
from app.database.session import init_db
from app.bot.handlers import (
    start_handler,
    help_handler,
    today_handler,
    tomorrow_handler,
    week_handler,
    memory_handler,
    message_handler,
    callback_query_handler,
    schedule_handler,
)
from app.scheduler.reminder_jobs import check_due_reminders, check_class_reminders


async def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di file .env")

    init_db()

    from telegram import BotCommand

    async def post_init(application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai bot dan tampilkan menu utama"),
            BotCommand("today", "Tampilkan tugas hari ini"),
            BotCommand("tomorrow", "Tampilkan tugas besok"),
            BotCommand("week", "Tampilkan tugas minggu ini"),
            BotCommand("schedule", "Tampilkan jadwal kuliah mingguan"),
            BotCommand("help", "Tampilkan bantuan penggunaan"),
        ])

    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("today", today_handler))
    app.add_handler(CommandHandler("tomorrow", tomorrow_handler))
    app.add_handler(CommandHandler("week", week_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("memory", memory_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    
    # Task reminder check job
    scheduler.add_job(
        check_due_reminders,
        "interval",
        seconds=settings.reminder_check_interval_seconds,
        args=[app.bot],
        id="check_due_reminders",
        replace_existing=True,
    )
    
    # Class schedule reminder check job
    scheduler.add_job(
        check_class_reminders,
        "interval",
        seconds=settings.reminder_check_interval_seconds,
        args=[app.bot],
        id="check_class_reminders",
        replace_existing=True,
    )
    
    # Start scheduler within the async context
    scheduler.start()

    print("Telegram AI Study Reminder Bot berjalan...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
