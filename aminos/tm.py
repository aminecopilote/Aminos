"""Translation memory: SQLite store with exact and fuzzy (difflib) lookup."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher

from .checks import numbers
from .normalize import normalize


FUZZY_CAP = 0.90


@dataclass
class Match:
    source: str
    target: str
    score: float


class TranslationMemory:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS tm (
            norm TEXT, src_lang TEXT, tgt_lang TEXT, source TEXT, target TEXT,
            PRIMARY KEY (norm, src_lang, tgt_lang))""")

    def add(self, source: str, target: str, src_lang: str, tgt_lang: str) -> None:
        if source.strip() and target.strip():
            self.db.execute("INSERT OR REPLACE INTO tm VALUES (?,?,?,?,?)",
                            (normalize(source), src_lang, tgt_lang, source, target))
            self.db.commit()

    def __len__(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM tm").fetchone()[0]

    def lookup(self, source: str, src_lang: str, tgt_lang: str, threshold: float = 0.75, limit: int = 3) -> list[Match]:
        norm, wanted = normalize(source), numbers(source)
        rows = self.db.execute("SELECT norm, source, target FROM tm WHERE src_lang=? AND tgt_lang=?",
                               (src_lang, tgt_lang)).fetchall()
        out = []
        for n, s, t in rows:
            score = 1.0 if n == norm else SequenceMatcher(None, norm, n, autojunk=False).ratio()
            if n != norm and numbers(s) != wanted:
                score = min(score, FUZZY_CAP)  # different figures/dates: a hint, never a reusable translation
            if score >= threshold:
                out.append(Match(s, t, score))
        return sorted(out, key=lambda m: -m.score)[:limit]

    def export_tsv(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for s, t in self.db.execute("SELECT source, target FROM tm"):
                f.write(f"{s.replace(chr(9), ' ')}\t{t.replace(chr(9), ' ')}\n")

    def import_tsv(self, path: str, src_lang: str, tgt_lang: str) -> int:
        n = 0
        for line in open(path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                self.add(parts[0], parts[1], src_lang, tgt_lang)
                n += 1
        return n
