"""Importers for public parallel corpora and term bases (UN, EU) into the translation memory / glossary.

Formats
  TMX    DGT-TM, JRC-Acquis, UN Parallel Corpus (OPUS TMX), Europarl (OPUS TMX); .gz accepted
  Moses  two line-aligned text files, one per language (OPUS exports of UNPC, Europarl, MultiUN)
  TBX    IATE and UNTERM term-base exports (TBX 2/3, namespace tolerant); .gz accepted

All readers stream, so multi-gigabyte files do not need to fit in memory. The files themselves are
not shipped: download them from the publishers (see lab/CORPORA.md) and point the importers at them.
"""
from __future__ import annotations

import gzip
import itertools
import re
from pathlib import Path
from typing import Iterable, Iterator
from xml.etree import ElementTree as ET

from .glossary import Glossary, Term
from .tm import TranslationMemory

LANGS = ("ar", "fr", "en", "nl")
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_INLINE = {"bpt", "ept", "ph", "it", "ut", "sub"}  # TMX inline markup: keep tail text, drop content


def lang_code(raw: str) -> str:
    """'FR-FR' / 'fr_CA' / 'EN-GB' -> 'fr' / 'fr' / 'en'."""
    return re.split(r"[-_]", raw.strip().lower())[0]


def _open(path: str | Path):
    p = str(path)
    return gzip.open(p, "rb") if p.endswith(".gz") else open(p, "rb")


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _seg_text(seg: ET.Element) -> str:
    parts = [seg.text or ""]
    for child in seg:
        if _local(child.tag) not in _INLINE:
            parts.append(_seg_text(child))
        parts.append(child.tail or "")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def iter_tmx(path: str | Path, langs: Iterable[str] = LANGS) -> Iterator[dict[str, str]]:
    """Yield one {lang: text} dict per translation unit, restricted to `langs`."""
    wanted = set(langs)
    with _open(path) as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if _local(el.tag) != "tu":
                continue
            unit: dict[str, str] = {}
            for tuv in el:
                if _local(tuv.tag) != "tuv":
                    continue
                lang = lang_code(tuv.get(_XML_LANG) or tuv.get("lang") or "")
                seg = next((c for c in tuv if _local(c.tag) == "seg"), None)
                if lang in wanted and seg is not None and lang not in unit:
                    text = _seg_text(seg)
                    if text:
                        unit[lang] = text
            el.clear()
            if len(unit) >= 2:
                yield unit


def _pairs(unit: dict[str, str], pairs: Iterable[tuple[str, str]] | None):
    if pairs is None:
        pairs = itertools.permutations(unit, 2)
    for s, t in pairs:
        if s in unit and t in unit:
            yield unit[s], unit[t], s, t


def import_tmx(tm: TranslationMemory, path: str | Path, langs: Iterable[str] = LANGS,
               pairs: Iterable[tuple[str, str]] | None = None, max_len: int = 1500) -> int:
    """Load a TMX file; both directions of every language pair unless `pairs` restricts them.

    Segments longer than `max_len` characters are skipped (usually mis-alignments or tables).
    """
    pairs = list(pairs) if pairs is not None else None
    rows = ((s, t, sl, tl) for unit in iter_tmx(path, langs) for s, t, sl, tl in _pairs(unit, pairs)
            if len(s) <= max_len and len(t) <= max_len)
    return tm.add_many(rows, origin=Path(path).name)


def import_moses(tm: TranslationMemory, src_file: str | Path, tgt_file: str | Path,
                 src_lang: str, tgt_lang: str, both_directions: bool = True, max_len: int = 1500) -> int:
    """Load two line-aligned plain-text files (line N of one is the translation of line N of the other)."""
    def lines(p):
        with _open(p) as f:
            for raw in f:
                yield raw.decode("utf-8", "replace").rstrip("\n")

    def rows():
        for s, t in zip(lines(src_file), lines(tgt_file)):
            s, t = s.strip(), t.strip()
            if not s or not t or len(s) > max_len or len(t) > max_len:
                continue
            yield s, t, src_lang, tgt_lang
            if both_directions:
                yield t, s, tgt_lang, src_lang
    return tm.add_many(rows(), origin=Path(src_file).name)


def iter_tbx(path: str | Path) -> Iterator[dict]:
    """Yield {'domain': str, 'terms': {lang: [term, ...]}} for every termEntry."""
    with _open(path) as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if _local(el.tag) != "termEntry":
                continue
            domain, terms = "", {}
            for node in el.iter():
                kind = _local(node.tag)
                if kind in ("descrip", "descripGrp") and (node.get("type") or "") in ("subjectField", "domain"):
                    domain = domain or (node.text or "").strip()
                elif kind == "langSet":
                    lang = lang_code(node.get(_XML_LANG) or node.get("lang") or "")
                    for t in node.iter():
                        if _local(t.tag) == "term" and (t.text or "").strip():
                            bucket = terms.setdefault(lang, [])
                            text = re.sub(r"\s+", " ", t.text).strip()
                            if text not in bucket:
                                bucket.append(text)
            el.clear()
            if len(terms) >= 2:
                yield {"domain": domain, "terms": terms}


def tbx_to_glossary(path: str | Path, src_lang: str, tgt_lang: str, gloss: Glossary | None = None,
                    max_variants: int = 3) -> Glossary:
    """Build a glossary src_lang -> tgt_lang from a TBX term base (variants joined as 'a / b')."""
    gloss = gloss or Glossary()
    origin = Path(path).name
    for entry in iter_tbx(path):
        srcs, tgts = entry["terms"].get(src_lang), entry["terms"].get(tgt_lang)
        if not srcs or not tgts:
            continue
        target = " / ".join(tgts[:max_variants])
        for s in srcs:
            gloss.add(Term(s, target, domain=entry["domain"], origin=origin))
    return gloss
