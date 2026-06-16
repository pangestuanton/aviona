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

[Render.com](https://render.com) menawarkan layanan **Web Service** gratis. Bot ini telah dilengkapi dengan dummy HTTP health-check server agar kompatibel dengan port binding Render Free Tier.

### Langkah-langkah:
1. **Buat Akun Render**: Masuk ke Render menggunakan akun GitHub Anda.
2. **Buat Web Service**:
   - Klik **New +** -> **Web Service**.
   - Hubungkan repositori GitHub bot Anda.
3. **Konfigurasi Build & Start Command**:
   - **Name**: `aviona-bot`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run.py`
   - **Instance Type**: `Free`
4. **Tambahkan Environment Variables**:
   - Di bagian **Environment**, tambahkan seluruh variabel dari file `.env`:
     - `TELEGRAM_BOT_TOKEN`
     - `OPENROUTER_API_KEY`
     - `AI_BASE_URL`
     - `AI_MODEL` (set ke `openrouter/free`)
     - `APP_TIMEZONE` (set ke `Asia/Jakarta`)
     - `DATABASE_URL` (jika menggunakan SQLite default: `sqlite:///study_bot.db`)
5. **Database Jangka Panjang & Uptime (Catatan Free Tier)**:
   - **Menjaga Bot Tetap Aktif**: Render Free Tier akan menidurkan (*spin down*) Web Service jika tidak menerima HTTP request selama 15 menit. Agar bot Anda tidak tidur, gunakan layanan ping gratis seperti [UptimeRobot](https://uptimerobot.com) untuk menembak URL Web Service Render Anda (`https://aviona-bot.onrender.com`) setiap 5-10 menit sekali.
   - **Penyimpanan SQLite**: Karena filesystem Render Free Tier bersifat *ephemeral* (kembali ke kondisi awal saat server di-deploy ulang atau restart), data chat history & pengingat lokal SQLite akan terhapus jika terjadi restart. Untuk database persisten gratis, Anda sangat disarankan untuk menggunakan database PostgreSQL eksternal gratis (misalnya dari [Supabase](https://supabase.com) atau [Neon](https://neon.tech)) lalu masukkan URL database eksternal tersebut ke variabel `DATABASE_URL`.

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
