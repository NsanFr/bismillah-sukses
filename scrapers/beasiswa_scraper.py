import logging
from bs4 import BeautifulSoup
from typing import List
from scrapers.base_scraper import BaseScraper
from database.models import OpportunityItem
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

class BeasiswaIdScraper(BaseScraper):
    """
    Scraper portal beasiswa terverifikasi: Beasiswa.id
    Menyediakan info beasiswa S1/D4 mahasiswa aktif dan kuliah gratis.
    """

    def __init__(self):
        super().__init__(name="BeasiswaID")
        self.target_url = "https://beasiswa.id/category/beasiswa-s1/"

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        html = await self.fetch_html(self.target_url)
        if not html:
            logger.warning(f"[{self.name}] Gagal mengambil halaman Beasiswa.id.")
            return items

        try:
            soup = BeautifulSoup(html, "html.parser")
            articles = soup.select("article, .post, .entry, .type-post")

            for art in articles:
                title_elem = art.select_one("h2, h3, .entry-title")
                link_elem = art.select_one("a[href]")
                desc_elem = art.select_one(".entry-summary, .entry-content, p")
                img_elem = art.select_one("img[src]")

                if not title_elem or not link_elem:
                    continue

                title = DataNormalizer.clean_text(title_elem.get_text())
                url = link_elem.get("href", "").strip()
                if not url.startswith("http"):
                    continue

                raw_desc = desc_elem.get_text() if desc_elem else ""
                desc = DataNormalizer.clean_text(raw_desc)
                full_text = f"{title} {desc}"

                deadline = DataNormalizer.extract_deadline(full_text)
                tags = DataNormalizer.classify_tags(full_text)
                if "Beasiswa Penuh" not in tags and "Beasiswa Parsial" not in tags:
                    tags.append("Beasiswa Mahasiswa")

                image_url = img_elem.get("src") if img_elem else None

                item = OpportunityItem(
                    title=title,
                    category="Beasiswa",
                    tags=tags,
                    organizer="Penyelenggara Beasiswa Mitra",
                    description=desc[:300] if desc else "Informasi beasiswa kuliah untuk mahasiswa aktif dan lulusan.",
                    url=url,
                    deadline=deadline,
                    source=self.name,
                    image_url=image_url
                )
                items.append(item)

        except Exception as e:
            logger.error(f"[{self.name}] Error saat parsing BeasiswaID: {e}", exc_info=True)

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} beasiswa.")
        return items
