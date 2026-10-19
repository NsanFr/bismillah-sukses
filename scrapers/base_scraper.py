import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import httpx
from bs4 import BeautifulSoup

from config.settings import DEFAULT_USER_AGENT, USE_STEALTH_FETCHER
from database.models import OpportunityItem

logger = logging.getLogger(__name__)


class HTMLAdaptor:
    """
    Adaptor ultra-ringan berbasis BeautifulSoup yang 100% kompatibel dengan Scrapling API
    (.css, .text, .attrib, .get).
    Memungkinkan bot berjalan lancar di hosting gratis (bot-hosting.net) tanpa perlu
    menginstal Playwright/Chromium yang memakan ratusan MB disk space.
    """

    def __init__(self, tag_or_html: Any):
        if isinstance(tag_or_html, str):
            self._tag = BeautifulSoup(tag_or_html, "html.parser")
        else:
            self._tag = tag_or_html

    def css(self, selector: str) -> List["HTMLAdaptor"]:
        try:
            # Hilangkan pseudo-selector yang khas scrapling jika ada
            clean_sel = selector.replace("::text", "").strip()
            if not clean_sel:
                return [self]
            elems = self._tag.select(clean_sel)
            return [HTMLAdaptor(el) for el in elems]
        except Exception:
            return []

    @property
    def text(self) -> str:
        return self._tag.get_text() if self._tag else ""

    @property
    def attrib(self) -> dict:
        return getattr(self._tag, "attrs", {})

    def get(self) -> str:
        return str(self._tag) if self._tag else ""


# Scrapling imports opsional (jika tersedia di environment besar)
try:
    from scrapling import Fetcher, StealthyFetcher
    from scrapling.parser import Adaptor as ScraplingAdaptor
    SCRAPLING_AVAILABLE = True
    Adaptor = ScraplingAdaptor
except ImportError:
    SCRAPLING_AVAILABLE = False
    Fetcher = None
    StealthyFetcher = None
    Adaptor = HTMLAdaptor
    logger.info("Scrapling/Playwright tidak terpasang. Menggunakan engine HTMLAdaptor ringan (kompatibel hosting hemat disk).")


class BaseScraper(ABC):
    """Kelas dasar untuk setiap scraper sumber data dengan dukungan adaptif Scrapling & httpx."""

    def __init__(self, name: str, timeout: float = 20.0):
        self.name = name
        self.timeout = timeout
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def fetch_html(
        self,
        url: str,
        stealth: bool = False,
        solve_cloudflare: bool = False,
        wait_ms: int = 0
    ) -> str:
        """Mengambil isi HTML halaman sebagai string teks."""
        adaptor = await self.fetch_adaptor(
            url,
            stealth=stealth,
            solve_cloudflare=solve_cloudflare,
            wait_ms=wait_ms
        )
        if adaptor is not None:
            try:
                res_content = adaptor.get()
                if res_content is not None:
                    return str(res_content)
            except Exception:
                pass
        return ""

    async def fetch_adaptor(
        self,
        url: str,
        stealth: bool = False,
        solve_cloudflare: bool = False,
        wait_ms: int = 0
    ) -> Any:
        """
        Mengembalikan objek Adaptor untuk query DOM cepat (.css / .xpath).
        Secara otomatis memilih Scrapling (jika tersedia) atau fallback ke HTTPX + HTMLAdaptor.
        """
        use_stealth = stealth and USE_STEALTH_FETCHER

        # 1. Coba gunakan Scrapling jika tersedia di environment
        if SCRAPLING_AVAILABLE:
            if use_stealth and StealthyFetcher is not None:
                try:
                    logger.debug(f"[{self.name}] Fetching dengan StealthyFetcher: {url}")
                    timeout_ms = int(self.timeout * 1000)
                    response = await asyncio.to_thread(
                        StealthyFetcher.fetch,
                        url,
                        headless=True,
                        solve_cloudflare=solve_cloudflare,
                        wait=wait_ms,
                        timeout=timeout_ms,
                    )
                    if response and response.status in (200, 301, 302):
                        return response
                    logger.warning(f"[{self.name}] StealthyFetcher status {getattr(response, 'status', 'Unknown')} untuk {url}")
                except Exception as e:
                    logger.warning(f"[{self.name}] StealthyFetcher gagal untuk {url}: {e}. Mencoba fallback.")

            # Standard Scrapling Fetcher
            if Fetcher is not None:
                try:
                    logger.debug(f"[{self.name}] Fetching dengan Scrapling Fetcher: {url}")
                    timeout_ms = int(self.timeout * 1000)
                    response = await asyncio.to_thread(
                        Fetcher.get,
                        url,
                        timeout=timeout_ms
                    )
                    if response and response.status in (200, 301, 302):
                        return response
                    logger.warning(f"[{self.name}] Scrapling Fetcher status {getattr(response, 'status', 'Unknown')} untuk {url}")
                except Exception as e:
                    logger.warning(f"[{self.name}] Scrapling Fetcher gagal untuk {url}: {e}. Mencoba fallback httpx.")

        # 2. Engine Utama / Fallback: HTTPX + HTMLAdaptor (ringan & hemat memori/disk)
        try:
            logger.debug(f"[{self.name}] Mengambil data via HTTPX untuk {url}")
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    if SCRAPLING_AVAILABLE and ScraplingAdaptor is not None:
                        try:
                            return ScraplingAdaptor(resp.text)
                        except Exception:
                            return HTMLAdaptor(resp.text)
                    return HTMLAdaptor(resp.text)
                logger.warning(f"[{self.name}] HTTP error {resp.status_code} saat mengakses {url}")
        except Exception as e:
            logger.error(f"[{self.name}] Gagal fetch URL {url}: {e}")

        # Mengembalikan Adaptor kosong agar pemanggil tidak crash saat query .css()
        if SCRAPLING_AVAILABLE and ScraplingAdaptor is not None:
            try:
                return ScraplingAdaptor("<html></html>")
            except Exception:
                return HTMLAdaptor("<html></html>")
        return HTMLAdaptor("<html></html>")

    @abstractmethod
    async def scrape(self) -> List[OpportunityItem]:
        """Metode wajib yang mengembalikan daftar OpportunityItem terstruktur."""
        pass
