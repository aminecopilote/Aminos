"""API tokens for automation (n8n and the like). Only the SHA-256 of a token is stored; the token is shown once.

Scopes: read (GET), write (GET, POST, PUT; never DELETE), system (only /erp/api/system/*: health, backup, jobs).
A read or write token is bound to one firm; a system token is global and is created on the server by its administrator.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

SCOPES = ("read", "write", "system")
PREFIX = "amn_"


class TokenStore:
    def __init__(self, data_dir: str | Path):
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self.path = str(Path(data_dir) / "api-tokens.sqlite")
        db = self._db()
        try:
            db.executescript("""CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY, label TEXT NOT NULL, hash TEXT UNIQUE NOT NULL, scope TEXT NOT NULL, org TEXT NOT NULL,
                created INTEGER NOT NULL, last_used INTEGER, revoked INTEGER NOT NULL DEFAULT 0)""")
            db.commit()
        finally:
            db.close()

    def _db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, scope: str, org: str = "", label: str = "") -> str:
        if scope not in SCOPES:
            raise ValueError(f"portée inconnue : {scope}")
        if scope != "system" and not org:
            raise ValueError("un jeton read/write est lié à un cabinet (--org)")
        token = PREFIX + secrets.token_urlsafe(32)
        db = self._db()
        try:
            db.execute("INSERT INTO tokens (label, hash, scope, org, created) VALUES (?,?,?,?,?)",
                       (label[:60], self._hash(token), scope, "" if scope == "system" else org, int(time.time())))
            db.commit()
        finally:
            db.close()
        return token

    def verify(self, token: str, now: float | None = None) -> dict | None:
        """-> {'id', 'scope', 'org', 'label'} for a live token, else None. last_used is refreshed at most once a minute."""
        if not token.startswith(PREFIX) or len(token) > 100:
            return None
        now = int(now if now is not None else time.time())
        db = self._db()
        try:
            row = db.execute("SELECT * FROM tokens WHERE hash=? AND revoked=0", (self._hash(token),)).fetchone()
            if not row:
                return None
            if not row["last_used"] or now - row["last_used"] > 60:
                db.execute("UPDATE tokens SET last_used=? WHERE id=?", (now, row["id"]))
                db.commit()
            return {"id": row["id"], "scope": row["scope"], "org": row["org"], "label": row["label"]}
        finally:
            db.close()

    def revoke(self, token_id: int) -> bool:
        db = self._db()
        try:
            cur = db.execute("UPDATE tokens SET revoked=1 WHERE id=? AND revoked=0", (token_id,))
            db.commit()
            return bool(cur.rowcount)
        finally:
            db.close()

    def list(self) -> list[dict]:
        db = self._db()
        try:
            return [dict(r) | {"hash": r["hash"][:8] + "…"} for r in db.execute("SELECT * FROM tokens ORDER BY id")]
        finally:
            db.close()
