# Project Structure

## app/ai

Tempat semua logika AI.

- `parser.py`: mengubah pesan bebas user menjadi JSON intent.
- `prompts.py`: system prompt AI.
- `memory.py`: menyimpan dan membaca memory/preferensi user.

## app/bot

Tempat handler Telegram.

- `handlers.py`: command `/start`, `/today`, `/week`, dan handler pesan bebas.
- `keyboards.py`: tombol reply keyboard.
- `messages.py`: teks default.

## app/database

Tempat database.

- `models.py`: tabel SQLAlchemy.
- `repository.py`: fungsi CRUD.
- `session.py`: koneksi database.

## app/scheduler

Tempat sistem reminder otomatis.

- `reminder_jobs.py`: cek reminder jatuh tempo dan kirim pesan.

## app/utils

Helper kecil seperti datetime dan text normalization.

## docs

Dokumentasi schema, command, dan struktur project.

## tests

Tempat unit test.
