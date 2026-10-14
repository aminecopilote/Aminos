import unittest
from pathlib import Path

from aminos.corpus import import_moses, import_tmx, iter_tbx, iter_tmx, lang_code, tbx_to_glossary
from aminos.tm import TranslationMemory

FX = Path(__file__).parent / "fixtures"


class MigrationTests(unittest.TestCase):
    def test_old_schema_memory_is_upgraded_and_searchable(self):
        import sqlite3, tempfile
        path = str(Path(tempfile.mkdtemp()) / "old.sqlite")
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE tm (norm TEXT, src_lang TEXT, tgt_lang TEXT, source TEXT, target TEXT, "
                   "PRIMARY KEY (norm, src_lang, tgt_lang))")
        db.execute("INSERT INTO tm VALUES ('le tribunal decide', 'fr', 'ar', 'Le tribunal décide', 'تقرر المحكمة')")
        db.commit(); db.close()
        tm = TranslationMemory(path)
        self.assertEqual(len(tm), 1)
        self.assertEqual(tm.lookup("Le tribunal décide", "fr", "ar")[0].score, 1.0)
        self.assertEqual(tm.lookup("Le tribunal décide aujourd'hui", "fr", "ar", threshold=0.7)[0].target, "تقرر المحكمة")
        tm.add("Autre phrase", "جملة أخرى", "fr", "ar")  # new inserts work after migration
        self.assertEqual(len(TranslationMemory(path)), 2)  # and persist, reopening is idempotent


class CorpusTests(unittest.TestCase):
    def test_lang_code(self):
        self.assertEqual([lang_code(x) for x in ("FR-FR", "nl_BE", "ar", "EN-GB")], ["fr", "nl", "ar", "en"])

    def test_tmx_units_and_inline_markup(self):
        units = list(iter_tmx(FX / "sample.tmx"))
        self.assertEqual(len(units), 2)  # single-language and de/es units are dropped
        self.assertEqual(set(units[0]), {"en", "fr", "nl", "ar"})
        self.assertEqual(units[1]["en"], "Article 5 enters into force on 1 January 2026.")

    def test_tmx_import_both_directions_all_pairs(self):
        tm = TranslationMemory()
        n = tm.add_many([])  # empty batch is harmless
        self.assertEqual(n, 0)
        n = import_tmx(tm, FX / "sample.tmx")
        self.assertEqual(n, 12 + 2)  # 4 languages -> 12 ordered pairs, plus en<->fr
        self.assertEqual(tm.lookup("Le tribunal entend les parties.", "fr", "ar")[0].target, "تستمع المحكمة إلى الأطراف.")
        self.assertEqual(tm.lookup("DE RECHTBANK hoort de partijen.", "nl", "en")[0].score, 1.0)  # case-insensitive exact
        self.assertGreaterEqual(tm.lookup("de rechtbank hoort de partijen", "nl", "en")[0].score, 0.98)  # no final dot

    def test_tmx_restricted_pairs(self):
        tm = TranslationMemory()
        import_tmx(tm, FX / "sample.tmx", pairs=[("en", "fr")])
        self.assertEqual(tm.stats(), {"en>fr": 2})

    def test_fuzzy_lookup_uses_index(self):
        tm = TranslationMemory()
        import_tmx(tm, FX / "sample.tmx", pairs=[("en", "nl")])
        hit = tm.lookup("The court shall hear all the parties.", "en", "nl", threshold=0.8)
        self.assertEqual(hit[0].target, "De rechtbank hoort de partijen.")
        self.assertLess(hit[0].score, 1.0)
        self.assertEqual(tm.lookup("completely unrelated sentence about bananas", "en", "nl"), [])

    def test_moses_skips_empty_pairs(self):
        tm = TranslationMemory()
        n = import_moses(tm, FX / "un.en", FX / "un.fr", "en", "fr")
        self.assertEqual(n, 3 * 2)  # the empty English line is skipped; 3 pairs, both directions
        self.assertEqual(tm.lookup("The Security Council decides.", "en", "fr")[0].target, "Le Conseil de sécurité décide.")

    def test_tbx_entries_and_glossary(self):
        entries = list(iter_tbx(FX / "sample.tbx"))
        self.assertEqual(len(entries), 2)  # both entries have at least two languages
        self.assertEqual(entries[0]["domain"], "Law")
        self.assertEqual(entries[0]["terms"]["ar"], ["حكم"])
        g = tbx_to_glossary(FX / "sample.tbx", "en", "fr")
        self.assertEqual(len(g), 2)  # judgment, ruling
        self.assertEqual(g.terms["judgment"].target, "jugement / arrêt")
        self.assertEqual(g.find("The judgment is final.")[0].target, "jugement / arrêt")
        self.assertEqual(len(tbx_to_glossary(FX / "sample.tbx", "ar", "nl")), 1)


if __name__ == "__main__":
    unittest.main()
