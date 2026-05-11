"""
================================================================
  database.py  —  SQLite database layer
================================================================
"""

import os
import time
import sqlite3
import threading

from config import ADMIN_ID


class Database:
    _local = threading.local()

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

    # ── Connection (one per thread) ───────────────────────────
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                os.path.join("data", "bot.db"),
                check_same_thread=False,
                timeout=10,
            )
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    # ── Init tables ───────────────────────────────────────────
    def init(self) -> None:
        cur = self._conn().cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                hash       TEXT PRIMARY KEY,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS processing (
                user_id    INTEGER PRIMARY KEY,
                started_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS vip_users (
                user_id    INTEGER PRIMARY KEY,
                expires_at INTEGER,
                granted_by INTEGER,
                granted_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS vip_global (
                id         INTEGER PRIMARY KEY CHECK (id=1),
                expires_at INTEGER,
                enabled_by INTEGER,
                enabled_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id  INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at INTEGER
            );
        """)
        self._conn().commit()

        # إضافة الأدمن الرئيسي تلقائياً
        cur.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (ADMIN_ID, ADMIN_ID, int(time.time())),
        )
        self._conn().commit()

    # ── Duplicate-request guard ───────────────────────────────
    def check_and_insert_request(self, hash_: str) -> bool:
        """Returns True if this request is new (not a duplicate)."""
        now = int(time.time())
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM requests WHERE created_at < ?", (now - 5,))
        cur.execute("SELECT 1 FROM requests WHERE hash = ?", (hash_,))
        if cur.fetchone():
            conn.commit()
            return False
        cur.execute(
            "INSERT INTO requests (hash, created_at) VALUES (?, ?)", (hash_, now)
        )
        conn.commit()
        return True

    # ── Busy guard ────────────────────────────────────────────
    def is_user_free(self, uid: int) -> bool:
        now  = int(time.time())
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM processing WHERE started_at < ?", (now - 300,))
        conn.commit()
        cur.execute("SELECT 1 FROM processing WHERE user_id = ?", (uid,))
        return cur.fetchone() is None

    def lock_user(self, uid: int) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO processing (user_id, started_at) VALUES (?, ?)",
            (uid, int(time.time())),
        )
        conn.commit()

    def unlock_user(self, uid: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM processing WHERE user_id = ?", (uid,))
        conn.commit()

    # ── Raw connection access ─────────────────────────────────
    def get_conn(self) -> sqlite3.Connection:
        return self._conn()
