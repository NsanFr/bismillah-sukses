import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from database.models import OpportunityItem
from utils.normalizer import DataNormalizer
from config.settings import TARGET_INSTAGRAM_ACCOUNTS

logger = logging.getLogger(__name__)

class InstagramPublicScraper(BaseScraper):
    """
    Scraper untuk akun Instagram dan media sosial publik terkurasi.
    Menggunakan multi-mirror fallback (Dumpoir, Imginn, Picuki) 
    agar tetap tahan terhadap pemblokiran IP atau rate-limit sewaktu-waktu.
    """

    def __init__(self, target_accounts: Optional[List[str]] = None):
        super().__init__(name="Social Media Scraper")
        self.accounts = target_accounts or TARGET_INSTAGRAM_ACCOUNTS

    async def scrape_account_from_mirror(self, account: str, base_url: str) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        target_url = f"{base_url}{account}"

        html = await self.fetch_html(target_url)
        if not html:
            return items

        soup = BeautifulSoup(html, "html.parser")
        posts = soup.select(".box-photo, .content_item, .launch-wrapper, .item, article")

        for post in posts[:5]:
            caption_elem = post.select_one(".content_item_text, .photo-description, .post-caption, p")
            img_elem = post.select_one("img[src]")
            link_elem = post.select_one("a[href]")

            raw_caption = caption_elem.get_text() if caption_elem else ""
            caption = DataNormalizer.clean_text(raw_caption)
            if not caption or len(caption) < 15:
                continue

            is_beasiswa = bool(re.search(r'\b(beasiswa|scholarship|funding)\b', caption.lower()))
            category = "Beasiswa" if is_beasiswa else "Lomba"

            first_line = caption.split(".")[0].split("\n")[0][:100]
            title = f"[@{account}] {first_line}"

            post_url = link_elem.get("href", "") if link_elem else f"https://instagram.com/{account}"
            if not post_url.startswith("http"):
                post_url = f"https://instagram.com/{account}"

            deadline = DataNormalizer.extract_deadline(caption)
            tags = DataNormalizer.classify_tags(caption)
            image_url = img_elem.get("src") if img_elem else None

            item = OpportunityItem(
                title=title,
                category=category,
                tags=tags,
                organizer=f"Media Sosial @{account}",
                description=caption[:350] + ("..." if len(caption) > 350 else ""),
                url=post_url,
                deadline=deadline,
                source=f"Sosmed (@{account})",
                image_url=image_url
            )
            items.append(item)

        return items

    async def scrape_account(self, account: str) -> List[OpportunityItem]:
        account = account.replace("@", "").strip()
        mirrors = [
            "https://dumpoir.com/v/",
            "https://imginn.com/",
            "https://picuki.com/profile/"
        ]

        for mirror in mirrors:
            try:
                items = await self.scrape_account_from_mirror(account, mirror)
                if items:
                    return items
            except Exception as e:
                logger.debug(f"[{self.name}] Mirror {mirror} gagal: {e}")

        logger.info(f"[{self.name}] Tidak dapat mengambil postingan baru dari @{account} (proteksi anti-bot aktif pada mirror).")
        return []

    async def scrape(self) -> List[OpportunityItem]:
        all_items: List[OpportunityItem] = []
        for acc in self.accounts:
            try:
                acc_items = await self.scrape_account(acc)
                all_items.extend(acc_items)
            except Exception as e:
                logger.error(f"[{self.name}] Terjadi kesalahan saat membaca {acc}: {e}")

        logger.info(f"[{self.name}] Selesai mengekstrak {len(all_items)} postingan dari media sosial.")
        return all_items
