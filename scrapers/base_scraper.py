import logging
import httpx
from abc import ABC, abstractmethod
from typing import List
from database.models import OpportunityItem
from config.settings import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Kelas dasar untuk setiap scraper sumber data."""

    def __init__(self, name: str, timeout: float = 15.0):
        self.name = name
        self.timeout = timeout
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def fetch_html(self, url: str) -> str:
        """Mengambil isi HTML halaman dengan error handling dan timeout aman."""
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(f"[{self.name}] HTTP error {e.response.status_code} saat mengakses {url}")
                return ""
            except Exception as e:
                logger.error(f"[{self.name}] Gagal fetch URL {url}: {e}")
                return ""

    @abstractmethod
    async def scrape(self) -> List[OpportunityItem]:
        """Metode wajib yang mengembalikan daftar OpportunityItem terstruktur."""
        pass
