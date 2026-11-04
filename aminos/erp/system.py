"""System endpoints for automation: service health, backups, superagent jobs. Reachable with `system` tokens only."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
import urllib.request
from pathlib import Path

from ..notary.ledger import Ledger, LedgerError

APP_HEALTH = os.environ.get("AMINOS_APP_URL", "http://127.0.0.1:8501") + "/_stcore/health"


def _probe(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # local services only; the URL comes from the environment
            return r.status == 200
    except Exception:
        return False


def _orgs(root: Path) -> list[Path]:
    base = root / "tenants"
    return sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []


def status(root: str | Path) -> dict:
    root = Path(root)
    usage = shutil.disk_usage(root)
    orgs = []
    for d in _orgs(root):
        info: dict = {"org": d.name}
        erp = d / "erp.sqlite"
        if erp.exists():
            db = sqlite3.connect(erp)
            try:
                info["clients"] = db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
                info["open_cases"] = db.execute("SELECT COUNT(*) FROM cases WHERE status NOT IN ('livre','facture','clos')").fetchone()[0]
                info["unpaid_invoices"] = db.execute("SELECT COUNT(*) FROM documents WHERE kind='invoice' AND status='sent'").fetchone()[0]
            finally:
                db.close()
        audit = d / "audit.jsonl"
        try:
            info["audit_entries"] = Ledger(audit).verify() if audit.exists() else 0
            info["audit_ok"] = True
        except LedgerError as e:
            info["audit_ok"], info["audit_error"] = False, str(e)[:120]
        orgs.append(info)
    problems = []
    app_ok = _probe(APP_HEALTH)
    if not app_ok:
        problems.append("application de traduction injoignable")
    if usage.free / usage.total < 0.10:
        problems.append("moins de 10 % d'espace disque libre")
    problems += [f"journal d'audit altéré : {o['org']}" for o in orgs if not o["audit_ok"]]
    return {"time": int(time.time()), "ok": not problems, "problems": problems,
            "services": {"erp": True, "app": app_ok},
            "disk": {"total_gb": round(usage.total / 1e9, 1), "free_gb": round(usage.free / 1e9, 1)}, "orgs": orgs}


def jobs(root: str | Path) -> list[dict]:
    out = []
    for d in _orgs(Path(root)):
        for f in sorted((d / "work" / "jobs").glob("*/job.json")) if (d / "work" / "jobs").exists() else []:
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            out.append({"org": d.name, "id": j.get("id"), "status": j.get("status"), "issues": len(j.get("issues", [])),
                        "updated": j.get("updated")})
    return out


def _copy_sqlite(src: Path, dst: Path) -> dict:
    """Online backup (consistent even while the app writes), then an integrity check of the copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    a, b = sqlite3.connect(src), sqlite3.connect(dst)
    try:
        a.backup(b)
        ok = b.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        a.close()
        b.close()
    return {"file": str(dst), "bytes": dst.stat().st_size, "integrity_ok": ok}


def backup(root: str | Path, keep: int | None = None) -> dict:
    """Consistent copy of accounts, every firm's databases and ledgers into <root>/backups/<stamp>/ (mode 0700)."""
    root = Path(root)
    keep = keep or int(os.environ.get("AMINOS_BACKUP_KEEP", "14"))
    dest = root / "backups" / time.strftime("%Y%m%d-%H%M%S")
    dest.mkdir(parents=True, mode=0o700)
    files = []
    for name in ("saas.sqlite", "api-tokens.sqlite"):
        if (root / name).exists():
            files.append(_copy_sqlite(root / name, dest / name))
    for d in _orgs(root):
        for rel in ("erp.sqlite", "tm.sqlite", "profile/memory.sqlite"):
            if (d / rel).exists():
                files.append(_copy_sqlite(d / rel, dest / d.name / rel))
        for rel in ("audit.jsonl", "work/ledger.jsonl"):
            if (d / rel).exists():
                (dest / d.name / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(d / rel, dest / d.name / rel)
                files.append({"file": str(dest / d.name / rel), "bytes": (d / rel).stat().st_size, "integrity_ok": True})
    manifest = {"created": int(time.time()), "dir": str(dest), "files": files, "ok": all(f["integrity_ok"] for f in files),
                "sha256_manifest": hashlib.sha256(json.dumps([f["file"] for f in files]).encode()).hexdigest()}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    old = sorted(p for p in (root / "backups").iterdir() if p.is_dir())
    for p in old[:-keep]:
        shutil.rmtree(p, ignore_errors=True)
    manifest["kept"] = min(len(old), keep)
    return manifest
