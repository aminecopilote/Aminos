"""Open a translation memory backend by name."""
from __future__ import annotations


def open_memory(path, backend: str = "sqlite", embedding: str = "hash"):
    if backend == "chroma":
        from .chroma_memory import SemanticMemory
        return SemanticMemory(path, embedding)
    if backend == "sqlite":
        from .tm import TranslationMemory
        return TranslationMemory(path)
    raise ValueError("backend must be 'sqlite' or 'chroma'")
