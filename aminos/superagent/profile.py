"""Agent profile: instructions, searchable memory, skills and parameters, all kept in one directory.

Layout of a profile directory
  instructions.md   house rules injected into every translation prompt (seeded with the legal-translation style)
  params.json       defaults: providers, mode, jurisdiction, translator identity, stamp/signature files
  memory.sqlite     notes (FTS5): preferences, client rules, past decisions
  skills/           text-only SKILL.md folders (see aminos.skills for the pinned third-party installer)

Nothing here reads a Claude account: the account cannot be read from a server. `import_claude_export` takes the
files the user exported or copied themselves (CLAUDE.md, memory notes, preferences, skill folders).
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from ..normalize import normalize

DEFAULT_INSTRUCTIONS = """\
Traduction juridique fidèle, mot à mot, rien d'omis. Document officiel (droit marocain, européen ou américain).
- Gras : noms propres, villes, pays/États, titres, dates clés. Prénom en gras, NOM en gras et majuscules.
- Traduire le texte des cachets, sceaux et tampons ; signaler logos, photos d'identité et autres éléments visuels entre crochets.
- Aucune annotation, explication ni commentaire. Aucun mot de la langue source, sauf terme sans équivalent exact : équivalent
  fonctionnel le plus proche, terme d'origine entre [crochets] seulement si indispensable.
- Vocabulaire juridique exact et à jour de la juridiction cible ; ton formel, rigoureux, neutre ; style naturel.
- Conserver la structure, la mise en page et la numérotation des articles. Écriture de droite à gauche pour l'arabe.
"""

DEFAULT_PARAMS = {
    "providers": ["anthropic"],
    "mode": "normal",
    "jurisdiction": "",
    "languages": ["ar", "fr", "en", "nl"],
    "translator": {"name": "", "capacity": "", "registration": "", "place": ""},
    "stamp_image": "",
    "signature_image": "",
    "cert": "", "key": "", "ca": "",
    "memory_notes_in_prompt": 6,
}

_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
_INSTRUCTION_FILES = {"claude.md", "agents.md", "instructions.md", "preferences.md", "preferences.txt", "custom-instructions.md"}


@dataclass
class Note:
    id: int
    text: str
    tags: str
    origin: str
    ts: float


class Profile:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "skills").mkdir(exist_ok=True)
        if not (self.root / "instructions.md").exists():
            (self.root / "instructions.md").write_text(DEFAULT_INSTRUCTIONS, encoding="utf-8")
        if not (self.root / "params.json").exists():
            self.save_params(DEFAULT_PARAMS)
        self.db = sqlite3.connect(self.root / "memory.sqlite")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, norm TEXT UNIQUE NOT NULL, text TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '', origin TEXT NOT NULL DEFAULT '', ts REAL NOT NULL);
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(norm, content='notes', content_rowid='id',
                tokenize='unicode61 remove_diacritics 2');
        """)

    # ---- parameters and instructions ------------------------------
    @property
    def params(self) -> dict:
        data = json.loads((self.root / "params.json").read_text(encoding="utf-8"))
        return {**DEFAULT_PARAMS, **data, "translator": {**DEFAULT_PARAMS["translator"], **data.get("translator", {})}}

    def save_params(self, params: dict) -> None:
        (self.root / "params.json").write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_param(self, key: str, value) -> None:
        p = self.params
        node, parts = p, key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        self.save_params(p)

    @property
    def instructions(self) -> str:
        return (self.root / "instructions.md").read_text(encoding="utf-8")

    def append_instructions(self, text: str, origin: str = "") -> None:
        cur = self.instructions.rstrip()
        if text.strip() and text.strip() not in cur:
            head = f"\n\n## Importé de {origin}\n" if origin else "\n\n"
            (self.root / "instructions.md").write_text(cur + head + text.strip() + "\n", encoding="utf-8")

    # ---- memory ----------------------------------------------------
    def remember(self, text: str, tags: str = "", origin: str = "") -> bool:
        text = text.strip()
        norm = normalize(text)
        if not norm:
            return False
        cur = self.db.execute("INSERT OR IGNORE INTO notes (norm, text, tags, origin, ts) VALUES (?,?,?,?,?)",
                              (norm, text, tags, origin, time.time()))
        if cur.rowcount:
            self.db.execute("INSERT INTO notes_fts (rowid, norm) VALUES (?, ?)", (cur.lastrowid, norm))
        self.db.commit()
        return bool(cur.rowcount)

    def forget(self, note_id: int) -> bool:
        row = self.db.execute("SELECT norm FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            return False
        self.db.execute("INSERT INTO notes_fts (notes_fts, rowid, norm) VALUES ('delete', ?, ?)", (note_id, row[0]))
        self.db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.db.commit()
        return True

    def notes(self) -> list[Note]:
        return [Note(*r) for r in self.db.execute("SELECT id, text, tags, origin, ts FROM notes ORDER BY id")]

    def search(self, query: str, limit: int = 6) -> list[Note]:
        words = sorted(set(re.findall(r"\w+", normalize(query))), key=lambda w: -len(w))[:12]
        if not words:
            return []
        q = " OR ".join('"%s"' % w.replace('"', "") for w in words)
        rows = self.db.execute(
            "SELECT n.id, n.text, n.tags, n.origin, n.ts FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid "
            "WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?", (q, limit)).fetchall()
        return [Note(*r) for r in rows]

    def prompt_extra(self, sample_text: str = "") -> str:
        """What goes into the model prompt: house instructions + the memory notes closest to the text."""
        parts = [self.instructions.strip()]
        k = int(self.params["memory_notes_in_prompt"])
        notes = self.search(sample_text[:4000], k) if sample_text and k else []
        if notes:
            parts.append("Notes de mémoire pertinentes :\n" + "\n".join(f"- {n.text}" for n in notes))
        return "\n\n".join(parts)

    # ---- skills ----------------------------------------------------
    def skills(self) -> list[str]:
        return sorted(p.parent.name for p in (self.root / "skills").glob("*/SKILL.md"))

    def import_skill_dir(self, src: str | Path) -> tuple[str, list[str]]:
        """Copy one skill folder as text only. Scripts and binaries are skipped (listed in the second value)."""
        src = Path(src)
        name = _NAME.sub("-", src.name).strip("-.") or "skill"
        dst = self.root / "skills" / name
        skipped: list[str] = []
        for f in sorted(src.rglob("*")):
            if not f.is_file() or f.is_symlink():
                continue
            rel = f.relative_to(src)
            if f.suffix.lower() in _TEXT_SUFFIXES and f.stat().st_size <= 2_000_000:
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dst / rel)
            else:
                skipped.append(str(rel))
        if not (dst / "SKILL.md").exists():
            shutil.rmtree(dst, ignore_errors=True)
            raise ValueError(f"{src}: pas de SKILL.md")
        return name, skipped

    # ---- import ----------------------------------------------------
    def import_claude_export(self, path: str | Path) -> dict:
        """Import what the user exported by hand: instruction files, memory notes, skill folders.

        - CLAUDE.md / AGENTS.md / preferences.* / instructions.md -> instructions
        - other .md/.txt files -> memory notes, one per paragraph or bullet
        - folders holding a SKILL.md -> skills (text only)
        - conversations.json of a data export is NOT ingested (confidential, large, not memory)
        """
        path = Path(path)
        report = {"instructions": [], "notes": 0, "skills": [], "skipped": []}
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        skill_dirs = {p.parent for p in files if p.name == "SKILL.md"}
        for d in sorted(skill_dirs):
            name, skipped = self.import_skill_dir(d)
            report["skills"].append(name)
            report["skipped"] += [f"{name}/{s}" for s in skipped]
        for f in files:
            if any(d in f.parents or f.parent == d for d in skill_dirs):
                continue
            low = f.name.lower()
            if low == "conversations.json":
                report["skipped"].append(f"{f.name} (conversations non importées)")
                continue
            if f.suffix.lower() not in {".md", ".txt"}:
                report["skipped"].append(f.name)
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if low in _INSTRUCTION_FILES:
                self.append_instructions(text, f.name)
                report["instructions"].append(f.name)
                continue
            for block in _blocks(text):
                report["notes"] += self.remember(block, origin=f.name)
        return report


def _blocks(text: str) -> list[str]:
    """Paragraphs, or bullet lines when the file is a list."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        bullets = [l for l in lines if re.match(r"^([-*•]|\d+[.)])\s+", l)]
        if lines and len(bullets) == len(lines):
            out += [re.sub(r"^([-*•]|\d+[.)])\s+", "", l) for l in lines]
        elif lines:
            out.append(" ".join(l for l in lines if not l.startswith("#")) or "")
    return [b for b in out if len(b) > 3]
