import asyncio
import logging
from typing import List
from database.models import OpportunityItem
from database.db_manager import DatabaseManager
from scrapers.indbeasiswa_scraper import IndBeasiswaScraper
from scrapers.kemahasiswaan_scraper import KemahasiswaanScraper
from scrapers.instagram_scraper import InstagramPublicScraper

logger = logging.getLogger(__name__)

class ScraperManager:
    """Mengelola dan menjalankan semua modul scraper secara bersamaan (concurrent)."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.scrapers = [
            IndBeasiswaScraper(),
            KemahasiswaanScraper(),
            InstagramPublicScraper()
        ]

    async def run_all(self) -> List[OpportunityItem]:
        """
        Menjalankan seluruh scraper, menyaring duplikasi ke database,
        dan mengembalikan daftar item BARU yang belum pernah dibroadcast.
        """
        logger.info("Memulai proses scraping dari seluruh sumber...")
        tasks = [scraper.scrape() for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        newly_discovered_items: List[OpportunityItem] = []

        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Scraper task menghasilkan error: {res}")
                continue
            if not isinstance(res, list):
                continue

            for item in res:
                # Masukkan ke database, jika baru (belum duplikat) maka simpan ke daftar broadcast
                is_new, item_id = self.db.add_opportunity(item)
                if is_new:
                    logger.info(f"[NEW ITEM DETECTED] ({item.category}) {item.title}")
                    newly_discovered_items.append(item)

        logger.info(f"Selesai! Ditemukan {len(newly_discovered_items)} item baru.")
        return newly_discovered_items
