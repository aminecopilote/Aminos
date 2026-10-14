import tempfile
import unittest
from pathlib import Path

from aminos.saas import AuthError, QuotaExceeded, SaaSStore
from aminos.saas.store import LOCK_MINUTES, MAX_FAILURES, hash_password, verify_password

PW = "correct horse battery"


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.s = SaaSStore(self.root)
        self.alice = self.s.create_user("Alice", PW, "cabinet-a")
        self.bob = self.s.create_user("bob", PW, "cabinet-b", quota_docs_day=2, quota_chars_day=100)

    def test_password_hash_is_salted_and_verified(self):
        a, b = hash_password(PW), hash_password(PW)
        self.assertNotEqual(a, b)
        self.assertTrue(verify_password(PW, a) and not verify_password(PW + "x", a))
        self.assertFalse(verify_password(PW, "garbage"))
        self.assertNotIn(PW, (self.root / "saas.sqlite").read_bytes().decode("latin1"))

    def test_login_success_and_generic_failures(self):
        self.assertEqual(self.s.authenticate("ALICE", PW).username, "alice")
        msgs = set()
        for u, p in (("alice", "wrong-password-1"), ("nobody", PW)):
            with self.assertRaises(AuthError) as c:
                self.s.authenticate(u, p)
            msgs.add(str(c.exception))
        self.assertEqual(len(msgs), 1)  # unknown user and wrong password are indistinguishable

    def test_disabled_account_cannot_log_in(self):
        self.s.update_user("alice", active=False)
        with self.assertRaises(AuthError):
            self.s.authenticate("alice", PW)

    def test_lockout_then_release(self):
        t = 1_000_000
        for i in range(MAX_FAILURES):
            with self.assertRaises(AuthError):
                self.s.authenticate("alice", "bad-password-xx", now=t + i)
        with self.assertRaises(AuthError):  # right password is refused while locked
            self.s.authenticate("alice", PW, now=t + MAX_FAILURES)
        self.assertEqual(self.s.authenticate("alice", PW, now=t + LOCK_MINUTES * 60 + 60).username, "alice")

    def test_weak_password_and_bad_names_rejected(self):
        for args in (("carol", "short", "x"), ("../etc", PW, "x"), ("carol", PW, "../evil"), ("carol", PW, "A B")):
            with self.assertRaises(AuthError):
                self.s.create_user(*args)
        with self.assertRaises(AuthError):
            self.s.create_user("alice", PW, "cabinet-a")  # duplicate

    def test_tenants_are_isolated_directories(self):
        pa, pb = self.s.tm_path(self.alice), self.s.tm_path(self.bob)
        self.assertNotEqual(pa, pb)
        self.assertEqual(Path(pa).parent.parent, self.root / "tenants")
        with self.assertRaises(AuthError):
            self.s.tenant_dir("../../etc")

    def test_quota_documents_and_characters(self):
        self.s.consume(self.bob, 40)
        self.s.consume(self.bob, 40)
        with self.assertRaises(QuotaExceeded):
            self.s.consume(self.bob, 1)  # third document
        carol = self.s.create_user("carol", PW, "cabinet-b", quota_docs_day=9, quota_chars_day=100)
        with self.assertRaises(QuotaExceeded):
            self.s.consume(carol, 101)
        self.s.consume(carol, 60)
        with self.assertRaises(QuotaExceeded):
            self.s.consume(carol, 60)
        self.assertEqual(self.s.usage_today("carol"), (1, 60))

    def test_quota_resets_next_day(self):
        self.s.consume(self.bob, 100, now=0)
        self.s.consume(self.bob, 100, now=86400 + 1)

    def test_audit_chain_per_org_without_content(self):
        self.s.audit(self.alice, "translate", "ab" * 32, "contrat.docx")
        self.s.audit(self.alice, "download")
        self.s.audit(self.bob, "translate")
        self.assertEqual(self.s.audit_ledger("cabinet-a").verify(), 2)
        self.assertEqual(self.s.audit_ledger("cabinet-b").verify(), 1)
        p = self.s.tenant_dir("cabinet-a") / "audit.jsonl"
        p.write_text(p.read_text().replace('"alice"', '"mallory"'))
        with self.assertRaises(Exception):
            self.s.audit_ledger("cabinet-a").verify()

    def test_bootstrap_admin_only_once(self):
        fresh = SaaSStore(tempfile.mkdtemp())
        self.assertFalse(fresh.bootstrap_admin(None, None))
        self.assertTrue(fresh.bootstrap_admin("root", PW))
        self.assertTrue(fresh.get("root").is_admin)
        self.assertFalse(fresh.bootstrap_admin("other", PW))
        self.assertEqual(fresh.count_users(), 1)


if __name__ == "__main__":
    unittest.main()
