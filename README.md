# Telegram AI Study Reminder Bot

Bot Telegram untuk mengingatkan jadwal kuliah dan tugas dengan memory yang kuat.

Fitur MVP:
1. User bisa tambah tugas dengan bahasa bebas.
2. User bisa tambah jadwal kuliah.
3. Bot bisa kirim reminder otomatis.
4. Bot bisa menampilkan tugas hari ini, besok, dan minggu ini.
5. Bot punya memory preferensi user.
6. Bot bisa memahami perintah edit dan hapus tugas.

## Arsitektur

```text
Telegram
  ↓
python-telegram-bot
  ↓
AI Parser
  ↓
Database SQLite/PostgreSQL
  ↓
Scheduler Reminder
```

## Struktur Folder

```text
telegram_ai_study_bot/
├── app/
│   ├── ai/
│   │   ├── memory.py
│   │   ├── parser.py
│   │   └── prompts.py
│   ├── bot/
│   │   ├── handlers.py
│   │   ├── keyboards.py
│   │   └── messages.py
│   ├── database/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── session.py
│   ├── scheduler/
│   │   └── reminder_jobs.py
│   ├── utils/
│   │   ├── datetime_utils.py
│   │   └── text_utils.py
│   ├── config.py
│   └── main.py
├── docs/
│   ├── DATABASE_SCHEMA.sql
│   ├── EXAMPLE_COMMANDS.md
│   └── PROJECT_STRUCTURE.md
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── run.py
```

## Cara Menjalankan

### 1. Buat virtual environment

```bash
python -m venv .venv
```

Aktifkan:

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

CMD:

```bash
.venv\Scripts\activate.bat
```

Linux/Mac:

```bash
source .venv/bin/activate
```

### 2. Install dependency

```bash
pip install -r requirements.txt
```

### 3. Buat file `.env`

Copy `.env.example` menjadi `.env`, lalu isi token:

```env
TELEGRAM_BOT_TOKEN=isi_token_botfather
OPENAI_API_KEY=isi_api_key_kamu
AI_BASE_URL=
AI_MODEL=gpt-4.1-mini
APP_TIMEZONE=Asia/Jakarta
DATABASE_URL=sqlite:///study_bot.db
```

Untuk OpenRouter:

```env
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openai/gpt-4o-mini
```

### 4. Jalankan bot

```bash
python run.py
```

## Contoh Chat ke Bot

```text
ingetin tugas ASD dikumpul Jumat jam 8 malam
```

```text
jadwal kuliah matematika diskrit setiap senin jam 10 sampai 11.40 di ruang GKU 102
```

```text
tampilkan tugas hari ini
```

```text
aku lebih suka diingatkan H-1 dan 2 jam sebelum deadline
```

```text
hapus tugas ASD
```

## Catatan Penting

- Versi awal memakai SQLite agar gampang dijalankan.
- Untuk production, disarankan pindah ke PostgreSQL/Supabase.
- Untuk memory semantik yang lebih kuat, bisa tambah pgvector.
- Scheduler mengecek reminder setiap 60 detik.
