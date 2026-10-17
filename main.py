import asyncio
import logging
import sys
import os
import discord
from discord.ext import commands
from rich.logging import RichHandler

from config.settings import DISCORD_TOKEN, GUILD_ID
from database.db_manager import DatabaseManager
from scrapers.scraper_manager import ScraperManager

# Setup Logging dengan Rich format
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("DiscordCuratorBot")

class CuratorBot(commands.Bot):
    def __init__(self):
        # Intents: default sudah mencukupi untuk slash commands dan kirim embed
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        # Inisialisasi Database dan Scraper Manager
        self.db = DatabaseManager(db_path="bot_data.sqlite")
        self.scraper_manager = ScraperManager(self.db)

    async def setup_hook(self):
        """Memuat extension cogs dan menyinkronkan application slash commands."""
        logger.info("Memuat extension cogs...")
        await self.load_extension("cogs.opportunities")
        await self.load_extension("cogs.scheduler")

        # Sinkronisasi Slash Commands
        try:
            if GUILD_ID:
                guild_obj = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Berhasil menyinkronkan {len(synced)} slash commands ke server {GUILD_ID}.")
            else:
                synced = await self.tree.sync()
                logger.info(f"Berhasil menyinkronkan {len(synced)} slash commands secara global.")
        except Exception as e:
            logger.error(f"Gagal menyinkronkan slash commands: {e}")

    async def on_ready(self):
        logger.info(f"Bot berhasil online sebagai: {self.user.name} (ID: {self.user.id})")
        logger.info("Bot siap menyaring info lomba & beasiswa mahasiswa!")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Info Lomba & Beasiswa (/lomba, /beasiswa)"
            )
        )

async def main():
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        logger.error(
            "DISCORD_TOKEN belum diisi di file .env!\n"
            "Silakan buat bot di Discord Developer Portal (https://discord.com/developers/applications), "
            "salin Token-nya, dan masukkan ke file .env"
        )
        return

    bot = CuratorBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dimatikan oleh user.")
