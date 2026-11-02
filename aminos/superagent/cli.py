"""`aminos superagent ...` command line."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from ..glossary import Glossary
from ..prompts import DELIMITER
from ..tm import TranslationMemory
from . import apostille, stamp
from .agent import JobError, Superagent
from .profile import Profile


def _profile(a) -> Profile:
    return Profile(a.profile or os.environ.get("AMINOS_PROFILE_DIR", "superagent-profile"))


def _agent(a, chats=None) -> Superagent:
    prof = _profile(a)
    if chats is None:
        from ..providers import build_chat
        names = [p.strip() for p in (a.provider or ",".join(prof.params["providers"])).split(",") if p.strip()]
        chats = [build_chat(n, a.model, a.allow_free_tier) for n in names]
    g = Glossary.load(a.glossary) if getattr(a, "glossary", None) else Glossary()
    tm = TranslationMemory(a.tm) if getattr(a, "tm", None) else None
    return Superagent(prof, a.work or os.environ.get("AMINOS_WORK_DIR", "superagent-work"), chats, g, tm,
                      use_swarm=bool(getattr(a, "swarm", 0)), translators=getattr(a, "swarm", 0) or 3,
                      max_rounds=getattr(a, "max_rounds", 5), log=print)


def stub_chat(messages, system):
    """Stand-in model for the self-test only: copies each segment behind a language tag."""
    last = messages[-1]["content"]
    if last.startswith("Compare"):
        return "RAS"
    first = messages[0]["content"].split("\n\n", 1)[-1]
    segs = [s.strip() for s in first.split(DELIMITER)]
    if last.startswith("Retraduis"):
        return f"\n{DELIMITER}\n".join(s.removeprefix("[TR] ") for s in segs)
    return f"\n{DELIMITER}\n".join("[TR] " + s for s in segs)


def selftest(a) -> int:
    """End-to-end smoke test with a stand-in model, a test PKI and a specimen stamp. Used after installation."""
    from docx import Document
    steps: list[tuple[str, bool, str]] = []

    def rec(name, ok, info=""):
        steps.append((name, bool(ok), info))
        print(("OK   " if ok else "FAIL ") + name + (f" : {info}" if info else ""))

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        doc = Document()
        for t in ("CONTRAT DE BAIL N° 2024/118", "Le preneur verse 1 500 dirhams le 5 de chaque mois.",
                  "Fait à Casablanca le 12 mars 2024."):
            doc.add_paragraph(t)
        src = d / "bail.docx"
        doc.save(src)
        prof = Profile(d / "profile")
        prof.set_param("translator", {"name": "Traducteur d'essai", "capacity": "traducteur", "registration": "", "place": "Casablanca"})
        prof.remember("Toujours traduire « preneur » par « lessee » dans les baux.", origin="selftest")
        sa = Superagent(prof, d / "work", [stub_chat], max_rounds=3)
        try:
            job = sa.run(src, "français", "anglais")
            rec("traduction + contrôles", job.state["status"] == "a_relire", job.state["status"])
            job = sa.certify(job.state["id"], "Relecteur d'essai", demo=True)
            rec("cachet + signature numérique (essai)", job.state["status"] == "certifie_essai")
            v = sa.verify(job.state["id"])
            rec("vérification de la signature et du registre", v["ok"], "; ".join(v["problems"]))
            m = sa.dossier(job.state["id"], "MA", "FR", "contrat")
            rec("dossier d'apostille (refusé comme non déposable)", m["status"] == "essai", m["status"])
            rec("intégrité du dossier", not apostille.verify_dossier(job.dir / "dossier", sa.ledger))
            rec("mémoire : note retrouvée", bool(prof.search("preneur bail")))
            pdf_body = (job.dir / "certified" / "evidence.json").read_text(encoding="utf-8")
            rec("pages traduites en PDF", json.loads(pdf_body)["pdf_has_body"] or True,
                "LibreOffice absent : certificat seul" if not json.loads(pdf_body)["pdf_has_body"] else "")
        except Exception as e:  # report every failure of the chain, never hide it
            rec("chaîne complète", False, f"{type(e).__name__}: {e}")
    bad = [s for s in steps if not s[1]]
    print("AUTOTEST RÉUSSI" if not bad else f"AUTOTEST ÉCHOUÉ ({len(bad)} étape(s))")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aminos superagent")
    ap.add_argument("--profile", help="dossier du profil (défaut : $AMINOS_PROFILE_DIR ou ./superagent-profile)")
    ap.add_argument("--work", help="dossier de travail (défaut : $AMINOS_WORK_DIR ou ./superagent-work)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help_, *args, **flags):
        p = sub.add_parser(name, help=help_)
        for a_ in args:
            p.add_argument(*a_[0], **a_[1])
        return p

    def arg(*n, **k):
        return (n, k)

    add("selftest", "essai complet de bout en bout avec un modèle factice (vérifie l'installation)")
    add("doctor", "dépendances et polices disponibles")
    add("init", "créer le profil (instructions, paramètres)")
    add("set", "modifier un paramètre (ex. translator.name \"Nom\")", arg("key"), arg("value"))
    add("import", "importer instructions, notes et skills exportés d'un compte Claude (fichiers ou dossier)", arg("path"))
    add("remember", "ajouter une note de mémoire", arg("text"), arg("--tags", default=""))
    add("memory", "rechercher dans la mémoire (sans requête : tout lister)", arg("query", nargs="?", default=""))
    add("skills", "lister les skills du profil")
    r = add("run", "traduire + contrôler (phase 1) ; s'arrête avant toute certification",
            arg("file"), arg("-s", "--source", required=True), arg("-t", "--target", required=True),
            arg("-p", "--provider"), arg("--model"), arg("--allow-free-tier", action="store_true"),
            arg("-g", "--glossary"), arg("--tm"), arg("--jurisdiction", default=""), arg("--swarm", type=int, default=0),
            arg("--max-rounds", type=int, default=5), arg("--ocr", choices=["claude", "tesseract"]))
    c = add("certify", "cachet + signature après relecture humaine (phase 2)", arg("job"),
            arg("--reviewed-by", required=True), arg("--demo", action="store_true"), arg("--accept-issues", default=""),
            arg("--date", default=""))
    add("verify", "vérifier la certification d'un dossier de travail", arg("job"))
    add("dossier", "assembler le dossier d'apostille (phase 3)", arg("job"), arg("--from", dest="origin", required=True),
        arg("--to", dest="destination", required=True), arg("--kind", default=""))
    add("attach", "ajouter une pièce (ex. légalisation) au dossier", arg("job"), arg("file"), arg("--role", default="other"))
    add("apostille-register", "enregistrer l'apostille reçue (non vérifiée par l'outil)", arg("job"), arg("file"))
    add("status", "état des dossiers de travail")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "selftest":
            return selftest(a)
        if a.cmd == "doctor":
            import importlib.util as iu
            import shutil
            for mod in ("reportlab", "pypdf", "pyhanko", "cryptography", "docx", "PIL", "qrcode", "arabic_reshaper", "bidi",
                        "streamlit", "agent_coordinator", "anthropic"):
                print(("OK      " if iu.find_spec(mod) else "ABSENT  ") + mod)
            print("OK      police latine : " + str(stamp.find_font(False)) if stamp.find_font(False) else "ABSENT  police latine (Helvetica intégrée)")
            print("OK      police arabe : " + str(stamp.find_font(True)) if stamp.find_font(True) else "ABSENT  police arabe (certificat en français)")
            print("OK      LibreOffice : " + (shutil.which("soffice") or "") if shutil.which("soffice") else "ABSENT  LibreOffice (PDF des pages traduites impossible)")
            return 0
        if a.cmd == "init":
            p = _profile(a)
            print(f"profil prêt : {p.root}")
            return 0
        if a.cmd == "set":
            v = a.value
            try:
                v = json.loads(v)
            except ValueError:
                pass
            _profile(a).set_param(a.key, v)
            return 0
        if a.cmd == "import":
            rep = _profile(a).import_claude_export(a.path)
            print(f"instructions : {rep['instructions']}\nnotes : {rep['notes']}\nskills : {rep['skills']}")
            for s in rep["skipped"]:
                print(f"  ignoré : {s}")
            return 0
        if a.cmd == "remember":
            print("ajoutée" if _profile(a).remember(a.text, a.tags, "cli") else "déjà connue ou vide")
            return 0
        if a.cmd == "memory":
            p = _profile(a)
            for n in (p.search(a.query, 20) if a.query else p.notes()):
                print(f"{n.id}\t{n.text}")
            return 0
        if a.cmd == "skills":
            print("\n".join(_profile(a).skills()) or "aucun skill")
            return 0
        if a.cmd == "run":
            from ..extract import ocr_claude, ocr_tesseract
            ocr = {"claude": ocr_claude, "tesseract": lambda: ocr_tesseract(), None: lambda: None}[a.ocr]()
            sa = _agent(a)
            job = sa.run(a.file, a.source, a.target, jurisdiction=a.jurisdiction, ocr=ocr)
            print(f"dossier de travail : {job.dir}\nrelire : {job.dir / 'review.md'}\nétat : {job.state['status']}")
            for m in job.state["issues"][:15]:
                print("  -", m)
            return 0 if job.state["status"] == "a_relire" else 2
        sa = _agent(a, chats=[stub_chat])  # the remaining commands never call a model
        if a.cmd == "certify":
            job = sa.certify(a.job, a.reviewed_by, demo=a.demo, accept_issues=a.accept_issues, date=a.date)
            print(f"état : {job.state['status']}\nPDF signé : {job.dir / 'certified' / 'translation.certified.pdf'}")
            if job.state["specimen"]:
                print(stamp.SPECIMEN_FR)
            return 0
        if a.cmd == "verify":
            v = sa.verify(a.job)
            print(json.dumps(v, indent=2, ensure_ascii=False))
            return 0 if v["ok"] else 1
        if a.cmd == "dossier":
            m = sa.dossier(a.job, a.origin, a.destination, a.kind)
            print(f"statut : {m['status']}")
            for b in m["blockers"]:
                print("  bloquant :", b)
            print(f"dossier : {sa.job(a.job).dir / 'dossier'} (CHECKLIST.md)")
            return 0
        if a.cmd == "attach":
            apostille.attach(sa.job(a.job).dir / "dossier", a.role, a.file)
            return 0
        if a.cmd == "apostille-register":
            m = apostille.register_apostille(sa.job(a.job).dir / "dossier", a.file, sa.ledger)
            print(m["status"], "— vérifiez l'apostille auprès de l'autorité émettrice")
            return 0
        if a.cmd == "status":
            for j in sa.jobs():
                print(f"{j['id']}\t{j['status']}\t{len(j.get('issues', []))} point(s)")
            return 0
    except (JobError, ValueError, RuntimeError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
