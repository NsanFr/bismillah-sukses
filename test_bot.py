import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

# Mengatasi encoding cp1252 pada terminal Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Tambahkan direktori root ke sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import discord
from cogs.opportunities import OpportunitiesCog, OpportunityPaginatorView
from cogs.scheduler import SchedulerCog
from database.db_manager import DatabaseManager
from database.models import OpportunityItem
from scrapers.indbeasiswa_scraper import IndBeasiswaScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.kemahasiswaan_scraper import KemahasiswaanScraper
from scrapers.puspresnas_scraper import PuspresnasScraper
from scrapers.scraper_manager import ScraperManager
from utils.embeds import create_opportunity_embed
from utils.normalizer import DataNormalizer

TEST_DB_FILE = "unit_test_bot.sqlite"


async def test_normalizer():
    print("--- [1] Menguji Data Normalizer ---")
    test_caption = "Pendaftaran Lomba Hackathon AI dibuka s.d 28 November 2026. Hadiah puluhan juta rupiah!"
    deadline = DataNormalizer.extract_deadline(test_caption)
    tags = DataNormalizer.classify_tags(test_caption)
    print(f"Hasil Ekstraksi Deadline: {deadline}")
    print(f"Hasil Klasifikasi Tags: {tags}")
    assert deadline == "2026-11-28", "Deadline tidak cocok!"
    assert "IT & Coding" in tags, "Tag IT & Coding tidak terdeteksi!"

    # Uji format ISO langsung
    dl_iso = DataNormalizer.extract_deadline("Deadline: 2026-10-31")
    assert dl_iso == "2026-10-31", "Format ISO deadline gagal diekstrak!"

    # Uji format DD/MM/YYYY
    dl_slash = DataNormalizer.extract_deadline("Batas akhir pendaftaran 25/12/2026")
    assert dl_slash == "2026-12-25", "Format slash deadline gagal diekstrak!"

    print(">> Normalizer OK!")


async def test_database():
    print("\n--- [2] Menguji Database, Deduplikasi, Prune, Upcoming Deadlines, & Stats ---")
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    db = DatabaseManager(db_path=TEST_DB_FILE)
    today = datetime.now()

    item1 = OpportunityItem(
        title="Lomba Hackathon Mahasiswa Nasional 2026",
        category="Lomba",
        tags=["IT & Coding"],
        organizer="Kemdikbud",
        description="Kompetisi membuat solusi berbasis AI",
        url="https://example.com/hackathon-2026",
        deadline=(today + timedelta(days=5)).strftime("%Y-%m-%d"),
        source="Test Source",
    )

    # Tambah pertama kali -> Harus Berhasil (True)
    is_new, item_id = db.add_opportunity(item1)
    print(f"Tambah Item 1: is_new={is_new}, id={item_id}")
    assert is_new is True, "Item 1 harus baru!"

    # Tambah kedua kali item yang sama -> Harus Terdeteksi Duplikat (False)
    is_new2, _ = db.add_opportunity(item1)
    print(f"Tambah Item 1 lagi (duplikat): is_new={is_new2}")
    assert is_new2 is False, "Item duplikat harus ditolak!"

    # Uji Pencarian dengan tag filter
    results = db.search_opportunities(category="Lomba", keyword="hackathon", tag="IT & Coding")
    print(f"Hasil Pencarian 'hackathon' + tag 'IT & Coding': {len(results)} item ditemukan")
    assert len(results) >= 1, "Pencarian harus menemukan minimal 1 item!"

    # Uji get_upcoming_deadlines
    upcoming = db.get_upcoming_deadlines(days=7)
    print(f"Hasil get_upcoming_deadlines (7 hari): {len(upcoming)} item")
    assert len(upcoming) >= 1, "Item dengan deadline 5 hari ke depan harus terdeteksi!"
    assert upcoming[0].title == item1.title
    print(">> get_upcoming_deadlines OK!")

    # Uji Konfigurasi Guild & Role Notifikasi
    db.set_guild_channels(
        guild_id=987654321,
        lomba_channel_id=111111,
        beasiswa_channel_id=222222,
        notification_role_id=333333,
    )
    setting = db.get_guild_setting(987654321)
    assert setting is not None, "Pengaturan guild harus tersimpan!"
    assert setting["lomba_channel_id"] == 111111
    assert setting["beasiswa_channel_id"] == 222222
    assert setting["notification_role_id"] == 333333
    print(">> Guild Settings dengan Role Notifikasi OK!")

    # Uji Reset Channel dengan nilai 0
    db.set_guild_channels(guild_id=987654321, beasiswa_channel_id=0)
    setting_updated = db.get_guild_setting(987654321)
    assert setting_updated["lomba_channel_id"] == 111111
    assert setting_updated["beasiswa_channel_id"] is None, "Channel beasiswa harus di-reset menjadi None!"
    assert setting_updated["notification_role_id"] == 333333
    print(">> Reset Channel dengan nilai 0 OK!")

    # Uji Auto-Pruning
    item_expired = OpportunityItem(
        title="Kompetisi Tahun 2021",
        category="Lomba",
        tags=["Umum"],
        organizer="Test",
        description="Event lama",
        url="https://example.com/expired-2021",
        deadline="2021-05-15",
        source="Test",
    )
    db.add_opportunity(item_expired)
    pruned_count = db.prune_expired_opportunities()
    assert pruned_count == 1, f"Harus ada 1 item kadaluarsa yang dinonaktifkan, didapat: {pruned_count}"
    print(f">> Auto-prune OK! {pruned_count} item dinonaktifkan.")

    # Uji get_stats
    stats = db.get_stats()
    print(f">> Statistik Database: {stats}")
    assert stats["total_items"] == 2
    assert stats["active_lomba"] == 1
    assert stats["total_guilds"] == 1

    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    print(">> Database & Deduplikasi OK!")


async def test_scrapers():
    print("\n--- [3] Menguji Network Scraping (Kemahasiswaan UI/UGM/UNDIP & Puspresnas) ---")

    # 1. Kemahasiswaan UI, UGM, & UNDIP Scraper (Multi-Campus Expanded)
    print("Testing KemahasiswaanScraper (Multi-Campus: UI, UGM, UNDIP)...")
    kema_scraper = KemahasiswaanScraper()
    items_kema = await kema_scraper.scrape()
    print(f"Kemahasiswaan Kampus Scraper menghasilkan {len(items_kema)} item.")
    assert len(items_kema) >= 20, "Kemahasiswaan multi-kampus harus menghasilkan minimal 20 item!"
    print(f"  [Contoh 1]: {items_kema[0].title} | Org: {items_kema[0].organizer}")
    print(f"  [Contoh 2]: {items_kema[-1].title} | Org: {items_kema[-1].organizer}")

    # 2. Puspresnas / BPTI Scraper (dengan Curated Official Fallback)
    print("Testing PuspresnasScraper...")
    pusp_scraper = PuspresnasScraper()
    items_pusp = await pusp_scraper.scrape()
    print(f"Puspresnas / BPTI Scraper menghasilkan {len(items_pusp)} item.")
    assert len(items_pusp) >= 10, "Puspresnas / BPTI harus menghasilkan data kompetisi nasional!"
    print(f"  [Contoh]: {items_pusp[0].title} | Tags: {items_pusp[0].tags}")

    # 3. Instagram Scraper (instagrapi safe execution)
    print("Testing InstagramScraper...")
    ig_scraper = InstagramScraper(target_accounts=["test_dummy_acc"])
    items_ig = await ig_scraper.scrape()
    print(f"Instagram Scraper executed safely, returned {len(items_ig)} items without crashing.")
    assert isinstance(items_ig, list), "Instagram Scraper harus mengembalikan list!"

    print(">> Scraping Selesai & Berhasil!")


async def test_slash_commands_and_broadcast_mock():
    print("\n--- [4] Menguji Logika Slash Commands, UI Pagination, & Mock Broadcast ---")
    test_mock_db_file = "test_mock_slash.sqlite"
    if os.path.exists(test_mock_db_file):
        os.remove(test_mock_db_file)
    mock_db = DatabaseManager(test_mock_db_file)
    mock_bot = MagicMock()
    mock_bot.user = MagicMock()
    mock_bot.user.id = 12345
    mock_bot.user.name = "TestCuratorBot"
    mock_bot.user.avatar = None
    mock_bot.latency = 0.042

    opp_cog = OpportunitiesCog(mock_bot, mock_db)

    # 1. Uji validasi permission bot pada /setchannel (Bot kekurangan izin)
    mock_guild = MagicMock()
    mock_guild.id = 55555
    mock_guild.name = "Komunitas Mahasiswa"
    mock_guild.icon = None

    bot_member = MagicMock()
    mock_guild.me = bot_member

    bad_channel = MagicMock(spec=discord.TextChannel)
    bad_channel.id = 101010
    bad_channel.mention = "<#101010>"
    bad_perms = discord.Permissions(send_messages=True, embed_links=False)
    bad_channel.permissions_for.return_value = bad_perms

    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.guild_id = 55555
    interaction.response = AsyncMock()

    await opp_cog.cmd_setchannel.callback(
        opp_cog,
        interaction,
        channel_lomba=bad_channel,
        channel_beasiswa=None,
        role_notifikasi=None,
    )

    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args[0][0]
    assert "Gagal Mengatur Channel Broadcast" in call_args
    assert "Sematkan Tautan (Embed Links)" in call_args
    print(">> Validasi Bot Missing Permissions pada /setchannel: OK!")

    # 2. Uji /setchannel dengan izin lengkap (Sukses)
    good_channel = MagicMock(spec=discord.TextChannel)
    good_channel.id = 202020
    good_channel.mention = "<#202020>"
    good_perms = discord.Permissions(send_messages=True, embed_links=True)
    good_channel.permissions_for.return_value = good_perms

    mock_role = MagicMock(spec=discord.Role)
    mock_role.id = 88888
    mock_role.mention = "<@&88888>"

    interaction_good = MagicMock(spec=discord.Interaction)
    interaction_good.guild = mock_guild
    interaction_good.guild_id = 55555
    interaction_good.response = AsyncMock()

    await opp_cog.cmd_setchannel.callback(
        opp_cog,
        interaction_good,
        channel_lomba=good_channel,
        channel_beasiswa=good_channel,
        role_notifikasi=mock_role,
    )

    interaction_good.response.send_message.assert_called_once()
    good_reply = interaction_good.response.send_message.call_args[0][0]
    assert "Konfigurasi Broadcast Berhasil Diperbarui" in good_reply
    assert "<@&88888>" in good_reply

    setting = mock_db.get_guild_setting(55555)
    assert setting["lomba_channel_id"] == 202020
    assert setting["notification_role_id"] == 88888
    print(">> Eksekusi Sukses /setchannel dengan Role Notifikasi: OK!")

    # 3. Uji /channelinfo
    interaction_info = MagicMock(spec=discord.Interaction)
    interaction_info.guild = mock_guild
    interaction_info.guild_id = 55555
    interaction_info.response = AsyncMock()

    await opp_cog.cmd_channelinfo.callback(opp_cog, interaction_info)
    interaction_info.response.send_message.assert_called_once()
    info_embed = interaction_info.response.send_message.call_args[1]["embed"]
    assert "Status Konfigurasi Broadcast" in info_embed.title
    print(">> Eksekusi /channelinfo: OK!")

    # 4. Uji OpportunityPaginatorView
    item_sample1 = OpportunityItem(
        title="Lomba Hackathon 1",
        category="Lomba",
        tags=["IT & Coding"],
        organizer="Test Org",
        description="Desc 1",
        url="https://example.com/hackathon-1",
        deadline="2026-11-20",
        source="Test",
    )
    item_sample2 = OpportunityItem(
        title="Lomba Hackathon 2",
        category="Lomba",
        tags=["IT & Coding"],
        organizer="Test Org",
        description="Desc 2",
        url="https://example.com/hackathon-2",
        deadline="2026-11-25",
        source="Test",
    )
    paginator = OpportunityPaginatorView([item_sample1, item_sample2], author_id=999)
    assert len(paginator.children) == 4, "Harus ada 4 komponen di paginator view!"
    assert paginator.page_indicator.label == "1 / 2"
    assert paginator.link_btn.url == "https://example.com/hackathon-1"
    assert paginator.prev_button.disabled is True
    assert paginator.next_button.disabled is False
    print(">> OpportunityPaginatorView state & tombol navigasi: OK!")

    # 5. Uji /deadline command
    mock_db.add_opportunity(item_sample1)
    mock_db.add_opportunity(item_sample2)

    interaction_deadline = MagicMock(spec=discord.Interaction)
    interaction_deadline.guild = mock_guild
    interaction_deadline.user = MagicMock(id=999)
    interaction_deadline.response = AsyncMock()
    interaction_deadline.followup = AsyncMock()

    await opp_cog.cmd_deadline.callback(opp_cog, interaction_deadline, hari=60, kategori="Semua")
    interaction_deadline.followup.send.assert_called_once()
    deadline_content = interaction_deadline.followup.send.call_args[1]["content"]
    assert "peluang dengan deadline terdekat" in deadline_content
    print(">> Eksekusi Slash Command /deadline: OK!")

    # 6. Uji Mock Broadcast Scheduler dengan Role Mention
    mock_sm = MagicMock(spec=ScraperManager)
    sched_cog = SchedulerCog(mock_bot, mock_db, mock_sm)

    sample_item = OpportunityItem(
        title="Lomba Desain Poster Nasional 2026",
        category="Lomba",
        tags=["Desain & Kreatif"],
        organizer="Kemdikbud",
        description="Kompetisi desain poster kreatif mahasiswa nasional.",
        url="https://example.com/lomba-poster",
        deadline="2026-12-15",
        source="Test Source",
    )

    mock_channel_target = AsyncMock(spec=discord.TextChannel)
    sched_cog._resolve_channel = AsyncMock(return_value=mock_channel_target)

    sent = await sched_cog.broadcast_opportunity(sample_item)
    assert sent == 1, f"Ekspektasi 1 channel broadcast terkirim, didapat: {sent}"
    mock_channel_target.send.assert_called_once()
    send_kwargs = mock_channel_target.send.call_args[1]
    assert send_kwargs["content"] == "<@&88888>", f"Ekspektasi role mention <@&88888>, didapat {send_kwargs['content']}"
    assert isinstance(send_kwargs["embed"], discord.Embed), "Embed harus disertakan dalam broadcast!"
    print(">> Mock Broadcast dengan Role Mention & Embed: OK!")

    if os.path.exists(test_mock_db_file):
        os.remove(test_mock_db_file)


async def main():
    await test_normalizer()
    await test_database()
    await test_slash_commands_and_broadcast_mock()
    await test_scrapers()
    print("\n" + "=" * 60)
    print("🎉 [SUCCESS] SELURUH PENGUJIAN SISTEM LENGKAP & SUKSES!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
