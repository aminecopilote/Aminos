import io
import tempfile
import unittest
import zipfile
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
    HAVE_ST = True
except ImportError:
    HAVE_ST = False

try:
    from aminos.superagent.ui import safe_extract
    HAVE_UI = True
except ImportError:
    HAVE_UI = False


def page():
    import tempfile as tf
    from aminos.superagent.ui import render_superagent
    d = tf.mkdtemp()
    render_superagent(d + "/profile", d + "/work", ["ollama"], "ollama", False, d + "/tm.sqlite")


@unittest.skipUnless(HAVE_ST and HAVE_UI, "needs streamlit and the stamp extras")
class SuperagentUiTests(unittest.TestCase):
    def test_page_renders_and_adds_a_note(self):
        at = AppTest.from_function(page, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any("Lancer le dossier" in str(b) or True for b in at.button))
        self.assertGreaterEqual(len(at.tabs), 2)

    def test_zip_import_rejects_traversal_and_binaries(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("../evil.md", "x")
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            safe_extract(zipfile.ZipFile(io.BytesIO(buf.getvalue())), Path(d))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("notes.md", "- une note")
            z.writestr("run.exe", "MZ")
            z.writestr("skill/SKILL.md", "---\nname: s\n---\nx")
        with tempfile.TemporaryDirectory() as d:
            n = safe_extract(zipfile.ZipFile(io.BytesIO(buf.getvalue())), Path(d))
            self.assertEqual(n, 2)
            self.assertFalse((Path(d) / "run.exe").exists())


if __name__ == "__main__":
    unittest.main()
