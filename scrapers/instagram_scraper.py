import asyncio
import logging
import os
import random
import time
from typing import List, Optional

from config.settings import (
    IG_PASSWORD,
    IG_SESSION_FILE,
    IG_SESSION_ID,
    IG_USERNAME,
    TARGET_INSTAGRAM_ACCOUNTS,
)
from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

try:
    from instagrapi import Client
    from instagrapi.exceptions import (
        BadPassword,
        ChallengeRequired,
        ClientError,
        FeedbackRequired,
        LoginRequired,
        RateLimitError,
        TwoFactorRequired,
    )
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    Client = None
    logger.warning("Package instagrapi tidak terpasang. Scraping Instagram dinonaktifkan.")


class InstagramScraper(BaseScraper):
    """
    Scraper Instagram berbasis instagrapi.
    Mendukung session persistence (load/dump settings), login cookie sessionid,
    kredensial akun, serta fallback anonymous public request.
    """

    OPPORTUNITY_KEYWORDS = [
        "lomba", "beasiswa", "kompetisi", "competition", "scholarship",
        "sayembara", "hackathon", "olimpiade", "olympiad", "pkm",
        "gemastik", "call for paper", "call for essays", "fellowship",
        "grant", "kontes", "turnamen", "bootcamp"
    ]

    def __init__(self, target_accounts: Optional[List[str]] = None):
        super().__init__(name="Instagram Curator Scraper", timeout=30.0)
        self.accounts = target_accounts or TARGET_INSTAGRAM_ACCOUNTS
        self.session_file = IG_SESSION_FILE
        self._client: Optional[Client] = None

    def _get_authenticated_client(self) -> Optional[Client]:
        """Inisialisasi dan autentikasi instagrapi.Client secara tersinkronisasi."""
        if not INSTAGRAPI_AVAILABLE or Client is None:
            return None

        if self._client is not None:
            return self._client

        cl = Client()
        cl.delay_range = [1, 3]

        # 1. Coba muat sesi tersimpan dari file JSON
        if self.session_file and os.path.exists(self.session_file):
            try:
                cl.load_settings(self.session_file)
                logger.info(f"[{self.name}] Berhasil memuat session Instagram dari {self.session_file}")
                self._client = cl
                return self._client
            except Exception as e:
                logger.warning(f"[{self.name}] Gagal memuat session file {self.session_file}: {e}")

        # 2. Coba login menggunakan sessionid cookie jika disediakan di environment
        if IG_SESSION_ID:
            try:
                cl.login_by_sessionid(IG_SESSION_ID)
                logger.info(f"[{self.name}] Berhasil login ke Instagram via IG_SESSION_ID.")
                if self.session_file:
                    cl.dump_settings(self.session_file)
                self._client = cl
                return self._client
            except Exception as e:
                logger.warning(f"[{self.name}] Gagal login via IG_SESSION_ID: {e}")

        # 3. Coba login menggunakan username & password jika disediakan
        if IG_USERNAME and IG_PASSWORD:
            try:
                logger.info(f"[{self.name}] Melakukan login Instagram untuk akun: {IG_USERNAME}")
                cl.login(IG_USERNAME, IG_PASSWORD)
                logger.info(f"[{self.name}] Login Instagram berhasil.")
                if self.session_file:
                    cl.dump_settings(self.session_file)
                self._client = cl
                return self._client
            except (TwoFactorRequired, ChallengeRequired) as e:
                logger.error(f"[{self.name}] Login Instagram membutuhkan verifikasi manual (2FA/Challenge): {e}")
            except BadPassword:
                logger.error(f"[{self.name}] Password Instagram salah. Periksa konfigurasi IG_PASSWORD.")
            except Exception as e:
                logger.warning(f"[{self.name}] Gagal login username/password Instagram: {e}")

        # 4. Fallback ke anonymous public client
        logger.debug(f"[{self.name}] Berjalan dalam mode Instagram anonymous public request.")
        self._client = cl
        return self._client

    def _sync_scrape_account(self, cl: Client, raw_account: str) -> List[OpportunityItem]:
        """Mengambil dan memfilter media postingan dari satu akun target (sync/thread-safe)."""
        items: List[OpportunityItem] = []
        account = raw_account.replace("@", "").strip()
        if not account:
            return items

        try:
            logger.info(f"[{self.name}] Mengambil data akun @{account}...")
            user_id = cl.user_id_from_username(account)
            medias = cl.user_medias(user_id, amount=6)

            for media in medias:
                caption = media.caption_text or ""
                if not caption:
                    continue

                caption_lower = caption.lower()
                # Cek apakah postingan relevan dengan info lomba atau beasiswa
                is_relevant = any(kw in caption_lower for kw in self.OPPORTUNITY_KEYWORDS)
                if not is_relevant:
                    continue

                # Buat judul bersih dari baris awal caption
                clean_caption = DataNormalizer.clean_text(caption)
                first_line = clean_caption.split("\n")[0].strip()
                if len(first_line) > 100:
                    first_line = first_line[:97] + "..."
                if len(first_line) < 10:
                    first_line = f"Peluang Kompetisi & Beasiswa Terbaru dari @{account}"

                # Ekstraksi kategori, deadline, dan tags
                category = "Beasiswa" if "beasiswa" in caption_lower or "scholarship" in caption_lower else "Lomba"
                deadline = DataNormalizer.extract_deadline(caption)
                tags = DataNormalizer.classify_tags(caption)
                if category == "Beasiswa" and "Beasiswa Mahasiswa" not in tags:
                    tags.append("Beasiswa Mahasiswa")

                url = f"https://www.instagram.com/p/{media.code}/"
                thumb_url = str(media.thumbnail_url) if media.thumbnail_url else None

                item = OpportunityItem(
                    title=first_line,
                    category=category,
                    tags=tags,
                    organizer=f"@{account} (Instagram)",
                    description=clean_caption[:300] if clean_caption else f"Info resmi dari @{account}.",
                    url=url,
                    deadline=deadline,
                    source=f"Instagram (@{account})",
                    image_url=thumb_url,
                )
                items.append(item)

        except (LoginRequired, FeedbackRequired, RateLimitError) as e:
            logger.warning(f"[{self.name}] Instagram rate limit / login required saat mengakses @{account}: {e}")
        except ClientError as e:
            logger.warning(f"[{self.name}] Client error saat mengakses @{account}: {e}")
        except Exception as e:
            logger.warning(f"[{self.name}] Error tak terduga saat scraping @{account}: {e}")

        return items

    def _sync_scrape_all(self) -> List[OpportunityItem]:
        """Menjalankan scraping seluruh target akun dengan delay acak aman."""
        client = self._get_authenticated_client()
        if client is None:
            return []

        all_items: List[OpportunityItem] = []
        for account in self.accounts:
            res = self._sync_scrape_account(client, account)
            all_items.extend(res)
            # Delay sopan 1-2.5 detik antar akun untuk menghindari rate limit
            time.sleep(random.uniform(1.0, 2.5))

        return all_items

    async def scrape(self) -> List[OpportunityItem]:
        """Metode utama scraping asynchronous via worker thread."""
        try:
            items = await asyncio.to_thread(self._sync_scrape_all)
            logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} item dari Instagram.")
            return items
        except Exception as e:
            logger.error(f"[{self.name}] Gagal menjalankan scraping Instagram: {e}", exc_info=True)
            return []


# Alias untuk kompatibilitas ke modul lama
InstagramPublicScraper = InstagramScraper
