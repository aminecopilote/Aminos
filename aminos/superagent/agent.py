"""The superagent: one resumable job from a source document to a certified translation and an apostille dossier.

Phases (each one is saved, so a crash or a rerun resumes instead of starting over):
  run      extract -> terms/TM -> translate with an escalation ladder -> document-level QA -> draft .docx + review table
  certify  after HUMAN review: stamp, statement page, digital signature, ledger entry
  dossier  assemble the apostille file (never issues the apostille)

"Repeat until conclusive" is bounded: when the ladder is exhausted the job is reported `non_concluant` with the issues that
remain. It is never turned into a success, and certification is refused unless a human accepts the remaining issues explicitly.
A certified translation needs a translator who answers for it, so `certify` always records who reviewed the text.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .. import checks, pipeline
from ..docx_out import build_docx
from ..extract import extract_paragraphs
from ..glossary import Glossary
from ..llm import Chat
from ..normalize import normalize
from ..notary import seal
from ..notary.hashing import sha256_file
from ..notary.ledger import Ledger, LedgerError
from ..notary.pki import create_test_pki
from ..swarm import HAVE_COORDINATOR, Strategy, _index_chunks
from ..tm import TranslationMemory
from . import apostille, stamp
from .profile import Profile

STATUS_REVIEW, STATUS_NO_RESULT = "a_relire", "non_concluant"


class JobError(Exception):
    pass


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-.") or "doc"


def build_ladder(n_chats: int, max_rounds: int = 5) -> tuple[Strategy, ...]:
    """normal, hard, then hard again on each further model (providers are tried in turn)."""
    ladder = [Strategy("normal", 0), Strategy("hard", 0)]
    for r in range(2, max(2, max_rounds)):
        ladder.append(Strategy("hard", min(r - 1, max(n_chats - 1, 0))))
    return tuple(ladder)


@dataclass
class Job:
    dir: Path
    state: dict

    @property
    def path(self) -> Path:
        return self.dir / "job.json"

    def save(self) -> None:
        self.state["updated"] = int(time.time())
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def step(self, name: str, status: str, **info) -> None:
        self.state.setdefault("steps", {})[name] = {"status": status, "ts": int(time.time()), **info}
        self.save()


class Superagent:
    def __init__(self, profile: Profile, workdir: str | Path, chats: list[Chat], glossary: Glossary | None = None,
                 tm: TranslationMemory | None = None, use_swarm: bool = False, translators: int = 3, max_rounds: int = 5,
                 log=lambda msg: None):
        if not chats:
            raise JobError("aucun modèle configuré")
        self.profile, self.workdir, self.chats = profile, Path(workdir), chats
        self.glossary, self.tm = glossary or Glossary(), tm
        self.use_swarm = use_swarm and HAVE_COORDINATOR
        self.translators, self.max_rounds, self.log = translators, max_rounds, log
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.workdir / "ledger.jsonl")

    # ---- jobs ------------------------------------------------------
    def job(self, job_id: str) -> Job:
        d = self.workdir / "jobs" / _slug(job_id)
        if not (d / "job.json").exists():
            raise JobError(f"dossier de travail inconnu : {job_id}")
        return Job(d, json.loads((d / "job.json").read_text(encoding="utf-8")))

    def jobs(self) -> list[dict]:
        base = self.workdir / "jobs"
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(base.glob("*/job.json"))] if base.exists() else []

    # ---- phase 1 ---------------------------------------------------
    def run(self, file: str | Path, source: str, target: str, *, mode_hint: str = "", jurisdiction: str = "", ocr=None) -> Job:
        file = Path(file)
        sha = sha256_file(file)
        job_id = f"{_slug(file.stem)}-{sha[:8]}-{stamp.lang_code(source)}-{stamp.lang_code(target)}"
        d = self.workdir / "jobs" / job_id
        d.mkdir(parents=True, exist_ok=True)
        job = Job(d, json.loads((d / "job.json").read_text(encoding="utf-8")) if (d / "job.json").exists() else
                  {"id": job_id, "input": file.name, "sha256_in": sha, "source": source, "target": target,
                   "jurisdiction": jurisdiction or self.profile.params["jurisdiction"], "created": int(time.time()),
                   "steps": {}, "status": "en_cours", "issues": []})
        if not (d / "input").exists():
            (d / "input").mkdir()
            shutil.copyfile(file, d / "input" / file.name)

        paragraphs = self._extract(job, file, ocr)
        extra = self.profile.prompt_extra("\n".join(paragraphs[:30]))
        translated, remaining, rounds, reused = self._translate(job, paragraphs, extra)
        issues = remaining + self._qa(paragraphs, translated)
        issues = list(dict.fromkeys(issues))
        job.step("qa", "ok" if not issues else "issues", count=len(issues))

        docx = d / "translation.docx"
        build_docx(translated, target, str(docx))
        self._review_table(d / "review.md", paragraphs, translated, issues)
        job.state.update(status=STATUS_REVIEW if not issues else STATUS_NO_RESULT, issues=issues, rounds=rounds,
                         reused_from_tm=reused, sha256_translation=sha256_file(docx))
        job.step("render", "ok", docx=docx.name)
        self.log(f"{job_id} : {job.state['status']} ({len(issues)} point(s) à traiter)")
        return job

    def _extract(self, job: Job, file: Path, ocr) -> list[str]:
        cache = job.dir / "source.json"
        if cache.exists() and job.state["steps"].get("extract", {}).get("status") == "ok":
            return json.loads(cache.read_text(encoding="utf-8"))
        paragraphs = extract_paragraphs(file, ocr)
        if not paragraphs:
            job.step("extract", "empty")
            raise JobError("aucun texte extrait : document vide ou scan à passer à l'OCR (--ocr)")
        cache.write_text(json.dumps(paragraphs, ensure_ascii=False), encoding="utf-8")
        job.step("extract", "ok", paragraphs=len(paragraphs))
        return paragraphs

    def _translate(self, job: Job, paragraphs: list[str], extra: str):
        s = job.state
        src, tgt, juris = s["source"], s["target"], s["jurisdiction"]
        ladder = build_ladder(len(self.chats), self.max_rounds)
        if self.use_swarm:
            from ..swarm import run_job
            r = asyncio.run(run_job(paragraphs, src, tgt, self.chats, self.glossary, self.tm, ladder, juris, self.translators,
                                    extra=extra))
            job.step("translate", "ok" if r.ok else "issues", engine="swarm", rounds=len(r.rounds))
            return r.paragraphs, list(r.remaining_issues), r.rounds, r.reused_from_tm

        out = [""] * len(paragraphs)
        part = job.dir / "translation.partial.json"
        if part.exists():  # resume: keep what an interrupted run already produced
            saved = json.loads(part.read_text(encoding="utf-8"))
            if len(saved) == len(out):
                out = saved
        reused, todo = 0, []
        for i, para in enumerate(paragraphs):
            if out[i].strip():
                continue
            hit = self.tm.lookup(para, src, tgt, 0.98, 1) if self.tm is not None else []
            if hit:
                out[i], reused = hit[0].target, reused + 1
            else:
                todo.append(i)
        chunks = [[todo[j] for j in idx] for idx in _index_chunks([paragraphs[i] for i in todo], 1800)]
        pending, issues, rounds = list(range(len(chunks))), {}, []
        for rnd, strat in enumerate(ladder, 1):
            if not pending:
                break
            chat = self.chats[min(strat.chat, len(self.chats) - 1)]
            nxt = []
            for c in pending:
                srcs = [paragraphs[i] for i in chunks[c]]
                try:
                    r = pipeline.translate_chunk(chat, srcs, src, tgt, self.glossary, strat.mode, juris, extra)
                except Exception as e:  # rate limit, network, provider down: next round uses the next strategy
                    issues[c] = [f"erreur du modèle ({type(e).__name__}) : {str(e)[:120]}"]
                    nxt.append(c)
                    continue
                for i, t in zip(chunks[c], r.translations):
                    out[i] = t
                if r.issues:
                    issues[c] = r.issues
                    nxt.append(c)
                else:
                    issues.pop(c, None)
                    if self.tm is not None:
                        for a, b in zip(srcs, r.translations):
                            self.tm.add(a, b, src, tgt)
            rounds.append({"round": rnd, "mode": strat.mode, "chat": min(strat.chat, len(self.chats) - 1),
                           "chunks_run": len(pending), "chunks_clean": len(pending) - len(nxt)})
            pending = nxt
            part.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        remaining = [m for c in pending for m in issues.get(c, [])]
        job.step("translate", "ok" if not pending else "issues", engine="sequential", rounds=len(rounds))
        return out, remaining, rounds, reused

    def _qa(self, sources: list[str], translations: list[str]) -> list[str]:
        out = []
        for i, (s, t) in enumerate(zip(sources, translations), 1):
            if not t.strip():
                out.append(f"Segment {i} : traduction vide")
                continue
            out += [f"Segment {i} : {m}" for m in checks.compare(s, t).issues()]
            out += [f"Segment {i} : « {x.source} » doit être « {x.target} »" for x in self.glossary.missing_in(s, t)]
        return out

    @staticmethod
    def _review_table(path: Path, src: list[str], tgt: list[str], issues: list[str]) -> None:
        lines = ["# Relecture", "", "Points à traiter :", *([f"- {m}" for m in issues] or ["- aucun (contrôles automatiques)"]), "",
                 "| # | Source | Traduction |", "|---|---|---|"]
        esc = lambda x: x.replace("|", "\\|").replace("\n", " ")
        lines += [f"| {i} | {esc(a)} | {esc(b)} |" for i, (a, b) in enumerate(zip(src, tgt), 1)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- phase 2 ---------------------------------------------------
    def _signing(self, job: Job, demo: bool) -> dict:
        p = self.profile.params
        p12 = os.environ.get("AMINOS_P12") or p.get("p12", "")
        has_pem = bool(p.get("cert") and p.get("key"))
        if not demo and (p12 or has_pem):
            return {"real": True, "p12": p12 or None, "password": os.environ.get("AMINOS_P12_PASSWORD"),
                    "key": p.get("key") or None, "cert": p.get("cert") or None, "ca": p.get("ca") or None}
        pki = create_test_pki(job.dir / "certified" / "pki")
        return {"real": False, "p12": None, "password": None, "key": pki["key"], "cert": pki["cert"], "ca": pki["ca"]}

    def certify(self, job_id: str, reviewed_by: str, *, demo: bool = False, accept_issues: str = "",
                date: str = "", cert_lang: str | None = None) -> Job:
        job = self.job(job_id)
        s = job.state
        if not reviewed_by.strip():
            raise JobError("indiquez qui a relu et validé la traduction (--reviewed-by) : une traduction certifiée engage un traducteur")
        if s["status"] == STATUS_NO_RESULT and not accept_issues.strip():
            raise JobError("résultat non concluant : corrigez la traduction, ou acceptez expressément les points restants "
                           "(--accept-issues \"motif\")")
        out = job.dir / "certified"
        out.mkdir(exist_ok=True)
        docx = job.dir / "translation.docx"  # the translator may have corrected it after the review
        sha_tr = sha256_file(docx)
        sg = self._signing(job, demo)
        specimen = not sg["real"]
        tr = self.profile.params["translator"]
        params = self.profile.params
        stamp_png = Path(params["stamp_image"]) if params["stamp_image"] and Path(params["stamp_image"]).is_file() else None
        if stamp_png is None and specimen:
            stamp_png = stamp.make_stamp_png(out / "stamp-specimen.png",
                                             [tr["name"] or "TRADUCTEUR", tr["capacity"] or "Traducteur", tr["registration"],
                                              tr["place"]], specimen=True)
        sig_png = Path(params["signature_image"]) if params["signature_image"] and Path(params["signature_image"]).is_file() else None
        date = date or stamp.today()
        cert_pdf, box = stamp.build_certificate_pdf(
            out / "certificate.pdf", doc_name=s["input"], src_lang=s["source"], tgt_lang=s["target"], sha_src=s["sha256_in"],
            sha_tr=sha_tr, translator=tr, reviewed_by=reviewed_by, date=date, cert_lang=cert_lang, stamp_png=stamp_png,
            signature_png=sig_png, specimen=specimen, qr_payload=f"aminos:v1:sha256:{sha_tr}")
        body_pdf = stamp.docx_to_pdf(docx, out)
        if body_pdf:
            stamped = stamp.stamp_pages(body_pdf, out / "translation.stamped.pdf", text_lang=stamp.lang_code(s["target"]),
                                        stamp_png=stamp_png, specimen=specimen, sha_tr=sha_tr)
            final_in = stamp.append_pdf(stamped, cert_pdf, out / "translation.certified.unsigned.pdf")
        else:
            final_in = cert_pdf
        signed = seal.seal_pdf(final_in, out / "translation.certified.pdf", sg["key"], sg["cert"], sg["ca"],
                               reason="Certification de traduction", box=box, page=-1, signer_name=tr["name"],
                               location=tr["place"], p12=sg["p12"], p12_password=sg["password"])
        if sg["p12"]:
            p7s = seal.seal_detached_p12(docx, sg["p12"], sg["password"], out / "translation.docx.p7s")
        else:
            p7s = seal.seal_detached(docx, sg["key"], sg["cert"], sg["ca"] or sg["cert"], out / "translation.docx.p7s")
        shutil.copyfile(docx, out / "translation.docx")
        evidence = {
            "job": s["id"], "reviewed_by": reviewed_by, "translator": tr, "date": date, "specimen": specimen,
            "accepted_issues": accept_issues, "remaining_issues": s["issues"] if accept_issues else [],
            "files": {"original_sha256": s["sha256_in"], "translation_docx_sha256": sha_tr,
                      "certified_pdf_sha256": sha256_file(signed), "p7s_sha256": sha256_file(p7s)},
            "pdf_has_body": bool(body_pdf),
            "trust": "specimen-test-ca" if specimen else "certificate-supplied-by-translator",
            "ca": str(sg["ca"]) if sg["ca"] else "",
            "disclaimer": ("Essai : ni traduction assermentée, ni légalisation, ni apostille." if specimen else
                           "Signature numérique avec le certificat fourni par le traducteur ; sa valeur légale dépend de ce certificat."),
        }
        e = self.ledger.append(sha_tr, f"certification {s['id']}", {"signed_pdf": evidence["files"]["certified_pdf_sha256"]})
        evidence["ledger"] = {"seq": e["seq"], "entry_hash": e["hash"]}
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        s.update(status="certifie_essai" if specimen else "certifie", specimen=specimen)
        job.step("certify", "ok", specimen=specimen, pdf_has_body=bool(body_pdf))
        return job

    def verify(self, job_id: str) -> dict:
        job = self.job(job_id)
        out = job.dir / "certified"
        ev = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
        checks_: dict[str, bool] = {}
        problems: list[str] = []
        checks_["docx_unchanged"] = sha256_file(out / "translation.docx") == ev["files"]["translation_docx_sha256"]
        checks_["pdf_unchanged"] = sha256_file(out / "translation.certified.pdf") == ev["files"]["certified_pdf_sha256"]
        ca = ev.get("ca") or ""
        if ca and Path(ca).is_file():
            r = seal.verify_pdf(out / "translation.certified.pdf", ca)
            checks_["pdf_signature_valid_and_trusted"] = r["intact"] and r["valid"] and r["trusted"]
            ok, msg = seal.verify_detached(out / "translation.docx", out / "translation.docx.p7s", ca)
            checks_["docx_signature_valid"] = ok
            if not ok:
                problems.append(msg)
        else:
            problems.append("autorité de certification non fournie : signature non vérifiée contre une chaîne de confiance")
        try:
            self.ledger.verify()
            checks_["ledger_chain_intact"] = True
        except LedgerError as e:
            checks_["ledger_chain_intact"] = False
            problems.append(str(e))
        checks_["ledger_has_entry"] = any(x["hash"] == ev["ledger"]["entry_hash"] for x in self.ledger.entries())
        problems += [k for k, v in checks_.items() if not v]
        return {"ok": all(checks_.values()) and bool(ca and Path(ca).is_file()), "checks": checks_, "problems": problems,
                "specimen": ev["specimen"]}

    # ---- phase 3 ---------------------------------------------------
    def dossier(self, job_id: str, origin: str, destination: str, doc_kind: str = "") -> dict:
        job = self.job(job_id)
        if not job.state["status"].startswith("certifie"):
            raise JobError("traduction non certifiée : lancez d'abord « certify »")
        out = job.dir / "certified"
        pieces = [("original", next((job.dir / "input").iterdir())),
                  ("translation", out / "translation.docx"),
                  ("certificate", out / "translation.certified.pdf"),
                  ("signature", out / "translation.docx.p7s"),
                  ("evidence", out / "evidence.json")]
        m = apostille.build_dossier(job.dir / "dossier", pieces, origin=origin, destination=destination, doc_kind=doc_kind,
                                    specimen=bool(job.state.get("specimen")), ledger=self.ledger)
        job.step("dossier", m["status"])
        return m
