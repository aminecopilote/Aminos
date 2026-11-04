"""Accounts, tenants, quotas and audit. Standard library only.

Design choices
  * No public sign-up: an administrator creates accounts (legal documents are not for anonymous visitors).
  * Passwords: scrypt with a per-user salt, constant-time comparison, minimum length 12.
  * Brute force: after MAX_FAILURES failed logins in LOCK_MINUTES the account refuses logins for that window,
    with the same message as a wrong password. (A determined attacker can therefore lock a known account for
    15 minutes; that trade-off is accepted and documented.)
  * Isolation: every organisation owns a directory derived only from a validated slug, never from user input paths.
  * Audit: per organisation, hash-chained (Ledger). Entries hold who/what/when and a document fingerprint, never
    document text.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from ..notary.ledger import Ledger

MIN_PASSWORD = 12
MAX_FAILURES, LOCK_MINUTES = 5, 15
ROLES = ("admin", "user")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,39}$")
_N, _R, _P = 2 ** 15, 8, 1


class AuthError(Exception):
    pass


class QuotaExceeded(Exception):
    pass


@dataclass(frozen=True)
class User:
    username: str
    org: str
    role: str
    active: bool
    quota_docs_day: int
    quota_chars_day: int
    allow_remote_llm: bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=64 * 1024 * 1024, dklen=32)
    return "scrypt${}${}${}${}${}".format(_N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(h).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                              maxmem=64 * 1024 * 1024, dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


def check_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise AuthError(f"Mot de passe trop court (minimum {MIN_PASSWORD} caractères).")


def new_password() -> str:
    return secrets.token_urlsafe(14)


class SaaSStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        (self.root / "tenants").mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "saas.sqlite", check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, pw_hash TEXT NOT NULL, org TEXT NOT NULL, role TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1, quota_docs_day INTEGER NOT NULL DEFAULT 20,
                quota_chars_day INTEGER NOT NULL DEFAULT 400000, allow_remote_llm INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (username TEXT NOT NULL, ts INTEGER NOT NULL, ok INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS attempts_user ON attempts (username, ts);
            CREATE TABLE IF NOT EXISTS usage (username TEXT NOT NULL, day TEXT NOT NULL,
                docs INTEGER NOT NULL DEFAULT 0, chars INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (username, day));
        """)
        self.db.commit()

    # ---- users ------------------------------------------------------
    @staticmethod
    def _user(row) -> User:
        return User(row[0], row[1], row[2], bool(row[3]), row[4], row[5], bool(row[6]))

    _COLS = "username, org, role, active, quota_docs_day, quota_chars_day, allow_remote_llm"

    def create_user(self, username: str, password: str, org: str, role: str = "user", *,
                    quota_docs_day: int = 20, quota_chars_day: int = 400_000, allow_remote_llm: bool = False) -> User:
        username = username.strip().lower()
        if not _USERNAME.match(username):
            raise AuthError("Identifiant invalide (2 à 40 caractères : lettres minuscules, chiffres, . _ -).")
        if not _SLUG.match(org):
            raise AuthError("Cabinet invalide (1 à 40 caractères : lettres minuscules, chiffres, tirets).")
        if role not in ROLES:
            raise AuthError("Rôle inconnu.")
        check_password_strength(password)
        try:
            self.db.execute("INSERT INTO users VALUES (?,?,?,?,1,?,?,?,?)",
                            (username, hash_password(password), org, role, quota_docs_day, quota_chars_day,
                             int(allow_remote_llm), int(time.time())))
        except sqlite3.IntegrityError as e:
            raise AuthError("Cet identifiant existe déjà.") from e
        self.db.commit()
        self.tenant_dir(org)
        return self.get(username)

    def get(self, username: str) -> User | None:
        row = self.db.execute(f"SELECT {self._COLS} FROM users WHERE username=?", (username,)).fetchone()
        return self._user(row) if row else None

    def list_users(self, org: str | None = None) -> list[User]:
        q, args = f"SELECT {self._COLS} FROM users", ()
        if org is not None:
            q, args = q + " WHERE org=?", (org,)
        return [self._user(r) for r in self.db.execute(q + " ORDER BY org, username", args)]

    def count_users(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def update_user(self, username: str, *, active: bool | None = None, role: str | None = None,
                    quota_docs_day: int | None = None, quota_chars_day: int | None = None,
                    allow_remote_llm: bool | None = None) -> None:
        if role is not None and role not in ROLES:
            raise AuthError("Rôle inconnu.")
        for col, val in (("active", active), ("role", role), ("quota_docs_day", quota_docs_day),
                         ("quota_chars_day", quota_chars_day), ("allow_remote_llm", allow_remote_llm)):
            if val is not None:
                self.db.execute(f"UPDATE users SET {col}=? WHERE username=?", (int(val) if isinstance(val, bool) else val, username))
        self.db.commit()

    def set_password(self, username: str, password: str) -> None:
        check_password_strength(password)
        self.db.execute("UPDATE users SET pw_hash=? WHERE username=?", (hash_password(password), username))
        self.db.commit()

    # ---- login ------------------------------------------------------
    def _locked(self, username: str, now: int) -> bool:
        since = now - LOCK_MINUTES * 60
        fails = self.db.execute("SELECT COUNT(*) FROM attempts WHERE username=? AND ts>=? AND ok=0", (username, since)).fetchone()[0]
        return fails >= MAX_FAILURES

    def authenticate(self, username: str, password: str, now: int | None = None) -> User:
        """Return the active user or raise AuthError with one generic message for every failure cause."""
        now = int(now if now is not None else time.time())
        username = username.strip().lower()
        generic = AuthError("Identifiant ou mot de passe incorrect, ou compte verrouillé.")
        row = self.db.execute("SELECT pw_hash, active FROM users WHERE username=?", (username,)).fetchone()
        locked = self._locked(username, now)
        # always run one scrypt so response time does not reveal whether the account exists
        ok = verify_password(password, row[0] if row else hash_password("dummy-password-for-timing"))
        good = bool(row) and ok and bool(row[1]) and not locked
        if row:
            self.db.execute("INSERT INTO attempts VALUES (?,?,?)", (username, now, int(good)))
            self.db.execute("DELETE FROM attempts WHERE ts < ?", (now - 24 * 3600,))
            self.db.commit()
        if not good:
            raise generic
        return self.get(username)

    # ---- tenants, quotas, audit -------------------------------------
    def tenant_dir(self, org: str) -> Path:
        if not _SLUG.match(org):
            raise AuthError("Cabinet invalide.")
        d = self.root / "tenants" / org
        d.mkdir(parents=True, exist_ok=True)
        return d

    def tm_path(self, user: User) -> str:
        return str(self.tenant_dir(user.org) / "tm.sqlite")

    def audit(self, user: User, action: str, sha256: str = "", detail: str = "", now: float | None = None) -> dict:
        ledger = Ledger(self.tenant_dir(user.org) / "audit.jsonl")
        digest = sha256 or hashlib.sha256(action.encode()).hexdigest()
        return ledger.append(digest, action, {"user": user.username, "detail": detail[:200]}, now=now)

    def audit_ledger(self, org: str) -> Ledger:
        return Ledger(self.tenant_dir(org) / "audit.jsonl")

    @staticmethod
    def _day(now: float | None) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(now if now is not None else time.time()))

    def usage_today(self, username: str, now: float | None = None) -> tuple[int, int]:
        row = self.db.execute("SELECT docs, chars FROM usage WHERE username=? AND day=?", (username, self._day(now))).fetchone()
        return row or (0, 0)

    def consume(self, user: User, chars: int, now: float | None = None) -> None:
        """Count one document of `chars` characters against today's quota, or raise QuotaExceeded."""
        docs, used = self.usage_today(user.username, now)
        if docs + 1 > user.quota_docs_day:
            raise QuotaExceeded(f"Quota quotidien atteint : {user.quota_docs_day} document(s) par jour.")
        if used + chars > user.quota_chars_day:
            raise QuotaExceeded(f"Quota quotidien de caractères dépassé ({used + chars} > {user.quota_chars_day}).")
        self.db.execute("INSERT INTO usage VALUES (?,?,1,?) ON CONFLICT (username, day) DO UPDATE SET "
                        "docs=docs+1, chars=chars+?", (user.username, self._day(now), chars, chars))
        self.db.commit()

    def bootstrap_admin(self, username: str | None, password: str | None, org: str = "admin") -> bool:
        """Create the first administrator from deployment secrets when no account exists yet."""
        if self.count_users() or not username or not password:
            return False
        self.create_user(username, password, org, "admin", quota_docs_day=10 ** 6, quota_chars_day=10 ** 9)
        return True
