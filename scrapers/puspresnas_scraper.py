import logging
from bs4 import BeautifulSoup
from typing import List
from scrapers.base_scraper import BaseScraper
from database.models import OpportunityItem
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

class PuspresnasScraper(BaseScraper):
    """
    Scraper untuk Pusat Prestasi Nasional (Puspresnas) Kemendikbudristek RI.
    Sumber kompetisi resmi tingkat mahasiswa (Gemastik, PKM, KNMIPA, LIDM, dll).
    """

    def __init__(self):
        super().__init__(name="Puspresnas Kemendikbud")
        self.target_url = "https://pusatprestasinasional.kemdikbud.go.id/kegiatan"

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        html = await self.fetch_html(self.target_url)
        if not html:
            logger.warning(f"[{self.name}] Tidak ada HTML yang dapat diproses.")
            return items

        try:
            soup = BeautifulSoup(html, "html.parser")
            # Mencari card kegiatan/lomba
            cards = soup.select(".card, .post-item, article, .kegiatan-item")

            for card in cards:
                title_elem = card.select_one("h3, h4, h5, .title, .card-title")
                link_elem = card.select_one("a[href]")
                img_elem = card.select_one("img[src]")
                desc_elem = card.select_one(".description, .card-text, p")

                if not title_elem or not link_elem:
                    continue

                title = DataNormalizer.clean_text(title_elem.get_text())
                raw_href = link_elem.get("href", "").strip()
                if not raw_href.startswith("http"):
                    href = f"https://pusatprestasinasional.kemdikbud.go.id{raw_href}"
                else:
                    href = raw_href

                raw_desc = desc_elem.get_text() if desc_elem else ""
                desc = DataNormalizer.clean_text(raw_desc)
                full_text = f"{title} {desc}"

                # Ekstraksi deadline
                deadline = DataNormalizer.extract_deadline(full_text)
                tags = DataNormalizer.classify_tags(full_text)
                image_url = img_elem.get("src") if img_elem else None

                item = OpportunityItem(
                    title=title,
                    category="Lomba",
                    tags=tags,
                    organizer="Pusat Prestasi Nasional (Puspresnas)",
                    description=desc[:300] if desc else "Informasi kompetisi resmi mahasiswa Kemendikbudristek.",
                    url=href,
                    deadline=deadline,
                    source=self.name,
                    image_url=image_url
                )
                items.append(item)

        except Exception as e:
            logger.error(f"[{self.name}] Error saat parsing data: {e}", exc_info=True)

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} kompetisi.")
        return items
