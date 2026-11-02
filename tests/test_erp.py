import io
import json
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from aminos.erp import ErpError, ErpStore
from aminos.erp.web import COOKIE, ErpApp
from aminos.saas import SaaSStore

PW = "Correct-horse-battery-1"


class Client:
    """Calls the WSGI app directly, keeping the cookie jar like a browser would."""

    def __init__(self, app):
        self.app, self.cookie, self.csrf = app, "", ""

    def call(self, method, path, body=None, csrf=True, ctype="application/json", cookie=None):
        env = {}
        setup_testing_defaults(env)
        raw = json.dumps(body).encode() if body is not None else b""
        env.update(REQUEST_METHOD=method, PATH_INFO=path.split("?")[0], QUERY_STRING=path.partition("?")[2],
                   CONTENT_TYPE=ctype, CONTENT_LENGTH=str(len(raw)), **{"wsgi.input": io.BytesIO(raw)})
        c = self.cookie if cookie is None else cookie
        if c:
            env["HTTP_COOKIE"] = f"{COOKIE}={c}"
        if csrf and self.csrf:
            env["HTTP_X_CSRF_TOKEN"] = self.csrf
        out = {}
        res = b"".join(self.app(env, lambda s, h: out.update(status=int(s.split()[0]), headers=dict(h))))
        if "Set-Cookie" in out["headers"] and path.endswith("/login"):
            self.cookie = out["headers"]["Set-Cookie"].split(";")[0].split("=", 1)[1]
        try:
            data = json.loads(res)
        except ValueError:
            data = res.decode()
        return out["status"], data, out["headers"]

    def login(self, user):
        s, d, _ = self.call("POST", "/erp/api/login", {"username": user, "password": PW}, csrf=False)
        assert s == 200, d
        self.csrf = d["csrf"]
        return d


class ErpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        s = SaaSStore(self.data)
        s.create_user("alice", PW, "cab-a", "admin")
        s.create_user("bob", PW, "cab-a", "user")
        s.create_user("carol", PW, "cab-b", "admin")
        self.app = ErpApp(self.data)

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, user):
        c = Client(self.app)
        c.login(user)
        return c

    def make_invoice(self, c, price=10000):
        cl = c.call("POST", "/erp/api/clients", {"name": "Client SARL"})[1]
        q = c.call("POST", "/erp/api/documents", {"kind": "quote", "client_id": cl["id"], "vat_permille": 200,
                                                  "lines": [{"label": "Traduction", "qty_milli": 2500, "unit_cents": price}]})[1]
        c.call("POST", f"/erp/api/documents/{q['id']}/status", {"status": "sent"})
        inv = c.call("POST", f"/erp/api/documents/{q['id']}/invoice", {})[1]
        c.call("POST", f"/erp/api/documents/{inv['id']}/status", {"status": "sent"})
        return cl, q, inv

    # ---- access control ------------------------------------------
    def test_requires_login_and_csrf(self):
        c = Client(self.app)
        self.assertEqual(c.call("GET", "/erp/api/clients")[0], 401)
        c.login("alice")
        self.assertEqual(c.call("GET", "/erp/api/clients")[0], 200)
        c.csrf = "wrong"
        self.assertEqual(c.call("POST", "/erp/api/clients", {"name": "X"})[0], 403)
        c.csrf = ""
        self.assertEqual(c.call("POST", "/erp/api/clients", {"name": "X"})[0], 403)

    def test_json_only(self):
        c = self.client("alice")
        self.assertEqual(c.call("POST", "/erp/api/clients", {"name": "X"}, ctype="text/plain")[0], 415)

    def test_bad_password_and_tampered_cookie(self):
        c = Client(self.app)
        self.assertEqual(c.call("POST", "/erp/api/login", {"username": "alice", "password": "nope"}, csrf=False)[0], 401)
        good = self.client("alice")
        payload, sig = good.cookie.rsplit(".", 1)
        forged = Client(self.app)
        self.assertEqual(forged.call("GET", "/erp/api/me", cookie=payload + "." + "A" * len(sig))[0], 401)
        self.assertEqual(forged.call("GET", "/erp/api/me", cookie="garbage")[0], 401)

    def test_expired_and_disabled(self):
        c = self.client("bob")
        self.assertEqual(c.call("GET", "/erp/api/me")[0], 200)
        self.assertIsNone(self.app.session({"HTTP_COOKIE": f"{COOKIE}={c.cookie}"}, now=10**11)[0])
        self.app.store.update_user("bob", active=False)
        self.assertEqual(c.call("GET", "/erp/api/me")[0], 401)

    def test_tenants_are_isolated(self):
        a, b = self.client("alice"), self.client("carol")
        a.call("POST", "/erp/api/clients", {"name": "Secret client"})
        self.assertEqual(b.call("GET", "/erp/api/clients")[1], [])
        # alice's client id means nothing in carol's firm
        self.assertEqual(b.call("POST", "/erp/api/cases", {"client_id": 1, "title": "t", "src": "ar", "tgt": "fr"})[0], 400)
        self.assertTrue((self.data / "tenants" / "cab-a" / "erp.sqlite").exists())

    def test_delete_is_admin_only(self):
        a, bob = self.client("alice"), self.client("bob")
        cid = a.call("POST", "/erp/api/clients", {"name": "Y"})[1]["id"]
        self.assertEqual(bob.call("DELETE", f"/erp/api/clients/{cid}")[0], 403)
        self.assertEqual(a.call("DELETE", f"/erp/api/clients/{cid}")[0], 200)

    # ---- accounting rules ----------------------------------------
    def test_numbers_totals_and_payments(self):
        c = self.client("alice")
        _, q, inv = self.make_invoice(c)
        self.assertTrue(q["number"].startswith("DV-") and q["number"].endswith("-0001"))
        self.assertTrue(inv["number"].startswith("FA-") and inv["number"].endswith("-0001"))
        # 2.5 x 100.00 = 250.00 ; VAT 20 % = 50.00
        self.assertEqual((inv["subtotal_cents"], inv["vat_cents"], inv["total_cents"]), (25000, 5000, 30000))
        s, d, _ = c.call("POST", f"/erp/api/documents/{inv['id']}/payments", {"cents": 40000})
        self.assertEqual(s, 400)                                  # more than the balance
        s, d, _ = c.call("POST", f"/erp/api/documents/{inv['id']}/payments", {"cents": 10000, "method": "virement"})
        self.assertEqual((d["paid_cents"], d["balance_cents"], d["status"]), (10000, 20000, "sent"))
        s, d, _ = c.call("POST", f"/erp/api/documents/{inv['id']}/payments", {"cents": 20000})
        self.assertEqual((d["balance_cents"], d["status"]), (0, "paid"))
        self.assertEqual(c.call("POST", f"/erp/api/documents/{inv['id']}/status", {"status": "sent"})[0], 400)

    def test_quote_billed_once(self):
        c = self.client("alice")
        _, q, _ = self.make_invoice(c)
        self.assertEqual(c.call("POST", f"/erp/api/documents/{q['id']}/invoice", {})[0], 400)

    def test_draft_invoice_takes_no_payment(self):
        c = self.client("alice")
        cl = c.call("POST", "/erp/api/clients", {"name": "Z"})[1]
        inv = c.call("POST", "/erp/api/documents", {"kind": "invoice", "client_id": cl["id"], "lines": [{"label": "x", "qty_milli": 1000, "unit_cents": 100}]})[1]
        self.assertEqual(c.call("POST", f"/erp/api/documents/{inv['id']}/payments", {"cents": 100})[0], 400)

    def test_validation(self):
        c = self.client("alice")
        cl = c.call("POST", "/erp/api/clients", {"name": "V"})[1]
        bad = [{"kind": "quote", "client_id": cl["id"], "lines": []},
               {"kind": "quote", "client_id": cl["id"], "lines": [{"label": "x", "qty_milli": -1, "unit_cents": 1}]},
               {"kind": "quote", "client_id": cl["id"], "lines": [{"label": "x", "qty_milli": 1000, "unit_cents": "1"}]},
               {"kind": "other", "client_id": cl["id"], "lines": [{"label": "x", "qty_milli": 1, "unit_cents": 1}]},
               {"kind": "quote", "client_id": cl["id"], "issue_date": "2026-13-45", "lines": [{"label": "x", "qty_milli": 1, "unit_cents": 1}]}]
        for body in bad:
            self.assertEqual(c.call("POST", "/erp/api/documents", body)[0], 400, body)
        self.assertEqual(c.call("POST", "/erp/api/cases", {"client_id": cl["id"], "title": "t", "src": "fr", "tgt": "fr"})[0], 400)
        self.assertEqual(c.call("POST", "/erp/api/clients", {"name": ""})[0], 400)

    def test_case_flow_and_dashboard(self):
        c = self.client("alice")
        cl = c.call("POST", "/erp/api/clients", {"name": "Cab"})[1]
        case = c.call("POST", "/erp/api/cases", {"client_id": cl["id"], "title": "Acte de naissance", "src": "ar", "tgt": "fr",
                                                 "deadline": "2020-01-01", "job_id": "acte-12345678-ar-fr"})[1]
        self.assertTrue(case["ref"].endswith("-0001"))
        dash = c.call("GET", "/erp/api/dashboard")[1]
        self.assertEqual(dash["cases_by_status"], {"nouveau": 1})
        self.assertEqual(len(dash["late_cases"]), 1)
        c.call("PUT", f"/erp/api/cases/{case['id']}", {"status": "livre"})
        self.assertEqual(c.call("GET", "/erp/api/dashboard")[1]["late_cases"], [])
        self.assertEqual(c.call("PUT", f"/erp/api/cases/{case['id']}", {"status": "bogus"})[0], 400)

    def test_sql_injection_is_inert(self):
        c = self.client("alice")
        c.call("POST", "/erp/api/clients", {"name": "Normal"})
        s, rows, _ = c.call("GET", "/erp/api/clients?q=" + "%27%20OR%201%3D1%3B--")
        self.assertEqual((s, rows), (200, []))
        c.call("POST", "/erp/api/clients", {"name": "x'); DROP TABLE clients;--"})
        self.assertEqual(len(c.call("GET", "/erp/api/clients")[1]), 2)

    # ---- output hardening ----------------------------------------
    def test_print_page_escapes_html(self):
        c = self.client("alice")
        cl = c.call("POST", "/erp/api/clients", {"name": "<script>alert(1)</script>"})[1]
        d = c.call("POST", "/erp/api/documents", {"kind": "quote", "client_id": cl["id"], "notes": "<img src=x onerror=1>",
                                                  "lines": [{"label": "<b>x</b>", "qty_milli": 1000, "unit_cents": 100}]})[1]
        s, page, h = c.call("GET", f"/erp/print/{d['id']}")
        self.assertEqual(s, 200)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("script-src 'self'", h["Content-Security-Policy"])

    def test_static_whitelist_and_traversal(self):
        c = Client(self.app)
        self.assertEqual(c.call("GET", "/erp/static/bootstrap.min.css")[0], 200)
        for p in ("/erp/static/../store.py", "/erp/static/%2e%2e%2fstore.py", "/erp/static/..%5cstore.py"):
            s, body, _ = c.call("GET", p)
            self.assertIn(s, (401, 404))                      # never served, whatever the rejection path
            self.assertNotIn("class ErpStore", str(body))
        self.assertEqual(c.call("GET", "/erp/static/index.html")[0], 404)
        s, page, h = c.call("GET", "/erp/")
        self.assertEqual(s, 200)
        self.assertIn("app.js", page)
        self.assertNotIn("http://", page.replace("http://www.w3.org", ""))      # nothing from a third party

    def test_secret_file_is_private(self):
        self.assertEqual((self.data / "erp-secret").stat().st_mode & 0o077, 0)

    def test_audit_records_writes(self):
        c = self.client("alice")
        c.call("POST", "/erp/api/clients", {"name": "Audited"})
        labels = [e["label"] for e in self.app.store.audit_ledger("cab-a").entries()]
        self.assertIn("erp:client.add", labels)
        self.app.store.audit_ledger("cab-a").verify()


class StoreTests(unittest.TestCase):
    def test_numbering_is_gapless_per_year(self):
        with tempfile.TemporaryDirectory() as d:
            s = ErpStore(Path(d) / "e.sqlite")
            cl = s.add_client({"name": "A"})
            nums = [s.create_document({"kind": "invoice", "client_id": cl["id"], "issue_date": f"2025-0{m}-01",
                                       "lines": [{"label": "x", "qty_milli": 1000, "unit_cents": 1}]})["number"] for m in (1, 2, 3)]
            self.assertEqual(nums, ["FA-2025-0001", "FA-2025-0002", "FA-2025-0003"])
            n26 = s.create_document({"kind": "invoice", "client_id": cl["id"], "issue_date": "2026-01-01",
                                     "lines": [{"label": "x", "qty_milli": 1000, "unit_cents": 1}]})["number"]
            self.assertEqual(n26, "FA-2026-0001")

    def test_client_with_documents_cannot_be_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            s = ErpStore(Path(d) / "e.sqlite")
            cl = s.add_client({"name": "A"})
            s.add_case({"client_id": cl["id"], "title": "t", "src": "ar", "tgt": "fr"})
            with self.assertRaises(ErpError):
                s.delete_client(cl["id"])


if __name__ == "__main__":
    unittest.main()
