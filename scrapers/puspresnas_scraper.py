import logging
from datetime import datetime
from typing import List

from database.models import OpportunityItem
from scrapers.base_scraper import BaseScraper
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class PuspresnasScraper(BaseScraper):
    """
    Scraper untuk Balai Pengembangan Talenta Indonesia (BPTI) / Pusat Prestasi Nasional (Puspresnas)
    Kementerian Pendidikan Dasar dan Menengah RI / Kemendikbudristek.
    Menyediakan kompetisi resmi nasional: GEMASTIK, PKM/PIMNAS, LIDM, PILMAPRES, SATRIA DATA, dsb.
    Dilengkapi katalog kurasi ajang talenta nasional jika live request terhalang proteksi Cloudflare di hosting.
    """

    OFFICIAL_AJANG_TALENTA = [
        {
            "title": "GEMASTIK - Pagelaran Mahasiswa Nasional Bidang TIK",
            "desc": "Kompetisi TIK resmi mahasiswa terbesar di Indonesia meliputi pemrograman, keamanan siber, animasi, UX design, data mining, dan karya tulis TIK.",
            "tags": ["IT & Coding", "AI & ML", "Kompetisi Mahasiswa", "Prestasi Nasional"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "PKM & PIMNAS - Program Kreativitas Mahasiswa & Pekan Ilmiah Mahasiswa Nasional",
            "desc": "Ajang riset dan inovasi bergengsi mahasiswa nasional untuk pendanaan proposal riset eksakta, sosial humaniora, pengabdian masyarakat, kewirausahaan, dan karsa cipta.",
            "tags": ["Karya Tulis & Riset", "Business & Case", "Kompetisi Mahasiswa"],
            "url": "https://simbelmawa.kemdikbud.go.id/",
        },
        {
            "title": "LIDM - Lomba Inovasi Digital Mahasiswa",
            "desc": "Kompetisi inovasi pendidikan digital meliputi inovasi materi digital, video digital pendidikan, poster digital, dan pengembangan teknologi pembelajaran.",
            "tags": ["IT & Coding", "Desain & Kreatif", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "PILMAPRES - Pemilihan Mahasiswa Berprestasi Nasional",
            "desc": "Ajang seleksi dan penganugerahan mahasiswa terbaik tingkat nasional berdasarkan portofolio capaian unggulan, gagasan kreatif, dan bahasa internasional.",
            "tags": ["Kompetisi Nasional", "Ajang Talenta", "Prestasi Mahasiswa"],
            "url": "https://pusatprestasinasional.kemdikbud.go.id/",
        },
        {
            "title": "SATRIA DATA - Statistika Ria dan Festival Sains Data",
            "desc": "Kompetisi komputasi data, pemodelan statistik, dan analisis big data nasional untuk menguji kemampuan mahasiswa di era kecerdasan artifisial.",
            "tags": ["IT & Coding", "AI & ML", "Karya Tulis & Riset"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "ONMIPA - Olimpiade Nasional Matematika dan Ilmu Pengetahuan Alam",
            "desc": "Olimpiade sains tingkat perguruan tinggi bidang Matematika, Fisika, Kimia, dan Biologi untuk menjaring talenta riset masa depan.",
            "tags": ["Karya Tulis & Riset", "Kompetisi Nasional"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "KRI - Kontes Robot Indonesia",
            "desc": "Kompetisi rancang bangun dan rekayasa robotika mahasiswa tingkat nasional (SAR, sepak bola beroda, seni tari, tematik).",
            "tags": ["IT & Coding", "Kompetisi Mahasiswa", "Teknik & Rekayasa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "KBMK - Kompetisi Mahasiswa Nasional Bidang Ilmu Bisnis, Manajemen, dan Keuangan",
            "desc": "Kompetisi analisis kasus bisnis nyata, investasi pasar modal, dan perencanaan bisnis berkelanjutan tingkat perguruan tinggi.",
            "tags": ["Business & Case", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "NUDC - National University Debating Championship",
            "desc": "Kejuaraan debat parlementer bahasa Inggris (British Parliamentary) tingkat nasional bagi mahasiswa seluruh Indonesia.",
            "tags": ["Debat & Pidato", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "KDMI - Kompetisi Debat Mahasiswa Indonesia",
            "desc": "Kompetisi debat ilmiah berbahasa Indonesia tingkat nasional untuk mengasah daya kritis, argumentasi logis, dan retorika mahasiswa.",
            "tags": ["Debat & Pidato", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "KRTI - Kontes Robot Terbang Indonesia",
            "desc": "Kompetisi aeromodelling, drone otonom, fixed wing, dan teknologi wahana tanpa awak mahasiswa nasional.",
            "tags": ["IT & Coding", "Teknik & Rekayasa", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
        {
            "title": "KMHE - Kontes Mobil Hemat Energi",
            "desc": "Kompetisi rancang bangun kendaraan prototipe dan urban concept dengan efisiensi bahan bakar dan energi listrik terbaik.",
            "tags": ["Desain & Kreatif", "Teknik & Rekayasa", "Kompetisi Mahasiswa"],
            "url": "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
        },
    ]

    def __init__(self):
        super().__init__(name="BPTI / Puspresnas Kemendikdasmen", timeout=20.0)
        self.target_urls = [
            "https://bpti.kemendikdasmen.go.id/ajang-talenta/",
            "https://bpti.kemendikdasmen.go.id/",
        ]

    def _get_curated_fallback_items(self) -> List[OpportunityItem]:
        """Mengembalikan katalog ajang talenta nasional resmi Kemendikdasmen."""
        current_year = datetime.now().year
        deadline_default = f"{current_year}-12-31"

        items = []
        for ajang in self.OFFICIAL_AJANG_TALENTA:
            item = OpportunityItem(
                title=f"{ajang['title']} {current_year}",
                category="Lomba",
                tags=ajang["tags"],
                organizer="BPTI Kemendikdasmen / Puspresnas",
                description=ajang["desc"],
                url=ajang["url"],
                deadline=deadline_default,
                source=self.name,
                image_url="https://ditmawa.ugm.ac.id/wp-content/themes/ugm-theme-dti/assets/images/ugm_logo.png"
            )
            items.append(item)
        return items

    async def scrape(self) -> List[OpportunityItem]:
        items: List[OpportunityItem] = []
        seen_titles = set()

        for url in self.target_urls:
            try:
                adaptor = await self.fetch_adaptor(
                    url,
                    stealth=True,
                    solve_cloudflare=True,
                    wait_ms=4000,
                )

                if adaptor is None:
                    continue

                # 1. Ekstraksi dari Accordion/Toggle Ajang Talenta (jika berhasil tembus)
                toggle_items = adaptor.css(".elementor-toggle-item, .elementor-accordion-item")
                for it in toggle_items:
                    a_elem = it.css("a.elementor-toggle-title, a.elementor-accordion-title")
                    if not a_elem:
                        continue

                    title = DataNormalizer.clean_text(a_elem[0].text or a_elem[0].get() or "")
                    if not title or len(title) < 5 or title.lower() in seen_titles:
                        continue

                    seen_titles.add(title.lower())

                    content_elem = it.css(".elementor-tab-content")
                    desc = ""
                    if content_elem:
                        desc = DataNormalizer.clean_text(content_elem[0].get())

                    links = content_elem[0].css("a") if content_elem else []
                    item_url = url
                    for l in links:
                        raw_href = (l.attrib.get("href") or "").strip()
                        if raw_href and raw_href.startswith("http") and not raw_href.startswith("javascript"):
                            item_url = raw_href
                            break

                    full_text = f"{title} {desc}"
                    tags = DataNormalizer.classify_tags(full_text)
                    if not tags or tags == ["Umum"]:
                        tags = ["Kompetisi Nasional", "Ajang Talenta"]
                    deadline = DataNormalizer.extract_deadline(full_text)

                    imgs = content_elem[0].css("img") if content_elem else []
                    img_url = imgs[0].attrib.get("src") if imgs else None

                    item = OpportunityItem(
                        title=title,
                        category="Lomba",
                        tags=tags,
                        organizer="BPTI Kemendikdasmen / Puspresnas",
                        description=desc[:300] if desc else "Ajang talenta dan kompetisi resmi nasional mahasiswa BPTI Kemendikdasmen.",
                        url=item_url,
                        deadline=deadline,
                        source=self.name,
                        image_url=img_url,
                    )
                    items.append(item)

                if len(items) >= 10:
                    break

            except Exception as e:
                logger.debug(f"[{self.name}] Error scraping URL {url}: {e}")

        # Fallback resmi: jika live request terhalang proteksi Cloudflare di hosting
        if not items:
            logger.info(f"[{self.name}] Live scrape terproteksi/kosong. Menggunakan katalog ajang talenta nasional terkurasi.")
            items = self._get_curated_fallback_items()

        logger.info(f"[{self.name}] Berhasil mengekstrak {len(items)} kompetisi resmi.")
        return items
