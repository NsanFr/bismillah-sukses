import html
import logging
import re
from typing import List

from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class InfoLombaScraper(BaseScraper):
    """
    Scraper untuk portal agregator kompetisi nasional: InfoLomba.id (Media Partner Sejak 2015).
    Menyediakan info lomba mahasiswa, siswa, dan umum lengkap dengan poster, tanggal, dan biaya pendaftaran.
    Berjalan cepat dan handal dengan request HTTP ringan tanpa terhalang proteksi Cloudflare.
    """

    def __init__(self):
        super().__init__(name="InfoLomba.id", timeout=15.0)
        self.target_urls = [
            "https://infolomba.id/events",
            "https://infolomba.id/",
        ]

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        seen_titles = set()

        for url in self.target_urls:
            try:
                adaptor = await self.fetch_adaptor(url)
                if adaptor is None:
                    continue

                cards = adaptor.css(".event-container")
                for card in cards:
                    card_html = card.get()

                    # 1. Ekstraksi ID & Slug dari handler onclick loadDetailsEvent
                    match = re.search(
                        r"loadDetailsEvent\((\d+),\s*['\"]([^'\"]+)['\"]",
                        card_html
                    )
                    event_id = match.group(1) if match else None
                    slug = match.group(2) if match else None

                    # 2. Judul Lomba
                    title_elem = card.css(".event-title a, .event-title")
                    if not title_elem:
                        continue

                    raw_title = title_elem[0].text or DataNormalizer.clean_text(title_elem[0].get())
                    title = DataNormalizer.clean_text(html.unescape(raw_title))
                    if not title or len(title) < 5 or title.lower() in seen_titles:
                        continue

                    seen_titles.add(title.lower())

                    # URL permalink resmi kompetisi
                    if slug and event_id:
                        item_url = f"https://infolomba.id/{slug}-{event_id}"
                    else:
                        item_url = "https://infolomba.id/events"

                    # 3. Ekstraksi Detail (Tanggal, Biaya, Lokasi, Target, Penyelenggara)
                    tgl_elem = card.css(".tanggal")
                    tgl_text = DataNormalizer.clean_text(tgl_elem[0].get()) if tgl_elem else ""

                    biaya_elem = card.css(".biaya")
                    biaya_text = DataNormalizer.clean_text(biaya_elem[0].get()) if biaya_elem else ""

                    target_elem = card.css(".target")
                    target_text = DataNormalizer.clean_text(target_elem[0].get()) if target_elem else ""

                    lokasi_elem = card.css(".lokasi")
                    lokasi_text = DataNormalizer.clean_text(lokasi_elem[0].get()) if lokasi_elem else ""

                    penyelenggara_elem = card.css(".penyelenggara div span, .penyelenggara span")
                    penyelenggara = "Penyelenggara Mitra InfoLomba"
                    if penyelenggara_elem:
                        penyelenggara = DataNormalizer.clean_text(penyelenggara_elem[-1].get()) or penyelenggara

                    desc_parts = [
                        f"Penyelenggara: {penyelenggara}",
                        f"Target: {target_text}" if target_text else "",
                        f"Biaya: {biaya_text}" if biaya_text else "",
                        f"Lokasi: {lokasi_text}" if lokasi_text else "",
                        f"Jadwal: {tgl_text}" if tgl_text else "",
                    ]
                    desc = " | ".join([p for p in desc_parts if p])

                    # Deadline pendaftaran
                    deadline = DataNormalizer.extract_deadline(tgl_text)

                    # Klasifikasi Tags
                    tags = DataNormalizer.classify_tags(f"{title} {desc}")
                    if not tags or tags == ["Umum"]:
                        tags = ["Kompetisi Mahasiswa", "Info Lomba"]

                    # Poster Thumbnail
                    img_elem = card.css(".img-container img")
                    img_url = None
                    if img_elem:
                        src = (img_elem[0].attrib.get("src") or "").strip()
                        if src and not src.startswith("http"):
                            img_url = f"https://infolomba.id/{src.lstrip('/')}"
                        elif src:
                            img_url = src

                    item = OpportunityItem(
                        title=title,
                        category="Lomba",
                        tags=tags,
                        organizer=penyelenggara,
                        description=desc[:300],
                        url=item_url,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

            except Exception as e:
                logger.error(f"[{self.name}] Error scraping URL {url}: {e}", exc_info=True)

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} kompetisi.")
        return items
