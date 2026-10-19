import logging
import time
from datetime import datetime, timezone
from typing import List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config.settings import (
    DEFAULT_BEASISWA_CHANNEL_ID,
    DEFAULT_LOMBA_CHANNEL_ID,
    SCRAPE_INTERVAL_MINUTES,
)
from database.db_manager import DatabaseManager
from database.models import OpportunityItem
from scrapers.scraper_manager import ScraperManager
from utils.embeds import create_opportunity_embed

logger = logging.getLogger(__name__)


class SchedulerCog(commands.Cog):
    """Background task untuk menjalankan web scraping otomatis, auto-pruning, dan broadcast."""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, scraper_manager: ScraperManager):
        self.bot = bot
        self.db = db
        self.scraper_manager = scraper_manager
        self.start_time = time.time()
        self.last_scraped_at: Optional[datetime] = None
        self.auto_scrape_loop.change_interval(minutes=SCRAPE_INTERVAL_MINUTES)

    async def cog_load(self):
        self.auto_scrape_loop.start()

    def cog_unload(self):
        self.auto_scrape_loop.cancel()

    async def _resolve_channel(self, channel_id: int) -> Optional[discord.abc.Messageable]:
        """Mendapatkan objek channel dari cache bot atau API Discord (fetch_channel)."""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                logger.debug(f"Gagal resolve channel ID {channel_id}: {e}")
                return None

        if isinstance(channel, discord.abc.Messageable):
            return channel
        return None

    async def broadcast_opportunity(
        self,
        item: OpportunityItem,
        target_guild_id: Optional[int] = None
    ) -> int:
        """
        Mengirimkan satu item peluang ke channel yang relevan.
        Jika target_guild_id diberikan, hanya kirim ke server tersebut.
        Mengembalikan jumlah channel yang sukses menerima pesan.
        """
        embed = create_opportunity_embed(item)
        is_lomba = item.category.lower() == "lomba"
        success_count = 0

        # Ambil pengaturan guild
        if target_guild_id:
            setting = self.db.get_guild_setting(target_guild_id)
            guild_configs = [setting] if setting else []
        else:
            guild_configs = self.db.get_all_guild_settings()

        for cfg in guild_configs:
            target_channel_id = cfg["lomba_channel_id"] if is_lomba else cfg["beasiswa_channel_id"]
            if not target_channel_id:
                continue

            channel = await self._resolve_channel(target_channel_id)
            if not channel:
                logger.warning(f"Channel {target_channel_id} tidak dapat dijangkau oleh bot.")
                continue

            # Buat teks pesan (sertakan role mention jika diatur)
            role_id = cfg["notification_role_id"]
            mention_text = f"<@&{role_id}>" if role_id else None

            try:
                await channel.send(content=mention_text, embed=embed)
                success_count += 1
            except discord.Forbidden:
                logger.warning(f"Bot tidak memiliki izin kirim pesan di channel {target_channel_id}.")
            except Exception as e:
                logger.error(f"Gagal broadcast ke channel {target_channel_id}: {e}")

        # Fallback default channel jika mode global dan belum ada yang terkirim
        if not target_guild_id and not guild_configs:
            default_id = DEFAULT_LOMBA_CHANNEL_ID if is_lomba else DEFAULT_BEASISWA_CHANNEL_ID
            if default_id:
                channel = await self._resolve_channel(default_id)
                if channel:
                    try:
                        await channel.send(embed=embed)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Gagal broadcast ke default channel {default_id}: {e}")

        return success_count

    @tasks.loop(minutes=60)
    async def auto_scrape_loop(self):
        """Loop rutin: auto-prune expired items, scrape seluruh sumber, lalu broadcast item baru."""
        await self.bot.wait_until_ready()
        logger.info("⏰ Memulai siklus otomatis: Auto-prune, Scrape, dan Broadcast...")

        try:
            # 1. Auto-prune peluang yang deadlinenya sudah lewat
            pruned_count = self.db.prune_expired_opportunities()
            if pruned_count > 0:
                logger.info(f"Auto-prune: {pruned_count} peluang kadaluarsa dinonaktifkan.")

            # 2. Jalankan scraping seluruh sumber terdaftar
            self.last_scraped_at = datetime.now(timezone.utc)
            new_items = await self.scraper_manager.run_all()

            if not new_items:
                logger.info("Tidak ada item baru yang perlu dibroadcast pada siklus ini.")
                return

            # 3. Broadcast setiap item baru yang belum pernah masuk database
            total_broadcasted = 0
            for item in new_items:
                sent = await self.broadcast_opportunity(item)
                total_broadcasted += sent

            logger.info(f"Siklus selesai. {len(new_items)} item baru dibroadcast ke {total_broadcasted} channel.")

        except Exception as e:
            logger.error(f"Error pada loop auto_scrape_loop: {e}", exc_info=True)

    @auto_scrape_loop.before_loop
    async def before_auto_scrape(self):
        await self.bot.wait_until_ready()

    # =========================================================================
    # SLASH COMMANDS: ADMIN & MONITORING
    # =========================================================================

    @app_commands.command(
        name="forcescrape",
        description="Jalankan scraping segera tanpa menunggu interval jadwal otomatis."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def cmd_forcescrape(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        pruned = self.db.prune_expired_opportunities()
        self.last_scraped_at = datetime.now(timezone.utc)
        new_items = await self.scraper_manager.run_all()

        total_sent = 0
        for item in new_items:
            sent = await self.broadcast_opportunity(item)
            total_sent += sent

        embed = discord.Embed(
            title="⚡ Force Scrape Selesai",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="✨ Item Baru Ditemukan", value=f"**{len(new_items)}** item", inline=True)
        embed.add_field(name="📢 Broadcast Terkirim", value=f"**{total_sent}** kali", inline=True)
        embed.add_field(name="🗑️ Auto-Prune Kadaluarsa", value=f"**{pruned}** item", inline=True)

        if new_items:
            sample_titles = "\n".join([f"• [{it.category}] {it.title[:50]}..." for it in new_items[:5]])
            embed.add_field(name="📋 Sampel Item Baru", value=sample_titles, inline=False)

        await interaction.followup.send(embed=embed)

    @cmd_forcescrape.error
    async def cmd_forcescrape_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "⛔ Anda membutuhkan hak akses **Administrator** untuk menjalankan force scrape.",
                ephemeral=True
            )

    @app_commands.command(
        name="testbroadcast",
        description="Kirim contoh broadcast ke channel yang diatur di server ini untuk verifikasi tampilan."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        kategori="Pilih sampel kategori yang ingin diuji coba"
    )
    async def cmd_testbroadcast(
        self,
        interaction: discord.Interaction,
        kategori: Optional[Literal["Semua", "Lomba", "Beasiswa"]] = "Semua"
    ):
        await interaction.response.defer(ephemeral=True)

        guild_setting = self.db.get_guild_setting(interaction.guild_id)
        if not guild_setting or (not guild_setting["lomba_channel_id"] and not guild_setting["beasiswa_channel_id"]):
            await interaction.followup.send(
                "⚠️ Server ini belum mengatur channel broadcast. Gunakan `/setchannel` terlebih dahulu.",
                ephemeral=True
            )
            return

        test_items: List[OpportunityItem] = []

        if kategori in ("Semua", "Lomba") and guild_setting["lomba_channel_id"]:
            test_items.append(
                OpportunityItem(
                    title="[TEST] Kompetisi Hackathon & AI Mahasiswa Nasional 2026",
                    category="Lomba",
                    tags=["IT & Coding", "AI & ML", "Kompetisi Mahasiswa"],
                    organizer="Puspresnas / BPTI Kemendikdasmen",
                    description=(
                        "Ini adalah broadcast pengujian sistem. Kompetisi nasional tahunan untuk menguji "
                        "kemampuan inovasi digital, kecerdasan buatan, dan implementasi teknologi tepat guna."
                    ),
                    url="https://bpti.kemendikdasmen.go.id/ajang-talenta/",
                    deadline="2026-12-31",
                    source="Test Broadcast",
                    image_url="https://ditmawa.ugm.ac.id/wp-content/themes/ugm-theme-dti/assets/images/ugm_logo.png"
                )
            )

        if kategori in ("Semua", "Beasiswa") and guild_setting["beasiswa_channel_id"]:
            test_items.append(
                OpportunityItem(
                    title="[TEST] Beasiswa Prestasi Mahasiswa Unggul S1/D4 2026",
                    category="Beasiswa",
                    tags=["Beasiswa Penuh", "Beasiswa Mahasiswa", "S1 / D4"],
                    organizer="Mitra Yayasan Pendidikan",
                    description=(
                        "Ini adalah broadcast pengujian sistem. Bantuan biaya pendidikan penuh, tunjangan bulanan, "
                        "dan program pengembangan kepemimpinan untuk mahasiswa aktif berprestasi."
                    ),
                    url="https://indbeasiswa.com/",
                    deadline="2026-11-30",
                    source="Test Broadcast",
                    image_url=None
                )
            )

        if not test_items:
            await interaction.followup.send(
                f"⚠️ Channel untuk kategori **{kategori}** belum diatur di server ini. Atur via `/setchannel`.",
                ephemeral=True
            )
            return

        sent_count = 0
        for item in test_items:
            sent = await self.broadcast_opportunity(item, target_guild_id=interaction.guild_id)
            sent_count += sent

        await interaction.followup.send(
            f"✅ **Test Broadcast Berhasil Dikirim!**\n"
            f"Terkirim ke **{sent_count}** channel di server ini. Silakan periksa channel terkait untuk melihat tampilan embed dan mention role.",
            ephemeral=True
        )

    @cmd_testbroadcast.error
    async def cmd_testbroadcast_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "⛔ Anda membutuhkan hak akses **Administrator** untuk menjalankan test broadcast.",
                ephemeral=True
            )

    @app_commands.command(
        name="botstatus",
        description="Lihat ringkasan status bot, statistik database, dan jadwal scraping."
    )
    async def cmd_botstatus(self, interaction: discord.Interaction):
        stats = self.db.get_stats()
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}j {minutes}m {seconds}d"

        last_scrape_str = (
            self.last_scraped_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if self.last_scraped_at
            else "Belum ada (dalam antrean)"
        )
        ping_ms = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🤖 Status & Statistik Bot Info Lomba & Beasiswa",
            color=discord.Color.teal(),
            timestamp=discord.utils.utcnow()
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="📶 Latensi Discord", value=f"{ping_ms} ms", inline=True)
        embed.add_field(name="🔄 Interval Scrape", value=f"Setiap {SCRAPE_INTERVAL_MINUTES} menit", inline=True)

        embed.add_field(name="🕒 Scrape Terakhir", value=last_scrape_str, inline=False)

        embed.add_field(name="🏆 Lomba Aktif", value=str(stats["active_lomba"]), inline=True)
        embed.add_field(name="🎓 Beasiswa Aktif", value=str(stats["active_beasiswa"]), inline=True)
        embed.add_field(name="📦 Total Data Disimpan", value=str(stats["total_items"]), inline=True)

        embed.add_field(name="🏰 Server Terhubung", value=f"{stats['total_guilds']} server", inline=True)
        embed.add_field(name="⚙️ Scraper Engine", value="Scrapling (Stealth) + instagrapi", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    db: DatabaseManager = bot.db  # type: ignore
    scraper_manager: ScraperManager = bot.scraper_manager  # type: ignore
    await bot.add_cog(SchedulerCog(bot, db, scraper_manager))
