import re
from typing import Optional, List, Tuple
from datetime import datetime

class DataNormalizer:
    @staticmethod
    def extract_deadline(text: str) -> Optional[str]:
        """
        Mendeteksi tanggal deadline dari string/caption dengan berbagai format Indonesia/Inggris.
        Contoh:
        - "Deadline: 25 Oktober 2026"
        - "Batas pendaftaran: 15/11/2026"
        - "Closing date: 30 Nov 2026"
        """
        if not text:
            return None

        # Format 0: YYYY-MM-DD atau YYYY/MM/DD (ISO standard)
        match_iso = re.search(r'\b(20\d{2})[\/\-](\d{1,2})[\/\-](\d{1,2})\b', text)
        if match_iso:
            y, m, d = match_iso.groups()
            return f"{y}-{int(m):02d}-{int(d):02d}"

        # Format 1: DD/MM/YYYY atau DD-MM-YYYY
        match_num = re.search(r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b', text)
        if match_num:
            d, m, y = match_num.groups()
            if len(y) == 2:
                y = "20" + y
            return f"{y}-{int(m):02d}-{int(d):02d}"

        # Format 2: "15 November 2026" atau "15 Nov 2026"
        bulan_map = {
            'januari': '01', 'jan': '01', 'january': '01',
            'februari': '02', 'feb': '02', 'february': '02',
            'maret': '03', 'mar': '03', 'march': '03',
            'april': '04', 'apr': '04',
            'mei': '05', 'may': '05',
            'juni': '06', 'jun': '06', 'june': '06',
            'juli': '07', 'jul': '07', 'july': '07',
            'agustus': '08', 'ags': '08', 'agt': '08', 'august': '08', 'aug': '08',
            'september': '09', 'sep': '09', 'sept': '09',
            'oktober': '10', 'okt': '10', 'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'desember': '12', 'des': '12', 'december': '12', 'dec': '12'
        }

        pattern = r'\b(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})\b'
        matches = re.finditer(pattern, text)
        for m in matches:
            day, month_str, year = m.groups()
            m_lower = month_str.lower()
            if m_lower in bulan_map:
                month_num = bulan_map[m_lower]
                return f"{year}-{month_num}-{int(day):02d}"

        return None

    @staticmethod
    def classify_tags(text: str) -> List[str]:
        """Menentukan tag kategori spesifik dari teks konten."""
        tags = set()
        text_lower = text.lower()

        keywords = {
            "IT & Coding": ["coding", "hackathon", "data science", "web development", "mobile app", "cyber security", "ai", "machine learning", "competitive programming", "software"],
            "Business & Case": ["business plan", "bmc", "case competition", "marketing", "startup", "investasi", "saham", "ekonomi", "finance"],
            "Karya Tulis & Riset": ["karya tulis", "ktil", "esai", "essay", "paper", "penelitian", "ilmiah", "call for paper", "olimpiade"],
            "Desain & Kreatif": ["desain", "poster", "videografi", "fotografi", "ui/ux", "animasi", "film pendek", "tiktok", "reels"],
            "Debat & Pidato": ["debat", "debate", "speech", "storytelling", "pidato", "mun", "model united nations"],
            "Beasiswa Penuh": ["fully funded", "beasiswa penuh", "biaya hidup", "beasiswa s1", "beasiswa kuliah"],
            "Beasiswa Parsial": ["bantuan dana", "uang saku", "partial", "subsidi", "uang kuliah tunggal", "ukt"]
        }

        for category, word_list in keywords.items():
            for w in word_list:
                if re.search(r'\b' + re.escape(w) + r'\b', text_lower):
                    tags.add(category)
                    break

        return list(tags) if tags else ["Umum"]

    @staticmethod
    def clean_text(text: str) -> str:
        """Membersihkan spasi berlebih, tag HTML, dan karakter sampah."""
        if not text:
            return ""
        # Hapus tag HTML
        cleaned = re.sub(r'<[^>]+>', ' ', text)
        # Rapikan whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
