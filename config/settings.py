import os
from typing import List
from dotenv import load_dotenv

# Memuat file .env jika ada
load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
GUILD_ID: str = os.getenv("GUILD_ID", "")  # Opsional untuk sync cepat slash command

# Channel IDs untuk broadcast otomatis (opsional via env atau command /setchannel)
DEFAULT_LOMBA_CHANNEL_ID: int = int(os.getenv("DEFAULT_LOMBA_CHANNEL_ID", "0"))
DEFAULT_BEASISWA_CHANNEL_ID: int = int(os.getenv("DEFAULT_BEASISWA_CHANNEL_ID", "0"))

# Interval scrape otomatis dalam menit (default: 60 menit)
SCRAPE_INTERVAL_MINUTES: int = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))

# User-Agent realistis untuk mencegah blokir scraper
DEFAULT_USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)

# Akun publik Instagram / TikTok target info lomba/beasiswa
TARGET_INSTAGRAM_ACCOUNTS: List[str] = [
    acc.strip() for acc in os.getenv("TARGET_INSTAGRAM_ACCOUNTS", "infolomba,infolombamahasiswa,beasiswa.id").split(",") if acc.strip()
]
