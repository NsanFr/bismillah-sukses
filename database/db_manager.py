import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

from database.models import OpportunityItem

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = "bot_data.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, uri=True)
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

            # Migrasi aman jika tabel guild_settings lama belum memiliki notification_role_id
            try:
                cursor.execute("ALTER TABLE guild_settings ADD COLUMN notification_role_id INTEGER")
            except sqlite3.OperationalError:
                pass  # Kolom sudah ada

            # Indeks untuk query cepat
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON opportunities(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON opportunities(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON opportunities(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_active ON opportunities(is_active)")

            conn.commit()
            logger.info("Database berhasil diinisialisasi.")

    @staticmethod
    def generate_hash(title: str, url: str) -> str:
        """Membuat hash unik untuk mendeteksi data duplikat."""
        raw = f"{title.strip().lower()}|{url.strip().lower()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def add_opportunity(self, item: OpportunityItem) -> Tuple[bool, Optional[int]]:
        """
        Menambahkan item peluang baru jika belum pernah tersimpan (deduplikasi via content_hash).
        Mengembalikan tuple: (is_new: bool, inserted_id: Optional[int])
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
                # Data sudah ada di database (duplikat terdeteksi)
                return False, None

    def search_opportunities(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10
    ) -> List[OpportunityItem]:
        """Mencari data berdasarkan kategori dan kata kunci teks."""
        query = "SELECT * FROM opportunities WHERE is_active = 1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if keyword:
            query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
            wildcard = f"%{keyword}%"
            params.extend([wildcard, wildcard, wildcard])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        results: List[OpportunityItem] = []
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
                    organizer=row["organizer"],
                    description=row["description"],
                    url=row["url"],
                    deadline=row["deadline"],
                    source=row["source"],
                    image_url=row["image_url"],
                    source_id=row["source_id"]
                ))
        return results

    def set_guild_channels(
        self,
        guild_id: int,
        lomba_channel_id: Optional[int] = None,
        beasiswa_channel_id: Optional[int] = None,
        notification_role_id: Optional[int] = None
    ):
        """
        Menyimpan atau memperbarui konfigurasi channel broadcast guild dan role notifikasi.
        Jika nilai bernilai 0, channel/role tersebut akan di-reset (dikosongkan / None).
        Jika bernilai None, setting lama dipertahankan.
        """
        existing = self.get_guild_setting(guild_id)

        if existing:
            new_lomba = existing["lomba_channel_id"] if lomba_channel_id is None else (None if lomba_channel_id == 0 else lomba_channel_id)
            new_beasiswa = existing["beasiswa_channel_id"] if beasiswa_channel_id is None else (None if beasiswa_channel_id == 0 else beasiswa_channel_id)
            new_role = existing["notification_role_id"] if notification_role_id is None else (None if notification_role_id == 0 else notification_role_id)
        else:
            new_lomba = None if lomba_channel_id in (0, None) else lomba_channel_id
            new_beasiswa = None if beasiswa_channel_id in (0, None) else beasiswa_channel_id
            new_role = None if notification_role_id in (0, None) else notification_role_id

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO guild_settings (guild_id, lomba_channel_id, beasiswa_channel_id, notification_role_id, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    lomba_channel_id = excluded.lomba_channel_id,
                    beasiswa_channel_id = excluded.beasiswa_channel_id,
                    notification_role_id = excluded.notification_role_id,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, new_lomba, new_beasiswa, new_role))
            conn.commit()

    def get_guild_setting(self, guild_id: int) -> Optional[sqlite3.Row]:
        """Mengambil konfigurasi spesifik 1 server (guild)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
            return cursor.fetchone()

    def get_all_guild_settings(self) -> List[sqlite3.Row]:
        """Mengambil pengaturan semua guild untuk pengiriman broadcast otomatis."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guild_settings")
            return cursor.fetchall()

    def prune_expired_opportunities(self) -> int:
        """
        Menonaktifkan (is_active = 0) peluang lomba/beasiswa yang deadlinenya
        sudah terlewati dibandingkan tanggal hari ini (format YYYY-MM-DD).
        Mengembalikan jumlah baris yang dinonaktifkan.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE opportunities
                SET is_active = 0
                WHERE is_active = 1
                  AND deadline IS NOT NULL
                  AND deadline GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                  AND deadline < ?
            """, (today_str,))
            affected = cursor.rowcount
            conn.commit()
            if affected > 0:
                logger.info(f"Auto-prune: {affected} peluang dinonaktifkan karena telah melewati deadline ({today_str}).")
            return affected

    def get_stats(self) -> dict:
        """Mengembalikan statistik ringkas database bot."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM opportunities")
            total_items = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM opportunities WHERE is_active = 1 AND category = 'Lomba'")
            active_lomba = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM opportunities WHERE is_active = 1 AND category = 'Beasiswa'")
            active_beasiswa = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM guild_settings")
            total_guilds = cursor.fetchone()[0]

            return {
                "total_items": total_items,
                "active_lomba": active_lomba,
                "active_beasiswa": active_beasiswa,
                "total_guilds": total_guilds,
            }
