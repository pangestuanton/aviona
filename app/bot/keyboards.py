from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# Persistent bottom reply keyboard
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🤖 Mode Belajar", "🧠 Memori Saya"],
        ["🧹 Mulai Baru", "ℹ️ Bantuan"],
    ],
    resize_keyboard=True,
)

# Inline menu keyboard for the welcome message
MAIN_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🤖 Mode Belajar", callback_data="menu_mode"),
            InlineKeyboardButton("🧠 Memori Saya", callback_data="menu_memory"),
        ],
        [
            InlineKeyboardButton("🧹 Mulai Baru", callback_data="confirm_reset"),
            InlineKeyboardButton("ℹ️ Bantuan", callback_data="help_info"),
        ],
    ]
)

# Keyboard to select the learning persona
MODE_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✨ Standar (Asisten Ramah)", callback_data="setmode_standard"),
        ],
        [
            InlineKeyboardButton("📚 Tutor Disiplin (Ada Kuis)", callback_data="setmode_tutor"),
        ],
        [
            InlineKeyboardButton("💡 Sokrates (Tanya Balik)", callback_data="setmode_socratic"),
        ],
        [
            InlineKeyboardButton("💻 Programmer / Coder", callback_data="setmode_coder"),
        ],
        [
            InlineKeyboardButton("📝 Summarizer (Peringkas)", callback_data="setmode_summarizer"),
        ],
        [
            InlineKeyboardButton("🔙 Kembali", callback_data="back_main"),
        ]
    ]
)

# Confirmation menu for resetting data
RESET_CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🧹 Bersihkan Riwayat Chat", callback_data="reset_history_act"),
            InlineKeyboardButton("🧠 Lupakan Semua Memori", callback_data="reset_memory_act"),
        ],
        [
            InlineKeyboardButton("🔙 Kembali", callback_data="back_main"),
        ]
    ]
)
