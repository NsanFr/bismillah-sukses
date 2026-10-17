import sqlite3
import hashlib
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime
from database.models import OpportunityItem

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "bot_data.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Membuat tabel jika belum ada dengan skema yang bersih dan terindeks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabel untuk menyimpan postingan lomba & beasiswa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    organizer TEXT,
                    description TEXT,
                    url TEXT NOT NULL,
                    deadline TEXT,
                    source TEXT NOT NULL,
                    image_url TEXT,
                    source_id TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabel konfigurasi server discord (channel broadcast dan role)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    lomba_channel_id INTEGER,
                    beasiswa_channel_id INTEGER,
                    notification_role_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indeks untuk query cepat
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON opportunities(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON opportunities(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON opportunities(content_hash)")
            
            conn.commit()
            logger.info("Database berhasil diinisialisasi.")

    @staticmethod
    def generate_hash(title: str, url: str) -> str:
        """Membuat hash unik untuk mendeteksi data duplikat."""
        raw = f"{title.strip().lower()}|{url.strip().lower()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def add_opportunity(self, item: OpportunityItem) -> Tuple[bool, Optional[int]]:
        """
        Menambahkan item opportunity baru.
        Return (True, id) jika berhasil ditambah (baru),
        Return (False, None) jika sudah ada (duplikat).
        """
        content_hash = self.generate_hash(item.title, item.url)
        tags_json = json.dumps(item.tags, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO opportunities (
                        content_hash, title, category, tags, organizer,
                        description, url, deadline, source, image_url, source_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content_hash, item.title, item.category, tags_json, item.organizer,
                    item.description, item.url, item.deadline, item.source, item.image_url, item.source_id
                ))
                conn.commit()
                return True, cursor.lastrowid
            except sqlite3.IntegrityError:
                # Duplikat hash terdeteksi
                return False, None
            except Exception as e:
                logger.error(f"Gagal menambahkan data ke database: {e}")
                return False, None

    def search_opportunities(self, category: Optional[str] = None, keyword: Optional[str] = None, limit: int = 10) -> List[OpportunityItem]:
        """Mencari data berdasarkan kategori dan kata kunci teks."""
        query = "SELECT * FROM opportunities WHERE is_active = 1"
        params = []

        if category:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(category)

        if keyword:
            query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
            wildcard = f"%{keyword.lower()}%"
            params.extend([wildcard, wildcard, wildcard])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        results = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                try:
                    tags = json.loads(row["tags"]) if row["tags"] else []
                except Exception:
                    tags = []

                results.append(OpportunityItem(
                    title=row["title"],
                    category=row["category"],
                    tags=tags,
                    organizer=row["organizer"] or "Tidak diketahui",
                    description=row["description"] or "",
                    url=row["url"],
                    deadline=row["deadline"],
                    source=row["source"],
                    image_url=row["image_url"],
                    source_id=row["source_id"]
                ))
        return results

    def set_guild_channels(self, guild_id: int, lomba_channel_id: Optional[int] = None, beasiswa_channel_id: Optional[int] = None):
        """Menyimpan atau memperbarui konfigurasi channel broadcast guild."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO guild_settings (guild_id, lomba_channel_id, beasiswa_channel_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    lomba_channel_id = COALESCE(?, guild_settings.lomba_channel_id),
                    beasiswa_channel_id = COALESCE(?, guild_settings.beasiswa_channel_id),
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, lomba_channel_id, beasiswa_channel_id, lomba_channel_id, beasiswa_channel_id))
            conn.commit()

    def get_all_guild_settings(self) -> List[sqlite3.Row]:
        """Mengambil pengaturan semua guild untuk pengiriman broadcast otomatis."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guild_settings")
            return cursor.fetchall()
