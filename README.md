# Bot Discord Kurator Lomba & Beasiswa Mahasiswa 🎓🏆

Bot Discord otomatis yang memantau, menyaring (*filter*), dan mengumpulkan info **lomba tingkat mahasiswa** dan **beasiswa aktif** dari berbagai sumber web terverifikasi dan media sosial, lalu mengirimkannya via *Slash Commands* dan auto-broadcast.

---

## 🌟 Fitur Unggulan
1. **Multi-Source Scraping**:
   - Portal Kemahasiswaan Kampus Terakreditasi Unggul (UI, UGM, dsb).
   - Portal Beasiswa Nasional (IndBeasiswa, BeasiswaID).
   - Akun Media Sosial Publik Terkurasi (Instagram & TikTok) dengan proteksi fallback anti-ban.
2. **Deduplikasi Cerdas**: Menggunakan SHA-256 hash berbasis judul dan URL pendaftaran untuk mencegah duplikasi notifikasi.
3. **Data Normalizer & Kategori**:
   - Ekstraksi otomatis tanggal deadline pendaftaran (format teks Indonesia & numerik).
   - Klasifikasi otomatis bidang: `IT & Coding`, `Business & Case`, `Karya Tulis & Riset`, `Desain & Kreatif`, `Debat & Pidato`, `Beasiswa Penuh`, dll.
4. **Rich Embeds Discord**: Tampilan embed yang rapi, lengkap dengan nama penyelenggara, deadline, tag kategori, thumbnail, dan link resmi pendaftaran.
5. **Background Scheduler**: Loop otomatis yang memeriksa update secara berkala tanpa membebani server Discord.

---

## 📁 Struktur Proyek
```
bot dc/
├── .env.example              # Template token & konfigurasi bot
├── main.py                   # Titik masuk utama Discord Bot
├── test_bot.py               # Unit test dan scraper verification suite
├── config/
│   └── settings.py           # Manajemen konfigurasi environment
├── database/
│   ├── models.py             # Schema data Pydantic (OpportunityItem)
│   └── db_manager.py         # SQLite manager dengan auto-indexing & deduplikasi
├── scrapers/
│   ├── base_scraper.py       # Kelas abstrak async scraper dengan httpx
│   ├── kemahasiswaan_scraper.py # Scraper portal kampus UI & Ditmawa UGM
│   ├── indbeasiswa_scraper.py   # Scraper portal beasiswa terverifikasi
│   ├── instagram_scraper.py     # Scraper akun sosmed dengan fallback multi-mirror
│   └── scraper_manager.py       # Manajer orkestrasi paralel untuk semua scraper
├── cogs/
│   ├── opportunities.py      # Slash Commands (/lomba, /beasiswa, /setchannel)
│   └── scheduler.py          # Background auto-scraping & auto-broadcast
└── utils/
    ├── normalizer.py         # Regex deadline extractor & tag classifier
    └── embeds.py             # Formatter Discord Embed interaktif
```

---

## 🚀 Cara Menjalankan Bot

### 1. Masuk ke Virtual Environment
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2. Atur Token Bot Discord
1. Salin `.env.example` menjadi `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Buka file `.env` dan isi token bot Anda dari [Discord Developer Portal](https://discord.com/developers/applications):
   ```env
   DISCORD_TOKEN=OTk5...
   # Opsional: masukkan Server ID untuk update instan Slash Command
   GUILD_ID=123456789012345678
   ```

### 3. Jalankan Pengujian Sistem
Untuk memverifikasi semua parser, database, dan scraping jaringan:
```powershell
python test_bot.py
```

### 4. Nyalakan Bot
```powershell
python main.py
```

---

## 💬 Daftar Slash Commands

| Perintah | Deskripsi |
|---|---|
| `/lomba [keyword] [jumlah]` | Mencari informasi kompetisi aktif (contoh: `/lomba keyword:coding jumlah:5`) |
| `/beasiswa [keyword] [jumlah]` | Mencari beasiswa aktif (contoh: `/beasiswa keyword:s1 jumlah:3`) |
| `/setchannel [channel_lomba] [channel_beasiswa]` | *(Admin)* Mengatur channel Discord untuk broadcast berkala |
