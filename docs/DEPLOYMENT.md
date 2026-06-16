# Panduan Deployment Aviona Learn (Aktif 24/7)

Dokumen ini menjelaskan cara men-deploy bot Telegram **Aviona Learn** ke cloud agar dapat berjalan 24/7 secara gratis atau dengan biaya sangat murah tanpa harus membiarkan laptop Anda menyala terus-menerus.

Karena bot ini memiliki penjadwal (scheduler) pengingat tugas (`APScheduler`) yang berjalan di latar belakang secara berkelanjutan, bot ini harus berjalan sebagai aplikasi Python yang persisten (bukan Serverless Functions seperti Vercel gratisan biasa yang mati secara berkala).

Berikut adalah 3 opsi deployment terbaik:

---

## Opsi 1: Railway (Sangat Direkomendasikan - Paling Mudah)

[Railway.app](https://railway.app) adalah platform cloud modern yang sangat mudah digunakan untuk aplikasi Python persisten.

### Langkah-langkah:
1. **Buat Repositori GitHub**:
   - Unggah seluruh kode project Anda ke repositori GitHub pribadi/publik.
2. **Siapkan Railway Account**:
   - Masuk ke Railway menggunakan akun GitHub Anda.
3. **Tambahkan Start Command**:
   - Railway secara otomatis mendeteksi file `requirements.txt` Anda.
   - Buat file bernama `Procfile` di direktori utama project Anda (opsional, Railway juga membolehkan input custom command di dashboard mereka):
     ```text
     worker: python run.py
     ```
4. **Deploy Baru**:
   - Di dashboard Railway, klik **New Project** -> **Deploy from GitHub repo**.
   - Pilih repositori bot Telegram Anda.
5. **Konfigurasi Environment Variables**:
   - Klik tab **Variables** di panel Railway Anda, lalu tambahkan semua nilai dari file `.env` lokal Anda:
     - `TELEGRAM_BOT_TOKEN`
     - `OPENAI_API_KEY`
     - `AI_BASE_URL`
     - `AI_MODEL`
     - `APP_TIMEZONE` (set ke `Asia/Jakarta`)
     - `DATABASE_URL` (bisa gunakan SQLite default `sqlite:///data/study_bot.db` dengan menambahkan volume persisten di Railway agar database tidak hilang saat deploy ulang, ATAU buat database PostgreSQL gratisan di Railway lalu arahkan `DATABASE_URL` ke database tersebut).
6. **Selesai!** Railway akan men-build dan menjalankan bot Anda di cloud secara otomatis.

---

## Opsi 2: Render (Free Tier - Alternatif Gratis)

[Render.com](https://render.com) menawarkan opsi **Background Worker** gratis yang cocok untuk bot Telegram berbasis polling.

### Langkah-langkah:
1. **Buat Akun Render**: Masuk ke Render menggunakan akun GitHub Anda.
2. **Buat Background Worker**:
   - Klik **New +** -> **Background Worker**.
   - Hubungkan repositori GitHub bot Anda.
3. **Konfigurasi Build & Start Command**:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run.py`
4. **Tambahkan Environment Variables**:
   - Di bagian **Environment**, tambahkan seluruh isi `.env` (Token Telegram, API Key OpenAI, Timezone, dll).
5. **Database Persisten**:
   - Jika menggunakan SQLite default, Anda harus mengaitkan **Render Disk** (volume persisten) ke direktori database Anda agar tugas yang disimpan tidak hilang ketika server ter-restart/redeploy.
   - Caranya: Arahkan `DATABASE_URL` ke `/var/data/study_bot.db` dan pasang (mount) Render Disk di path `/var/data`.

---

## Opsi 3: VPS (Hostinger / DigitalOcean / IDCloudHost - Kontrol Penuh)

Jika Anda memiliki VPS Linux (Ubuntu), ini adalah opsi paling stabil dan murah jika Anda memiliki banyak bot.

### Langkah-langkah:
1. **Hubungkan ke VPS via SSH**:
   ```bash
   ssh root@ip_vps_kamu
   ```
2. **Install Python & Git**:
   ```bash
   sudo apt update
   ```
3. **Kloning Repositori & Install Dependensi**:
   ```bash
   git clone <url_repo_kamu> telebot
   cd telebot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Buat file `.env`**: Buat file `.env` menggunakan `nano .env` dan isi token Anda.
5. **Jalankan Bot dengan Process Manager (PM2 atau Systemd)**:
   Agar bot tidak mati saat koneksi SSH Anda ditutup, gunakan process manager.

   #### Menggunakan Systemd (Rekomendasi Linux):
   Buat file service systemd:
   ```bash
   sudo nano /etc/systemd/system/aviona.service
   ```
   Isi dengan konfigurasi berikut:
   ```ini
   [Unit]
   Description=Aviona Learn Telegram Bot Service
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/telebot
   ExecStart=/root/telebot/.venv/bin/python run.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Aktifkan dan jalankan service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable aviona
   sudo systemctl start aviona
   ```
   Cek status apakah bot sudah aktif berjalan:
   ```bash
   sudo systemctl status aviona
   ```

Sekarang bot Telegram Aviona Learn Anda sudah ter-host secara aman di cloud dan siap melayani Anda 24/7!
