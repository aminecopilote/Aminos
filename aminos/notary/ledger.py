"""Append-only, hash-chained ledger (JSON lines). Each entry commits to the previous one, so editing,
deleting or reordering any past entry breaks verification. `head()` is the value to publish or
anchor elsewhere (e-mail to a third party, public timestamp, blockchain) when stronger proof of date
is needed: the ledger alone only proves ordering, not wall-clock time."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

GENESIS = "0" * 64


class LedgerError(Exception):
    pass


def _entry_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def head(self) -> str:
        e = self.entries()
        return e[-1]["hash"] if e else GENESIS

    def append(self, sha256: str, label: str = "", extra: dict | None = None, now: float | None = None) -> dict:
        self.verify()  # never extend a broken chain
        entries = self.entries()
        body = {"seq": len(entries) + 1, "ts": int(now if now is not None else time.time()), "sha256": sha256,
                "label": label, "extra": extra or {}, "prev": self.head()}
        entry = {**body, "hash": _entry_hash(body)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return entry

    def verify(self) -> int:
        """Return the number of valid entries or raise LedgerError naming the first broken one."""
        prev = GENESIS
        for i, e in enumerate(self.entries(), 1):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("seq") != i:
                raise LedgerError(f"entry {i}: sequence number {e.get('seq')} (entry removed or reordered)")
            if e.get("prev") != prev:
                raise LedgerError(f"entry {i}: broken link to the previous entry")
            if _entry_hash(body) != e.get("hash"):
                raise LedgerError(f"entry {i}: content modified")
            prev = e["hash"]
        return i if (i := len(self.entries())) else 0

    def find(self, sha256: str) -> list[dict]:
        return [e for e in self.entries() if e["sha256"] == sha256]
