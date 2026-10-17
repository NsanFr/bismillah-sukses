import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from database.db_manager import DatabaseManager
from utils.embeds import create_opportunity_embed
import logging

logger = logging.getLogger(__name__)

class OpportunitiesCog(commands.Cog):
    """Cog untuk menangani Slash Commands pencarian Lomba dan Beasiswa."""

    def __init__(self, bot: commands.Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @app_commands.command(name="lomba", description="Cari info kompetisi mahasiswa aktif yang tersedia.")
    @app_commands.describe(
        keyword="Kata kunci pencarian (contoh: coding, desain, bmc, paper)",
        jumlah="Jumlah hasil yang ingin ditampilkan (maksimal 10)"
    )
    async def cmd_lomba(self, interaction: discord.Interaction, keyword: Optional[str] = None, jumlah: Optional[int] = 3):
        await interaction.response.defer(ephemeral=False)
        jumlah = max(1, min(jumlah or 3, 10))

        results = self.db.search_opportunities(category="Lomba", keyword=keyword, limit=jumlah)

        if not results:
            msg = "❌ Belum ada info lomba yang cocok"
            if keyword:
                msg += f" dengan kata kunci `'{keyword}'`."
            else:
                msg += " saat ini. Scraper akan segera mengupdate data."
            await interaction.followup.send(msg)
            return

        embeds = [create_opportunity_embed(item) for item in results]
        await interaction.followup.send(
            content=f"🎯 Menemukan **{len(results)}** info lomba terbaru:",
            embeds=embeds[:10]
        )

    @app_commands.command(name="beasiswa", description="Cari info beasiswa mahasiswa aktif yang sedang dibuka.")
    @app_commands.describe(
        keyword="Kata kunci pencarian (contoh: s1, prestasi, bantuan, ukt)",
        jumlah="Jumlah hasil yang ingin ditampilkan (maksimal 10)"
    )
    async def cmd_beasiswa(self, interaction: discord.Interaction, keyword: Optional[str] = None, jumlah: Optional[int] = 3):
        await interaction.response.defer(ephemeral=False)
        jumlah = max(1, min(jumlah or 3, 10))

        results = self.db.search_opportunities(category="Beasiswa", keyword=keyword, limit=jumlah)

        if not results:
            msg = "❌ Belum ada info beasiswa yang cocok"
            if keyword:
                msg += f" dengan kata kunci `'{keyword}'`."
            else:
                msg += " saat ini."
            await interaction.followup.send(msg)
            return

        embeds = [create_opportunity_embed(item) for item in results]
        await interaction.followup.send(
            content=f"🎓 Menemukan **{len(results)}** beasiswa terbaru:",
            embeds=embeds[:10]
        )

    @app_commands.command(name="setchannel", description="Atur channel broadcast otomatis untuk info lomba dan beasiswa di server ini.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel_lomba="Channel Discord untuk mengirim info lomba baru",
        channel_beasiswa="Channel Discord untuk mengirim info beasiswa baru"
    )
    async def cmd_setchannel(
        self,
        interaction: discord.Interaction,
        channel_lomba: Optional[discord.TextChannel] = None,
        channel_beasiswa: Optional[discord.TextChannel] = None
    ):
        if not channel_lomba and not channel_beasiswa:
            await interaction.response.send_message(
                "⚠️ Harap pilih minimal salah satu channel (`channel_lomba` atau `channel_beasiswa`).",
                ephemeral=True
            )
            return

        lomba_id = channel_lomba.id if channel_lomba else None
        beasiswa_id = channel_beasiswa.id if channel_beasiswa else None

        self.db.set_guild_channels(
            guild_id=interaction.guild_id,
            lomba_channel_id=lomba_id,
            beasiswa_channel_id=beasiswa_id
        )

        response_parts = []
        if channel_lomba:
            response_parts.append(f"📌 Channel Lomba diset ke {channel_lomba.mention}")
        if channel_beasiswa:
            response_parts.append(f"🎓 Channel Beasiswa diset ke {channel_beasiswa.mention}")

        await interaction.response.send_message("\n".join(response_parts), ephemeral=True)

async def setup(bot: commands.Bot):
    db: DatabaseManager = bot.db  # type: ignore
    await bot.add_cog(OpportunitiesCog(bot, db))
