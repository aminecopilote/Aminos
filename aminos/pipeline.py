"""Multi-pass translation pipeline with terminology enforcement and structural checks.

Modes
  fast    one draft, then deterministic checks (draft quality only)
  normal  draft -> deterministic checks (glossary + numbers) -> correction pass if any issue
  hard    draft -> back-translation -> comparison -> correction (also fed with deterministic issues)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import checks, prompts
from .glossary import Glossary
from .llm import Chat
from .tm import TranslationMemory

MODES = ("fast", "normal", "hard")


@dataclass
class ChunkResult:
    sources: list[str]
    translations: list[str]
    issues: list[str] = field(default_factory=list)
    comparison: str = ""
    passes: int = 1


def chunk_paragraphs(paragraphs: list[str], max_chars: int = 1800) -> list[list[str]]:
    chunks, cur, size = [], [], 0
    for p in paragraphs:
        if cur and size + len(p) > max_chars:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p)
    if cur:
        chunks.append(cur)
    return chunks


def split_segments(reply: str, n: int) -> list[str]:
    """Split on the delimiter; pad or truncate to exactly n segments."""
    parts = [p.strip() for p in reply.split(prompts.DELIMITER)]
    return (parts + [""] * n)[:n]


def deterministic_issues(gloss: Glossary, sources: list[str], translations: list[str]) -> list[str]:
    issues = []
    for i, (s, t) in enumerate(zip(sources, translations), 1):
        if not t.strip():
            issues.append(f"Segment {i} : traduction vide")
            continue
        for term in gloss.missing_in(s, t):
            issues.append(f"Segment {i} : « {term.source} » doit être traduit par « {term.target} »")
        for msg in checks.compare(s, t).issues():
            issues.append(f"Segment {i} : {msg}")
    return issues


def translate_chunk(chat: Chat, sources: list[str], source_lang: str, target_lang: str,
                    gloss: Glossary | None = None, mode: str = "normal", jurisdiction: str = "") -> ChunkResult:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    gloss = gloss or Glossary()
    joined = f"\n{prompts.DELIMITER}\n".join(sources)
    system = prompts.system_prompt(source_lang, target_lang, gloss.prompt_block(joined), jurisdiction)
    thread: list[dict] = []

    def ask(msg: str) -> str:
        thread.append({"role": "user", "content": msg})
        reply = chat(thread, system)
        thread.append({"role": "assistant", "content": reply})
        return reply

    final = ask(prompts.translate(joined))
    translations = split_segments(final, len(sources))
    result = ChunkResult(sources, translations)
    result.issues = deterministic_issues(gloss, sources, translations)

    if mode == "fast":
        return result

    comparison = ""
    if mode == "hard":
        ask(prompts.back_translate(source_lang))
        comparison = ask(prompts.compare())
        result.comparison = comparison

    needs_fix = bool(result.issues) or (mode == "hard" and comparison.strip().rstrip(".").upper() != "RAS")
    if needs_fix:
        fixed = ask(prompts.correct(target_lang, "\n".join(result.issues)))
        result.translations = split_segments(fixed, len(sources))
        result.passes += 1
        result.issues = deterministic_issues(gloss, sources, result.translations)
    return result


def translate_document(chat: Chat, paragraphs: list[str], source_lang: str, target_lang: str,
                       gloss: Glossary | None = None, mode: str = "normal", jurisdiction: str = "",
                       max_chars: int = 1800, tm: TranslationMemory | None = None,
                       reuse_threshold: float = 0.98) -> list[str]:
    """Translate paragraphs; returns one translation per input paragraph.

    With a translation memory, paragraphs matching >= reuse_threshold are reused without
    calling the model; new translations are stored back in the memory.
    """
    out: list[str | None] = [None] * len(paragraphs)
    todo: list[int] = []
    for i, para in enumerate(paragraphs):
        hit = tm.lookup(para, source_lang, target_lang, reuse_threshold, 1) if tm else []
        if hit:
            out[i] = hit[0].target
        else:
            todo.append(i)
    for chunk in chunk_paragraphs([paragraphs[i] for i in todo], max_chars):
        r = translate_chunk(chat, chunk, source_lang, target_lang, gloss, mode, jurisdiction)
        for src, tgt in zip(chunk, r.translations):
            idx = todo.pop(0)
            out[idx] = tgt
            if tm and not r.issues:
                tm.add(src, tgt, source_lang, target_lang)
    return [t or "" for t in out]
