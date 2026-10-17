import asyncio
import os
import sys

# Mengatasi encoding cp1252 pada terminal Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')

# Tambahkan direktori root ke sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db_manager import DatabaseManager
from scrapers.indbeasiswa_scraper import IndBeasiswaScraper
from scrapers.kemahasiswaan_scraper import KemahasiswaanScraper
from utils.normalizer import DataNormalizer
from database.models import OpportunityItem

TEST_DB_FILE = "unit_test_bot.sqlite"

async def test_normalizer():
    print("--- [1] Menguji Data Normalizer ---")
    test_caption = "Pendaftaran Lomba Hackathon AI dibuka s.d 28 November 2026. Hadiah puluhan juta rupiah!"
    deadline = DataNormalizer.extract_deadline(test_caption)
    tags = DataNormalizer.classify_tags(test_caption)
    print(f"Hasil Ekstraksi Deadline: {deadline}")
    print(f"Hasil Klasifikasi Tags: {tags}")
    assert deadline == "2026-11-28", "Deadline tidak cocok!"
    assert "IT & Coding" in tags, "Tag IT & Coding tidak terdeteksi!"
    print(">> Normalizer OK!")

async def test_database():
    print("\n--- [2] Menguji Database & Deduplikasi ---")
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    db = DatabaseManager(db_path=TEST_DB_FILE)

    item1 = OpportunityItem(
        title="Lomba Hackathon Mahasiswa Nasional 2026",
        category="Lomba",
        tags=["IT & Coding"],
        organizer="Kemdikbud",
        description="Kompetisi membuat solusi berbasis AI",
        url="https://example.com/hackathon-2026",
        deadline="2026-11-28",
        source="Test Source"
    )

    # Tambah pertama kali -> Harus Berhasil (True)
    is_new, item_id = db.add_opportunity(item1)
    print(f"Tambah Item 1: is_new={is_new}, id={item_id}")
    assert is_new is True, "Item 1 harus baru!"

    # Tambah kedua kali item yang sama -> Harus Terdeteksi Duplikat (False)
    is_new2, _ = db.add_opportunity(item1)
    print(f"Tambah Item 1 lagi (duplikat): is_new={is_new2}")
    assert is_new2 is False, "Item duplikat harus ditolak!"

    # Uji Pencarian
    results = db.search_opportunities(category="Lomba", keyword="hackathon")
    print(f"Hasil Pencarian 'hackathon': {len(results)} item ditemukan")
    assert len(results) >= 1, "Pencarian harus menemukan minimal 1 item!"
    print(">> Database & Deduplikasi OK!")

async def test_scrapers():
    print("\n--- [3] Menguji Network Scraping Live (IndBeasiswa & Kemahasiswaan) ---")
    ind_scraper = IndBeasiswaScraper()
    items_ind = await ind_scraper.scrape()
    print(f"IndBeasiswa Scraper menghasilkan {len(items_ind)} item.")
    assert len(items_ind) > 0, "IndBeasiswa harus menghasilkan data!"

    kema_scraper = KemahasiswaanScraper()
    items_kema = await kema_scraper.scrape()
    print(f"Kemahasiswaan Kampus Scraper menghasilkan {len(items_kema)} item.")
    assert len(items_kema) > 0, "Kemahasiswaan harus menghasilkan data!"

    first = items_ind[0]
    print(f"\n[Sampel Beasiswa]: {first.title}")
    print(f"URL: {first.url}")
    print(f"Tags: {first.tags}")
    print(f"Deadline: {first.deadline}")
    print(">> Live Scraping Selesai & Berhasil!")

async def main():
    await test_normalizer()
    await test_database()
    await test_scrapers()
    print("\n[SUCCESS] SEMUA PENGUJIAN OTOMATIS SUKSES TANPA ERROR!")

if __name__ == "__main__":
    asyncio.run(main())
