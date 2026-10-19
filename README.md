# Bot Discord Kurator Lomba & Beasiswa Mahasiswa 🎓🏆

Bot Discord otomatis yang memantau, menyaring (*filter*), dan mengumpulkan info **lomba tingkat mahasiswa** dan **beasiswa aktif** dari berbagai sumber web terverifikasi dan media sosial, lalu mengirimkannya via *Slash Commands* dan auto-broadcast.

---

## 🌟 Fitur Unggulan

1. **Next-Gen Web Scraping (Scrapling & Stealth Engine)**:
   - **Bypass Proteksi Cloudflare**: Didukung engine browser Scrapling StealthyFetcher yang mampu menembus interstitial anti-bot/anti-DDoS seperti pada `indbeasiswa.com`.
   - **Pusat Prestasi Nasional (BPTI Kemendikdasmen)**: Mengambil data kompetisi resmi mahasiswa nasional (GEMASTIK, PKM, LIDM, PILMAPRES, SATRIA DATA, dsb) dari `bpti.kemendikdasmen.go.id`.
   - **Portal Kampus Terakreditasi Unggul**: Menyaring pengumuman prestasi dan beasiswa dari UI & Ditmawa UGM.
   - **Instagram Scraping (instagrapi)**: Pengambilan media postingan Instagram dengan session persistence, cookie auth, dan fallback anonymous yang aman.
2. **Deduplikasi Cerdas**: Menggunakan SHA-256 hash berbasis judul dan URL pendaftaran untuk mencegah duplikasi notifikasi.
3. **Data Normalizer & Auto-Pruning**:
   - Ekstraksi otomatis tanggal deadline pendaftaran (format ISO `YYYY-MM-DD`, `DD/MM/YYYY`, dan teks Indonesia).
   - **Auto-Prune**: Secara otomatis menonaktifkan (`is_active = 0`) peluang yang deadlinenya telah terlewati.
   - Klasifikasi otomatis bidang: `IT & Coding`, `Business & Case`, `Karya Tulis & Riset`, `Desain & Kreatif`, `Debat & Pidato`, `Beasiswa Penuh`, dll.
4. **Rich Embeds Discord & Role Mention**:
   - Tampilan embed yang rapi, lengkap dengan nama penyelenggara, deadline, tag kategori, thumbnail, dan link resmi.
   - Mendukung mention role otomatis (`role_notifikasi`) pada broadcast info baru.
5. **Background Scheduler & Admin Tools**:
   - Loop otomatis yang memeriksa update secara berkala (`SCRAPE_INTERVAL_MINUTES`).
   - Fitur admin: `/forcescrape`, `/testbroadcast`, `/channelinfo`, dan `/botstatus`.

---

## 📁 Struktur Proyek
```
colabboration-project/
├── .env.example              # Template token & konfigurasi bot
├── main.py                   # Titik masuk utama Discord Bot
├── test_bot.py               # Unit test dan scraper verification suite
├── requirements.txt          # Daftar dependencies proyek
├── config/
│   └── settings.py           # Manajemen konfigurasi environment
├── database/
│   ├── models.py             # Schema data Pydantic (OpportunityItem)
│   └── db_manager.py         # SQLite manager dengan auto-indexing & deduplikasi
├── scrapers/
│   ├── base_scraper.py       # Kelas dasar scraper berbasis Scrapling & httpx
│   ├── kemahasiswaan_scraper.py # Scraper portal kampus UI & Ditmawa UGM
│   ├── indbeasiswa_scraper.py   # Scraper IndBeasiswa (Cloudflare bypass)
│   ├── puspresnas_scraper.py    # Scraper ajang talenta BPTI Kemendikdasmen
│   ├── instagram_scraper.py     # Scraper akun IG berbasis instagrapi
│   └── scraper_manager.py       # Manajer orkestrasi paralel untuk semua scraper
├── cogs/
│   ├── opportunities.py      # Slash Commands (/lomba, /beasiswa, /setchannel, /channelinfo)
│   └── scheduler.py          # Background scheduler, auto-broadcast, /forcescrape, /testbroadcast, /botstatus
└── utils/
    ├── normalizer.py         # Regex deadline extractor & tag classifier
    └── embeds.py             # Formatter Discord Embed interaktif
```

---

## 🚀 Cara Menjalankan Bot

### 1. Instalasi Dependencies
```bash
pip install -r requirements.txt
```

### 2. Atur Token Bot Discord & Konfigurasi
1. Salin `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
2. Buka file `.env` dan isi token bot Anda dari [Discord Developer Portal](https://discord.com/developers/applications):
   ```env
   DISCORD_TOKEN=your_token_here
   # Opsional: masukkan Server ID untuk sinkronisasi instan Slash Command
   GUILD_ID=123456789012345678

   # Opsional: Kredensial akun Instagram untuk instagrapi
   IG_USERNAME=
   IG_PASSWORD=
   IG_SESSION_ID=
   ```

### 3. Jalankan Pengujian Sistem
Untuk memverifikasi parser, database, slash commands mock, dan scraping live:
```bash
python test_bot.py
```

### 4. Nyalakan Bot
```bash
python main.py
```

---

## 💬 Daftar Slash Commands

| Perintah | Hak Akses | Deskripsi |
|---|---|---|
| `/lomba [keyword] [jumlah]` | Semua User | Mencari informasi kompetisi aktif (contoh: `/lomba keyword:coding jumlah:5`) |
| `/beasiswa [keyword] [jumlah]` | Semua User | Mencari beasiswa aktif (contoh: `/beasiswa keyword:s1 jumlah:3`) |
| `/setchannel [channel_lomba] [channel_beasiswa] [role_notifikasi]` | Administrator | Mengatur channel broadcast otomatis dan role yang dimention (dilengkapi validasi permission bot) |
| `/channelinfo` | Semua User | Melihat channel broadcast aktif dan role notifikasi di server saat ini |
| `/forcescrape` | Administrator | Menjalankan scraping segera tanpa menunggu timer dan langsung menyiarkan item baru |
| `/testbroadcast [kategori]` | Administrator | Mengirim sampel broadcast untuk menguji tampilan embed dan permission channel |
| `/botstatus` | Semua User | Menampilkan statistik database, waktu scraping terakhir, latensi, dan uptime bot |
