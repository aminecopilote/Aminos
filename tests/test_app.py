import os
import tempfile
import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit not installed
    AppTest = None

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def validation_box(at):
    return next(c for c in at.checkbox if c.label.startswith("Validation d'Alami"))


def button(at, label):
    return next(b for b in at.button if b.label == label)


@unittest.skipIf(AppTest is None, "streamlit not installed")
class AppFlowTests(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def seeded(self):
        from aminos.glossary import Glossary, Term
        g = Glossary()
        g.add(Term("الحكم", "jugement"))
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["pairs"] = [("الحكم عدد 12", "Le jugement n° 12")]
        at.session_state["gloss"] = g
        at.session_state["final"] = "Le jugement n° 12"
        return at.run()

    def test_renders_without_error(self):
        at = AppTest.from_file(APP, default_timeout=60).run()
        self.assertFalse(at.exception)

    def test_review_flags_lost_number_and_term(self):
        at = self.seeded()
        at.text_area[0].set_value("La décision n° 13").run()
        warnings = " ".join(w.value for w in at.warning)
        self.assertIn("jugement", warnings)
        self.assertIn("12", warnings)

    def test_certification_flow_requires_validation_then_seals(self):
        at = self.seeded()
        button(at, "Créer la clé HMAC").click().run()
        button(at, "Générer le document certifié").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("00001." in s.value for s in at.success))
        seal = button(at, "Sceller")
        self.assertTrue(seal.proto.disabled)           # no validation yet
        validation_box(at).check().run()
        self.assertFalse(button(at, "Sceller").proto.disabled)
        button(at, "Sceller").click().run()
        self.assertTrue(any("scellé" in s.value for s in at.success))
        rows = Path("registre-certifications.csv").read_text(encoding="utf-8")
        self.assertIn("scellé", rows)
        self.assertEqual([p.name for p in Path("archive").iterdir()], ["00001.%d.docx" % __import__("datetime").date.today().year])
        self.assertTrue(list(Path("evaluations").glob("*.md")))

    def test_below_threshold_blocks_seal(self):
        at = self.seeded()
        button(at, "Créer la clé HMAC").click().run()
        button(at, "Générer le document certifié").click().run()
        next(n for n in at.number_input if n.label == "Fidélité").set_value(4).run()
        validation_box(at).check().run()
        self.assertTrue(button(at, "Sceller").proto.disabled)
        self.assertTrue(any("Seuil" in e.value for e in at.error))


if __name__ == "__main__":
    unittest.main()
