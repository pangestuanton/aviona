# Aviona Learn: AI Study Assistant Telegram Bot

Aviona Learn adalah asisten AI personal cerdas untuk mahasiswa Indonesia yang terintegrasi dengan Telegram. Bot ini siap membantumu belajar pemrograman, matematika, subjek kuliah, membuat ringkasan, memberikan panduan belajar, membantu debugging kode, serta menjawab berbagai pertanyaan Q&A secara alami dan santai menggunakan Bahasa Indonesia.

## Fitur Utama

1. **Percakapan AI Bebas**: Mengobrol dan bertanya tentang materi kuliah apa saja secara natural dalam Bahasa Indonesia.
2. **5 Mode Belajar (Tutoring Personas)**:
   - **Standar**: Asisten belajar ramah, hangat, dan mudah dipahami.
   - **Tutor Disiplin**: Menjelaskan konsep dasar secara mendalam dan memberikan kuis/latihan soal di akhir penjelasan.
   - **Penuntun Sokrates**: Tidak memberikan jawaban langsung, melainkan membimbing logikamu lewat pertanyaan balik yang mendidik.
   - **Programmer/Coder**: Membantu debugging, menulis kode bersih (clean code), dan menjelaskan algoritma pemrograman.
   - **Summarizer**: Menyajikan penjelasan secara sangat padat dalam bentuk poin-poin penting.
3. **Short-Term Session Memory**: Mengingat riwayat obrolan terakhir (context window 10 pesan) agar percakapan tetap nyambung.
4. **Self-Learning Long-Term Memory**: AI secara otomatis mengenali dan menyimpan informasi personal penting tentangmu (seperti nama, jurusan, semester, atau preferensi belajarmu) ketika kamu menceritakannya.
5. **Menu Interaktif Telegram**: Tombol menu keyboard (`MAIN_KEYBOARD` dan inline buttons) untuk berpindah mode, mengelola memori, dan mereset percakapan secara cepat tanpa mengetik.

---

## Arsitektur

```text
Telegram App
    ↓
python-telegram-bot
    ↓
AI Conversational Parser (app/ai/parser.py)
    ↓
OpenAI-Compatible API (OpenRouter, OpenAI, etc.)
    ↓
SQLite Database (Menyimpan riwayat chat & memori jangka panjang)
```

---

## Struktur Folder

```text
TeleBot/
├── app/
│   ├── ai/
│   │   ├── parser.py       # Conversational AI wrapper & memory extraction
│   │   └── prompts.py      # System prompts & tutoring persona configurations
│   ├── bot/
│   │   ├── handlers.py     # Telegram message & callback commands handlers
│   │   ├── keyboards.py    # Reply keyboards & inline menus
│   │   └── messages.py     # Message string templates (HTML formatting)
│   ├── database/
│   │   ├── models.py       # SQLAlchemy Database Models (UserProfile, ChatMessage, Memory)
│   │   ├── repository.py   # Database query helper operations
│   │   └── session.py      # Database engine & session management
│   ├── utils/
│   │   └── datetime_utils.py # Date and timezone conversion utilities
│   ├── config.py           # Application environment configuration
│   └── main.py             # Bot initialization & runner
├── tests/
│   ├── test_parser.py      # Unit tests for AI flow & memory saving
│   └── test_timezone_logic.py # Timezone formatting tests
├── .env.example            # Example configuration file
├── requirements.txt        # Python package dependencies
├── run.py                  # Entry script to start the bot
└── study_bot.db            # Local SQLite database
```

---

## Cara Menjalankan Secara Lokal

### 1. Buat Virtual Environment & Aktifkan
```bash
python -m venv .venv
```
- **Windows PowerShell**:
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- **Windows CMD**:
  ```bash
  .venv\Scripts\activate.bat
  ```
- **Linux/macOS**:
  ```bash
  source .venv/bin/activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi File `.env`
Salin file `.env.example` menjadi `.env` dan lengkapi variabel berikut:
```env
TELEGRAM_BOT_TOKEN=token_bot_telegram_dari_botfather
OPENAI_API_KEY=api_key_openai_atau_openrouter

# Konfigurasi AI Provider (Opsional, bawaan: OpenRouter)
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openrouter/free

# Konfigurasi Database & Timezone
APP_TIMEZONE=Asia/Jakarta
DATABASE_URL=sqlite:///study_bot.db
```

### 4. Jalankan Bot
```bash
python run.py
```

---

## Panduan Perintah Telegram (Commands)

- `/start`: Memulai bot, mendaftarkan profil, dan menampilkan menu interaktif.
- `/mode`: Membuka menu inline keyboard untuk mengganti persona belajar AI.
- `/memory`: Menampilkan seluruh fakta jangka panjang yang bot ingat tentangmu.
- `/forget`: Menghapus semua memori jangka panjang yang bot ingat.
- `/reset`: Membersihkan riwayat percakapan singkat (chat history) agar percakapan baru tidak terpengaruh topik sebelumnya.
- `/help`: Menampilkan panduan bantuan penggunaan bot.

---

## Contoh Penggunaan Chat

- **Materi Kuliah**: *"Jelaskan tentang cara kerja Bubble Sort dan visualisasinya!"*
- **Math**: *"Bantu aku mengintegralkan 2x^2 + 5x"*
- **Self-Learning Memory**: *"Nama panggilan saya Anton, saya mahasiswa Informatika semester 4"* (Bot akan otomatis menyimpan info ini dan menggunakannya saat merespon obrolan berikutnya).
- **Code Debugging (Coder Mode)**: *"Kenapa kode python ini error: IndexError: list index out of range?"*
