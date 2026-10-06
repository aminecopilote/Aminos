import json
import tempfile
import unittest
from pathlib import Path

from aminos import checks
from aminos.glossary import Glossary, Term, import_path
from aminos.normalize import normalize, tokens
from aminos.pipeline import split_segments, translate_chunk, chunk_paragraphs


def make_gloss():
    g = Glossary()
    g.add(Term("المحكمة الابتدائية", "tribunal de première instance"))
    g.add(Term("الحكم", "jugement"))
    g.add(Term("الدعوى", "action en justice / instance"))
    return g


class NormalizeTests(unittest.TestCase):
    def test_arabic_variants(self):
        self.assertEqual(normalize("أَحْكَامٌ"), normalize("احكام"))
        self.assertEqual(normalize("المادة ١٢"), "الماده 12")

    def test_prefix_stripping(self):
        self.assertEqual(tokens("بالمحكمة"), tokens("المحكمة"))


class GlossaryTests(unittest.TestCase):
    def test_find_longest_and_prefixed(self):
        found = {t.target for t in make_gloss().find("صدر الحكم عن المحكمة الابتدائية بالرباط")}
        self.assertEqual(found, {"jugement", "tribunal de première instance"})

    def test_missing_in_accepts_variants_and_accents(self):
        g = make_gloss()
        self.assertEqual(g.missing_in("الدعوى", "L'instance est close"), [])
        self.assertEqual([t.source for t in g.missing_in("الحكم", "la décision")], ["الحكم"])
        self.assertEqual(g.missing_in("الحكم", "Le JUGEMENT"), [])

    def test_conflict_reported_first_wins(self):
        g = Glossary()
        g.add(Term("الحكم", "jugement"))
        g.add(Term("الحكم", "sentence"))
        self.assertEqual(len(g), 1)
        self.assertEqual(len(g.conflicts), 1)

    def test_import_formats_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.csv").write_text("مصطلح,ترجمة\nالحكم,jugement\n", encoding="utf-8")
            (d / "b.txt").write_text("المحكمة = tribunal\nالدعوى\tinstance\n", encoding="utf-8")
            (d / "c.json").write_text(json.dumps({"الطعن": "pourvoi"}), encoding="utf-8")
            (d / "d.tsv").write_text("المتهم\tprévenu\tpénal\tnote\n", encoding="utf-8")
            g = import_path(d)
            self.assertEqual(len(g), 5)
            self.assertEqual(g.terms[normalize("المتهم")].domain, "pénal")
            g.save(d / "out.json")
            self.assertEqual(len(Glossary.load(d / "out.json")), 5)


class ChecksTests(unittest.TestCase):
    def test_numbers(self):
        r = checks.compare("المادة ١٢ بتاريخ 2024", "Article 12 du 2023")
        self.assertEqual(r.missing_numbers, ["2024"])
        self.assertEqual(r.extra_numbers, ["2023"])
        self.assertTrue(checks.compare("Art. 5", "المادة ٥").ok)


class PipelineTests(unittest.TestCase):
    def fake(self, replies):
        calls = []
        it = iter(replies)

        def chat(messages, system):
            calls.append((list(messages), system))
            return next(it)
        chat.calls = calls
        return chat

    def test_split_segments_pads_and_truncates(self):
        self.assertEqual(split_segments("a §§§ b", 3), ["a", "b", ""])
        self.assertEqual(split_segments("a §§§ b §§§ c", 2), ["a", "b"])

    def test_chunking(self):
        self.assertEqual(chunk_paragraphs(["aaa", "bbb", "ccc"], 5), [["aaa"], ["bbb"], ["ccc"]])

    def test_normal_corrects_when_glossary_violated(self):
        chat = self.fake(["la décision", "le jugement"])
        r = translate_chunk(chat, ["الحكم"], "arabe", "français", make_gloss(), "normal")
        self.assertEqual(r.translations, ["le jugement"])
        self.assertEqual(r.passes, 2)
        self.assertEqual(r.issues, [])
        self.assertIn("الحكم => jugement", chat.calls[0][1])

    def test_normal_single_pass_when_clean(self):
        chat = self.fake(["le jugement"])
        r = translate_chunk(chat, ["الحكم"], "arabe", "français", make_gloss(), "normal")
        self.assertEqual(r.passes, 1)
        self.assertEqual(len(chat.calls), 1)

    def test_hard_runs_back_translation_and_compare(self):
        chat = self.fake(["le jugement", "الحكم", "RAS"])
        r = translate_chunk(chat, ["الحكم"], "arabe", "français", make_gloss(), "hard")
        self.assertEqual(len(chat.calls), 3)
        self.assertEqual(r.passes, 1)

    def test_fast_never_corrects(self):
        chat = self.fake(["la décision"])
        r = translate_chunk(chat, ["الحكم"], "arabe", "français", make_gloss(), "fast")
        self.assertEqual(r.passes, 1)
        self.assertTrue(r.issues)


if __name__ == "__main__":
    unittest.main()
