import logging
from typing import List

from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class KemahasiswaanScraper(BaseScraper):
    """
    Scraper portal kemahasiswaan universitas terakreditasi unggul (UI, UGM, UNDIP).
    Menyediakan info lomba/prestasi dan beasiswa resmi tingkat mahasiswa aktif tanpa proteksi Cloudflare.
    """

    def __init__(self):
        super().__init__(name="Portal Kemahasiswaan Kampus", timeout=15.0)
        self.sources = [
            # Universitas Indonesia (UI)
            {
                "url": "https://kemahasiswaan.ui.ac.id/category/prestasi/",
                "category": "Lomba",
                "organizer": "Kemahasiswaan UI",
            },
            {
                "url": "https://kemahasiswaan.ui.ac.id/category/beasiswa/",
                "category": "Beasiswa",
                "organizer": "Mitra Beasiswa UI",
            },
            {
                "url": "https://kemahasiswaan.ui.ac.id/category/pengumuman/",
                "category": "Beasiswa",
                "organizer": "Kemahasiswaan UI",
            },
            # Universitas Gadjah Mada (UGM)
            {
                "url": "https://ditmawa.ugm.ac.id/category/prestasi/info-lomba/",
                "category": "Lomba",
                "organizer": "Ditmawa UGM",
            },
            {
                "url": "https://ditmawa.ugm.ac.id/category/prestasi/",
                "category": "Lomba",
                "organizer": "Ditmawa UGM",
            },
            {
                "url": "https://ditmawa.ugm.ac.id/category/beasiswa/",
                "category": "Beasiswa",
                "organizer": "Mitra Ditmawa UGM",
            },
            # Universitas Diponegoro (UNDIP)
            {
                "url": "https://kemahasiswaan.undip.ac.id/category/beasiswa/",
                "category": "Beasiswa",
                "organizer": "Ditmawa UNDIP",
            },
            {
                "url": "https://kemahasiswaan.undip.ac.id/kantorprestasi/",
                "category": "Lomba",
                "organizer": "Kantor Prestasi UNDIP",
            },
        ]

    async def scrape_source(self, target: dict) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        adaptor = await self.fetch_adaptor(target["url"])
        if adaptor is None:
            return items

        seen_urls = set()

        try:
            # 1. Pola card/article WordPress (UGM, UNDIP, dsb.)
            articles = adaptor.css("article, .post, .entry")
            if articles:
                for art in articles:
                    title_elem = art.css("h2 a, h3 a, h4 a, .entry-title a")
                    if not title_elem:
                        continue

                    title = DataNormalizer.clean_text(title_elem[0].text or "")
                    href = (title_elem[0].attrib.get("href") or "").strip()

                    if not title or len(title) < 8 or not href.startswith("http") or href in seen_urls:
                        continue

                    seen_urls.add(href)

                    # Deskripsi cuplikan
                    desc_elem = art.css(".entry-summary, p")
                    raw_desc = desc_elem[0].text if desc_elem else ""
                    desc = DataNormalizer.clean_text(raw_desc)

                    # Thumbnail image
                    img_elem = art.css("img")
                    img_url = img_elem[0].attrib.get("src") if img_elem else None

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
                        source=f"{self.name} ({target['organizer']})",
                        image_url=img_url,
                    )
                    items.append(item)

            # 2. Fallback untuk layout heading langsung (UI, dsb.)
            if not items:
                headings = adaptor.css("h2, h3, h4")
                for h in headings:
                    a_elem = h.css("a")
                    if not a_elem:
                        continue

                    title = DataNormalizer.clean_text(a_elem[0].text or "")
                    href = (a_elem[0].attrib.get("href") or "").strip()

                    if not title or len(title) < 8 or not href.startswith("http") or href in seen_urls:
                        continue

                    seen_urls.add(href)

                    full_text = title
                    deadline = DataNormalizer.extract_deadline(full_text)
                    tags = DataNormalizer.classify_tags(full_text)

                    item = OpportunityItem(
                        title=title,
                        category=target["category"],
                        tags=tags,
                        organizer=target["organizer"],
                        description=f"Pengumuman resmi {target['category']} dari {target['organizer']}.",
                        url=href,
                        deadline=deadline,
                        source=f"{self.name} ({target['organizer']})",
                    )
                    items.append(item)

        except Exception as e:
            logger.error(f"[{self.name}] Error scraping {target['url']}: {e}", exc_info=True)

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
