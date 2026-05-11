"""
================================================================
  vip.py  —  VIP & Admin management
================================================================
"""

import re
import time

from config import ADMIN_ID
from database import Database


class VipManager:
    def __init__(self, db: Database):
        self.db   = db
        self.conn = db.get_conn()

    # ── VIP check ─────────────────────────────────────────────
    def is_vip(self, uid: int) -> bool:
        # Admins are always VIP
        if self.is_admin(uid):
            return True

        now = int(time.time())

        # Global VIP active?
        row = self.conn.execute(
            "SELECT expires_at FROM vip_global WHERE id=1"
        ).fetchone()
        if row and row["expires_at"] > now:
            return True

        # Personal VIP?
        row = self.conn.execute(
            "SELECT expires_at FROM vip_users WHERE user_id=?", (uid,)
        ).fetchone()
        if row and row["expires_at"] > now:
            return True

        return False

    # ── Grant / revoke personal VIP ───────────────────────────
    def grant_vip(self, uid: int, seconds: int, granted_by: int) -> bool:
        expires = int(time.time()) + seconds
        self.conn.execute(
            "INSERT OR REPLACE INTO vip_users (user_id, expires_at, granted_by, granted_at) "
            "VALUES (?,?,?,?)",
            (uid, expires, granted_by, int(time.time())),
        )
        self.conn.commit()
        return True

    def revoke_vip(self, uid: int) -> bool:
        self.conn.execute("DELETE FROM vip_users WHERE user_id=?", (uid,))
        self.conn.commit()
        return True

    # ── Global VIP ────────────────────────────────────────────
    def grant_global_vip(self, seconds: int, enabled_by: int) -> bool:
        expires = int(time.time()) + seconds
        self.conn.execute(
            "INSERT OR REPLACE INTO vip_global (id, expires_at, enabled_by, enabled_at) "
            "VALUES (1,?,?,?)",
            (expires, enabled_by, int(time.time())),
        )
        self.conn.commit()
        return True

    def revoke_global_vip(self) -> bool:
        self.conn.execute("DELETE FROM vip_global WHERE id=1")
        self.conn.commit()
        return True

    # ── Expiry helpers ────────────────────────────────────────
    def get_vip_expiry(self, uid: int) -> int | None:
        now = int(time.time())

        row = self.conn.execute(
            "SELECT expires_at FROM vip_global WHERE id=1"
        ).fetchone()
        if row and row["expires_at"] > now:
            return row["expires_at"]

        row = self.conn.execute(
            "SELECT expires_at FROM vip_users WHERE user_id=?", (uid,)
        ).fetchone()
        if row and row["expires_at"] > now:
            return row["expires_at"]

        return None

    def get_global_vip_info(self) -> dict | None:
        now = int(time.time())
        row = self.conn.execute(
            "SELECT * FROM vip_global WHERE id=1"
        ).fetchone()
        if row and row["expires_at"] > now:
            return dict(row)
        return None

    # ── Admin management ──────────────────────────────────────
    def is_admin(self, uid: int) -> bool:
        if uid == ADMIN_ID:
            return True
        row = self.conn.execute(
            "SELECT 1 FROM admins WHERE user_id=?", (uid,)
        ).fetchone()
        return row is not None

    def add_admin(self, uid: int, added_by: int) -> bool:
        self.conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?,?,?)",
            (uid, added_by, int(time.time())),
        )
        self.conn.commit()
        return True

    def remove_admin(self, uid: int) -> bool:
        if uid == ADMIN_ID:
            return False
        self.conn.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        self.conn.commit()
        return True

    def list_admins(self) -> list[int]:
        rows = self.conn.execute("SELECT user_id FROM admins").fetchall()
        return [r["user_id"] for r in rows]

    # ── Duration parser ───────────────────────────────────────
    @staticmethod
    def parse_duration(dur: str) -> int | None:
        """Parse '7d', '24h', '30m' → seconds."""
        m = re.match(r"^(\d+)(d|h|m)$", dur.strip().lower())
        if not m:
            return None
        n, unit = int(m.group(1)), m.group(2)
        return {"d": 86400, "h": 3600, "m": 60}[unit] * n
