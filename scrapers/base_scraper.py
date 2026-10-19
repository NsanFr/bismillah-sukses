import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from config.settings import DEFAULT_USER_AGENT, USE_STEALTH_FETCHER
from database.models import OpportunityItem

logger = logging.getLogger(__name__)

# Scrapling imports dengan fallback
try:
    from scrapling import Fetcher, StealthyFetcher
    from scrapling.parser import Adaptor, Selector
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    Fetcher = None
    StealthyFetcher = None
    Adaptor = None
    Selector = None
    logger.warning("Package Scrapling tidak tersedia. Fallback ke httpx.")


class BaseScraper(ABC):
    """Kelas dasar untuk setiap scraper sumber data dengan dukungan Scrapling dan stealth fetcher."""

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
        """Mengambil isi HTML halaman dengan Scrapling (atau fallback httpx)."""
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
    ) -> Optional["Adaptor"]:
        """Mengembalikan objek Scrapling Adaptor/Selector untuk query DOM cepat (.css / .xpath)."""
        use_stealth = stealth and USE_STEALTH_FETCHER

        # 1. Coba gunakan Scrapling jika tersedia
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
                    logger.warning(f"[{self.name}] StealthyFetcher mengembalikan status {getattr(response, 'status', 'Unknown')} untuk {url}")
                except Exception as e:
                    logger.warning(f"[{self.name}] StealthyFetcher gagal untuk {url}: {e}. Mencoba fallback standard fetch.")

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

        # 2. Fallback HTTPX
        try:
            logger.debug(f"[{self.name}] Menggunakan fallback httpx untuk {url}")
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    if SCRAPLING_AVAILABLE and Adaptor is not None:
                        return Adaptor(resp.text)
                    return resp.text
                logger.warning(f"[{self.name}] Fallback httpx HTTP error {resp.status_code} saat mengakses {url}")
        except Exception as e:
            logger.error(f"[{self.name}] Gagal total fetch URL {url}: {e}")

        # Mengembalikan Adaptor kosong agar pemanggil tidak crash saat query DOM
        if SCRAPLING_AVAILABLE and Adaptor is not None:
            return Adaptor("<html></html>")
        return None

    @abstractmethod
    async def scrape(self) -> List[OpportunityItem]:
        """Metode wajib yang mengembalikan daftar OpportunityItem terstruktur."""
        pass
