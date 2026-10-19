import logging
from typing import List

from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class IndBeasiswaScraper(BaseScraper):
    """
    Scraper untuk portal beasiswa terverifikasi: IndBeasiswa.com
    Menggunakan Scrapling StealthyFetcher untuk menembus proteksi Cloudflare anti-bot.
    """

    def __init__(self):
        super().__init__(name="IndBeasiswa", timeout=25.0)
        self.target_url = "https://indbeasiswa.com/"

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        adaptor = await self.fetch_adaptor(
            self.target_url,
            stealth=True,
            solve_cloudflare=True,
            wait_ms=5000,
        )

        if adaptor is None:
            logger.warning(f"[{self.name}] Gagal mengambil halaman {self.target_url}")
            return items

        try:
            # 1. Coba deteksi kartu khusus beasiswa (.beasiswa-card)
            cards = adaptor.css(".beasiswa-card")

            if cards:
                for card in cards:
                    title_elem = card.css(".beasiswa-title")
                    link_elem = card.css("a.beasiswa-detail, a")

                    if not title_elem or not link_elem:
                        continue

                    title = DataNormalizer.clean_text(title_elem[0].text or "")
                    if not title or len(title) < 5:
                        continue

                    url = (link_elem[0].attrib.get("href") or "").strip()
                    if not url.startswith("http"):
                        continue

                    # Deadline bisa langsung dari data attribute atau text
                    status_div = card.css(".beasiswa-status")
                    deadline = None
                    if status_div and "data-deadline-date" in status_div[0].attrib:
                        raw_date = status_div[0].attrib.get("data-deadline-date")
                        deadline = DataNormalizer.extract_deadline(raw_date or "")

                    if not deadline:
                        deadline_elem = card.css(".beasiswa-deadline")
                        dl_text = deadline_elem[0].text if deadline_elem else ""
                        deadline = DataNormalizer.extract_deadline(dl_text)

                    # Penyelenggara & Jenjang
                    org_elem = card.css(".beasiswa-penyelenggara")
                    org_text = DataNormalizer.clean_text(org_elem[0].text or "") if org_elem else "IndBeasiswa"
                    org_clean = org_text.replace("🏫", "").strip() or "IndBeasiswa"

                    jenjang_elem = card.css(".beasiswa-jenjang")
                    jenjang_text = DataNormalizer.clean_text(jenjang_elem[0].text or "") if jenjang_elem else ""

                    lokasi_elem = card.css(".beasiswa-lokasi")
                    lokasi_text = DataNormalizer.clean_text(lokasi_elem[0].text or "") if lokasi_elem else ""

                    desc_parts = [p for p in [org_clean, jenjang_text, lokasi_text] if p]
                    desc = " | ".join(desc_parts) if desc_parts else "Informasi beasiswa kuliah resmi untuk pelajar dan mahasiswa."

                    # Gambar jika ada
                    img_elem = card.css("img")
                    img_url = img_elem[0].attrib.get("src") if img_elem else None

                    full_text = f"{title} {desc}"
                    tags = DataNormalizer.classify_tags(full_text)
                    if "Beasiswa Penuh" not in tags and "Beasiswa Parsial" not in tags:
                        tags.append("Beasiswa Mahasiswa")

                    item = OpportunityItem(
                        title=title,
                        category="Beasiswa",
                        tags=tags,
                        organizer=org_clean,
                        description=desc[:300],
                        url=url,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

            # 2. Fallback jika format artikel standar WordPress
            if not items:
                posts = adaptor.css("article, .post, .entry")
                for post in posts:
                    title_elem = post.css("h2 a, h3 a, .entry-title a")
                    if not title_elem:
                        continue

                    title = DataNormalizer.clean_text(title_elem[0].text or "")
                    if not title or len(title) < 5 or "cari beasiswa" in title.lower():
                        continue

                    url = (title_elem[0].attrib.get("href") or "").strip()
                    if not url.startswith("http"):
                        continue

                    desc_elem = post.css(".entry-summary, p")
                    raw_desc = desc_elem[0].text if desc_elem else ""
                    desc = DataNormalizer.clean_text(raw_desc)

                    img_elem = post.css("img")
                    img_url = img_elem[0].attrib.get("src") if img_elem else None

                    full_text = f"{title} {desc}"
                    deadline = DataNormalizer.extract_deadline(full_text)
                    tags = DataNormalizer.classify_tags(full_text)
                    if "Beasiswa Penuh" not in tags and "Beasiswa Parsial" not in tags:
                        tags.append("Beasiswa Mahasiswa")

                    item = OpportunityItem(
                        title=title,
                        category="Beasiswa",
                        tags=tags,
                        organizer="Mitra IndBeasiswa",
                        description=desc[:300] if desc else "Informasi beasiswa kuliah resmi untuk mahasiswa.",
                        url=url,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

        except Exception as e:
            logger.error(f"[{self.name}] Error saat parsing IndBeasiswa: {e}", exc_info=True)

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} beasiswa.")
        return items
