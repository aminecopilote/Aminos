"""SQL layer. Money is stored as integer cents; every statement is parameterised; numbering is gapless per kind and year."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

CASE_STATUS = ("nouveau", "devis", "en_cours", "a_relire", "certifie", "livre", "facture", "clos")
DOC_KINDS = {"quote": "DV", "invoice": "FA"}
DOC_STATUS = ("draft", "sent", "accepted", "paid", "void")
LANGS = ("ar", "fr", "en", "nl")

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'particulier', email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '', address TEXT NOT NULL DEFAULT '', tax_id TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '', created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY, ref TEXT UNIQUE NOT NULL, client_id INTEGER NOT NULL REFERENCES clients(id),
    title TEXT NOT NULL, src TEXT NOT NULL, tgt TEXT NOT NULL, doc_kind TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'nouveau', deadline TEXT NOT NULL DEFAULT '', words INTEGER NOT NULL DEFAULT 0,
    job_id TEXT NOT NULL DEFAULT '', created INTEGER NOT NULL, updated INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS cases_client ON cases(client_id);
CREATE INDEX IF NOT EXISTS cases_status ON cases(status);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, number TEXT UNIQUE NOT NULL, client_id INTEGER NOT NULL REFERENCES clients(id),
    case_id INTEGER REFERENCES cases(id), issue_date TEXT NOT NULL, due_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft', currency TEXT NOT NULL DEFAULT 'MAD', vat_permille INTEGER NOT NULL DEFAULT 200,
    notes TEXT NOT NULL DEFAULT '', source_quote INTEGER REFERENCES documents(id), created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS lines (
    id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    label TEXT NOT NULL, qty_milli INTEGER NOT NULL, unit_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL REFERENCES documents(id), cents INTEGER NOT NULL,
    paid_on TEXT NOT NULL, method TEXT NOT NULL DEFAULT '', reference TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS counters (kind TEXT, year INTEGER, last INTEGER NOT NULL, PRIMARY KEY (kind, year));
"""


class ErpError(ValueError):
    """Bad input or a refused transition: the message is safe to show to the user."""


def _req(d: dict, key: str, maxlen: int = 200) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ErpError(f"champ obligatoire : {key}")
    if len(v) > maxlen:
        raise ErpError(f"{key} trop long")
    return v.strip()


def _opt(d: dict, key: str, maxlen: int = 500) -> str:
    v = d.get(key, "")
    if v is None:
        return ""
    if not isinstance(v, str) or len(v) > maxlen:
        raise ErpError(f"{key} invalide")
    return v.strip()


def _int(d: dict, key: str, lo: int, hi: int, default: int | None = None) -> int:
    v = d.get(key, default)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ErpError(f"{key} invalide")
    return v


def _date(v: str, key: str, required: bool = False) -> str:
    if not v:
        if required:
            raise ErpError(f"{key} obligatoire")
        return ""
    try:
        time.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise ErpError(f"{key} : date AAAA-MM-JJ attendue") from None
    return v


def line_total(qty_milli: int, unit_cents: int) -> int:
    return (qty_milli * unit_cents + 500) // 1000


class ErpStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.tx() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def tx(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _rows(cur) -> list[dict]:
        return [dict(r) for r in cur.fetchall()]

    # ---- clients ---------------------------------------------------
    def add_client(self, d: dict) -> dict:
        with self.tx() as db:
            cur = db.execute("INSERT INTO clients (name, kind, email, phone, address, tax_id, notes, created) VALUES (?,?,?,?,?,?,?,?)",
                             (_req(d, "name"), _opt(d, "kind", 40) or "particulier", _opt(d, "email", 200), _opt(d, "phone", 60),
                              _opt(d, "address", 400), _opt(d, "tax_id", 60), _opt(d, "notes", 2000), int(time.time())))
            return dict(db.execute("SELECT * FROM clients WHERE id=?", (cur.lastrowid,)).fetchone())

    def update_client(self, cid: int, d: dict) -> dict:
        with self.tx() as db:
            if not db.execute("SELECT 1 FROM clients WHERE id=?", (cid,)).fetchone():
                raise ErpError("client introuvable")
            db.execute("UPDATE clients SET name=?, kind=?, email=?, phone=?, address=?, tax_id=?, notes=? WHERE id=?",
                       (_req(d, "name"), _opt(d, "kind", 40) or "particulier", _opt(d, "email", 200), _opt(d, "phone", 60),
                        _opt(d, "address", 400), _opt(d, "tax_id", 60), _opt(d, "notes", 2000), cid))
            return dict(db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone())

    def delete_client(self, cid: int) -> None:
        with self.tx() as db:
            if db.execute("SELECT 1 FROM cases WHERE client_id=? UNION SELECT 1 FROM documents WHERE client_id=?", (cid, cid)).fetchone():
                raise ErpError("client lié à des dossiers ou des documents : suppression refusée")
            db.execute("DELETE FROM clients WHERE id=?", (cid,))

    def clients(self, q: str = "") -> list[dict]:
        with self.tx() as db:
            like = f"%{q.strip()}%"
            return self._rows(db.execute("SELECT * FROM clients WHERE name LIKE ? OR email LIKE ? ORDER BY name LIMIT 500", (like, like)))

    # ---- cases -----------------------------------------------------
    def _next(self, db, kind: str, year: int) -> int:
        db.execute("INSERT OR IGNORE INTO counters (kind, year, last) VALUES (?,?,0)", (kind, year))
        db.execute("UPDATE counters SET last = last + 1 WHERE kind=? AND year=?", (kind, year))
        return db.execute("SELECT last FROM counters WHERE kind=? AND year=?", (kind, year)).fetchone()[0]

    def add_case(self, d: dict) -> dict:
        src, tgt = _req(d, "src", 8).lower(), _req(d, "tgt", 8).lower()
        if src not in LANGS or tgt not in LANGS or src == tgt:
            raise ErpError("langues : ar, fr, en, nl (source différente de la cible)")
        with self.tx() as db:
            cid = _int(d, "client_id", 1, 2**31)
            if not db.execute("SELECT 1 FROM clients WHERE id=?", (cid,)).fetchone():
                raise ErpError("client introuvable")
            year = time.localtime().tm_year
            ref = f"DOS-{year}-{self._next(db, 'case', year):04d}"
            now = int(time.time())
            cur = db.execute("INSERT INTO cases (ref, client_id, title, src, tgt, doc_kind, status, deadline, words, job_id, created, updated) "
                             "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                             (ref, cid, _req(d, "title"), src, tgt, _opt(d, "doc_kind", 100), "nouveau",
                              _date(_opt(d, "deadline", 10), "deadline"), _int(d, "words", 0, 10_000_000, 0), _opt(d, "job_id", 120), now, now))
            return dict(db.execute("SELECT * FROM cases WHERE id=?", (cur.lastrowid,)).fetchone())

    def update_case(self, case_id: int, d: dict) -> dict:
        with self.tx() as db:
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not row:
                raise ErpError("dossier introuvable")
            status = d.get("status", row["status"])
            if status not in CASE_STATUS:
                raise ErpError("statut inconnu")
            db.execute("UPDATE cases SET title=?, doc_kind=?, status=?, deadline=?, words=?, job_id=?, updated=? WHERE id=?",
                       (_req({"title": d.get("title", row["title"])}, "title"), _opt({"x": d.get("doc_kind", row["doc_kind"])}, "x", 100),
                        status, _date(_opt({"x": d.get("deadline", row["deadline"])}, "x", 10), "deadline"),
                        _int({"x": d.get("words", row["words"])}, "x", 0, 10_000_000), _opt({"x": d.get("job_id", row["job_id"])}, "x", 120),
                        int(time.time()), case_id))
            return dict(db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())

    def cases(self, status: str = "", client_id: int = 0) -> list[dict]:
        sql, args = ("SELECT c.*, cl.name AS client_name FROM cases c JOIN clients cl ON cl.id=c.client_id WHERE 1=1", [])
        if status:
            sql += " AND c.status=?"
            args.append(status)
        if client_id:
            sql += " AND c.client_id=?"
            args.append(client_id)
        with self.tx() as db:
            return self._rows(db.execute(sql + " ORDER BY c.updated DESC LIMIT 500", args))

    # ---- quotes and invoices --------------------------------------
    def create_document(self, d: dict) -> dict:
        kind = d.get("kind")
        if kind not in DOC_KINDS:
            raise ErpError("type de document : quote ou invoice")
        raw = d.get("lines")
        if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
            raise ErpError("au moins une ligne (100 au plus)")
        lines = []
        for ln in raw:
            if not isinstance(ln, dict):
                raise ErpError("ligne invalide")
            lines.append((_req(ln, "label", 300), _int(ln, "qty_milli", 1, 10**9), _int(ln, "unit_cents", 0, 10**10)))
        issue = _date(_opt(d, "issue_date", 10) or time.strftime("%Y-%m-%d"), "issue_date", True)
        with self.tx() as db:
            client_id = _int(d, "client_id", 1, 2**31)
            if not db.execute("SELECT 1 FROM clients WHERE id=?", (client_id,)).fetchone():
                raise ErpError("client introuvable")
            case_id = d.get("case_id")
            if case_id is not None and not db.execute("SELECT 1 FROM cases WHERE id=? AND client_id=?", (case_id, client_id)).fetchone():
                raise ErpError("dossier introuvable pour ce client")
            year = int(issue[:4])
            number = f"{DOC_KINDS[kind]}-{year}-{self._next(db, kind, year):04d}"
            cur = db.execute("INSERT INTO documents (kind, number, client_id, case_id, issue_date, due_date, status, currency, vat_permille, notes, created) "
                             "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                             (kind, number, client_id, case_id, issue, _date(_opt(d, "due_date", 10), "due_date"), "draft",
                              (_opt(d, "currency", 3) or "MAD").upper(), _int(d, "vat_permille", 0, 1000, 200), _opt(d, "notes", 2000),
                              int(time.time())))
            db.executemany("INSERT INTO lines (doc_id, label, qty_milli, unit_cents) VALUES (?,?,?,?)",
                           [(cur.lastrowid, *ln) for ln in lines])
            return self._document(db, cur.lastrowid)

    def _document(self, db, doc_id: int) -> dict:
        row = db.execute("SELECT d.*, c.name AS client_name, c.address AS client_address, c.tax_id AS client_tax_id FROM documents d "
                         "JOIN clients c ON c.id=d.client_id WHERE d.id=?", (doc_id,)).fetchone()
        if not row:
            raise ErpError("document introuvable")
        doc = dict(row)
        doc["lines"] = self._rows(db.execute("SELECT label, qty_milli, unit_cents FROM lines WHERE doc_id=? ORDER BY id", (doc_id,)))
        for ln in doc["lines"]:
            ln["total_cents"] = line_total(ln["qty_milli"], ln["unit_cents"])
        doc["subtotal_cents"] = sum(l["total_cents"] for l in doc["lines"])
        doc["vat_cents"] = (doc["subtotal_cents"] * doc["vat_permille"] + 500) // 1000
        doc["total_cents"] = doc["subtotal_cents"] + doc["vat_cents"]
        doc["paid_cents"] = db.execute("SELECT COALESCE(SUM(cents),0) FROM payments WHERE doc_id=?", (doc_id,)).fetchone()[0]
        doc["balance_cents"] = doc["total_cents"] - doc["paid_cents"]
        doc["payments"] = self._rows(db.execute("SELECT * FROM payments WHERE doc_id=? ORDER BY paid_on, id", (doc_id,)))
        return doc

    def document(self, doc_id: int) -> dict:
        with self.tx() as db:
            return self._document(db, doc_id)

    def documents(self, kind: str = "") -> list[dict]:
        with self.tx() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM documents WHERE (?='' OR kind=?) ORDER BY id DESC LIMIT 500", (kind, kind))]
            return [self._document(db, i) for i in ids]

    def set_document_status(self, doc_id: int, status: str) -> dict:
        if status not in DOC_STATUS:
            raise ErpError("statut inconnu")
        with self.tx() as db:
            doc = self._document(db, doc_id)
            if doc["status"] == "paid" and status != "void":
                raise ErpError("facture soldée : seul l'annulation est possible")
            if status == "paid" and doc["balance_cents"] > 0:
                raise ErpError("solde restant : enregistrez le paiement")
            db.execute("UPDATE documents SET status=? WHERE id=?", (status, doc_id))
            return self._document(db, doc_id)

    def quote_to_invoice(self, quote_id: int) -> dict:
        with self.tx() as db:
            q = self._document(db, quote_id)
            if q["kind"] != "quote" or q["status"] not in ("sent", "accepted"):
                raise ErpError("seul un devis envoyé ou accepté peut être facturé")
            if db.execute("SELECT 1 FROM documents WHERE source_quote=? AND status<>'void'", (quote_id,)).fetchone():
                raise ErpError("ce devis est déjà facturé")
            year = int(time.strftime("%Y"))
            number = f"FA-{year}-{self._next(db, 'invoice', year):04d}"
            cur = db.execute("INSERT INTO documents (kind, number, client_id, case_id, issue_date, due_date, status, currency, vat_permille, notes, source_quote, created) "
                             "VALUES ('invoice',?,?,?,?,?,'draft',?,?,?,?,?)",
                             (number, q["client_id"], q["case_id"], time.strftime("%Y-%m-%d"), "", q["currency"], q["vat_permille"],
                              q["notes"], quote_id, int(time.time())))
            db.executemany("INSERT INTO lines (doc_id, label, qty_milli, unit_cents) VALUES (?,?,?,?)",
                           [(cur.lastrowid, l["label"], l["qty_milli"], l["unit_cents"]) for l in q["lines"]])
            db.execute("UPDATE documents SET status='accepted' WHERE id=?", (quote_id,))
            return self._document(db, cur.lastrowid)

    def add_payment(self, doc_id: int, d: dict) -> dict:
        with self.tx() as db:
            doc = self._document(db, doc_id)
            if doc["kind"] != "invoice" or doc["status"] in ("void", "draft"):
                raise ErpError("paiement possible sur une facture envoyée seulement")
            cents = _int(d, "cents", 1, 10**11)
            if cents > doc["balance_cents"]:
                raise ErpError("le paiement dépasse le solde")
            db.execute("INSERT INTO payments (doc_id, cents, paid_on, method, reference) VALUES (?,?,?,?,?)",
                       (doc_id, cents, _date(_opt(d, "paid_on", 10) or time.strftime("%Y-%m-%d"), "paid_on", True),
                        _opt(d, "method", 40), _opt(d, "reference", 100)))
            if cents == doc["balance_cents"]:
                db.execute("UPDATE documents SET status='paid' WHERE id=?", (doc_id,))
            return self._document(db, doc_id)

    # ---- dashboard -------------------------------------------------
    def dashboard(self, today: str | None = None) -> dict:
        today = today or time.strftime("%Y-%m-%d")
        with self.tx() as db:
            by_status = {r[0]: r[1] for r in db.execute("SELECT status, COUNT(*) FROM cases GROUP BY status")}
            late = self._rows(db.execute("SELECT c.ref, c.title, c.deadline, cl.name AS client_name FROM cases c JOIN clients cl ON cl.id=c.client_id "
                                         "WHERE c.deadline<>'' AND c.deadline<? AND c.status NOT IN ('livre','facture','clos') ORDER BY c.deadline",
                                         (today,)))
            invoices = [self._document(db, r[0]) for r in db.execute("SELECT id FROM documents WHERE kind='invoice' AND status IN ('sent','paid')")]
            overdue = [{"number": i["number"], "client_name": i["client_name"], "due_date": i["due_date"], "balance_cents": i["balance_cents"]}
                       for i in invoices if i["status"] == "sent" and i["due_date"] and i["due_date"] < today and i["balance_cents"] > 0]
            months: dict[str, int] = {}
            for i in invoices:
                for p in i["payments"]:
                    months[p["paid_on"][:7]] = months.get(p["paid_on"][:7], 0) + p["cents"]
            return {"cases_by_status": by_status, "late_cases": late, "overdue_invoices": overdue,
                    "outstanding_cents": sum(i["balance_cents"] for i in invoices if i["status"] == "sent"),
                    "revenue_by_month_cents": dict(sorted(months.items())),
                    "clients": db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]}
