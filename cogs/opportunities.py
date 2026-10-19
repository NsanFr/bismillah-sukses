import logging
from typing import List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.db_manager import DatabaseManager
from database.models import OpportunityItem
from utils.embeds import create_opportunity_embed

logger = logging.getLogger(__name__)


class OpportunityPaginatorView(discord.ui.View):
    """
    Komponen interaktif Discord UI untuk navigasi multi-halaman embed lomba & beasiswa.
    Dilengkapi tombol Sebelumnya, Indikator Halaman, Berikutnya, dan Tautan Registrasi Langsung.
    """

    def __init__(self, items: List[OpportunityItem], author_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.items = items
        self.embeds = [create_opportunity_embed(item) for item in items]
        self.author_id = author_id
        self.current_page = 0

        # Tombol Link Eksternal dinamis
        initial_url = self.items[0].url if self.items and self.items[0].url.startswith("http") else "https://discord.com"
        self.link_btn = discord.ui.Button(
            label="🔗 Buka Link Resmi",
            style=discord.ButtonStyle.link,
            url=initial_url
        )
        self.add_item(self.link_btn)

        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.embeds) - 1)
        self.page_indicator.label = f"{self.current_page + 1} / {len(self.embeds)}"

        # Update link pendaftaran jika URL valid
        cur_url = self.items[self.current_page].url
        if cur_url and cur_url.startswith("http"):
            self.link_btn.url = cur_url
            self.link_btn.disabled = False
        else:
            self.link_btn.url = "https://discord.com"
            self.link_btn.disabled = True

    @discord.ui.button(label="◀ Sebelumnya", style=discord.ButtonStyle.secondary, custom_id="opp_prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Anda tidak dapat mengontrol tombol navigasi pengguna lain.", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.primary, disabled=True, custom_id="opp_page")
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Berikutnya ▶", style=discord.ButtonStyle.secondary, custom_id="opp_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Anda tidak dapat mengontrol tombol navigasi pengguna lain.", ephemeral=True)
            return
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        # Nonaktifkan navigasi tombol ketika waktu interaksi habis
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.style != discord.ButtonStyle.link:
                child.disabled = True


class OpportunitiesCog(commands.Cog):
    """Cog untuk menangani Slash Commands pencarian Lomba, Beasiswa, Deadline Mendesak, dan manajemen Channel."""

    def __init__(self, bot: commands.Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @app_commands.command(name="lomba", description="Cari info kompetisi mahasiswa aktif yang tersedia.")
    @app_commands.describe(
        keyword="Kata kunci bebas (contoh: hackathon, esai, poster, robot)",
        bidang="Filter bidang/kategori khusus lomba",
        jumlah="Jumlah hasil yang ingin ditampilkan (maksimal 15)"
    )
    @app_commands.choices(bidang=[
        app_commands.Choice(name="💻 IT & Coding / Hackathon", value="IT & Coding"),
        app_commands.Choice(name="📈 Business Plan & Case", value="Business & Case"),
        app_commands.Choice(name="📝 Karya Tulis Ilmiah / Riset", value="Karya Tulis & Riset"),
        app_commands.Choice(name="🎨 Desain & Kreatif / Poster", value="Desain & Kreatif"),
        app_commands.Choice(name="🎙️ Debat & Pidato", value="Debat & Pidato"),
    ])
    async def cmd_lomba(
        self,
        interaction: discord.Interaction,
        keyword: Optional[str] = None,
        bidang: Optional[app_commands.Choice[str]] = None,
        jumlah: Optional[int] = 5
    ):
        await interaction.response.defer(ephemeral=False)
        jumlah = max(1, min(jumlah or 5, 15))
        tag_val = bidang.value if bidang else None

        results = self.db.search_opportunities(
            category="Lomba",
            keyword=keyword,
            tag=tag_val,
            limit=jumlah
        )

        if not results:
            msg = "❌ Belum ada info lomba yang cocok"
            filters = []
            if keyword:
                filters.append(f"kata kunci '**{keyword}**'")
            if bidang:
                filters.append(f"bidang '**{bidang.name}**'")
            if filters:
                msg += " dengan " + " dan ".join(filters) + "."
            else:
                msg += " saat ini."
            await interaction.followup.send(msg)
            return

        if len(results) == 1:
            await interaction.followup.send(
                content=f"🏆 Ditemukan **1** peluang lomba mahasiswa:",
                embed=create_opportunity_embed(results[0])
            )
        else:
            view = OpportunityPaginatorView(results, author_id=interaction.user.id)
            await interaction.followup.send(
                content=f"🏆 Ditemukan **{len(results)}** peluang lomba mahasiswa (gunakan tombol untuk navigasi):",
                embed=view.embeds[0],
                view=view
            )

    @app_commands.command(name="beasiswa", description="Cari info beasiswa mahasiswa aktif yang sedang dibuka.")
    @app_commands.describe(
        keyword="Kata kunci pencarian (contoh: baznas, djarum, s1, prestasi)",
        jumlah="Jumlah hasil yang ingin ditampilkan (maksimal 15)"
    )
    async def cmd_beasiswa(
        self,
        interaction: discord.Interaction,
        keyword: Optional[str] = None,
        jumlah: Optional[int] = 5
    ):
        await interaction.response.defer(ephemeral=False)
        jumlah = max(1, min(jumlah or 5, 15))

        results = self.db.search_opportunities(
            category="Beasiswa",
            keyword=keyword,
            limit=jumlah
        )

        if not results:
            msg = "❌ Belum ada info beasiswa yang cocok"
            if keyword:
                msg += f" dengan kata kunci '**{keyword}**'."
            else:
                msg += " saat ini."
            await interaction.followup.send(msg)
            return

        if len(results) == 1:
            await interaction.followup.send(
                content=f"🎓 Ditemukan **1** beasiswa kuliah aktif:",
                embed=create_opportunity_embed(results[0])
            )
        else:
            view = OpportunityPaginatorView(results, author_id=interaction.user.id)
            await interaction.followup.send(
                content=f"🎓 Ditemukan **{len(results)}** beasiswa kuliah aktif (gunakan tombol untuk navigasi):",
                embed=view.embeds[0],
                view=view
            )

    @app_commands.command(
        name="deadline",
        description="Lihat daftar lomba dan beasiswa yang akan ditutup dalam waktu dekat."
    )
    @app_commands.describe(
        hari="Rentang hari ke depan yang dicek (default: 14 hari)",
        kategori="Filter kategori peluang"
    )
    async def cmd_deadline(
        self,
        interaction: discord.Interaction,
        hari: Optional[int] = 14,
        kategori: Optional[Literal["Semua", "Lomba", "Beasiswa"]] = "Semua"
    ):
        await interaction.response.defer(ephemeral=False)
        hari = max(1, min(hari or 14, 60))

        results = self.db.get_upcoming_deadlines(
            days=hari,
            category=kategori,
            limit=10
        )

        if not results:
            await interaction.followup.send(
                f"🎉 Tidak ada info {kategori.lower() if kategori != 'Semua' else 'lomba/beasiswa'} "
                f"yang mendekati batas akhir pendaftaran dalam **{hari} hari** ke depan."
            )
            return

        cat_label = f" ({kategori})" if kategori != "Semua" else ""
        if len(results) == 1:
            await interaction.followup.send(
                content=f"⏳ Ditemukan **1** peluang{cat_label} dengan deadline terdekat (dalam {hari} hari):",
                embed=create_opportunity_embed(results[0])
            )
        else:
            view = OpportunityPaginatorView(results, author_id=interaction.user.id)
            await interaction.followup.send(
                content=f"⏳ Ditemukan **{len(results)}** peluang{cat_label} dengan deadline terdekat (dalam {hari} hari):",
                embed=view.embeds[0],
                view=view
            )

    @app_commands.command(
        name="setchannel",
        description="Atur channel broadcast otomatis info lomba/beasiswa dan role notifikasi."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel_lomba="Channel Discord untuk mengirim info lomba baru",
        channel_beasiswa="Channel Discord untuk mengirim info beasiswa baru",
        role_notifikasi="Role yang akan dimention saat broadcast info baru (opsional)"
    )
    async def cmd_setchannel(
        self,
        interaction: discord.Interaction,
        channel_lomba: Optional[discord.TextChannel] = None,
        channel_beasiswa: Optional[discord.TextChannel] = None,
        role_notifikasi: Optional[discord.Role] = None
    ):
        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Perintah ini hanya dapat dijalankan di dalam server Discord.",
                ephemeral=True
            )
            return

        if not channel_lomba and not channel_beasiswa and not role_notifikasi:
            await interaction.response.send_message(
                "⚠️ Harap pilih minimal salah satu opsi (`channel_lomba`, `channel_beasiswa`, atau `role_notifikasi`).",
                ephemeral=True
            )
            return

        # Validasi permission bot pada channel target
        bot_member = interaction.guild.me
        if not bot_member:
            try:
                bot_member = await interaction.guild.fetch_member(self.bot.user.id)
            except Exception:
                bot_member = None

        permission_errors = []
        for ch, ch_name in [(channel_lomba, "Channel Lomba"), (channel_beasiswa, "Channel Beasiswa")]:
            if ch is not None and bot_member is not None:
                perms = ch.permissions_for(bot_member)
                missing = []
                if not perms.send_messages:
                    missing.append("`Kirim Pesan (Send Messages)`")
                if not perms.embed_links:
                    missing.append("`Sematkan Tautan (Embed Links)`")

                if missing:
                    permission_errors.append(
                        f"⚠️ Bot tidak memiliki izin {', '.join(missing)} di channel {ch.mention} ({ch_name})."
                    )

        if permission_errors:
            error_response = (
                "❌ **Gagal Mengatur Channel Broadcast**\n"
                + "\n".join(permission_errors)
                + "\n\nSilakan berikan izin tersebut pada bot di channel terkait dan coba kembali."
            )
            await interaction.response.send_message(error_response, ephemeral=True)
            return

        lomba_id = channel_lomba.id if channel_lomba else None
        beasiswa_id = channel_beasiswa.id if channel_beasiswa else None
        role_id = role_notifikasi.id if role_notifikasi else None

        self.db.set_guild_channels(
            guild_id=interaction.guild_id,
            lomba_channel_id=lomba_id,
            beasiswa_channel_id=beasiswa_id,
            notification_role_id=role_id
        )

        response_parts = ["✅ **Konfigurasi Broadcast Berhasil Diperbarui!**\n"]
        if channel_lomba:
            response_parts.append(f"📌 **Channel Lomba**: {channel_lomba.mention}")
        if channel_beasiswa:
            response_parts.append(f"🎓 **Channel Beasiswa**: {channel_beasiswa.mention}")
        if role_notifikasi:
            response_parts.append(f"🔔 **Role Notifikasi**: {role_notifikasi.mention}")

        await interaction.response.send_message("\n".join(response_parts), ephemeral=True)

    @cmd_setchannel.error
    async def cmd_setchannel_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """Menangkap error permission pada perintah /setchannel."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "⛔ Anda membutuhkan hak akses **Administrator** untuk mengatur channel broadcast.",
                ephemeral=True
            )
        else:
            logger.error(f"Error pada cmd_setchannel: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Terjadi kesalahan saat memproses konfigurasi channel.",
                    ephemeral=True
                )

    @app_commands.command(
        name="channelinfo",
        description="Lihat konfigurasi channel broadcast dan role notifikasi di server ini."
    )
    @app_commands.guild_only()
    async def cmd_channelinfo(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Perintah ini hanya dapat dijalankan di dalam server Discord.",
                ephemeral=True
            )
            return

        setting = self.db.get_guild_setting(interaction.guild_id)

        embed = discord.Embed(
            title=f"📡 Status Konfigurasi Broadcast - {interaction.guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        if not setting:
            embed.description = (
                "Server ini belum mengatur channel broadcast otomatis.\n"
                "Gunakan perintah `/setchannel` untuk mulai menerima notifikasi info lomba & beasiswa!"
            )
            embed.add_field(name="📌 Channel Lomba", value="*Belum diatur*", inline=True)
            embed.add_field(name="🎓 Channel Beasiswa", value="*Belum diatur*", inline=True)
            embed.add_field(name="🔔 Role Notifikasi", value="*Tidak ada*", inline=True)
        else:
            lomba_val = f"<#{setting['lomba_channel_id']}>" if setting["lomba_channel_id"] else "*Belum diatur*"
            beasiswa_val = f"<#{setting['beasiswa_channel_id']}>" if setting["beasiswa_channel_id"] else "*Belum diatur*"
            role_val = f"<@&{setting['notification_role_id']}>" if setting["notification_role_id"] else "*Tidak ada*"

            embed.add_field(name="📌 Channel Lomba", value=lomba_val, inline=True)
            embed.add_field(name="🎓 Channel Beasiswa", value=beasiswa_val, inline=True)
            embed.add_field(name="🔔 Role Notifikasi", value=role_val, inline=True)
            if setting["updated_at"]:
                embed.set_footer(text=f"Terakhir diperbarui: {setting['updated_at']}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    db: DatabaseManager = bot.db  # type: ignore
    await bot.add_cog(OpportunitiesCog(bot, db))
