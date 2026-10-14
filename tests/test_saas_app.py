import os
import tempfile
import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
    HAVE_ST = True
except ImportError:
    HAVE_ST = False

ROOT = Path(__file__).resolve().parent.parent
PW = "correct horse battery"


@unittest.skipUnless(HAVE_ST, "needs streamlit")
class SaasAppTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self._old = dict(os.environ)
        os.environ.update(AMINOS_DATA_DIR=self.data, AMINOS_ADMIN_USER="root", AMINOS_ADMIN_PASSWORD=PW)
        os.environ.pop("AMINOS_ALLOW_REMOTE_LLM", None)
        import streamlit as st
        st.cache_resource.clear()

    def tearDown(self):
        os.environ.clear(); os.environ.update(self._old)

    def app(self):
        return AppTest.from_file(str(ROOT / "saas_app.py"), default_timeout=60).run()

    def login(self, at, user, pw):
        at.text_input[0].set_value(user); at.text_input[1].set_value(pw)
        at.button[0].click()
        return at.run()

    def test_login_screen_has_no_translation_ui(self):
        at = self.app()
        self.assertEqual([b.label for b in at.button], ["Se connecter"])
        self.assertFalse(at.sidebar.selectbox)

    def test_wrong_password_rejected_right_one_accepted(self):
        at = self.login(self.app(), "root", "wrong-password-1")
        self.assertTrue(at.error and "incorrect" in at.error[0].value)
        at = self.login(self.app(), "root", PW)
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(at.tabs and [t.label for t in at.tabs] == ["Traduction", "Administration"])

    def test_regular_user_sees_no_admin_and_locked_down_sidebar(self):
        from aminos.saas import SaaSStore
        SaaSStore(self.data).create_user("alice", PW, "cabinet-a")
        at = self.login(self.app(), "alice", PW)
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(at.tabs)
        labels = [w.label for w in at.sidebar.text_input]
        self.assertNotIn("Clé ANTHROPIC_API_KEY", labels)          # no key typed into a shared process
        self.assertNotIn("Base de mémoire de traduction", labels)  # no user-chosen path
        providers = at.sidebar.multiselect[0]
        self.assertEqual(providers.options, ["ollama"])             # remote providers off by default

    def test_admin_creates_account_and_it_works(self):
        at = self.login(self.app(), "root", PW)
        with_form = at
        # fill the "create" form
        inputs = {w.label: w for w in with_form.text_input}
        inputs["Identifiant"].set_value("bob"); inputs["Cabinet (ex. cabinet-alami)"].set_value("cabinet-b")
        next(b for b in with_form.button if b.label == "Créer").click()
        with_form.run()
        self.assertFalse(with_form.exception, with_form.exception)
        self.assertTrue(any("Compte créé" in s.value for s in with_form.success), [s.value for s in with_form.success])
        from aminos.saas import SaaSStore
        self.assertEqual(SaaSStore(self.data).get("bob").org, "cabinet-b")


if __name__ == "__main__":
    unittest.main()
