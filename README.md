# Bot Discord Kurator Lomba & Beasiswa Mahasiswa 🎓🏆

Bot Discord otomatis yang memantau, menyaring (*filter*), dan mengumpulkan info **lomba tingkat mahasiswa** dan **beasiswa aktif** dari berbagai sumber web terverifikasi dan media sosial, lalu mengirimkannya via *Slash Commands* dan auto-broadcast.

---

## 🌟 Fitur Unggulan

1. **Multi-Source Scraping Tangguh (Multi-Kampus & Nasional)**:
   - **Multi-Campus Network**: Menyaring pengumuman prestasi, kompetisi, dan beasiswa resmi dari **Universitas Indonesia (UI)**, **Universitas Gadjah Mada (UGM)**, dan **Universitas Diponegoro (UNDIP)** (>55+ item aktif).
   - **Pusat Prestasi Nasional (BPTI Kemendikdasmen)**: Mengambil data ajang kompetisi resmi mahasiswa nasional (GEMASTIK, PKM/PIMNAS, LIDM, PILMAPRES, SATRIA DATA, ONMIPA, KRI, KRTI, KMHE, dsb) dengan katalog kurasi resmi.
   - **IndBeasiswa Scraper**: Ekstraksi kartu beasiswa terstruktur (`.beasiswa-card`) dengan dukungan stealth Cloudflare bypass.
   - **Instagram Scraping (instagrapi)**: Pengambilan media postingan Instagram dengan session persistence dan fallback aman.
2. **Interactive UI Pagination**:
   - Tampilan `/lomba`, `/beasiswa`, dan `/deadline` menggunakan **Discord UI Buttons** (`◀ Sebelumnya`, `Halaman X/Y`, `Berikutnya ▶`, dan tombol tautan eksternal `🔗 Buka Link Resmi`).
   - Rapi, modern, dan sangat nyaman diakses dari layar handphone (mobile-friendly).
3. **Fitur Khusus `/deadline` (Info Mendesak)**:
   - Menampilkan peluang lomba dan beasiswa yang **akan segera ditutup dalam waktu dekat** (misal 7 atau 14 hari ke depan), diurutkan dari yang paling mendesak.
4. **Deduplikasi & Auto-Pruning Cerdas**:
   - SHA-256 hash berbasis judul dan URL pendaftaran untuk mencegah duplikasi notifikasi.
   - **Auto-Prune**: Secara otomatis menonaktifkan (`is_active = 0`) peluang yang tanggal batas akhirnya telah terlewati.
   - Klasifikasi otomatis bidang: `IT & Coding`, `Business & Case`, `Karya Tulis & Riset`, `Desain & Kreatif`, `Debat & Pidato`, `Beasiswa Mahasiswa`, dll.
5. **Background Scheduler & Role Mention**:
   - Loop otomatis yang memeriksa update secara berkala (`SCRAPE_INTERVAL_MINUTES`).
   - Mendukung mention role otomatis (`role_notifikasi`) pada broadcast info baru.
   - Fitur admin: `/forcescrape`, `/testbroadcast`, `/channelinfo`, dan `/botstatus`.

---

## 📁 Struktur Proyek
```
colabboration-project/
├── .env.example              # Template token & konfigurasi bot
├── main.py                   # Titik masuk utama Discord Bot
├── test_bot.py               # Unit test dan scraper verification suite
├── requirements.txt          # Daftar dependencies proyek (hemat disk ~30MB)
├── config/
│   └── settings.py           # Manajemen konfigurasi environment
├── database/
│   ├── models.py             # Schema data Pydantic (OpportunityItem)
│   └── db_manager.py         # SQLite manager dengan auto-indexing & deduplikasi
├── scrapers/
│   ├── base_scraper.py       # Kelas dasar scraper dengan HTMLAdaptor ringan
│   ├── kemahasiswaan_scraper.py # Scraper multi-kampus (UI, UGM, UNDIP)
│   ├── indbeasiswa_scraper.py   # Scraper IndBeasiswa (.beasiswa-card)
│   ├── puspresnas_scraper.py    # Scraper BPTI / Puspresnas Kemendikdasmen
│   ├── instagram_scraper.py     # Scraper akun IG berbasis instagrapi
│   └── scraper_manager.py       # Manajer orkestrasi paralel untuk semua scraper
├── cogs/
│   ├── opportunities.py      # Slash Commands (/lomba, /beasiswa, /deadline, /setchannel, /channelinfo)
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
| `/lomba [keyword] [bidang] [jumlah]` | Semua User | Mencari informasi kompetisi aktif dengan filter bidang (IT, Bisnis, Karya Tulis, Desain, Debat) |
| `/beasiswa [keyword] [jumlah]` | Semua User | Mencari beasiswa aktif (contoh: `/beasiswa keyword:baznas jumlah:5`) |
| `/deadline [hari] [kategori]` | Semua User | Melihat lomba dan beasiswa yang akan ditutup dalam waktu dekat (misal 7 atau 14 hari ke depan) |
| `/setchannel [channel_lomba] [channel_beasiswa] [role_notifikasi]` | Administrator | Mengatur channel broadcast otomatis dan role yang dimention (dilengkapi validasi permission bot) |
| `/channelinfo` | Semua User | Melihat channel broadcast aktif dan role notifikasi di server saat ini |
| `/forcescrape` | Administrator | Menjalankan scraping segera tanpa menunggu timer dan langsung menyiarkan item baru |
| `/testbroadcast [kategori]` | Administrator | Mengirim sampel broadcast untuk menguji tampilan embed dan permission channel |
| `/botstatus` | Semua User | Menampilkan statistik database, waktu scraping terakhir, latensi, dan uptime bot |
