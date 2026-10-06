"""Command line: aminos glossary import|find|check ... / aminos translate ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import checks
from .glossary import Glossary, import_path


def _read_paragraphs(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        import docx
        return [p.text for p in docx.Document(str(path)).paragraphs if p.text.strip()]
    text = path.read_text(encoding="utf-8")
    return [p.strip() for p in text.split("\n\n") if p.strip()] if "\n\n" in text else [
        l.strip() for l in text.splitlines() if l.strip()]


def _cmd_import(a) -> int:
    g = import_path(a.path, (a.src_col, a.tgt_col))
    g.save(a.out)
    print(f"{len(g)} termes enregistrés dans {a.out}; {len(g.conflicts)} conflit(s).")
    for old, new in g.conflicts[:20]:
        print(f"  conflit : {old.source} => {old.target} ({old.origin}) / {new.target} ({new.origin})")
    return 0


def _cmd_find(a) -> int:
    g = Glossary.load(a.glossary)
    text = Path(a.file).read_text(encoding="utf-8")
    for t in g.find(text):
        print(f"{t.source}\t{t.target}")
    return 0


def _cmd_check(a) -> int:
    g = Glossary.load(a.glossary) if a.glossary else Glossary()
    src, tgt = Path(a.source).read_text(encoding="utf-8"), Path(a.translation).read_text(encoding="utf-8")
    issues = checks.compare(src, tgt).issues() + [
        f"« {t.source} » doit être traduit par « {t.target} »" for t in g.missing_in(src, tgt)]
    print("\n".join(issues) or "RAS")
    return 1 if issues else 0


def _cmd_translate(a) -> int:
    from .docx_out import build_docx
    from .llm import anthropic_chat
    from .pipeline import translate_document
    g = Glossary.load(a.glossary) if a.glossary else Glossary()
    paragraphs = _read_paragraphs(Path(a.file))
    results = translate_document(anthropic_chat(a.model), paragraphs, a.source, a.target, g, a.mode, a.jurisdiction)
    out = [t for r in results for t in r.translations]
    build_docx(out, a.target, a.out)
    for r in results:
        for i in r.issues:
            print("ATTENTION :", i, file=sys.stderr)
    print(f"{len(out)} paragraphes écrits dans {a.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aminos")
    sub = ap.add_subparsers(dest="cmd", required=True)

    gp = sub.add_parser("glossary-import", help="importer un fichier ou dossier de glossaires")
    gp.add_argument("path"); gp.add_argument("-o", "--out", default="glossary.json")
    gp.add_argument("--src-col", type=int, default=0); gp.add_argument("--tgt-col", type=int, default=1)
    gp.set_defaults(fn=_cmd_import)

    fp = sub.add_parser("glossary-find", help="termes du glossaire présents dans un texte")
    fp.add_argument("glossary"); fp.add_argument("file"); fp.set_defaults(fn=_cmd_find)

    cp = sub.add_parser("check", help="contrôle déterministe source/traduction (nombres, terminologie)")
    cp.add_argument("source"); cp.add_argument("translation"); cp.add_argument("-g", "--glossary")
    cp.set_defaults(fn=_cmd_check)

    tp = sub.add_parser("translate", help="traduire un .docx/.txt vers un .docx")
    tp.add_argument("file"); tp.add_argument("-o", "--out", required=True)
    tp.add_argument("-s", "--source", required=True); tp.add_argument("-t", "--target", required=True)
    tp.add_argument("-g", "--glossary"); tp.add_argument("-m", "--mode", choices=["fast", "normal", "hard"], default="normal")
    tp.add_argument("--model", default="claude-sonnet-5-5"); tp.add_argument("--jurisdiction", default="")
    tp.set_defaults(fn=_cmd_translate)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
