import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from aminos import n8n
from aminos.erp.tokens import TokenStore


class N8nTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.res = n8n.prepare(self.d / "out", self.d / "data", "cab-a", "http://erp:8502", "http://app:8501", "http://alert/x")

    def tearDown(self):
        self.tmp.cleanup()

    def flows(self):
        return [json.loads(Path(p).read_text(encoding="utf-8")) for p in self.res["workflows"]]

    def test_five_valid_workflows(self):
        flows = self.flows()
        self.assertEqual(len(flows), 5)
        for f in flows:
            names = {n["name"] for n in f["nodes"]}
            self.assertEqual(len(names), len(f["nodes"]), "duplicate node names")
            for src, v in f["connections"].items():
                self.assertIn(src, names)
                for outs in v["main"]:
                    for t in outs:
                        self.assertIn(t["node"], names)
            self.assertFalse(f["active"])

    def test_workflow_ids_file_matches_the_workflows(self):
        ids = (Path(self.res["credentials"]).parent / "workflow-ids.txt").read_text().split()
        self.assertEqual(sorted(ids), sorted(f["id"] for f in self.flows()))
        self.assertEqual(len(set(ids)), 5)

    def test_no_secret_inside_workflows(self):
        text = "".join(Path(p).read_text(encoding="utf-8") for p in self.res["workflows"])
        self.assertNotIn("amn_", text)
        self.assertNotIn(self.res["intake_secret"], text)
        self.assertIn("http://erp:8502", text)

    def test_every_credential_reference_exists(self):
        creds = json.loads(Path(self.res["credentials"]).read_text())
        known = {c["id"] for c in creds}
        for f in self.flows():
            for node in f["nodes"]:
                for ref in node.get("credentials", {}).values():
                    self.assertIn(ref["id"], known)

    def test_tokens_have_least_privilege(self):
        creds = {c["name"]: c["data"]["value"] for c in json.loads(Path(self.res["credentials"]).read_text())}
        ts = TokenStore(self.d / "data")
        sysd = ts.verify(creds[n8n.CRED_SYSTEM].removeprefix("Bearer "))
        self.assertEqual((sysd["scope"], sysd["org"]), ("system", ""))
        self.assertEqual(ts.verify(creds[n8n.CRED_READ].removeprefix("Bearer "))["scope"], "read")
        wr = ts.verify(creds[n8n.CRED_WRITE].removeprefix("Bearer "))
        self.assertEqual((wr["scope"], wr["org"]), ("write", "cab-a"))

    def test_workflows_cannot_delete_or_run_commands(self):
        text = "".join(Path(p).read_text(encoding="utf-8") for p in self.res["workflows"])
        self.assertNotIn('"DELETE"', text)
        self.assertNotIn("executeCommand", text)

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_credentials_file_is_private(self):
        self.assertEqual(stat.S_IMODE(os.stat(self.res["credentials"]).st_mode), 0o600)

    def test_prepare_is_idempotent_and_keeps_tokens(self):
        before = Path(self.res["credentials"]).read_text()
        again = n8n.prepare(self.d / "out", self.d / "data", "cab-a", "http://erp2:8502", "http://app:8501")
        self.assertEqual(Path(again["credentials"]).read_text(), before)          # same tokens, nothing new minted
        self.assertEqual(again["intake_secret"], self.res["intake_secret"])
        self.assertEqual(len(TokenStore(self.d / "data").list()), 3)
        self.assertIn("http://erp2:8502", Path(again["workflows"][0]).read_text(encoding="utf-8"))   # urls refreshed

    def test_alerts_are_silent_without_a_url(self):
        n8n.write_workflows(self.d / "w", "http://e", "http://a", "")
        health = json.loads((self.d / "w" / "aminos-surveillance.json").read_text(encoding="utf-8"))
        cfg = next(n for n in health["nodes"] if n["name"] == "Config")
        alert = next(a for a in cfg["parameters"]["assignments"]["assignments"] if a["name"] == "alertUrl")
        self.assertEqual(alert["value"], "")


if __name__ == "__main__":
    unittest.main()
