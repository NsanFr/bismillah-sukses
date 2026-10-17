import discord
from discord.ext import commands, tasks
from database.db_manager import DatabaseManager
from scrapers.scraper_manager import ScraperManager
from utils.embeds import create_opportunity_embed
from config.settings import SCRAPE_INTERVAL_MINUTES, DEFAULT_LOMBA_CHANNEL_ID, DEFAULT_BEASISWA_CHANNEL_ID
import logging

logger = logging.getLogger(__name__)

class SchedulerCog(commands.Cog):
    """Background task untuk menjalankan web scraping otomatis dan broadcast ke server Discord."""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, scraper_manager: ScraperManager):
        self.bot = bot
        self.db = db
        self.scraper_manager = scraper_manager
        # Mulai loop interval sesuai konfigurasi
        self.auto_scrape_loop.change_interval(minutes=SCRAPE_INTERVAL_MINUTES)
        self.auto_scrape_loop.start()

    def cog_unload(self):
        self.auto_scrape_loop.cancel()

    @tasks.loop(minutes=60)
    async def auto_scrape_loop(self):
        await self.bot.wait_until_ready()
        logger.info("⏰ Memulai rutinitas berkala: Scrape dan Broadcast...")

        try:
            new_items = await self.scraper_manager.run_all()
            if not new_items:
                logger.info("Tidak ada item baru yang perlu dibroadcast.")
                return

            guild_configs = self.db.get_all_guild_settings()

            for item in new_items:
                embed = create_opportunity_embed(item)
                is_lomba = item.category.lower() == "lomba"

                # 1. Kirim ke konfigurasi spesifik tiap server Discord
                for cfg in guild_configs:
                    target_channel_id = cfg["lomba_channel_id"] if is_lomba else cfg["beasiswa_channel_id"]
                    if target_channel_id:
                        channel = self.bot.get_channel(target_channel_id)
                        if channel and isinstance(channel, discord.TextChannel):
                            try:
                                await channel.send(embed=embed)
                            except Exception as e:
                                logger.error(f"Gagal kirim pesan ke channel {target_channel_id}: {e}")

                # 2. Fallback: Kirim ke DEFAULT channel ID dari settings jika diatur
                default_channel_id = DEFAULT_LOMBA_CHANNEL_ID if is_lomba else DEFAULT_BEASISWA_CHANNEL_ID
                if default_channel_id:
                    channel = self.bot.get_channel(default_channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        try:
                            await channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Gagal kirim ke default channel {default_channel_id}: {e}")

        except Exception as e:
            logger.error(f"Error pada background task auto_scrape_loop: {e}", exc_info=True)

    @auto_scrape_loop.before_loop
    async def before_auto_scrape(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    db: DatabaseManager = bot.db  # type: ignore
    scraper_manager: ScraperManager = bot.scraper_manager  # type: ignore
    await bot.add_cog(SchedulerCog(bot, db, scraper_manager))
