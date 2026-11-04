"""Translation memory: SQLite store, exact lookup, fuzzy lookup over an FTS5 candidate index.

The fuzzy search no longer scans the whole table: FTS5 returns the few hundred segments sharing the
rarest words of the query, and only those are scored with difflib. This keeps lookups fast on
corpus-sized memories (UN, EU) while the API stays the same.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Iterator

from .normalize import normalize

_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass
class Match:
    source: str
    target: str
    score: float


class TranslationMemory:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self._migrate()
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tm (
                id INTEGER PRIMARY KEY, norm TEXT NOT NULL, src_lang TEXT NOT NULL, tgt_lang TEXT NOT NULL,
                source TEXT NOT NULL, target TEXT NOT NULL, origin TEXT NOT NULL DEFAULT '',
                UNIQUE (norm, src_lang, tgt_lang));
            CREATE INDEX IF NOT EXISTS tm_pair ON tm (src_lang, tgt_lang);
            CREATE VIRTUAL TABLE IF NOT EXISTS tm_fts USING fts5(
                norm, content='tm', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
        """)
        if self._old:
            self.db.execute("INSERT INTO tm_fts (tm_fts) VALUES ('rebuild')")
        self.db.commit()

    def _migrate(self) -> None:
        """Upgrade a memory created by the first version (no id column, no index)."""
        cols = [r[1] for r in self.db.execute("PRAGMA table_info(tm)")]
        if cols and "id" not in cols:
            self.db.execute("ALTER TABLE tm RENAME TO tm_old")
            self.db.execute("DROP INDEX IF EXISTS tm_pair")
            self._old = True
        else:
            self._old = False
        if self._old:
            self.db.executescript("""
                CREATE TABLE tm (id INTEGER PRIMARY KEY, norm TEXT NOT NULL, src_lang TEXT NOT NULL,
                    tgt_lang TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL,
                    origin TEXT NOT NULL DEFAULT '', UNIQUE (norm, src_lang, tgt_lang));
                INSERT INTO tm (norm, src_lang, tgt_lang, source, target)
                    SELECT norm, src_lang, tgt_lang, source, target FROM tm_old;
                DROP TABLE tm_old;
            """)

    # ---- writing ---------------------------------------------------
    def _insert(self, source: str, target: str, src_lang: str, tgt_lang: str, origin: str) -> bool:
        source, target = source.strip(), target.strip()
        if not source or not target:
            return False
        norm = normalize(source)
        if not norm:
            return False
        cur = self.db.execute(
            "INSERT OR IGNORE INTO tm (norm, src_lang, tgt_lang, source, target, origin) VALUES (?,?,?,?,?,?)",
            (norm, src_lang, tgt_lang, source, target, origin))
        if cur.rowcount:  # new segment: index it
            self.db.execute("INSERT INTO tm_fts (rowid, norm) VALUES (?, ?)", (cur.lastrowid, norm))
        else:  # same normalised source already stored: the newer translation replaces the older
            self.db.execute("UPDATE tm SET source=?, target=?, origin=? WHERE norm=? AND src_lang=? AND tgt_lang=?",
                            (source, target, origin, norm, src_lang, tgt_lang))
        return True

    def add(self, source: str, target: str, src_lang: str, tgt_lang: str, origin: str = "") -> None:
        if self._insert(source, target, src_lang, tgt_lang, origin):
            self.db.commit()

    def add_many(self, rows: Iterable[tuple[str, str, str, str]], origin: str = "", batch: int = 5000) -> int:
        """rows of (source, target, src_lang, tgt_lang); one commit per batch."""
        n = 0
        for i, (s, t, sl, tl) in enumerate(rows, 1):
            n += self._insert(s, t, sl, tl, origin)
            if i % batch == 0:
                self.db.commit()
        self.db.commit()
        return n

    def __len__(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM tm").fetchone()[0]

    def stats(self) -> dict[str, int]:
        return {f"{s}>{t}": n for s, t, n in
                self.db.execute("SELECT src_lang, tgt_lang, COUNT(*) FROM tm GROUP BY 1, 2 ORDER BY 1, 2")}

    # ---- reading ---------------------------------------------------
    @staticmethod
    def _query(norm: str, max_terms: int = 10) -> str:
        words = sorted(set(_WORD.findall(norm)), key=lambda w: -len(w))[:max_terms]
        return " OR ".join('"%s"' % w.replace('"', "") for w in words)

    def lookup(self, source: str, src_lang: str, tgt_lang: str, threshold: float = 0.75,
               limit: int = 3, candidates: int = 300) -> list[Match]:
        norm = normalize(source)
        if not norm:
            return []
        exact = self.db.execute("SELECT source, target FROM tm WHERE norm=? AND src_lang=? AND tgt_lang=?",
                                (norm, src_lang, tgt_lang)).fetchone()
        out = [Match(exact[0], exact[1], 1.0)] if exact else []
        query = self._query(norm)
        if query and len(out) < limit:
            rows = self.db.execute(
                "SELECT tm.norm, tm.source, tm.target FROM tm_fts JOIN tm ON tm.id = tm_fts.rowid "
                "WHERE tm_fts MATCH ? AND tm.src_lang=? AND tm.tgt_lang=? ORDER BY rank LIMIT ?",
                (query, src_lang, tgt_lang, candidates)).fetchall()
            sm = SequenceMatcher(autojunk=False)
            sm.set_seq2(norm)
            for n, s, t in rows:
                if n == norm:
                    continue
                if 2 * min(len(n), len(norm)) / (len(n) + len(norm)) < threshold:
                    continue  # ratio() can never exceed this bound, so skip the costly comparison
                sm.set_seq1(n)
                score = sm.ratio()
                if score >= threshold:
                    out.append(Match(s, t, score))
        return sorted(out, key=lambda m: -m.score)[:limit]

    # ---- exchange --------------------------------------------------
    def export_tsv(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for s, t in self.db.execute("SELECT source, target FROM tm"):
                f.write(f"{s.replace(chr(9), ' ')}\t{t.replace(chr(9), ' ')}\n")

    def import_tsv(self, path: str, src_lang: str, tgt_lang: str) -> int:
        def rows() -> Iterator[tuple[str, str, str, str]]:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2:
                        yield parts[0], parts[1], src_lang, tgt_lang
        return self.add_many(rows(), origin=path)
