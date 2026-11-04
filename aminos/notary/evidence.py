"""One call to notarise a document locally and one to check it later."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import seal
from .hashing import sha256_file
from .ledger import Ledger, LedgerError

DISCLAIMER = ("Test seal from a self-made CA: not a Hague apostille, not an eIDAS qualified signature, "
              "no external timestamp. Proves integrity against this ledger only.")


def notarize(doc: str | Path, workdir: str | Path, pki: dict[str, Path], label: str = "") -> Path:
    """Fingerprint + seal + ledger entry for `doc`; returns the evidence JSON path (<doc>.evidence.json)."""
    doc, workdir = Path(doc), Path(workdir)
    digest = sha256_file(doc)
    ev: dict = {"file": doc.name, "bytes": doc.stat().st_size, "sha256": digest, "disclaimer": DISCLAIMER}
    if doc.suffix.lower() == ".pdf":
        sealed = seal.seal_pdf(doc, doc.with_suffix(".sealed.pdf"), pki["key"], pki["cert"], pki["ca"])
        ev["seal"] = {"type": "pades-test", "file": sealed.name, "sha256": sha256_file(sealed)}
    else:
        p7s = seal.seal_detached(doc, pki["key"], pki["cert"], pki["ca"])
        ev["seal"] = {"type": "cms-detached-test", "file": p7s.name, "sha256": sha256_file(p7s)}
    entry = Ledger(workdir / "ledger.jsonl").append(digest, label or doc.name, {"seal": ev["seal"]["sha256"]})
    ev["ledger"] = {"seq": entry["seq"], "ts": entry["ts"], "entry_hash": entry["hash"]}
    out = Path(str(doc) + ".evidence.json")
    out.write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def check(doc: str | Path, workdir: str | Path, ca: str | Path, evidence: str | Path | None = None) -> dict:
    """Return {'ok': bool, 'checks': {name: bool}, 'problems': [str]} for a notarised document."""
    doc = Path(doc)
    ev = json.loads(Path(evidence or str(doc) + ".evidence.json").read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    problems: list[str] = []

    checks["sha256_matches_evidence"] = sha256_file(doc) == ev["sha256"]
    if not checks["sha256_matches_evidence"]:
        problems.append("document changed since it was notarised")

    seal_path = doc.parent / ev["seal"]["file"]
    if ev["seal"]["type"] == "pades-test":
        r = seal.verify_pdf(seal_path, ca)
        checks["seal_valid"] = r["intact"] and r["valid"] and r["trusted"]
        if not checks["seal_valid"]:
            problems.append(f"PDF seal rejected: {r}")
    else:
        ok, msg = seal.verify_detached(doc, seal_path, ca)
        checks["seal_valid"] = ok
        if not ok:
            problems.append(f"detached seal rejected: {msg}")

    ledger = Ledger(Path(workdir) / "ledger.jsonl")
    try:
        ledger.verify()
        checks["ledger_chain_intact"] = True
    except LedgerError as e:
        checks["ledger_chain_intact"] = False
        problems.append(f"ledger: {e}")
    checks["ledger_has_entry"] = any(e["hash"] == ev["ledger"]["entry_hash"] for e in ledger.entries())
    if not checks["ledger_has_entry"]:
        problems.append("evidence entry not found in ledger")
    return {"ok": all(checks.values()), "checks": checks, "problems": problems}
