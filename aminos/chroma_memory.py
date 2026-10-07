"""Semantic memory on ChromaDB: fuzzy translation memory and semantic glossary lookup.

Embeddings
  hash          local character n-gram hashing: deterministic, offline, no model download (default)
  multilingual  sentence-transformers paraphrase-multilingual-MiniLM-L12-v2 (better paraphrase recall;
                downloads a model on first use, needs `pip install sentence-transformers`)

Safety: a match whose numbers/dates differ from the query is never reported above FUZZY_CAP, so it
can be shown as a hint but never silently reused as a translation.
"""
from __future__ import annotations

import hashlib
import math
import uuid
from pathlib import Path

from .checks import numbers
from .glossary import Glossary, Term
from .normalize import normalize
from .tm import Match

FUZZY_CAP = 0.90
_DIM = 512


class HashingEmbedding:
    """chromadb EmbeddingFunction: signed hashing of character 2-4-grams over normalised text."""

    def __init__(self, dim: int = _DIM):
        self.dim = dim

    @staticmethod
    def name() -> str:
        return "aminos-hash"

    def get_config(self) -> dict:
        return {"dim": self.dim}

    @staticmethod
    def build_from_config(config: dict) -> "HashingEmbedding":
        return HashingEmbedding(config.get("dim", _DIM))

    def is_legacy(self) -> bool:
        return False

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    def embed_query(self, input):
        return self(input)

    def __call__(self, input):
        out = []
        for text in input:
            vec = [0.0] * self.dim
            t = f" {normalize(text)} "
            for n in (2, 3, 4):
                for i in range(len(t) - n + 1):
                    h = int.from_bytes(hashlib.blake2b(t[i:i + n].encode(), digest_size=8).digest(), "big")
                    vec[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


def _embedding(kind: str):
    if kind == "hash":
        return HashingEmbedding()
    if kind == "multilingual":
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        return SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    raise ValueError("embedding must be 'hash' or 'multilingual'")


class SemanticMemory:
    """Same interface as tm.TranslationMemory (add / lookup / __len__), backed by Chroma."""

    def __init__(self, path: str | Path | None = None, embedding: str = "hash"):
        import chromadb
        # In-memory clients share one process-wide store: give each instance its own collections.
        suffix = "" if path else "_" + uuid.uuid4().hex[:12]
        self.client = chromadb.PersistentClient(path=str(path)) if path else chromadb.EphemeralClient()
        ef = _embedding(embedding)
        meta = {"hnsw:space": "cosine"}
        self.tm = self.client.get_or_create_collection("aminos_tm" + suffix, embedding_function=ef, metadata=meta)
        self.terms = self.client.get_or_create_collection("aminos_terms" + suffix, embedding_function=ef, metadata=meta)

    def __len__(self) -> int:
        return self.tm.count()

    # ---- translation memory -------------------------------------------------
    @staticmethod
    def _id(source: str, src_lang: str, tgt_lang: str) -> str:
        return hashlib.sha256(f"{src_lang}|{tgt_lang}|{normalize(source)}".encode()).hexdigest()

    def add(self, source: str, target: str, src_lang: str, tgt_lang: str) -> None:
        if source.strip() and target.strip():
            self.tm.upsert(ids=[self._id(source, src_lang, tgt_lang)], documents=[source],
                           metadatas=[{"target": target, "src_lang": src_lang, "tgt_lang": tgt_lang}])

    def lookup(self, source: str, src_lang: str, tgt_lang: str, threshold: float = 0.75, limit: int = 3) -> list[Match]:
        if not len(self):
            return []
        res = self.tm.query(query_texts=[source], n_results=min(limit * 3, len(self)),
                            where={"$and": [{"src_lang": src_lang}, {"tgt_lang": tgt_lang}]})
        wanted = numbers(source)
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            score = max(0.0, 1.0 - dist)
            if normalize(doc) == normalize(source):
                score = 1.0
            elif numbers(doc) != wanted:
                score = min(score, FUZZY_CAP)  # different figures/dates: a hint, never a reusable translation
            else:
                score = min(score, 0.999)      # only an identical text counts as 100 %
            if score >= threshold:
                out.append(Match(doc, meta["target"], score))
        return sorted(out, key=lambda m: -m.score)[:limit]

    def export_tsv(self, path: str) -> None:
        rows = self.tm.get(include=["documents", "metadatas"])
        with open(path, "w", encoding="utf-8") as f:
            for doc, meta in zip(rows["documents"], rows["metadatas"]):
                f.write(f"{doc.replace(chr(9), ' ')}\t{meta['target'].replace(chr(9), ' ')}\n")

    def import_tsv(self, path: str, src_lang: str, tgt_lang: str) -> int:
        n = 0
        for line in open(path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                self.add(parts[0], parts[1], src_lang, tgt_lang)
                n += 1
        return n

    # ---- semantic glossary ------------------------------------------------------
    def index_glossary(self, glossary: Glossary) -> int:
        terms = list(glossary.terms.values())
        for i in range(0, len(terms), 500):
            batch = terms[i:i + 500]
            self.terms.upsert(ids=[t.key() for t in batch], documents=[t.source for t in batch],
                              metadatas=[{"target": t.target, "domain": t.domain, "note": t.note,
                                          "origin": t.origin} for t in batch])
        return len(terms)

    def similar_terms(self, text: str, limit: int = 5, threshold: float = 0.6) -> list[tuple[Term, float]]:
        """Glossary entries close to `text` (e.g. inflected or misspelled forms the exact matcher misses)."""
        n = self.terms.count()
        if not n:
            return []
        res = self.terms.query(query_texts=[text], n_results=min(limit, n))
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            if 1.0 - dist >= threshold:
                out.append((Term(doc, meta["target"], meta.get("domain", ""), meta.get("note", ""),
                                 meta.get("origin", "")), 1.0 - dist))
        return out
