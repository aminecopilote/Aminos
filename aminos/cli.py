"""Command line: aminos glossary import|find|check ... / aminos translate ..."""
from __future__ import annotations

import argparse
import json
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
    if a.swarm:
        return _translate_swarm(a, paragraphs, g, tm)
    out = translate_document(build_chat(a.provider, a.model, a.allow_free_tier), paragraphs, a.source, a.target, g, a.mode,
                             a.jurisdiction, tm=tm)
    build_docx(out, a.target, a.out)
    print(f"{len(out)} paragraphes écrits dans {a.out}")
    return 0


def _translate_swarm(a, paragraphs, g, tm) -> int:
    import asyncio
    from .providers import build_chat
    from .swarm import run_job
    # one chat per provider, so a failing provider is replaced by the next one on the following round
    chats = [build_chat(p.strip(), a.model, a.allow_free_tier) for p in a.provider.split(",")]
    notarize = None
    if a.seal_dir:
        from .notary import evidence
        from .notary.pki import create_test_pki
        pki = create_test_pki(Path(a.seal_dir) / "pki")
        notarize = lambda path: evidence.check(path, a.seal_dir, pki["ca"], evidence.notarize(path, a.seal_dir, pki))
    r = asyncio.run(run_job(paragraphs, a.source, a.target, chats, g, tm, jurisdiction=a.jurisdiction,
                            translators=a.swarm, docx_out=a.out, notarize=notarize))
    for x in r.rounds:
        print(f"tour {x['round']} ({x['mode']}, fournisseur {x['chat']}) : {x['chunks_clean']}/{x['chunks_run']} blocs conformes")
    print(f"{len(paragraphs)} paragraphes dont {r.reused_from_tm} repris de la mémoire -> {a.out}")
    if r.notary:
        print("scellement d'essai :", "OK" if r.notary["ok"] else r.notary["problems"])
    if not r.ok:
        print("NON CONCLUANT : " + "; ".join(r.remaining_issues[:10]), file=sys.stderr)
    return 0 if r.ok else 2


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
    elif a.action == "stats":
        print(f"{len(tm)} segments")
        for pair, n in tm.stats().items():
            print(f"  {pair}\t{n}")
    else:
        for m in tm.lookup(a.file, a.source, a.target):
            print(f"{m.score:.0%}\t{m.source}\t{m.target}")
    return 0


def _cmd_corpus(a) -> int:
    from . import corpus
    if a.kind == "tbx":
        g = corpus.tbx_to_glossary(a.file, a.source, a.target)
        g.save(a.out)
        print(f"{len(g)} termes {a.source}->{a.target} dans {a.out}; {len(g.conflicts)} conflit(s).")
        return 0
    from .tm import TranslationMemory
    tm = TranslationMemory(a.db)
    langs = [x for x in a.langs.split(",") if x]
    if a.kind == "tmx":
        n = corpus.import_tmx(tm, a.file, langs)
    else:
        n = corpus.import_moses(tm, a.file, a.file2, langs[0], langs[1])
    print(f"{n} segments importés ({len(tm)} au total dans {a.db})")
    return 0


def _cmd_notary(a) -> int:
    from .notary import Ledger, evidence
    from .notary.pki import create_test_pki
    wd = Path(a.workdir)
    if a.action == "init":
        paths = create_test_pki(wd / "pki")
        print("PKI d'essai créée :", *[f"{k}={v}" for k, v in paths.items()], sep="\n  ")
        return 0
    if a.action == "ledger":
        n = Ledger(wd / "ledger.jsonl").verify()
        print(f"registre intact : {n} entrée(s); tête = {Ledger(wd / 'ledger.jsonl').head()}")
        return 0
    pki = {k: wd / "pki" / f for k, f in (("ca", "ca.pem"), ("cert", "signer.pem"), ("key", "signer.key"))}
    if a.action == "seal":
        print(evidence.notarize(a.file, wd, pki, a.label))
        return 0
    r = evidence.check(a.file, wd, pki["ca"])
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if r["ok"] else 1


def _cmd_skills(a) -> int:
    import os
    import shutil
    import tempfile
    from . import skills as sk
    mgr = sk.SkillManager(a.dest or os.environ.get("AMINOS_SKILLS_DIR", "skills-installed"))
    try:
        if a.action == "list":
            for key, m in sorted(mgr.installed().items()):
                print(f"{key}\t{m['commit'][:10]}\t{'avec scripts' if m['with_scripts'] else 'texte seul'}")
        elif a.action == "available":
            for s in mgr.available(a.target):
                print(f"{s.name}\t{s.description[:100]}")
        elif a.action == "install":
            for key, skipped in mgr.install(a.target, a.names, a.with_scripts, a.ref):
                print(f"installé : {key} ({mgr.installed()[key]['commit'][:10]})")
                for s in skipped:
                    print(f"  ignoré : {s}")
            print("Relisez les fichiers installés avant de les utiliser : ces skills ne sont pas audités.")
        elif a.action == "verify":
            problems = mgr.verify()
            print("\n".join(problems) or "RAS : fichiers conformes à l'installation")
            return 1 if problems else 0
        elif a.action == "update":
            keys = [a.target] if a.target else sorted(mgr.installed())
            for key in keys:
                plan = mgr.update(key, apply=a.yes, force=a.force)
                state = "à jour" if plan.empty else ("mis à jour" if a.yes else "mise à jour disponible (relancez avec --yes)")
                print(f"{key} : {state} {plan.old_commit[:10]} -> {plan.new_commit[:10]}")
                for label, items in (("ajoutés", plan.added), ("modifiés", plan.changed), ("supprimés", plan.removed),
                                     ("modifiés localement", plan.locally_modified)):
                    if items:
                        print(f"  {label} : {', '.join(items)}")
        elif a.action == "remove":
            mgr.remove(a.target)
            print(f"supprimé : {a.target}")
        elif a.action == "search":
            src = sk.SOURCES["awesome-agent-skills"]
            tmp = tempfile.mkdtemp()
            try:
                sk.fetch(src["url"], __import__("pathlib").Path(tmp) / "r", src["ref"])
                readme = (__import__("pathlib").Path(tmp) / "r" / "README.md").read_text(encoding="utf-8")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            for h in sk.search_index(readme, a.target):
                tag = "installable" if h["installable"] else "page web (installation manuelle)"
                print(f"{h['name']}\t{tag}\t{h['url']}\n    {h['description'][:110]}")
    except sk.SkillError as e:
        print(f"erreur : {e}", file=sys.stderr)
        return 2
    return 0


def _cmd_orchestrate(a) -> int:
    from . import orchestrator as orch
    run = orch.subprocess_runner(cwd=a.repo)
    logdir = Path(a.logdir) if a.logdir else orch.default_logdir()
    if a.once:
        print(json.dumps(orch.run_cycle(run, logdir, a.interval, a.execute, a.repo), ensure_ascii=False, indent=2))
        return 0
    orch.loop(run, logdir, a.interval, a.execute)
    return 0


def _cmd_colab_plan(a) -> int:
    from . import colab
    p = colab.plan()
    print(json.dumps(colab.as_dict(p), ensure_ascii=False, indent=2))
    return 0 if p.gpu != "none" else 1


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
    tp.add_argument("--swarm", type=int, default=0, metavar="N",
                    help="N agents traducteurs en parallèle; les blocs non conformes sont relancés (mode puis fournisseur suivant)")
    tp.add_argument("--seal-dir", help="avec --swarm : sceller le .docx obtenu avec une PKI d'essai dans ce dossier")
    tp.set_defaults(fn=_cmd_translate)

    pp = sub.add_parser("providers", help="lister les fournisseurs LLM gratuits")
    pp.set_defaults(fn=_cmd_providers)

    mp = sub.add_parser("tm", help="mémoire de traduction : import | export | lookup | stats")
    mp.add_argument("action", choices=["import", "export", "lookup", "stats"]); mp.add_argument("db")
    mp.add_argument("file", nargs="?", default="", help="fichier TSV (ou texte à chercher pour lookup)")
    mp.add_argument("-s", "--source", default=""); mp.add_argument("-t", "--target", default="")
    mp.set_defaults(fn=_cmd_tm)

    kp = sub.add_parser("corpus", help="importer un corpus public (TMX/Moses -> mémoire, TBX -> glossaire)")
    kp.add_argument("kind", choices=["tmx", "moses", "tbx"]); kp.add_argument("file")
    kp.add_argument("file2", nargs="?", help="moses : fichier de la langue cible")
    kp.add_argument("--db", default="tm.sqlite"); kp.add_argument("--langs", default="ar,fr,en,nl",
                    help="tmx : langues à garder; moses : source,cible")
    kp.add_argument("-s", "--source", default="en"); kp.add_argument("-t", "--target", default="fr")
    kp.add_argument("-o", "--out", default="glossary.json"); kp.set_defaults(fn=_cmd_corpus)

    np_ = sub.add_parser("notary", help="banc d'essai de notarisation locale (PKI d'essai, sceau, registre)")
    np_.add_argument("action", choices=["init", "seal", "verify", "ledger"]); np_.add_argument("file", nargs="?")
    np_.add_argument("-w", "--workdir", default="notary-work"); np_.add_argument("--label", default="")
    np_.set_defaults(fn=_cmd_notary)

    sp = sub.add_parser("skills", help="installer / vérifier / mettre à jour des skills (SKILL.md) tiers, versions épinglées")
    sp.add_argument("action", choices=["list", "available", "install", "verify", "update", "remove", "search"])
    sp.add_argument("target", nargs="?", default="", help="source (chatgpt-skills, owner/repo, URL GitHub /tree/...), skill, ou mot-clé")
    sp.add_argument("names", nargs="*", help="install : noms des skills")
    sp.add_argument("--dest", help="dossier d'installation (défaut : $AMINOS_SKILLS_DIR ou ./skills-installed)")
    sp.add_argument("--with-scripts", action="store_true", help="copier aussi les scripts (.py .ps1 .sh...) APRÈS les avoir relus")
    sp.add_argument("--ref", help="commit ou branche précis")
    sp.add_argument("--yes", action="store_true", help="update : appliquer"); sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=_cmd_skills)

    op = sub.add_parser("orchestrate", help="Orchestrateur Central : supervision de la machine (cycle JSON + journal)")
    op.add_argument("--once", action="store_true", help="un seul cycle, enregistrement JSON complet sur la sortie")
    op.add_argument("--interval", type=int, default=300, help="secondes entre deux cycles (défaut 300)")
    op.add_argument("--logdir", help=r"défaut : C:\orchestrator\logs sous Windows, ./orchestrator-logs ailleurs")
    op.add_argument("--execute", action="store_true", help="exécuter les actions de la liste blanche (sinon simple proposition)")
    op.add_argument("--repo", default=".", help="dépôt Git à surveiller")
    op.set_defaults(fn=_cmd_orchestrate)

    cp2 = sub.add_parser("colab-plan", help="GPU détecté et modèle local adapté (utilisé par le carnet Google Colab)")
    cp2.set_defaults(fn=_cmd_colab_plan)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
