"""Deterministic structural checks between a source text and its translation."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .normalize import normalize

_NUMBER = re.compile(r"\d+(?:[.,/]\d+)*")
_ARTICLE = re.compile(r"(?:article|art\.|المادة|الفصل|chapter|section|§)\s*\d+", re.I)


@dataclass
class Report:
    missing_numbers: list[str] = field(default_factory=list)
    extra_numbers: list[str] = field(default_factory=list)
    paragraph_mismatch: tuple[int, int] | None = None
    ok: bool = True

    def issues(self) -> list[str]:
        out = []
        if self.missing_numbers:
            out.append("Nombres absents de la traduction : " + ", ".join(self.missing_numbers))
        if self.extra_numbers:
            out.append("Nombres ajoutés dans la traduction : " + ", ".join(self.extra_numbers))
        if self.paragraph_mismatch:
            out.append("Nombre de segments : source %d, traduction %d" % self.paragraph_mismatch)
        return out


def numbers(text: str) -> Counter:
    return Counter(n.strip(".,") for n in _NUMBER.findall(normalize(text)))


def compare(source: str, translation: str, src_segments: int | None = None, tgt_segments: int | None = None) -> Report:
    s, t = numbers(source), numbers(translation)
    r = Report(missing_numbers=sorted((s - t).elements()), extra_numbers=sorted((t - s).elements()))
    if src_segments is not None and tgt_segments is not None and src_segments != tgt_segments:
        r.paragraph_mismatch = (src_segments, tgt_segments)
    r.ok = not (r.missing_numbers or r.extra_numbers or r.paragraph_mismatch)
    return r


def count_articles(text: str) -> int:
    return len(_ARTICLE.findall(text))
