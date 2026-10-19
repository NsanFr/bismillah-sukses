import logging
from typing import List

from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class PuspresnasScraper(BaseScraper):
    """
    Scraper untuk Balai Pengembangan Talenta Indonesia (BPTI) / Pusat Prestasi Nasional (Puspresnas)
    Kementerian Pendidikan Dasar dan Menengah RI / Kemendikbudristek.
    Menyediakan kompetisi resmi nasional: GEMASTIK, PKM/PIMNAS, LIDM, PILMAPRES, SATRIA DATA, dll.
    """

    def __init__(self):
        super().__init__(name="BPTI / Puspresnas Kemendikdasmen", timeout=25.0)
        self.target_urls = [
            "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
            "https://bpti.kemendikdasmen.go.id/",
        ]

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        seen_titles = set()

        for url in self.target_urls:
            try:
                adaptor = await self.fetch_adaptor(
                    url,
                    stealth=True,
                    solve_cloudflare=True,
                    wait_ms=4000,
                )

                if adaptor is None:
                    continue

                # 1. Ekstraksi dari Accordion/Toggle Ajang Talenta
                toggle_items = adaptor.css(".elementor-toggle-item, .elementor-accordion-item")
                for it in toggle_items:
                    a_elem = it.css("a.elementor-toggle-title, a.elementor-accordion-title")
                    if not a_elem:
                        continue

                    title = DataNormalizer.clean_text(a_elem[0].text or a_elem[0].get() or "")
                    if not title or len(title) < 5 or title.lower() in seen_titles:
                        continue

                    seen_titles.add(title.lower())

                    content_elem = it.css(".elementor-tab-content")
                    desc = ""
                    if content_elem:
                        desc = DataNormalizer.clean_text(content_elem[0].get())

                    links = content_elem[0].css("a") if content_elem else []
                    item_url = url
                    for l in links:
                        raw_href = (l.attrib.get("href") or "").strip()
                        if raw_href and raw_href.startswith("http") and not raw_href.startswith("javascript"):
                            item_url = raw_href
                            break

                    full_text = f"{title} {desc}"
                    tags = DataNormalizer.classify_tags(full_text)
                    if not tags or tags == ["Umum"]:
                        tags = ["Kompetisi Nasional", "Ajang Talenta"]
                    deadline = DataNormalizer.extract_deadline(full_text)

                    imgs = content_elem[0].css("img") if content_elem else []
                    img_url = imgs[0].attrib.get("src") if imgs else None

                    item = OpportunityItem(
                        title=title,
                        category="Lomba",
                        tags=tags,
                        organizer="BPTI Kemendikdasmen / Puspresnas",
                        description=desc[:300] if desc else "Ajang talenta dan kompetisi resmi nasional mahasiswa BPTI Kemendikdasmen.",
                        url=item_url,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

                # 2. Ekstraksi kartu pengumuman / artikel berita resmi jika ada
                cards = adaptor.css(".card, .post, article, .elementor-post")
                for card in cards:
                    title_elem = card.css("h2 a, h3 a, h4 a, .elementor-post__title a")
                    if not title_elem:
                        continue

                    title = DataNormalizer.clean_text(title_elem[0].text or "")
                    if not title or len(title) < 8 or title.lower() in seen_titles:
                        continue

                    seen_titles.add(title.lower())

                    href = (title_elem[0].attrib.get("href") or "").strip()
                    if not href.startswith("http"):
                        continue

                    desc_elem = card.css(".elementor-post__excerpt, .card-text, p")
                    raw_desc = desc_elem[0].text if desc_elem else ""
                    desc = DataNormalizer.clean_text(raw_desc)

                    img_elem = card.css("img")
                    img_url = img_elem[0].attrib.get("src") if img_elem else None

                    full_text = f"{title} {desc}"
                    deadline = DataNormalizer.extract_deadline(full_text)
                    tags = DataNormalizer.classify_tags(full_text)
                    if not tags:
                        tags = ["Kompetisi Nasional", "Prestasi"]

                    item = OpportunityItem(
                        title=title,
                        category="Lomba",
                        tags=tags,
                        organizer="BPTI Kemendikdasmen",
                        description=desc[:300] if desc else "Pengumuman kegiatan kompetisi BPTI Kemendikdasmen.",
                        url=href,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

                # Jika sudah berhasil mendapatkan items dari halaman ajang-talenta, tidak perlu spam halaman lainnya
                if len(items) >= 10:
                    break

            except Exception as e:
                logger.error(f"[{self.name}] Error scraping URL {url}: {e}", exc_info=True)

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} kompetisi resmi.")
        return items
