import json
import tempfile
import unittest
from pathlib import Path

try:
    import pyhanko  # noqa: F401
    import reportlab  # noqa: F401
    import pypdf  # noqa: F401
    from docx import Document
    from aminos.superagent import JobError, Profile, Superagent
    from aminos.superagent import apostille, stamp
    from aminos.superagent.cli import stub_chat
    HAVE = True
except ImportError:
    HAVE = False

from aminos.glossary import Glossary, Term
from aminos.prompts import DELIMITER


def make_doc(path, lines):
    d = Document()
    for t in lines:
        d.add_paragraph(t)
    d.save(path)


LINES = ["CONTRAT DE BAIL N° 2024/118", "Le preneur verse 1 500 dirhams le 5 de chaque mois."]


@unittest.skipUnless(HAVE, "needs the notary + stamp extras")
class SuperagentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        make_doc(self.d / "bail.docx", LINES)
        self.prof = Profile(self.d / "profile")
        self.prof.set_param("translator", {"name": "Test", "capacity": "traducteur", "registration": "", "place": "Rabat"})

    def tearDown(self):
        self.tmp.cleanup()

    def agent(self, chats, **kw):
        return Superagent(self.prof, self.d / "work", chats, **kw)

    # ---- profile -------------------------------------------------
    def test_import_export_files(self):
        src = self.d / "export"
        (src / "skills" / "mon-skill").mkdir(parents=True)
        (src / "skills" / "mon-skill" / "SKILL.md").write_text("---\nname: mon-skill\n---\ncorps", encoding="utf-8")
        (src / "skills" / "mon-skill" / "run.py").write_text("print('x')", encoding="utf-8")
        (src / "CLAUDE.md").write_text("Toujours vouvoyer.", encoding="utf-8")
        (src / "memoire.md").write_text("- Le client Alami veut « bailleur ».\n- Dates au format jj/mm/aaaa.", encoding="utf-8")
        (src / "conversations.json").write_text("[]", encoding="utf-8")
        rep = self.prof.import_claude_export(src)
        self.assertEqual(rep["skills"], ["mon-skill"])
        self.assertEqual(rep["notes"], 2)
        self.assertIn("Toujours vouvoyer", self.prof.instructions)
        self.assertTrue(any("run.py" in s for s in rep["skipped"]))      # scripts are never copied
        self.assertTrue(any("conversations" in s for s in rep["skipped"]))
        self.assertFalse((self.prof.root / "skills" / "mon-skill" / "run.py").exists())
        self.assertEqual(self.prof.skills(), ["mon-skill"])

    def test_memory_search_and_prompt(self):
        self.prof.remember("Le client Alami veut « bailleur » pour landlord.")
        self.assertFalse(self.prof.remember("le client alami veut « bailleur » pour landlord."))  # duplicate
        extra = self.prof.prompt_extra("contrat avec M. Alami, bailleur")
        self.assertIn("Alami", extra)
        self.assertIn("Gras", extra)                      # house rules always present
        n = self.prof.search("alami")[0]
        self.assertTrue(self.prof.forget(n.id))
        self.assertEqual(self.prof.search("alami"), [])

    def test_memory_reaches_the_model_prompt(self):
        self.prof.remember("Toujours traduire preneur par lessee.")
        seen = []

        def chat(messages, system):
            seen.append(system)
            return stub_chat(messages, system)
        self.agent([chat]).run(self.d / "bail.docx", "français", "anglais")
        self.assertTrue(any("lessee" in s for s in seen))

    # ---- run -----------------------------------------------------
    def test_run_then_certify_verify_dossier(self):
        sa = self.agent([stub_chat])
        job = sa.run(self.d / "bail.docx", "français", "anglais")
        self.assertEqual(job.state["status"], "a_relire")
        self.assertTrue((job.dir / "review.md").exists())
        job = sa.certify(job.state["id"], "Relecteur", demo=True)
        self.assertEqual(job.state["status"], "certifie_essai")
        v = sa.verify(job.state["id"])
        self.assertTrue(v["ok"], v)
        m = sa.dossier(job.state["id"], "MA", "FR", "contrat")
        self.assertEqual(m["status"], "essai")             # a specimen dossier is never submittable
        self.assertEqual(apostille.verify_dossier(job.dir / "dossier", sa.ledger), [])
        with self.assertRaises(ValueError):
            apostille.register_apostille(job.dir / "dossier", self.d / "bail.docx")

    def test_certify_requires_reviewer(self):
        sa = self.agent([stub_chat])
        job = sa.run(self.d / "bail.docx", "français", "anglais")
        with self.assertRaises(JobError):
            sa.certify(job.state["id"], "  ", demo=True)

    def test_tampering_is_detected(self):
        sa = self.agent([stub_chat])
        job = sa.run(self.d / "bail.docx", "français", "anglais")
        sa.certify(job.state["id"], "R", demo=True)
        (job.dir / "certified" / "translation.docx").write_bytes(b"altered")
        v = sa.verify(job.state["id"])
        self.assertFalse(v["ok"])
        self.assertFalse(v["checks"]["docx_unchanged"])

    def test_inconclusive_is_never_a_success(self):
        def bad(messages, system):  # drops the numbers on every call, whatever the mode
            return stub_chat(messages, system).replace("2024/118", "").replace("1 500", "")
        sa = self.agent([bad], max_rounds=3)
        job = sa.run(self.d / "bail.docx", "français", "anglais")
        self.assertEqual(job.state["status"], "non_concluant")
        self.assertTrue(job.state["issues"])
        self.assertEqual(len(job.state["rounds"]), 3)       # the whole ladder was tried
        with self.assertRaises(JobError):
            sa.certify(job.state["id"], "R", demo=True)
        job = sa.certify(job.state["id"], "R", demo=True, accept_issues="relu à la main")
        self.assertTrue(json.loads((job.dir / "certified" / "evidence.json").read_text())["remaining_issues"])

    def test_escalates_to_the_next_provider(self):
        def down(messages, system):
            raise RuntimeError("429 rate limit")
        sa = self.agent([down, stub_chat], max_rounds=4)
        job = sa.run(self.d / "bail.docx", "français", "anglais")
        self.assertEqual(job.state["status"], "a_relire")
        self.assertGreater(len(job.state["rounds"]), 1)

    def test_rerun_resumes_and_uses_memory(self):
        calls = {"n": 0}

        def counting(messages, system):
            calls["n"] += 1
            return stub_chat(messages, system)
        from aminos.tm import TranslationMemory
        tm = TranslationMemory(str(self.d / "tm.sqlite"))
        sa = self.agent([counting], tm=tm)
        sa.run(self.d / "bail.docx", "français", "anglais")
        first = calls["n"]
        sa.run(self.d / "bail.docx", "français", "anglais")
        self.assertEqual(calls["n"], first)                 # second run: everything comes from the memory / partial file

    # ---- stamp / apostille --------------------------------------
    def test_arabic_certificate(self):
        if not stamp.find_font(True):
            self.skipTest("no Arabic-capable font")
        pdf, box = stamp.build_certificate_pdf(
            self.d / "c.pdf", doc_name="x.docx", src_lang="arabe", tgt_lang="arabe", sha_src="a" * 64, sha_tr="b" * 64,
            translator={"name": "T", "capacity": "", "registration": "", "place": "Rabat"}, reviewed_by="R",
            date="2026-11-02", cert_lang="ar")
        text = pypdf.PdfReader(str(pdf)).pages[0].extract_text()
        self.assertIn("2026", text)
        self.assertEqual(len(box), 4)

    def test_checklist_is_honest(self):
        steps = " ".join(apostille.checklist("MA", "FR", "contrat"))
        self.assertIn("HCCH", steps)
        self.assertIn("ne la vérifie pas", steps)
        self.assertIn("à vérifier", apostille.hague_status("ZZ"))

    def test_dossier_blockers(self):
        f = self.d / "a.txt"
        f.write_text("x")
        m = apostille.build_dossier(self.d / "dos", [("original", f)], origin="MA", destination="FR")
        self.assertEqual(m["status"], "incomplet")
        self.assertIn("traduction manquante", m["blockers"])
        with self.assertRaises(ValueError):
            apostille.build_dossier(self.d / "dos2", [("bogus", f)], origin="MA", destination="FR")


if __name__ == "__main__":
    unittest.main()
