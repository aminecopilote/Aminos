"""Command line: aminos glossary import|find|check ... / aminos translate ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import checks
from .glossary import Glossary, import_path


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
    from .extract import extract_paragraphs, ocr_claude, ocr_tesseract
    from .providers import build_chat
    from .pipeline import translate_document
    from .tm import TranslationMemory
    g = Glossary.load(a.glossary) if a.glossary else Glossary()
    ocr = {"claude": ocr_claude, "tesseract": lambda: ocr_tesseract(), None: lambda: None}[a.ocr]()
    paragraphs = extract_paragraphs(a.file, ocr)
    tm = TranslationMemory(a.tm) if a.tm else None
    out = translate_document(build_chat(a.provider, a.model, a.allow_free_tier), paragraphs, a.source, a.target, g, a.mode,
                             a.jurisdiction, tm=tm)
    build_docx(out, a.target, a.out)
    print(f"{len(out)} paragraphes écrits dans {a.out}")
    return 0


def _cmd_cert(a) -> int:
    from . import certify as c
    if a.action == "keygen":
        c.make_key(a.key); print(f"clé créée : {a.key} (ne jamais la synchroniser ni la partager)"); return 0
    if a.action == "next-ref":
        print(c.next_ref(a.registry)); return 0
    if a.action == "declaration":
        print(c.declaration(a.source, a.target, a.ref, a.date)); return 0
    if a.action == "eval":
        scores = dict(kv.split("=") for kv in a.scores.split(",")) if a.scores else {}
        ev = c.Evaluation({k: int(v) for k, v in scores.items()}, a.point or [])
        c.write_evaluation(a.file, a.ref, ev)
        print(f"fiche écrite : {a.file} ; seuil {'atteint' if ev.passes() else 'NON atteint'} ; en attente de validation d'Alami")
        return 0 if ev.passes() else 1
    if a.action == "build":
        from .extract import extract_paragraphs
        r = c.certify(extract_paragraphs(a.file), a.source, a.target, a.key, a.registry, a.out_dir, a.ref, a.date)
        n = c.page_count(r["path"])
        print(f"{r['ref']} -> {r['path']} (pages : {n if n else 'non contrôlé'}) ; en attente d'évaluation et de scellé")
        return 0
    if a.action == "verify":
        ok = c.verify(a.file, a.key, a.registry, a.ref)
        print("VALIDE" if ok else "INVALIDE"); return 0 if ok else 1
    if a.action == "seal":
        c.seal(a.file, a.key, a.registry, a.ref, a.eval); print(f"{a.ref} scellé"); return 0
    return 2


def _cmd_providers(a) -> int:
    from .providers import PROVIDERS
    import os
    for p in PROVIDERS.values():
        ready = "prêt" if not p.env_key or os.environ.get(p.env_key) else f"clé {p.env_key} absente"
        print(f"{p.name:12} {p.data_policy:10} {p.model:42} {ready}  {p.note}")
    return 0


def _cmd_tm(a) -> int:
    from .tm import TranslationMemory
    tm = TranslationMemory(a.db)
    if a.action == "import":
        print(f"{tm.import_tsv(a.file, a.source, a.target)} segments importés ({len(tm)} au total)")
    elif a.action == "export":
        tm.export_tsv(a.file)
    else:
        for m in tm.lookup(a.file, a.source, a.target):
            print(f"{m.score:.0%}\t{m.source}\t{m.target}")
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
    tp.add_argument("--model", default=None, help="modèle (défaut propre à chaque fournisseur)"); tp.add_argument("--jurisdiction", default="")
    tp.add_argument("-p", "--provider", default="anthropic",
                    help="anthropic ou liste de repli : ollama,mistral,groq,gemini,openrouter,nvidia,huggingface,ovh")
    tp.add_argument("--allow-free-tier", action="store_true",
                    help="accepter l'envoi du texte à un fournisseur tiers (documents NON confidentiels)")
    tp.add_argument("--ocr", choices=["claude", "tesseract"], default=None, help="OCR pour scans/images")
    tp.add_argument("--tm", help="base SQLite de mémoire de traduction")
    tp.set_defaults(fn=_cmd_translate)

    cp2 = sub.add_parser("cert", help="traduction certifiée : keygen|next-ref|declaration|eval|build|verify|seal")
    cp2.add_argument("action", choices=["keygen", "next-ref", "declaration", "eval", "build", "verify", "seal"])
    cp2.add_argument("file", nargs="?", help="document (build/verify/seal) ou fiche (eval)")
    cp2.add_argument("-s", "--source"); cp2.add_argument("-t", "--target")
    cp2.add_argument("--ref"); cp2.add_argument("--date")
    cp2.add_argument("--key", default="cle-hmac.key"); cp2.add_argument("--registry", default="registre-certifications.csv")
    cp2.add_argument("--out-dir", default="archive"); cp2.add_argument("--eval", help="fiche d'évaluation validée (seal)")
    cp2.add_argument("--scores", help="fidelite=5,terminologie=4,conformite_marocaine=4,structure=5,ponctuation=5,formats=5")
    cp2.add_argument("--point", action="append", help="point à confirmer sur l'original (répétable)")
    cp2.set_defaults(fn=_cmd_cert)

    pp = sub.add_parser("providers", help="lister les fournisseurs LLM gratuits")
    pp.set_defaults(fn=_cmd_providers)

    mp = sub.add_parser("tm", help="mémoire de traduction : import | export | lookup")
    mp.add_argument("action", choices=["import", "export", "lookup"]); mp.add_argument("db")
    mp.add_argument("file", help="fichier TSV (ou texte à chercher pour lookup)")
    mp.add_argument("-s", "--source", default=""); mp.add_argument("-t", "--target", default="")
    mp.set_defaults(fn=_cmd_tm)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
