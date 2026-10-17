import discord
from database.models import OpportunityItem

def create_opportunity_embed(item: OpportunityItem) -> discord.Embed:
    """Membuat Discord Embed yang rapi, modern, dan informatif."""
    
    # Warna: Biru untuk Lomba (#2b7de9), Emas/Kuning untuk Beasiswa (#f5a623)
    color = discord.Color.blue() if item.category.lower() == "lomba" else discord.Color.gold()
    
    embed = discord.Embed(
        title=f"📢 [{item.category.upper()}] {item.title}",
        url=item.url,
        description=item.description,
        color=color
    )

    # Field Penyelenggara & Sumber
    embed.add_field(
        name="🏛️ Penyelenggara",
        value=item.organizer or "Tidak diketahui",
        inline=True
    )
    embed.add_field(
        name="🌐 Sumber Info",
        value=item.source or "Web Scraper",
        inline=True
    )

    # Field Deadline
    deadline_text = item.deadline if item.deadline else "Cek tautan resmi"
    embed.add_field(
        name="⏳ Batas Pendaftaran",
        value=f"**{deadline_text}**",
        inline=True
    )

    # Field Kategori / Tags
    if item.tags:
        tags_str = " ".join([f"`{tag}`" for tag in item.tags])
        embed.add_field(name="🏷️ Kategori", value=tags_str, inline=False)

    # Link pendaftaran langsung
    embed.add_field(
        name="🔗 Link Resmi",
        value=f"[Klik Di Sini Untuk Mendaftar]({item.url})",
        inline=False
    )

    # Gambar thumbnail / poster jika ada
    if item.image_url and item.image_url.startswith("http"):
        embed.set_thumbnail(url=item.image_url)

    embed.set_footer(text="Bot Kurator Lomba & Beasiswa Mahasiswa • Otomatis & Terverifikasi")
    return embed
