from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📋 Tugas Hari Ini", "📅 Tugas Besok"],
        ["🗓️ Tugas Minggu Ini", "📅 Jadwal Kuliah"],
        ["🧹 Bersihkan Chat", "ℹ️ Bantuan"],
    ],
    resize_keyboard=True,
)

MAIN_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("➕ Tambah Data", callback_data="menu_add"),
            InlineKeyboardButton("🔍 Cek Data", callback_data="menu_check"),
        ],
        [
            InlineKeyboardButton("🧹 Bersihkan Chat", callback_data="clear_chat"),
            InlineKeyboardButton("ℹ️ Bantuan", callback_data="help_info"),
        ],
    ]
)

ADD_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📝 Tambah Tugas", callback_data="add_task_prompt"),
            InlineKeyboardButton("📅 Tambah Jadwal", callback_data="add_schedule_prompt"),
        ],
        [
            InlineKeyboardButton("🔙 Kembali", callback_data="back_main"),
        ]
    ]
)

CHECK_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📋 Tugas Hari Ini", callback_data="tasks_today"),
            InlineKeyboardButton("📅 Tugas Besok", callback_data="tasks_tomorrow"),
        ],
        [
            InlineKeyboardButton("🗓️ Tugas Minggu Ini", callback_data="tasks_week"),
            InlineKeyboardButton("📅 Jadwal Kuliah", callback_data="view_schedule"),
        ],
        [
            InlineKeyboardButton("🔙 Kembali", callback_data="back_main"),
        ],
    ]
)


