from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["/today", "/tomorrow"],
        ["/week", "/memory"],
        ["/help"],
    ],
    resize_keyboard=True,
)

MAIN_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📋 Hari Ini", callback_data="tasks_today"),
            InlineKeyboardButton("📅 Besok", callback_data="tasks_tomorrow"),
        ],
        [
            InlineKeyboardButton("🗓️ Minggu Ini", callback_data="tasks_week"),
            InlineKeyboardButton("🧠 Memori", callback_data="tasks_memory"),
        ],
        [
            InlineKeyboardButton("ℹ️ Bantuan", callback_data="help_info"),
        ],
    ]
)

