import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from wsgiref.util import setup_testing_defaults

from aminos.erp import system
from aminos.erp.tokens import TokenStore
from aminos.erp.web import ErpApp, main
from aminos.saas import SaaSStore

PW = "Correct-horse-battery-1"
import collections
DISK = collections.namedtuple("usage", "total used free")


def call(app, method, path, token=None, body=None):
    env = {}
    setup_testing_defaults(env)
    raw = json.dumps(body).encode() if body is not None else b""
    env.update(REQUEST_METHOD=method, PATH_INFO=path.split("?")[0], QUERY_STRING=path.partition("?")[2],
               CONTENT_TYPE="application/json", CONTENT_LENGTH=str(len(raw)), **{"wsgi.input": io.BytesIO(raw)})
    if token:
        env["HTTP_AUTHORIZATION"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    out = {}
    res = b"".join(app(env, lambda s, h: out.update(status=int(s.split()[0]))))
    try:
        return out["status"], json.loads(res)
    except ValueError:
        return out["status"], res.decode()


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        s = SaaSStore(self.data)
        s.create_user("alice", PW, "cab-a", "admin")
        s.create_user("carol", PW, "cab-b", "admin")
        self.app = ErpApp(self.data)
        self.ts = TokenStore(self.data)
        self.write_a = self.ts.create("write", "cab-a", "n8n")
        self.read_a = self.ts.create("read", "cab-a", "viewer")
        self.write_b = self.ts.create("write", "cab-b", "n8n-b")
        self.system = self.ts.create("system", label="ops")

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_the_hash_is_stored(self):
        raw = (self.data / "api-tokens.sqlite").read_bytes()
        self.assertNotIn(self.write_a.encode(), raw)
        self.assertEqual(self.ts.verify(self.write_a)["org"], "cab-a")
        self.assertIsNone(self.ts.verify(self.write_a + "x"))
        self.assertIsNone(self.ts.verify("not-a-token"))

    def test_scopes(self):
        s, c = call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "Via n8n"})
        self.assertEqual(s, 201)
        self.assertEqual(call(self.app, "GET", "/erp/api/clients", self.read_a)[1][0]["name"], "Via n8n")
        self.assertEqual(call(self.app, "POST", "/erp/api/clients", self.read_a, {"name": "x"})[0], 403)      # read cannot write
        self.assertEqual(call(self.app, "DELETE", f"/erp/api/clients/{c['id']}", self.write_a)[0], 403)      # nobody deletes by token
        self.assertEqual(call(self.app, "GET", "/erp/api/clients", self.system)[0], 403)                      # system sees no firm data
        self.assertEqual(call(self.app, "GET", "/erp/api/clients")[0], 401)

    def test_firms_are_isolated(self):
        call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "Secret A"})
        self.assertEqual(call(self.app, "GET", "/erp/api/clients", self.write_b)[1], [])

    def test_revoked_and_malformed(self):
        tid = self.ts.verify(self.read_a)["id"]
        self.assertTrue(self.ts.revoke(tid))
        self.assertEqual(call(self.app, "GET", "/erp/api/clients", self.read_a)[0], 401)
        for bad in ("Basic abc", "Bearer", "Bearer amn_", "bearer " + "a" * 300):
            self.assertEqual(call(self.app, "GET", "/erp/api/clients", bad)[0], 401, bad)

    def test_token_actions_are_audited(self):
        call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "Audited"})
        e = [x for x in SaaSStore(self.data).audit_ledger("cab-a").entries() if x["label"] == "erp:client.add"]
        self.assertTrue(e and e[0]["extra"]["user"].startswith("token:"))

    def test_session_cannot_use_system_endpoints(self):
        env = {}
        setup_testing_defaults(env)
        s, _ = call(self.app, "GET", "/erp/api/system/status")
        self.assertEqual(s, 401)
        self.assertEqual(call(self.app, "GET", "/erp/api/system/status", self.write_a)[0], 403)

    # ---- system endpoints ---------------------------------------
    def test_status_reports_problems(self):
        call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "C"})
        with mock.patch.object(system, "_probe", return_value=True), \
                mock.patch.object(system.shutil, "disk_usage", return_value=DISK(100 * 10**9, 40 * 10**9, 60 * 10**9)):
            s, st = call(self.app, "GET", "/erp/api/system/status", self.system)
        self.assertEqual(s, 200)
        self.assertTrue(st["ok"], st)
        self.assertEqual([o["clients"] for o in st["orgs"] if o["org"] == "cab-a"], [1])
        with mock.patch.object(system, "_probe", return_value=False), \
                mock.patch.object(system.shutil, "disk_usage", return_value=DISK(100 * 10**9, 95 * 10**9, 5 * 10**9)):
            st = call(self.app, "GET", "/erp/api/system/status", self.system)[1]
        self.assertFalse(st["ok"])
        self.assertIn("application de traduction injoignable", st["problems"])
        self.assertIn("moins de 10 % d'espace disque libre", st["problems"])

    def test_status_detects_tampered_audit_log(self):
        call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "C"})
        log = self.data / "tenants" / "cab-a" / "audit.jsonl"
        log.write_text(log.read_text().replace("erp:client.add", "erp:client.zzz"), encoding="utf-8")
        with mock.patch.object(system, "_probe", return_value=True), \
                mock.patch.object(system.shutil, "disk_usage", return_value=DISK(100 * 10**9, 40 * 10**9, 60 * 10**9)):
            st = call(self.app, "GET", "/erp/api/system/status", self.system)[1]
        self.assertFalse(st["ok"])
        self.assertTrue(any("audit" in p for p in st["problems"]))

    def test_backup_is_consistent_private_and_pruned(self):
        call(self.app, "POST", "/erp/api/clients", self.write_a, {"name": "To keep"})
        with mock.patch.dict("os.environ", {"AMINOS_BACKUP_KEEP": "2"}):
            for _ in range(3):
                s, m = call(self.app, "POST", "/erp/api/system/backup", self.system)
                self.assertEqual(s, 200)
                self.assertTrue(m["ok"], m)
                import time
                time.sleep(1.1)
        self.assertEqual(len(list((self.data / "backups").iterdir())), 2)
        import sqlite3
        newest = sorted((self.data / "backups").iterdir())[-1]
        n = sqlite3.connect(newest / "cab-a" / "erp.sqlite").execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        self.assertEqual(n, 1)
        self.assertEqual(oct(newest.stat().st_mode & 0o777), "0o700")

    def test_jobs_listing(self):
        d = self.data / "tenants" / "cab-a" / "work" / "jobs" / "x-1"
        d.mkdir(parents=True)
        (d / "job.json").write_text(json.dumps({"id": "x-1", "status": "non_concluant", "issues": ["a", "b"], "updated": 1}))
        jobs = call(self.app, "GET", "/erp/api/system/jobs", self.system)[1]
        self.assertEqual(jobs, [{"org": "cab-a", "id": "x-1", "status": "non_concluant", "issues": 2, "updated": 1}])

    def test_cli_token_create_list_revoke(self):
        with mock.patch("sys.stdout", new=io.StringIO()) as out, mock.patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(main(["--data", str(self.data), "token", "create", "--scope", "write", "--org", "cab-a", "--label", "cli"]), 0)
            tok = out.getvalue().strip()
        self.assertTrue(tok.startswith("amn_"))
        self.assertEqual(self.ts.verify(tok)["label"], "cli")
        with mock.patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(main(["--data", str(self.data), "token", "create", "--scope", "write"]), 2)   # firm required


if __name__ == "__main__":
    unittest.main()
