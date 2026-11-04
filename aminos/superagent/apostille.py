"""Apostille dossier: assemble, check and checklist. It never issues or simulates an apostille.

An apostille (Hague Convention of 5 October 1961) is issued by a competent authority designated by the State that issued the
public document. Software can prepare the dossier and keep proof of what was submitted and received; it cannot issue the
apostille, and it cannot verify one without the issuing authority's register.
"""
from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path

from ..notary.hashing import sha256_file
from ..notary.ledger import Ledger

# Membership known with confidence. Anything absent is reported as "to verify": the HCCH status table is the source of truth.
HAGUE_MEMBERS = {"MA": "Maroc", "FR": "France", "BE": "Belgique", "NL": "Pays-Bas", "LU": "Luxembourg", "ES": "Espagne",
                 "DE": "Allemagne", "IT": "Italie", "PT": "Portugal", "CH": "Suisse", "GB": "Royaume-Uni",
                 "US": "États-Unis"}
HCCH_STATUS = "https://www.hcch.net/fr/instruments/conventions/status-table/?cid=41"

ROLES = ("original", "translation", "certificate", "signature", "evidence", "legalisation", "other")


def hague_status(country: str) -> str:
    c = country.strip().upper()
    if not c:
        return "pays non indiqué"
    return (f"{HAGUE_MEMBERS[c]} : partie à la Convention de La Haye de 1961 (confirmer l'entrée en vigueur et les éventuelles "
            f"objections sur la table d'état de la HCCH)" if c in HAGUE_MEMBERS
            else f"{c} : à vérifier sur la table d'état de la HCCH ({HCCH_STATUS}) ; hors Convention, la voie est la légalisation consulaire")


def checklist(origin: str, destination: str, doc_kind: str = "", specimen: bool = False) -> list[str]:
    steps = [
        f"Pays d'émission du document / de la traduction certifiée : {hague_status(origin)}.",
        f"Pays de destination : {hague_status(destination)}.",
        "Confirmer auprès de l'autorité de destination (administration, tribunal, ambassade) : l'apostille de l'original est-elle "
        "exigée, la traduction doit-elle être assermentée, dans quel pays, et la signature du traducteur doit-elle être légalisée ?",
        "Original : copie lisible ou original selon l'exigence de l'autorité ; conserver son empreinte (déjà inscrite dans le manifeste).",
        "Traduction : relue et validée par un traducteur habilité ; cachet et signature du traducteur apposés par lui-même.",
        "Si l'autorité compétente exige la légalisation de la signature du traducteur (notaire, tribunal, mairie selon le pays), "
        "joindre la preuve au dossier avec : aminos superagent attach <dossier> <fichier> --role legalisation.",
        "Déposer le dossier auprès de l'autorité compétente désignée par le pays d'émission (liste officielle HCCH : "
        "« Autorités compétentes »). Conserver le reçu de dépôt.",
        "À réception de l'apostille : aminos superagent apostille-register <dossier> <fichier>. L'outil en garde l'empreinte ; "
        "il ne la vérifie pas : vérifiez-la auprès de l'autorité émettrice (registre électronique e-Register s'il existe).",
    ]
    if doc_kind:
        steps.insert(3, f"Nature du document : {doc_kind}. Un acte d'état civil, notarié ou judiciaire n'a pas le même circuit "
                        f"qu'un document administratif ou privé : confirmer l'autorité compétente pour cette nature.")
    if specimen:
        steps.insert(0, "ATTENTION : dossier d'ESSAI (cachet et signature non officiels). Il ne peut pas être déposé.")
    return steps


def build_dossier(out_dir: str | Path, pieces: list[tuple[str, Path]], *, origin: str, destination: str,
                  doc_kind: str = "", specimen: bool = False, ledger: Ledger | None = None) -> dict:
    """pieces: (role, file). Copies them as 01-..., writes manifest.json and CHECKLIST.md, returns the manifest."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_files = []
    for i, (role, src) in enumerate(pieces, 1):
        if role not in ROLES:
            raise ValueError(f"rôle inconnu : {role}")
        dst = out / f"{i:02d}-{role}-{Path(src).name}"
        shutil.copyfile(src, dst)
        manifest_files.append({"role": role, "file": dst.name, "bytes": dst.stat().st_size, "sha256": sha256_file(dst)})
    roles = {f["role"] for f in manifest_files}
    blockers = []
    if "original" not in roles:
        blockers.append("original manquant")
    if "translation" not in roles:
        blockers.append("traduction manquante")
    if "certificate" not in roles and "signature" not in roles:
        blockers.append("traduction non certifiée (ni certificat signé ni signature)")
    if specimen:
        blockers.append("cachet et signature d'essai : dossier non déposable")
    manifest = {"created": int(time.time()), "origin": origin, "destination": destination, "doc_kind": doc_kind,
                "files": manifest_files, "blockers": blockers,
                "status": "pret_a_deposer" if not blockers else ("essai" if specimen else "incomplet"),
                "apostille": None,
                "notice": "Ce dossier n'est pas une apostille. L'apostille est délivrée par l'autorité compétente."}
    if ledger is not None:
        e = ledger.append(sha256_manifest(manifest), f"dossier {out.name}", {"status": manifest["status"]})
        manifest["ledger"] = {"seq": e["seq"], "entry_hash": e["hash"]}
    _write(out, manifest, checklist(origin, destination, doc_kind, specimen))
    return manifest


def sha256_manifest(manifest: dict) -> str:
    import hashlib
    body = {k: manifest[k] for k in ("origin", "destination", "doc_kind", "files")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _write(out: Path, manifest: dict, steps: list[str]) -> None:
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Dossier d'apostille — liste de contrôle", "", f"Statut : **{manifest['status']}**", ""]
    if manifest["blockers"]:
        lines += ["Points bloquants :", *[f"- {b}" for b in manifest["blockers"]], ""]
    lines += ["Étapes :", *[f"{i}. {s}" for i, s in enumerate(steps, 1)], "", "Pièces :",
              *[f"- {f['file']} (SHA-256 {f['sha256'][:16]}…)" for f in manifest["files"]], "",
              manifest["notice"], ""]
    (out / "CHECKLIST.md").write_text("\n".join(lines), encoding="utf-8")


def verify_dossier(out_dir: str | Path, ledger: Ledger | None = None) -> list[str]:
    out = Path(out_dir)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for f in m["files"] + ([m["apostille"]] if m.get("apostille") else []):
        p = out / f["file"]
        if not p.exists():
            problems.append(f"{f['file']} : absent")
        elif sha256_file(p) != f["sha256"]:
            problems.append(f"{f['file']} : modifié depuis l'assemblage")
    if ledger is not None and m.get("ledger"):
        if not any(e["hash"] == m["ledger"]["entry_hash"] for e in ledger.entries()):
            problems.append("entrée du registre introuvable")
    return problems


def attach(out_dir: str | Path, role: str, src: str | Path) -> dict:
    out = Path(out_dir)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    n = len(m["files"]) + 1
    dst = out / f"{n:02d}-{role}-{Path(src).name}"
    shutil.copyfile(src, dst)
    m["files"].append({"role": role, "file": dst.name, "bytes": dst.stat().st_size, "sha256": sha256_file(dst)})
    _write(out, m, checklist(m["origin"], m["destination"], m["doc_kind"], m["status"] == "essai"))
    return m


def register_apostille(out_dir: str | Path, src: str | Path, ledger: Ledger | None = None) -> dict:
    """Record the apostille the authority returned. Its authenticity is NOT checked here."""
    out = Path(out_dir)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if m["status"] == "essai":
        raise ValueError("dossier d'essai : aucune apostille ne peut y être rattachée")
    dst = out / f"99-apostille-recue-{Path(src).name}"
    shutil.copyfile(src, dst)
    m["apostille"] = {"role": "apostille", "file": dst.name, "bytes": dst.stat().st_size, "sha256": sha256_file(dst),
                      "received": int(time.time()), "verified": False}
    m["status"] = "apostille_recue_non_verifiee"
    if ledger is not None:
        e = ledger.append(m["apostille"]["sha256"], f"apostille reçue {out.name}", {})
        m["apostille"]["ledger_entry"] = e["hash"]
    _write(out, m, checklist(m["origin"], m["destination"], m["doc_kind"]))
    return m


def zip_dossier(out_dir: str | Path) -> Path:
    out = Path(out_dir)
    z = out.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out.iterdir()):
            zf.write(f, f"{out.name}/{f.name}")
    return z
