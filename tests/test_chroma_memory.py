import tempfile
import unittest

from aminos.glossary import Glossary, Term
from aminos.tm import TranslationMemory

try:
    from aminos.chroma_memory import SemanticMemory
except ImportError:  # chromadb not installed
    SemanticMemory = None

LONG = " ".join(["La société requérante a produit les pièces justificatives de sa demande"] * 6)


class NumberGuardTests(unittest.TestCase):
    def test_sqlite_tm_never_reuses_translation_with_other_year(self):
        tm = TranslationMemory()
        tm.add(LONG + " Jugement du 12 mai 2024.", "trad", "fr", "ar")
        hit = tm.lookup(LONG + " Jugement du 12 mai 2023.", "fr", "ar", 0.5)[0]
        self.assertLess(hit.score, 0.98)  # below the reuse threshold: shown as a hint only


@unittest.skipIf(SemanticMemory is None, "chromadb not installed")
class ChromaTests(unittest.TestCase):
    def test_exact_fuzzy_number_guard_and_language_isolation(self):
        m = SemanticMemory()
        m.add("صدر الحكم بتاريخ 2024 عن المحكمة الابتدائية بالرباط", "Jugement rendu en 2024", "ar", "fr")
        self.assertEqual(m.lookup("صدر الحكم بتاريخ 2024 عن المحكمة الابتدائية بالرباط", "ar", "fr")[0].score, 1.0)
        other_year = m.lookup("صدر الحكم بتاريخ 2023 عن المحكمة الابتدائية بالرباط", "ar", "fr", 0.5)[0]
        self.assertLessEqual(other_year.score, 0.90)
        self.assertEqual(m.lookup("صدر الحكم بتاريخ 2024 عن المحكمة الابتدائية بالرباط", "ar", "en", 0.1), [])

    def test_instances_are_isolated_and_empty_is_safe(self):
        a, b = SemanticMemory(), SemanticMemory()
        a.add("نص", "texte", "ar", "fr")
        self.assertEqual((len(a), len(b)), (1, 0))
        self.assertEqual(b.lookup("نص", "ar", "fr"), [])

    def test_persistence_and_upsert(self):
        with tempfile.TemporaryDirectory() as d:
            m = SemanticMemory(d)
            m.add("الحكم", "jugement", "ar", "fr")
            m.add("الحكم", "décision", "ar", "fr")  # same source: replaced, not duplicated
            del m
            m2 = SemanticMemory(d)
            self.assertEqual(len(m2), 1)
            self.assertEqual(m2.lookup("الحكم", "ar", "fr")[0].target, "décision")

    def test_document_pipeline_with_chroma(self):
        from aminos.pipeline import translate_document
        m = SemanticMemory()
        calls = []

        def chat(messages, system):
            calls.append(1)
            return "le tribunal"
        translate_document(chat, ["المحكمة"], "ar", "fr", mode="fast", tm=m)
        translate_document(chat, ["المحكمة"], "ar", "fr", mode="fast", tm=m)
        self.assertEqual(len(calls), 1)  # second run served from memory

    def test_semantic_glossary(self):
        m = SemanticMemory()
        g = Glossary()
        g.add(Term("المحكمة الابتدائية", "tribunal de première instance"))
        g.add(Term("الاستئناف", "appel"))
        self.assertEqual(m.index_glossary(g), 2)
        found = m.similar_terms("المحاكم الابتدائية")
        self.assertEqual(found[0][0].target, "tribunal de première instance")


if __name__ == "__main__":
    unittest.main()
