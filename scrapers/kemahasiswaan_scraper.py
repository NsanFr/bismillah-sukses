import logging
import re
from bs4 import BeautifulSoup
from typing import List
from scrapers.base_scraper import BaseScraper
from database.models import OpportunityItem
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

class KemahasiswaanScraper(BaseScraper):
    """
    Scraper portal kemahasiswaan universitas terakreditasi unggul (UI & UGM).
    Menyediakan info lomba/prestasi dan beasiswa resmi tingkat mahasiswa aktif.
    """

    def __init__(self):
        super().__init__(name="Portal Kemahasiswaan Kampus")
        self.sources = [
            {"url": "https://kemahasiswaan.ui.ac.id/category/prestasi/", "category": "Lomba", "organizer": "Kemahasiswaan UI"},
            {"url": "https://kemahasiswaan.ui.ac.id/category/beasiswa/", "category": "Beasiswa", "organizer": "Mitra Beasiswa UI"},
            {"url": "https://ditmawa.ugm.ac.id/category/prestasi/info-lomba/", "category": "Lomba", "organizer": "Ditmawa UGM"},
            {"url": "https://ditmawa.ugm.ac.id/category/beasiswa/", "category": "Beasiswa", "organizer": "Mitra Ditmawa UGM"},
        ]

    async def scrape_source(self, target: dict) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        html = await self.fetch_html(target["url"])
        if not html:
            return items

        try:
            soup = BeautifulSoup(html, "html.parser")
            headings = soup.find_all(["h2", "h3"])

            for h in headings:
                a_tag = h.find("a")
                if not a_tag:
                    continue

                title = DataNormalizer.clean_text(a_tag.get_text())
                href = a_tag.get("href", "").strip()

                if not title or len(title) < 10 or not href.startswith("http"):
                    continue

                # Ambil paragraf setelah heading jika ada
                desc = ""
                parent = h.parent
                if parent:
                    p_tag = parent.find("p")
                    if p_tag:
                        desc = DataNormalizer.clean_text(p_tag.get_text())

                full_text = f"{title} {desc}"
                deadline = DataNormalizer.extract_deadline(full_text)
                tags = DataNormalizer.classify_tags(full_text)

                item = OpportunityItem(
                    title=title,
                    category=target["category"],
                    tags=tags,
                    organizer=target["organizer"],
                    description=desc[:300] if desc else f"Pengumuman resmi {target['category']} mahasiswa.",
                    url=href,
                    deadline=deadline,
                    source=f"{self.name} ({target['organizer']})"
                )
                items.append(item)

        except Exception as e:
            logger.error(f"[{self.name}] Error scraping {target['url']}: {e}")

        return items

    async def scrape(self) -> List[OpportunityItem]:
        all_items: List[OpportunityItem] = []
        for target in self.sources:
            try:
                res = await self.scrape_source(target)
                all_items.extend(res)
            except Exception as e:
                logger.error(f"[{self.name}] Gagal mengekstrak dari {target['url']}: {e}")

        logger.info(f"[{self.name}] Berhasil mengekstrak total {len(all_items)} peluang lomba & beasiswa.")
        return all_items
