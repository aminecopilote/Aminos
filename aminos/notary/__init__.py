"""Local notarisation test bench: SHA-256 fingerprint, hash-chained ledger, test PKI, CMS/PAdES seals.

Nothing in this package touches the network. It proves integrity and existence-of-a-record on this
machine only. It is NOT a Hague apostille and NOT a qualified (eIDAS) signature: the test CA is
self-made. Use fictitious documents, never client files or real keys.
"""
from .hashing import sha256_file, sha256_bytes
from .ledger import Ledger, LedgerError

__all__ = ["sha256_file", "sha256_bytes", "Ledger", "LedgerError"]
