"""Web back-office: a small WSGI application (standard library only) serving a Bootstrap single-page UI and a JSON API.

Security model
  - accounts, scrypt hashes, lockout and audit log come from aminos.saas (the same accounts as the translation app)
  - session = HMAC-signed cookie (HttpOnly, SameSite=Strict, Secure behind HTTPS) re-checked against the account on each call
  - every write needs the X-CSRF-Token header (value held by the signed session) and a JSON body
  - one SQLite file per firm: a user can only ever reach the tenant directory of their own organisation
  - no inline script or style, strict Content-Security-Policy, nothing loaded from third-party hosts
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import time
from http.cookies import SimpleCookie
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
from socketserver import ThreadingMixIn

from ..saas import AuthError, SaaSStore
from .store import ErpError, ErpStore

STATIC = Path(__file__).parent / "static"
STATIC_TYPES = {"bootstrap.min.css": "text/css", "bootstrap.bundle.min.js": "text/javascript", "app.js": "text/javascript",
                "app.css": "text/css", "print.css": "text/css", "print.js": "text/javascript",
                "bootstrap-LICENSE.txt": "text/plain"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
MAX_BODY = 1_000_000
COOKIE = "aminos_erp"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


class ErpApp:
    def __init__(self, data_dir: str | Path, session_minutes: int = 480, cookie_secure: bool | None = None):
        self.store = SaaSStore(data_dir)
        self.ttl = session_minutes * 60
        self.cookie_secure = cookie_secure
        sf = Path(data_dir) / "erp-secret"
        if not sf.exists():
            fd = os.open(sf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(secrets.token_bytes(32))
        self.secret = sf.read_bytes()
        self._erp: dict[str, ErpStore] = {}

    # ---- sessions --------------------------------------------------
    def _sign(self, payload: str) -> str:
        return _b64(hmac.new(self.secret, payload.encode(), hashlib.sha256).digest())

    def issue(self, username: str, now: float | None = None) -> tuple[str, str]:
        csrf = secrets.token_hex(16)
        payload = _b64(json.dumps({"u": username, "exp": int((now or time.time()) + self.ttl), "csrf": csrf}).encode())
        return f"{payload}.{self._sign(payload)}", csrf

    def session(self, environ, now: float | None = None):
        raw = SimpleCookie(environ.get("HTTP_COOKIE", "")).get(COOKIE)
        if not raw or "." not in raw.value:
            return None, None
        payload, sig = raw.value.rsplit(".", 1)
        if not hmac.compare_digest(sig, self._sign(payload)):
            return None, None
        try:
            data = json.loads(_unb64(payload))
        except (ValueError, UnicodeDecodeError):
            return None, None
        if data.get("exp", 0) < (now or time.time()):
            return None, None
        user = self.store.get(data.get("u", ""))
        return (user, data["csrf"]) if user and user.active else (None, None)

    def erp(self, org: str) -> ErpStore:
        if org not in self._erp:
            self._erp[org] = ErpStore(self.store.tenant_dir(org) / "erp.sqlite")
        return self._erp[org]

    # ---- WSGI ------------------------------------------------------
    def __call__(self, environ, start_response):
        try:
            status, headers, body = self.handle(environ)
        except HttpError as e:
            status, headers, body = self._json({"error": e.message}, e.status)
        except (ErpError, AuthError) as e:
            status, headers, body = self._json({"error": str(e)}, 401 if isinstance(e, AuthError) else 400)
        except Exception as e:  # never leak internals to the client
            print(f"erp: {type(e).__name__}: {e}", file=sys.stderr)
            status, headers, body = self._json({"error": "erreur interne"}, 500)
        headers += [("Content-Security-Policy", CSP), ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"),
                    ("Cache-Control", "no-store"), ("X-Frame-Options", "DENY")]
        start_response(f"{status} {_REASON.get(status, 'OK')}", headers)
        return [body]

    @staticmethod
    def _json(obj, status: int = 200, extra=()):
        return status, [("Content-Type", "application/json; charset=utf-8"), *extra], json.dumps(obj, ensure_ascii=False).encode()

    def _body(self, environ) -> dict:
        if "application/json" not in environ.get("CONTENT_TYPE", ""):
            raise HttpError(415, "JSON attendu")
        try:
            n = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HttpError(400, "requête invalide") from None
        if n > MAX_BODY:
            raise HttpError(413, "requête trop volumineuse")
        try:
            data = json.loads(environ["wsgi.input"].read(n) or b"{}")
        except ValueError:
            raise HttpError(400, "JSON invalide") from None
        if not isinstance(data, dict):
            raise HttpError(400, "objet JSON attendu")
        return data

    def handle(self, environ):
        method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "")
        if path in ("/erp", "/erp/"):
            return 200, [("Content-Type", "text/html; charset=utf-8")], (STATIC.parent / "index.html").read_bytes()
        m = re.fullmatch(r"/erp/static/([A-Za-z0-9._-]+)", path)
        if m and method == "GET":
            if m.group(1) not in STATIC_TYPES:
                raise HttpError(404, "introuvable")
            return 200, [("Content-Type", STATIC_TYPES[m.group(1)] + "; charset=utf-8"), ("Cache-Control", "public, max-age=3600")], \
                (STATIC / m.group(1)).read_bytes()
        if path == "/erp/api/login" and method == "POST":
            d = self._body(environ)
            user = self.store.authenticate(str(d.get("username", "")), str(d.get("password", "")))
            token, csrf = self.issue(user.username)
            self.store.audit(user, "erp:login")
            secure = self.cookie_secure if self.cookie_secure is not None else environ.get("HTTP_X_FORWARDED_PROTO") == "https"
            cookie = f"{COOKIE}={token}; Path=/erp; HttpOnly; SameSite=Strict; Max-Age={self.ttl}" + ("; Secure" if secure else "")
            return self._json({"user": user.username, "org": user.org, "role": user.role, "csrf": csrf}, 200, [("Set-Cookie", cookie)])

        user, csrf = self.session(environ)
        if not user:
            raise HttpError(401, "non connecté")
        if method != "GET":
            if not hmac.compare_digest(environ.get("HTTP_X_CSRF_TOKEN", ""), csrf):
                raise HttpError(403, "jeton CSRF invalide")
        if path == "/erp/api/logout" and method == "POST":
            return self._json({"ok": True}, 200, [("Set-Cookie", f"{COOKIE}=; Path=/erp; Max-Age=0; HttpOnly; SameSite=Strict")])
        if path == "/erp/api/me":
            return self._json({"user": user.username, "org": user.org, "role": user.role, "csrf": csrf})
        erp = self.erp(user.org)
        m = re.fullmatch(r"/erp/print/(\d+)", path)
        if m and method == "GET":
            return 200, [("Content-Type", "text/html; charset=utf-8")], render_document(erp.document(int(m.group(1))), user.org).encode()
        return self.api(erp, user, method, path, environ)

    def api(self, erp: ErpStore, user, method: str, path: str, environ):
        q = {k: v[0] for k, v in __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(environ.get("QUERY_STRING", "")).items()}
        audit = lambda what, detail="": self.store.audit(user, f"erp:{what}", detail=detail)
        if path == "/erp/api/dashboard" and method == "GET":
            return self._json(erp.dashboard())
        if path == "/erp/api/clients":
            if method == "GET":
                return self._json(erp.clients(q.get("q", "")))
            if method == "POST":
                c = erp.add_client(self._body(environ))
                audit("client.add", str(c["id"]))
                return self._json(c, 201)
        m = re.fullmatch(r"/erp/api/clients/(\d+)", path)
        if m:
            cid = int(m.group(1))
            if method == "PUT":
                audit("client.update", str(cid))
                return self._json(erp.update_client(cid, self._body(environ)))
            if method == "DELETE":
                if not user.is_admin:
                    raise HttpError(403, "réservé à l'administrateur")
                erp.delete_client(cid)
                audit("client.delete", str(cid))
                return self._json({"ok": True})
        if path == "/erp/api/cases":
            if method == "GET":
                return self._json(erp.cases(q.get("status", ""), int(q["client_id"]) if q.get("client_id", "").isdigit() else 0))
            if method == "POST":
                c = erp.add_case(self._body(environ))
                audit("case.add", c["ref"])
                return self._json(c, 201)
        m = re.fullmatch(r"/erp/api/cases/(\d+)", path)
        if m and method == "PUT":
            audit("case.update", m.group(1))
            return self._json(erp.update_case(int(m.group(1)), self._body(environ)))
        if path == "/erp/api/documents":
            if method == "GET":
                return self._json(erp.documents(q.get("kind", "")))
            if method == "POST":
                d = erp.create_document(self._body(environ))
                audit("document.add", d["number"])
                return self._json(d, 201)
        m = re.fullmatch(r"/erp/api/documents/(\d+)/(status|invoice|payments)", path)
        if m and method == "POST":
            doc_id, action = int(m.group(1)), m.group(2)
            body = self._body(environ)
            if action == "status":
                d = erp.set_document_status(doc_id, str(body.get("status", "")))
            elif action == "invoice":
                d = erp.quote_to_invoice(doc_id)
            else:
                d = erp.add_payment(doc_id, body)
            audit(f"document.{action}", d["number"])
            return self._json(d)
        raise HttpError(404, "introuvable")


_REASON = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
           413: "Payload Too Large", 415: "Unsupported Media Type", 500: "Internal Server Error"}


def money(cents: int, cur: str) -> str:
    sign, cents = ("-" if cents < 0 else ""), abs(cents)
    return f"{sign}{cents // 100:,}.{cents % 100:02d} {cur}".replace(",", " ")


def render_document(doc: dict, org: str) -> str:
    """Printable quote/invoice (the browser's Print dialog makes the PDF). Every value is HTML-escaped."""
    e = html.escape
    title = "Devis" if doc["kind"] == "quote" else "Facture"
    rows = "".join(f"<tr><td>{e(l['label'])}</td><td class='n'>{l['qty_milli'] / 1000:g}</td>"
                   f"<td class='n'>{e(money(l['unit_cents'], doc['currency']))}</td><td class='n'>{e(money(l['total_cents'], doc['currency']))}</td></tr>"
                   for l in doc["lines"])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{e(title)} {e(doc['number'])}</title>
<link rel="stylesheet" href="/erp/static/print.css"></head><body>
<button id="print" class="noprint">Imprimer / enregistrer en PDF</button>
<h1>{e(title)} {e(doc['number'])}</h1>
<p>{e(org)}<br>Date : {e(doc['issue_date'])}{(' · Échéance : ' + e(doc['due_date'])) if doc['due_date'] else ''}</p>
<p><strong>{e(doc['client_name'])}</strong><br>{e(doc['client_address'])}<br>{e(doc['client_tax_id'])}</p>
<table><thead><tr><th>Désignation</th><th>Qté</th><th>PU</th><th>Total</th></tr></thead><tbody>{rows}</tbody>
<tfoot><tr><td colspan="3">Sous-total</td><td class="n">{e(money(doc['subtotal_cents'], doc['currency']))}</td></tr>
<tr><td colspan="3">TVA {doc['vat_permille'] / 10:g} %</td><td class="n">{e(money(doc['vat_cents'], doc['currency']))}</td></tr>
<tr><th colspan="3">Total TTC</th><th class="n">{e(money(doc['total_cents'], doc['currency']))}</th></tr></tfoot></table>
<p>{e(doc['notes'])}</p><script src="/erp/static/print.js"></script></body></html>"""


class _Threaded(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _Quiet(WSGIRequestHandler):
    def log_message(self, fmt, *args):  # request lines can hold ids, keep them out of the console
        pass


def serve(data_dir: str, host: str = "127.0.0.1", port: int = 8502) -> None:
    app = ErpApp(data_dir, int(os.environ.get("AMINOS_SESSION_MINUTES", "480")),
                 os.environ.get("AMINOS_COOKIE_SECURE") == "1" or None)
    app.store.bootstrap_admin(os.environ.get("AMINOS_ADMIN_USER"), os.environ.get("AMINOS_ADMIN_PASSWORD"))
    with make_server(host, port, app, _Threaded, _Quiet) as srv:
        print(f"back-office sur http://{host}:{port}/erp/", flush=True)
        srv.serve_forever()


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m aminos.erp")
    ap.add_argument("--data", default=os.environ.get("AMINOS_DATA_DIR", "saas-data"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("AMINOS_ERP_PORT", "8502")))
    a = ap.parse_args(argv)
    serve(a.data, a.host, a.port)
    return 0
